# Fan Concierge - Smart Stadium Assistant for FIFA World Cup 2026

A multilingual concierge and crowd-intelligence system built for
**Challenge 4: Smart Stadiums & Tournament Operations**. It targets fans
and venue staff during matchday, combining an AI-driven multilingual chat
assistant with real-time gate crowd status and accessibility guidance —
live, working, and running end to end.

**Runs entirely standalone.** No external services, no signup, no
configuration, no keys of any kind - clone it, install one dependency
file, and every feature works immediately.

**Live demo:** https://fifa-world-cup-2026-jtyk.vercel.app/
**Backend API:** https://fifa-world-cup-2026-eight-omega.vercel.app/api/health

---

## Problem statement coverage

Challenge 4 lists eight possible areas a submission can target: navigation,
crowd management, accessibility, transportation, sustainability,
multilingual assistance, operational intelligence, and real-time decision
support. Rather than touching all eight shallowly, this project goes deep
on the five most connected to the actual moment of friction on matchday -
the 90 minutes before kickoff, when a fan has to find their way, in their
language, through a crowd, to a gate that suits their needs:

| Challenge area | How this project addresses it |
|---|---|
| **Multilingual assistance** | Chat concierge answers in 8 languages (English, Spanish, Portuguese, French, Hindi, Arabic, German, Japanese), detected from what the fan actually typed |
| **Crowd management** | Live per-gate occupancy simulation, bucketed into low/moderate/high/critical, refreshed automatically, with an explicit lowest-occupancy recommendation |
| **Navigation** | The concierge and the live dashboard always agree on which gate to recommend, so a fan gets one consistent answer whether they ask in chat or read the dashboard |
| **Accessibility** | Dedicated accessibility-need selector (wheelchair, low vision, hearing impaired, cognitive/sensory support) that returns relevant facilities *and* factors accessibility into the gate recommendation itself |
| **Real-time decision support** | Every recommendation (gate to use, accessible gate to use) is computed live from current occupancy data, not static — this is the throughline connecting all three assistant surfaces (chat, dashboard, accessibility panel) |

Transportation, sustainability, and operational intelligence are
acknowledged as valid directions for this challenge but were deliberately
left out of scope here, in favor of doing the chosen five thoroughly
rather than eight superficially - see [Assumptions made](#assumptions-made)
for how the architecture leaves room to extend into them later.

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

Three pieces of logic work together:

1. **Multilingual concierge.** A fan types a question in any supported
   language. `services/concierge_engine.py` detects the intent behind the
   message by matching keywords (in the fan's own language) against a
   lookup table, then composes a natural-language reply in that language
   using only structured, factual venue data (gates, amenities,
   accessibility features). Because replies are always built from this
   fixed dataset rather than invented, they can never contradict the actual
   venue — grounding matters a lot when the answer affects where a fan
   physically walks. Recognized intents: restrooms, food, medical/first
   aid, lost & found, transport, accessibility, and gate/wait times.

2. **Crowd intelligence (decision support).** Each gate has a simulated,
   time-bucketed occupancy reading (a stand-in for a real turnstile/camera
   feed). The service buckets occupancy into low/moderate/high/critical,
   estimates a wait time, and computes a recommended gate. This is exposed
   both as a live dashboard and as context the concierge draws on when a fan
   asks which gate to use.

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
frontend/ 
   │  language + accessibility selectors, chat UI, live gate dashboard
   │  auto-detects local vs. deployed backend URL — no manual config
   ▼
backend/app/main.py  
   ├── routes/chat.py            → services/concierge_engine.py
   ├── routes/crowd.py           → services/crowd_service.py
   ├── routes/accessibility.py   → services/crowd_service.py + data/stadium_data.py
   └── routes/stadium.py         → data/stadium_data.py

core/rate_limit.py        — in-memory rate limiter, proxy-aware (X-Forwarded-For)
core/security_headers.py  — standard defensive HTTP headers on every response
```

This follows a Clean Architecture layering: **routes** only parse/validate
HTTP input and call a service; **services** hold all business logic and are
framework-agnostic; **models** (Pydantic schemas) are the shared contract
between layers; **data** is the static venue dataset, isolated so it can be
swapped for a real database without touching business logic. This
separation is also what makes the service layer directly unit-testable
without spinning up HTTP.

### Backend (`backend/`)

- **FastAPI** app exposing:
  - `POST /api/chat` — multilingual concierge chat
  - `GET /api/crowd-status` — live per-gate occupancy + recommendation
  - `GET /api/accessibility-info?need=...` — accessibility facilities + best gate
  - `GET /api/stadium/gates`, `/api/stadium/amenities`, `/api/stadium/match-context`
  - `GET /api/health` — liveness probe
- **Zero external dependencies.** `services/concierge_engine.py` runs
  entirely in-process: no network calls, no third-party services, no
  environment configuration required. Every endpoint is fully functional
  the moment `pip install -r requirements.txt` finishes.
- **Defense-in-depth security practices**, all covered by tests (see
  `SECURITY.md` for details): strict input validation on every request,
  origin-restricted CORS, a proxy-aware in-memory rate limiter on
  `/api/chat` (30 requests/60s per client, with automatic cleanup of
  expired entries so memory usage stays bounded), and standard security
  response headers (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`).
- 33 automated tests (`pytest`) covering crowd-level bucketing logic, gate
  recommendation logic, intent detection and reply composition in the
  concierge engine, rate limiting behavior (including cleanup and
  proxy-header handling), security headers, and full API route behavior
  including input validation.
- **Linted and formatted** with [ruff](https://docs.astral.sh/ruff/)
  (config in `backend/ruff.toml`), enforced automatically by CI
  (`.github/workflows/ci.yml`) on every push and pull request — lint,
  format check, and the full test suite all have to pass.

### Frontend (`frontend/`)

- Plain HTML/CSS/JS — deliberately no build step, so anyone can open
  `index.html` directly against a running backend with no `npm install`.
- **Auto-detects its environment**: uses `http://localhost:8000` when run
  locally and the deployed backend URL in production, with no manual
  editing required between the two.
- Live gate dashboard rendered as capacity gauges, auto-refreshing every 15s.
- Language selector (8 languages) and accessibility-need selector, both fed
  straight into the chat and accessibility API calls.
- "Accessibility Mode" toggle: increases font size across chat, gate cards,
  and the accessibility panel for fans who need larger text.
- Keyboard-focusable controls, a visible-on-focus "Skip to main content"
  link, `aria-live` regions on the chat log and crowd status so screen
  readers announce updates, `document.documentElement.lang` kept in sync
  with the selected language (so screen readers switch pronunciation
  correctly), and `prefers-reduced-motion` respected.

## Running it locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
No `.env` file, signup, or configuration of any kind is needed — every
endpoint, including `/api/chat`, works immediately.

**Tests and linting**
```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
ruff check .
ruff format --check .
```

**Frontend**
Open `frontend/index.html` directly in a browser, or serve it with any
static file server (e.g. `python -m http.server 5500` from the `frontend/`
folder). It automatically talks to `http://localhost:8000` when run
locally.

## Deploying on Vercel

This is a two-part deployment: the FastAPI backend as a Vercel Python
serverless project, and the static frontend as a second Vercel project.
Both can come from the same GitHub repository.

### 1. Deploy the backend

The repo already includes what Vercel needs to run the FastAPI app as a
serverless function — `backend/api/index.py` (re-exports the FastAPI app)
and `backend/vercel.json` (routes all paths to it). No setup required here.

On [vercel.com](https://vercel.com):
1. **Add New Project** → import your GitHub repo.
2. Under **Root Directory**, select `backend`.
3. Framework preset: **Other**. Leave build/install commands as default —
   Vercel auto-installs `requirements.txt`.
4. Deploy. No environment variables need to be set.
5. Note the deployed URL (e.g. `https://your-backend.vercel.app`).

### 2. Deploy the frontend

1. **Add New Project** again, same repo.
2. Under **Root Directory**, select `frontend`.
3. Framework preset: **Other** (static site) — no build command needed.
4. Deploy. The frontend auto-detects it's running in production and
   switches its backend URL automatically — no manual edit needed.
5. Your frontend URL (e.g. `https://your-frontend.vercel.app`) is the link
   to share.

### 3. Allow the frontend origin

Once you know your frontend's Vercel URL, add it to the backend's CORS
allow-list by setting an `ALLOWED_ORIGINS` environment variable on the
backend Vercel project (comma-separated list of origins, no trailing
slash), then redeploy the backend.

That's the whole deployment — no API keys, no secrets, no third-party
accounts beyond Vercel and GitHub.

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
- **Rate limiting is in-memory and single-process** by design — appropriate
  for this deployment's scale. The `RateLimiter.is_allowed(key)` interface
  is what a Redis-backed implementation would expose if this were ever
  scaled across multiple processes, so swapping the backend wouldn't change
  any calling code.
- **Eight languages** are supported as a representative sample of FIFA World
  Cup 2026's expected fan base; adding more is a one-line change to the
  `Language` enum and the phrase dictionaries in `concierge_engine.py`.
- **The concierge engine uses keyword-based intent matching**, not
  freeform language understanding. It correctly handles the common fan
  intents this README lists — restrooms, food, transport, medical, lost &
  found, accessibility, gate/wait times — in all 8 supported languages, but
  won't parse arbitrarily-phrased open-ended questions. This trade-off is
  deliberate: full functionality with zero external dependencies, rather
  than depending on any third-party service being available or configured.
- **Transportation, sustainability, and operational intelligence** (three
  of the eight listed challenge areas) are out of scope for this
  submission by choice, not oversight — the Clean Architecture layering
  means a `transport_service.py` or `sustainability_service.py` could be
  added following the exact same pattern as `crowd_service.py` without
  touching existing code.
- **No user accounts or persistence** — this is a stateless, session-less
  concierge suited to walk-up kiosk or personal-phone use during a single
  matchday visit, which matches how most fans would actually use it.

## Tech stack

- **Backend:** Python, Pydantic v2, pytest, ruff
- **Frontend:** HTML, CSS, vanilla JavaScript
- **Deployment:** Vercel 

## Further reading

- [`SECURITY.md`](./SECURITY.md) — security practices and what's tested
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — code style and how to run checks locally
