# 🤖 AI Resume Analyzer — Vercel Deployment

## What's included
| File | Purpose |
|------|---------|
| `api/index.py` | FastAPI backend — parses PDF, extracts skills, scores resume |
| `api/courses.py` | Course recommendations data |
| `public/index.html` | Frontend — drag-and-drop UI, results dashboard |
| `vercel.json` | Vercel routing config |
| `requirements.txt` | Python dependencies |

**No database. No MongoDB. No MySQL.** Pure stateless analysis.

---

## 🚀 Deploy to Vercel (Step-by-Step)

### Prerequisites
- A [Vercel account](https://vercel.com/signup) (free)
- [Git](https://git-scm.com/) installed
- [Node.js](https://nodejs.org/) installed (for Vercel CLI)

---

### Step 1 — Install Vercel CLI
```bash
npm install -g vercel
```

### Step 2 — Create a GitHub repo
1. Go to [github.com/new](https://github.com/new)
2. Create a new repo, e.g. `resume-analyzer`
3. Don't initialize with README

### Step 3 — Push this folder to GitHub
```bash
cd resume-analyzer-vercel

git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/resume-analyzer.git
git push -u origin main
```

### Step 4 — Deploy via Vercel CLI
```bash
vercel login       # opens browser, log in with GitHub/email
vercel             # follow prompts:
                   #   Set up and deploy? → Y
                   #   Which scope? → your account
                   #   Link to existing project? → N
                   #   Project name? → resume-analyzer (or anything)
                   #   In which directory? → . (current)
                   #   Override settings? → N
```

Vercel will give you a URL like `https://resume-analyzer-xyz.vercel.app` 🎉

### Step 5 — Deploy updates (any future changes)
```bash
git add .
git commit -m "Update"
git push
# Vercel auto-deploys on every push to main
```

---

### Alternative: Deploy via Vercel Dashboard (no CLI)
1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **"Import Git Repository"**
3. Connect your GitHub and select `resume-analyzer`
4. Leave all settings as default → click **Deploy**

---

## 🔧 Local Development

```bash
# Install Python deps
pip install -r requirements.txt

# Run backend
cd api
uvicorn index:app --reload --port 8000

# Then open public/index.html in a browser
# Change the fetch URL in index.html from '/api/analyze' to 'http://localhost:8000/api/analyze'
```

---

## ⚠️ Important Notes

1. **spaCy model size**: The `en_core_web_sm` model (~12MB) is downloaded during build. Vercel's free tier allows up to 250MB — this fits fine.

2. **Cold starts**: Vercel serverless functions have ~1-3s cold start. First request after idle may be slow.

3. **File size limit**: Vercel limits request body to **4.5MB**. Most resumes are well under this.

4. **No persistent storage**: By design — no user data is saved anywhere.

---

## 🏗️ Project Structure
```
resume-analyzer-vercel/
├── api/
│   ├── index.py        ← FastAPI app (Vercel Python serverless)
│   └── courses.py      ← Course data
├── public/
│   └── index.html      ← Frontend
├── requirements.txt
├── vercel.json
└── README.md
```
