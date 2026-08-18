# Design Document — Job Listing Ingestion

> Fill in the bracketed parts with your own words before submitting. This is a
> starting draft based on what the code actually does — read `main.py` first
> so what you write here matches what you can defend on the call.

## 1. Detection surface

What gives an automated client away on sites like LinkedIn/Indeed/Naukri:
- **Browser fingerprinting**: headless Chrome exposes tells like `navigator.webdriver = true`,
  missing plugins list, unusual canvas/WebGL rendering signatures.
- **TLS/JA3 fingerprinting**: the TLS handshake of common HTTP libraries (e.g. Python `requests`)
  looks different from a real browser's, even with a spoofed User-Agent.
- **Timing patterns**: requests fired at perfectly regular intervals (e.g. exactly every 2.000s)
  are a strong bot signal — humans (and good scrapers) are irregular.
- **Missing/inconsistent headers**: a real browser sends a large, consistent header set
  (Accept, Accept-Language, Sec-Fetch-*, Referer). A bare `requests.get()` sends almost none of these.
- **Behavioral patterns**: no mouse movement, no scroll events, sequential/systematic page traversal.
- **IP reputation**: datacenter IPs (like Render's) are flagged far more aggressively than
  residential IPs.

**What this design accounts for**: User-Agent rotation, jittered pacing instead of fixed
intervals, a realistic header set, and session-per-run identity separation.
**What it does NOT account for**: TLS fingerprinting, canvas/WebGL fingerprinting, and
CAPTCHA-solving — these require headless-browser infrastructure (e.g. Playwright with
stealth plugins) and/or residential proxies, which I scoped out for this demo. [Explain
why you scoped this out — time, cost, or the ToS line in section 4.]

## 2. Ingestion strategy

- **Rotation**: User-Agent rotated per session from a small pool; in a production version
  this would extend to proxy rotation (residential proxy pool) and rotating "identities"
  (cookie jars) per source.
- **Pacing**: jittered delay (`delay + random.uniform(0, 0.5)`) instead of a fixed sleep,
  with exponential backoff on 429/403 responses.
- **Session/identity management**: each scrape run gets a fresh `requests.Session()` with
  its own headers, simulating a distinct "visitor."
- **Fallback (Plan B)**: [Describe what you'd actually do — e.g. "if the primary source's
  API changes or starts blocking, fall back to a secondary public job feed (e.g. Remotive →
  Arbeitnow API), and serve the last successfully-cached data to consumers in the meantime
  rather than returning nothing."]

## 3. Resilience

- **Markup/schema changes**: `parse_job()` wraps field extraction in try/except — a failure
  on one field logs the error and skips that record, it doesn't crash the run.
- **Rate limiting**: `fetch_with_retry()` detects 429/403 responses and backs off exponentially
  (1s → 2s → 4s) instead of retrying immediately.
- **Empty/failed responses**: after `max_retries`, the run is logged as `failed` in `run_log`
  rather than silently returning nothing with no trace.
- **Circuit breaker**: after 3 consecutive failures for a source, that source is skipped for
  60 seconds (`circuit_is_open`) instead of continuing to hammer a source that's actively
  blocking us — this is what "keeps the pipeline running instead of silently failing."
  You can see all of this live at the `/status` endpoint.

## 4. Where I'd stop

[Be genuinely reflective here — this is graded on honesty, not on sounding maximally
aggressive or maximally cautious. Example framing:]

"I won't scrape any source that requires authenticated login (i.e., using a personal or
fake account to get past a login wall), and I treat `robots.txt` as a hard technical line
even where it isn't legally binding — if a site's `robots.txt` disallows a path, this
pipeline won't hit it. I also won't attempt to defeat CAPTCHA challenges; if a source
CAPTCHA-walls a request, that's the pipeline's signal to stop and fall back, not a puzzle
to solve. The demo itself only touches Remotive's public, terms-permitting API, and never
touched a real LinkedIn/Indeed/Naukri account, per the assessment's own scope guardrail."
