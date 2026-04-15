from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import io, os, re, random, tempfile
import spacy
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from courses import (
    ds_course, web_course, android_course, ios_course, uiux_course,
    resume_videos, interview_videos
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with io.BytesIO(file_bytes) as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
        text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    return text


def get_page_count(file_bytes: bytes) -> int:
    count = 0
    with io.BytesIO(file_bytes) as fh:
        for _ in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            count += 1
    return count


def extract_email(text: str):
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else None


def extract_phone(text: str):
    match = re.search(
        r'(\+?\d{1,3}[\s\-]?)?(\(?\d{3}\)?[\s\-]?)[\d\s\-]{7,10}', text
    )
    return match.group(0).strip() if match else None


def extract_name_simple(text: str):
    """Grab first non-blank line as a candidate name."""
    for line in text.split('\n'):
        line = line.strip()
        if line and len(line.split()) <= 5 and not re.search(r'@|http|www', line):
            return line
    return "Candidate"


SKILL_KEYWORDS = [
    'python','java','javascript','typescript','c++','c#','ruby','go','rust','swift',
    'kotlin','php','r','matlab','scala','html','css','react','angular','vue',
    'node','django','flask','fastapi','spring','laravel','tensorflow','pytorch',
    'keras','scikit-learn','pandas','numpy','sql','mysql','postgresql','mongodb',
    'redis','docker','kubernetes','git','aws','azure','gcp','linux','bash',
    'android','flutter','ios','xcode','figma','adobe xd','photoshop','illustrator',
    'machine learning','deep learning','nlp','data science','data analysis',
    'excel','powerpoint','tableau','power bi','hadoop','spark','kafka',
]

def extract_skills(text: str):
    text_lower = text.lower()
    found = [s for s in SKILL_KEYWORDS if re.search(r'\b' + re.escape(s) + r'\b', text_lower)]
    return list(dict.fromkeys(found))   # dedupe, preserve order


def detect_level(text: str) -> str:
    t = text.upper()
    if 'EXPERIENCE' in t or 'WORK EXPERIENCE' in t:
        return 'Experienced'
    if 'INTERNSHIP' in t or 'INTERNSHIPS' in t:
        return 'Intermediate'
    return 'Fresher'


DS_KW  = {'tensorflow','keras','pytorch','machine learning','deep learning','flask','streamlit','data science','nlp','scikit-learn','data analysis'}
WEB_KW = {'react','django','node','javascript','angular','vue','php','laravel','flask','html','css','typescript'}
AND_KW = {'android','flutter','kotlin','xml','kivy','java'}
IOS_KW = {'ios','swift','cocoa','xcode','objective-c'}
UX_KW  = {'ux','figma','adobe xd','zeplin','balsamiq','ui','prototyping','wireframes','photoshop','illustrator'}

def predict_field(skills):
    s = set(sk.lower() for sk in skills)
    scores = {
        'Data Science':        len(s & DS_KW),
        'Web Development':     len(s & WEB_KW),
        'Android Development': len(s & AND_KW),
        'IOS Development':     len(s & IOS_KW),
        'UI-UX Development':   len(s & UX_KW),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'General'


FIELD_RECO = {
    'Data Science':        ['Data Visualization','Predictive Analysis','Statistical Modeling','Data Mining',
                            'ML Algorithms','Keras','Pytorch','Scikit-learn','Tensorflow','Flask','Streamlit'],
    'Web Development':     ['React','Django','Node JS','React JS','PHP','Laravel','JavaScript','Angular JS','Flask','SDK'],
    'Android Development': ['Android','Flutter','Kotlin','XML','Java','Kivy','GIT','SDK','SQLite'],
    'IOS Development':     ['IOS','Swift','Cocoa','Xcode','Objective-C','SQLite','StoreKit','UI-Kit','Auto-Layout'],
    'UI-UX Development':   ['UI','Figma','Adobe XD','Zeplin','Prototyping','Wireframes','Illustrator',
                            'After Effects','Photoshop','User Research'],
    'General':             ['Communication','Problem Solving','Microsoft Office','Leadership','Project Management'],
}

FIELD_COURSES = {
    'Data Science': ds_course,
    'Web Development': web_course,
    'Android Development': android_course,
    'IOS Development': ios_course,
    'UI-UX Development': uiux_course,
    'General': web_course,
}


def score_resume(text: str) -> tuple[int, list]:
    tips = []
    score = 0

    checks = [
        (['Objective','Summary'],         6,  'Objective/Summary'),
        (['Education','School','College'], 12, 'Education Details'),
        (['Experience','EXPERIENCE'],      16, 'Work Experience'),
        (['Internship','INTERNSHIP'],      6,  'Internships'),
        (['Skill','SKILL'],                7,  'Skills Section'),
        (['Hobbies','HOBBIES'],            4,  'Hobbies'),
        (['Interests','INTERESTS'],        5,  'Interests'),
        (['Achievement','ACHIEVEMENT'],    13, 'Achievements'),
        (['Certification','CERTIFICATION'],12, 'Certifications'),
        (['Project','PROJECT'],            19, 'Projects'),
    ]

    for keywords, pts, label in checks:
        found = any(kw in text for kw in keywords)
        if found:
            score += pts
            tips.append({'present': True,  'label': label, 'points': pts})
        else:
            tips.append({'present': False, 'label': label, 'points': pts})

    return score, tips


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/analyze")
async def analyze_resume(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()

    try:
        resume_text = extract_text_from_pdf(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {e}")

    pages      = get_page_count(content)
    email      = extract_email(resume_text)
    phone      = extract_phone(resume_text)
    name       = extract_name_simple(resume_text)
    skills     = extract_skills(resume_text)
    level      = detect_level(resume_text)
    field      = predict_field(skills)
    reco_skills= FIELD_RECO.get(field, [])
    courses_raw= FIELD_COURSES.get(field, web_course)
    random.shuffle(courses_raw)
    courses    = [{'name': c[0], 'url': c[1]} for c in courses_raw[:8]]
    score, tips= score_resume(resume_text)
    res_vid    = random.choice(resume_videos)
    int_vid    = random.choice(interview_videos)

    return {
        'name':              name,
        'email':             email,
        'phone':             phone,
        'pages':             pages,
        'skills':            skills,
        'level':             level,
        'predicted_field':   field,
        'recommended_skills':reco_skills,
        'courses':           courses,
        'resume_score':      score,
        'score_tips':        tips,
        'resume_video':      res_vid,
        'interview_video':   int_vid,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
