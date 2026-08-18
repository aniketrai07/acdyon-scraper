# DECISIONS.md

## 1. Why this ingestion strategy over the obvious alternative I rejected?

[Example: "The obvious alternative was a full headless-browser approach (Playwright/Selenium)
for every request, which more closely mimics a real user. I rejected that as the default
for this demo because it's slower, heavier to deploy on a free tier, and only actually
necessary against sites with strong JS-rendering + fingerprinting defenses. Instead I used
lightweight HTTP requests with rotation/backoff/circuit-breaking, and would reserve headless
browsing for sources that specifically require it — using the cheaper method first and
escalating only when needed."]

## 2. One trade-off I made under the time limit, and what I'd do with a real week.

[Example: "I skipped proxy rotation entirely and used a single IP (Render's). With a real
week I'd add a small residential/rotating-proxy pool and tie proxy selection into the
circuit breaker, so a blocked IP gets swapped out automatically instead of just cooling down
and retrying from the same IP."]

## 3. Where I used AI tools, and what I personally verified or changed afterward.

[Be specific and honest — this is a direct grading axis. Example: "I used AI to scaffold
the initial retry/backoff structure and the FastAPI route layout. I personally rewrote the
jitter calculation after testing showed the original produced too-uniform intervals that
would still look bot-like, and I removed AI-suggested proxy-rotation code entirely because
I couldn't get real proxies to test it against and didn't want to submit code I hadn't
verified worked."]
