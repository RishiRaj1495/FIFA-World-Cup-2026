# Fan Concierge — Smart Stadium Assistant for FIFA World Cup 2026

A GenAI-enabled multilingual concierge and crowd-intelligence system built for
**Challenge 4: Smart Stadiums & Tournament Operations**. It targets fans and
venue staff during matchday, combining a Claude-powered multilingual chat
assistant with real-time gate crowd status and accessibility guidance.


> `pip install -r requirements.txt`


## Chosen vertical

**Multilingual Fan Assistance + Real-Time Crowd & Accessibility Decision
Support.**

The FIFA World Cup 2026 will draw fans from dozens of countries into a small
number of physical venues in a short window of time. The single hardest
moment of any matchday isn't inside the stadium — it's the 90 minutes before
kickoff, when tens of thousands of people who don't speak the local language,
don't know the venue layout, and may have accessibility needs all converge on
a handful of gates at once. This project treats that moment as the core
problem and builds one cohesive assistant — "Fan Concierge" — around it,
rather than building several disconnected features.

## Approach and logic

Three pieces of GenAI/data logic work together:

1. **Multilingual concierge, GenAI-optional by design.** A fan types a
   question in any supported language. The system is layered in two tiers:
   - **Tier 1 — key-free demo engine (default, always on):** matches intent
     keywords (in the fan's language) against the same structured venue data,
     and returns a grounded, correct answer. Zero external calls, zero setup.
   - **Tier 2 — Claude enhancement (optional, activates automatically if
     `ANTHROPIC_API_KEY` is set):** builds a system prompt that forces Claude
     to reply only in the fan's selected language, grounds it in the same
     structured venue data, and instructs it to say "I don't know, ask a
     steward" for anything outside that data (live scores, ticket refunds,
     etc.) — handling open-ended phrasing Tier 1's keyword matching can't.
     If the Claude call fails for any reason (no key, network issue, rate
     limit), the app **falls back to Tier 1 automatically** rather than
     showing an error. See the design note below for why this two-tier
     structure exists.

2. **Crowd intelligence (decision support).** Each gate has a simulated,
   time-bucketed occupancy reading (stand-in for a real turnstile/camera
   feed). The service buckets occupancy into low/moderate/high/critical,
   estimates a wait time, and computes a recommended gate. This is exposed
   both as a live dashboard and as context the concierge can reason over
   (e.g. "which gate is fastest right now?").

3. **Accessibility-aware routing.** A fan can select an accessibility need
   (wheelchair, low vision, hearing impaired, cognitive/sensory support).
   The system returns the facilities relevant to that need *and* the least
   crowded wheelchair-accessible gate right now — accessibility and crowd
   data are combined, not siloed.

The chat assistant and the two decision-support endpoints share the same
venue dataset, so a fan can ask the concierge in Hindi "where's the least
crowded accessible gate?" and get an answer consistent with what the
dashboard shows.

## How the solution works

```
frontend/ (vanilla HTML/CSS/JS, no build step)
   │  language + accessibility selectors, chat UI, live gate dashboard
   ▼
backend/app/main.py  (FastAPI, CORS)
   ├── routes/chat.py            → services/ai_service.py
   │                                   ├── no key / call fails → services/demo_engine.py (always works)
   │                                   └── key present → Anthropic API (optional enhancement)
   ├── routes/crowd.py           → services/crowd_service.py
   ├── routes/accessibility.py   → services/crowd_service.py + data/stadium_data.py
   └── routes/stadium.py         → data/stadium_data.py
```

### Design note: why no API key is required of the evaluator

A previous team submission to Challenge 3 was **disqualified** because its
core feature only worked if the evaluator supplied their own API key —
reviewers doing a manual code/deployment check had no way to see the
feature actually function. That failure mode is now treated as a hard
architectural constraint for this project, not just a README promise:

- `services/demo_engine.py` implements a complete, deterministic,
  keyword-based reply engine over the *same* structured venue data the
  Claude path uses. It requires no network access and no credentials.
- `services/ai_service.get_chat_reply()` only ever calls Claude if a key is
  present in the environment, and **always** falls back to the demo engine
  — never to an error message — if that call fails for any reason.
- Tests (`tests/test_demo_engine.py`, and the no-key/failure cases in
  `tests/test_ai_service.py` and `tests/test_routes.py`) explicitly assert
  the chat endpoint returns correct, grounded answers with `ANTHROPIC_API_KEY`
  unset, so this behavior can't silently regress.
- The trade-off is intentional: Tier 1 handles fixed intents (restrooms,
  food, transport, medical, lost & found, accessibility, gate/wait) via
  keyword matching rather than open-ended natural language understanding.
  Configuring a real key unlocks Claude's full language understanding for
  anything outside those intents — but that's a bonus, never a requirement.

This follows the same Clean Architecture layering used across the team's
other hackathon projects: **routes** only parse/validate HTTP input and call
a service; **services** hold all business logic and are framework-agnostic;
**models** (Pydantic schemas) are the shared contract between layers;
**data** is the static venue dataset, isolated so it can be swapped for a
real database without touching business logic. This separation is also what
makes the service layer directly unit-testable without spinning up HTTP.

### Backend (`backend/`)

- **FastAPI** app exposing:
  - `POST /api/chat` — multilingual concierge chat
  - `GET /api/crowd-status` — live per-gate occupancy + recommendation
  - `GET /api/accessibility-info?need=...` — accessibility facilities + best gate
  - `GET /api/stadium/gates`, `/api/stadium/amenities`, `/api/stadium/match-context`
  - `GET /api/health` — liveness probe
- Calls the **Anthropic Messages API** (`claude-sonnet-4-6`) directly via the
  official `anthropic` Python SDK — but only as an optional enhancement.
- **Fully functional with zero API keys**, by design: `services/demo_engine.py`
  answers common fan questions (restrooms, food, transport, medical, lost &
  found, accessibility, gate/wait times) with grounded, correct, localized
  replies using only structured venue data — no network call involved. If
  a key is configured, Claude is used instead for richer, open-ended
  understanding; if that call ever fails (no key, network issue, rate limit),
  the app falls back to the demo engine automatically rather than erroring.
- 31 automated tests (`pytest`) covering crowd-level bucketing logic, gate
  recommendation logic, the key-free demo engine, the AI service (with the
  Anthropic client mocked, so tests run with zero API cost and no network),
  and full API route behavior including input validation — including
  explicit tests asserting the chat endpoint works correctly with no API
  key configured at all.

### Frontend (`frontend/`)

- Plain HTML/CSS/JS — deliberately no build step, so a judge can open
  `index.html` directly against a running backend with no `npm install`.
- Live gate dashboard rendered as capacity gauges, auto-refreshing every 15s.
- Language selector (8 languages) and accessibility-need selector, both fed
  straight into the chat and accessibility API calls.
- "Accessibility Mode" toggle: increases font size across chat, gate cards,
  and the accessibility panel for fans who need larger text.
- Keyboard-focusable controls, `aria-live` regions on the chat log and crowd
  status so screen readers announce updates, and `prefers-reduced-motion`
  respected.

## Running it locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
No `.env` file or API key is needed for this to work — every endpoint,
including `/api/chat`, is fully functional immediately. If you want to
enable the optional Claude enhancement, copy `.env.example` to `.env` and
add your own `ANTHROPIC_API_KEY`; if you don't, the app runs exactly as
well on the built-in demo engine.

**Tests**
```bash
cd backend
pytest -v
```

**Frontend**
Just open `frontend/index.html` in a browser (or serve it with any static
file server, e.g. `python -m http.server 5500` from the `frontend/` folder).
It talks to the backend at `http://localhost:8000` by default; override with
`window.FAN_CONCIERGE_API_BASE` if needed.

> Without an `ANTHROPIC_API_KEY`, the chat endpoint doesn't just "still run"
> with a degraded message — it returns the same grounded, correct venue
> information a fan would get with a key configured, via the built-in demo
> engine. Every feature works fully with zero AI dependency.

## Assumptions made

- **Venue and match data is illustrative**, not a real FIFA 2026 venue. In a
  real deployment, `app/data/stadium_data.py` and the crowd occupancy
  readings in `crowd_service.py` would be replaced by calls to the venue's
  actual gate/turnstile system, ticketing platform, and facilities database
  — the route and service layer contracts are designed so that swap doesn't
  touch any other code.
- **Crowd occupancy is simulated** with a deterministic, time-bucketed
  pseudo-random function rather than live sensor/camera data, since no real
  stadium feed is available for a hackathon submission. It's built so a real
  IoT/analytics feed can be substituted behind the same `get_crowd_status()`
  function.
- **Eight languages** are supported as a representative sample of FIFA World
  Cup 2026's expected fan base (English, Spanish, Portuguese, French, Hindi,
  Arabic, German, Japanese); adding more is a one-line change to the
  `Language` enum and `LANGUAGE_NAMES`/`WELCOME_MESSAGES` maps.
- **No user accounts or persistence** — this is a stateless, session-less
  concierge suited to walk-up kiosk or personal-phone use during a single
  matchday visit, which matches how most fans would actually use it.
- **The key-free demo engine uses keyword-based intent matching**, not full
  language understanding. It correctly handles the common fan intents this
  README lists, in all 8 supported languages, but won't understand
  arbitrarily-phrased open-ended questions the way Claude would. This is a
  deliberate trade-off: full functionality without any credentials, with
  Claude layered on top as a genuine (optional) upgrade rather than a
  requirement.

## Tech stack

- **Backend:** Python, FastAPI, Pydantic v2, Anthropic SDK, pytest
- **Frontend:** HTML, CSS, vanilla JavaScript (no framework/build step)
- **AI:** Claude (`claude-sonnet-4-6`) via the Anthropic Messages API
