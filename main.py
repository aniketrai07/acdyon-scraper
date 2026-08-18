"""
Acdyon Technologies - Part 1: Job Listing Ingestion Demo
----------------------------------------------------------
This is a small but REAL ingestion pipeline. It pulls job listings from
Remotive's public API (a legal, no-auth, no-ban-risk source), but it is
architected as if the source were hostile - so you can explain every
anti-detection / resilience concept even though this particular API
doesn't punish you for scraping it.

Run locally:
    pip install -r requirements.txt
    uvicorn main:app --reload

Then open http://127.0.0.1:8000/scrape  in your browser to trigger a pull.
"""

import time
import random
import sqlite3
import logging
from datetime import datetime

from fastapi import FastAPI
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper")

app = FastAPI()

DB_PATH = "jobs.db"

# --- 1. Detection-surface mitigations -------------------------------------
# Real bot-blockers look at: User-Agent, header ordering/consistency,
# request timing regularity, and IP reputation. We simulate rotation +
# jitter here even though Remotive doesn't require it, to demonstrate
# the pattern.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0 Safari/537.36",
]

SOURCES = [
    {"name": "remotive", "url": "https://remotive.com/api/remote-jobs"},
]

# --- 2. Circuit breaker (resilience) ---------------------------------------
# If a source fails repeatedly, stop hammering it instead of retrying
# forever. This is exactly what the brief asks for under "Resilience".
FAILURE_THRESHOLD = 3
COOLDOWN_SECONDS = 60
_circuit_state = {}  # {source_name: {"failures": int, "open_until": float|None}}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            url TEXT,
            source TEXT,
            fetched_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS run_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            status TEXT,
            records_pulled INTEGER,
            error TEXT,
            run_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_session():
    """A fresh 'identity' per run - rotated header set."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def circuit_is_open(source_name):
    state = _circuit_state.get(source_name)
    if not state:
        return False
    return bool(state.get("open_until") and time.time() < state["open_until"])


def record_failure(source_name):
    state = _circuit_state.setdefault(source_name, {"failures": 0, "open_until": None})
    state["failures"] += 1
    if state["failures"] >= FAILURE_THRESHOLD:
        state["open_until"] = time.time() + COOLDOWN_SECONDS
        logger.warning("Circuit opened for %s after %d failures", source_name, state["failures"])


def record_success(source_name):
    _circuit_state[source_name] = {"failures": 0, "open_until": None}


def fetch_with_retry(session, url, max_retries=3):
    """Exponential backoff + jittered pacing - the 'pacing' and
    'fallback when blocked' parts of the ingestion strategy."""
    delay = 1
    for attempt in range(max_retries):
        try:
            time.sleep(delay + random.uniform(0, 0.5))  # jitter, not a fixed sleep
            resp = session.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (429, 403):
                logger.warning("Rate-limited/blocked (%s), backing off", resp.status_code)
                delay *= 2
            else:
                logger.warning("Unexpected status %s", resp.status_code)
                delay *= 2
        except requests.RequestException as e:
            logger.warning("Request failed: %s", e)
            delay *= 2
    return None


def parse_job(raw, source_name):
    """Defensive parsing - one bad field must never kill the whole record."""
    try:
        return {
            "id": str(raw.get("id") or raw.get("url")),
            "title": raw.get("title", "Unknown"),
            "company": raw.get("company_name", "Unknown"),
            "url": raw.get("url", ""),
            "source": source_name,
            "fetched_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error("Failed to parse record: %s", e)
        return None


def save_jobs(jobs):
    conn = sqlite3.connect(DB_PATH)
    for j in jobs:
        if not j:
            continue
        conn.execute("""
            INSERT OR REPLACE INTO jobs (id, title, company, url, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (j["id"], j["title"], j["company"], j["url"], j["source"], j["fetched_at"]))
    conn.commit()
    conn.close()


def log_run(source, status, count, error=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO run_log (source, status, records_pulled, error, run_at)
        VALUES (?, ?, ?, ?, ?)
    """, (source, status, count, error, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def run_scrape(source):
    name, url = source["name"], source["url"]

    if circuit_is_open(name):
        logger.warning("Skipping %s, circuit open (cooling down)", name)
        log_run(name, "skipped_circuit_open", 0)
        return 0

    session = get_session()
    data = fetch_with_retry(session, url)

    if data is None:
        record_failure(name)
        log_run(name, "failed", 0, error="no response after retries")
        return 0

    raw_jobs = data.get("jobs", [])[:50]  # capped for a fast demo
    parsed = [parse_job(j, name) for j in raw_jobs]
    parsed = [p for p in parsed if p]  # drop only the fields that failed, not the run

    save_jobs(parsed)
    record_success(name)
    log_run(name, "success", len(parsed))
    return len(parsed)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Acdyon scraper demo running. Try /scrape, /listings, /status"}


@app.get("/scrape")
def scrape():
    """Triggers one ingestion run across all configured sources."""
    results = {}
    for source in SOURCES:
        results[source["name"]] = run_scrape(source)
    return {"status": "done", "results": results}


@app.get("/listings")
def listings(limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM jobs ORDER BY fetched_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/status")
def status():
    """Proves the pipeline is observable - shows recent runs and failures."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    runs = conn.execute(
        "SELECT * FROM run_log ORDER BY run_at DESC LIMIT 10"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as c FROM jobs").fetchone()
    conn.close()
    return {
        "total_jobs_stored": total["c"],
        "recent_runs": [dict(r) for r in runs],
        "circuit_state": _circuit_state,
    }
