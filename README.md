# Acdyon Scraper Demo

This assumes you've never deployed a Python web app before. Follow in order.

## Part A — Get it running on your own laptop

### 1. Install Python (skip if you already have it)
- Go to https://www.python.org/downloads/ and install Python 3.11 or newer.
- Check it worked: open a terminal (Command Prompt / Terminal / PowerShell) and type:
  ```
  python --version
  ```
  If that fails, try `python3 --version`.

### 2. Put these files in a folder
- Create a folder on your computer, e.g. `acdyon-scraper`.
- Put `main.py`, `requirements.txt`, and this `README.md` inside it.

### 3. Open a terminal INSIDE that folder
- Windows: open the folder in File Explorer, click the address bar, type `cmd`, hit Enter.
- Mac/Linux: right-click the folder → "Open in Terminal" (or `cd` into it manually).

### 4. Create a virtual environment (keeps this project's packages separate)
```
python -m venv venv
```
Activate it:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

You'll see `(venv)` appear at the start of your terminal line — that means it worked.

### 5. Install the dependencies
```
pip install -r requirements.txt
```

### 6. Run the app
```
uvicorn main:app --reload
```
You should see something like `Uvicorn running on http://127.0.0.1:8000`.

### 7. Test it in your browser
Open these URLs one by one:
- `http://127.0.0.1:8000/` → should show a welcome message
- `http://127.0.0.1:8000/scrape` → triggers a real pull from Remotive's job API, stores results in a local file called `jobs.db`
- `http://127.0.0.1:8000/listings` → shows the jobs you just pulled
- `http://127.0.0.1:8000/status` → shows run history, failures, circuit-breaker state

If `/scrape` returns real job listings and `/listings` shows them — **it works.**

---

## Part B — Put it on GitHub (they ask for a repo link)

1. Make a free account at https://github.com if you don't have one.
2. Click the "+" in the top right → "New repository". Name it `acdyon-scraper`. Keep it Public. Don't add a README (you already have one).
3. Back in your terminal (inside the project folder), run:
   ```
   git init
   git add .
   git commit -m "Initial scraper demo"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/acdyon-scraper.git
   git push -u origin main
   ```
   (Replace `YOUR-USERNAME` with your actual GitHub username. If `git` isn't installed, get it from https://git-scm.com/downloads first.)
4. Add a `.gitignore` file (see below) BEFORE committing, so you don't upload your virtual environment folder.

Create a file named `.gitignore` with this content:
```
venv/
__pycache__/
jobs.db
```

---

## Part C — Deploy it live (they ask for a deployed URL)

Using **Render** (free, simplest option):

1. Go to https://render.com and sign up (you can sign in with GitHub — do that, it's faster).
2. Click "New +" → "Web Service".
3. Connect your GitHub account, then select the `acdyon-scraper` repo you just pushed.
4. Fill in:
   - **Name**: acdyon-scraper (or anything)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Choose the **Free** instance type.
6. Click "Create Web Service". Wait 2-5 minutes while it builds.
7. Once live, Render gives you a URL like `https://acdyon-scraper.onrender.com`.
8. Test the same way as before: visit `https://acdyon-scraper.onrender.com/scrape`, then `/listings`, then `/status`.

**Note:** Render's free tier "sleeps" after inactivity — the first request after sleeping takes ~30-60 seconds to wake up. That's normal, not a bug. Mention this in your DECISIONS.md if asked about limitations.

---

## Part D — What to actually submit

1. **Deployed URL** — your Render URL from Part C.
2. **GitHub repo link** — your repo from Part B.
3. **Design document** — see `DESIGN.md` (already drafted for you, fill in your own words).
4. **DECISIONS.md** — see `DECISIONS.md` (template provided, answer honestly).

Submit all of it through the Google Form linked in the assessment PDF.

---

## Part E — Before the follow-up call

Read through `main.py` line by line until you can explain, out loud, without looking:
- Why the User-Agent rotation exists
- What the circuit breaker does and why 3 failures triggers it
- Why there's a `time.sleep()` with random jitter instead of a fixed delay
- Why parsing failures don't crash the whole `/scrape` call

If any of those don't make sense yet, ask me and I'll explain that specific part before you submit.