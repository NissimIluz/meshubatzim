# Meshubatzim · לוח שיבוצים שבועי

Weekly family scheduling board. Each day is split into two shifts
(`08:00–14:00`, `14:00–20:00`); every cell holds an assignee name + notes.
Hebrew-only UI (RTL), Gregorian **and** Hebrew dates, live multi-user updates.

## Features

- Weekly grid (Sunday–Saturday), two shifts per day.
- Week selected via `?week=YYYY-MM-DD`; defaults to the current week.
- Lazy week creation, **up to `MAX_WEEKS_AHEAD` weeks ahead only**.
- Recurring ("from now on") templates pre-fill new weeks.
- Open viewing; editing gated by a **shared password** (`EDIT_PASSWORD`).
- **Realtime**: per-week SocketIO rooms — live presence ("others connected")
  and instant cell updates after each save.
- **Table ⇄ Cards** view toggle (mobile-friendly, remembered per browser).
- Every request + error logged to a `logs` DB table (and stdout).
- All configuration via environment (`.env`), DB-agnostic (SQLite ↔ Postgres).

## Architecture

```
app/
├── __init__.py          # create_app() — application factory
├── extensions.py        # db, migrate, socketio, csrf singletons
├── constants.py         # day names, shift keys, color palette
├── config via /config.py
├── models/              # Week, Slot, RecurringTemplate, Log
├── services/            # business logic (framework-light)
├── blueprints/          # schedule (views) · api (HTMX) · auth (login)
├── realtime/            # SocketIO events: rooms + presence + broadcast
├── logging/             # request logger + error handlers → logs table
├── utils/               # hebrew_dates (pyluach), week_utils (Sunday start)
├── templates/           # base + schedule/table + schedule/cards + cell
└── static/              # css/main.css, js/app.js
```

Layering: **blueprints → services → models**. Templates/realtime/logging are
side modules wired in the factory. Adding a feature = new service + route +
partial, without touching the core.

## Local development

Set `GROUP_ID` in `.env` (and in the production environment). Open the board
with `/?groupId=YOUR_VALUE`. Every request, including static assets and
Socket.IO, requires this query parameter; links and forms preserve it.
Missing/incorrect values, or an unset `GROUP_ID`, return HTTP 403.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env        # then edit values

# Create the schema (first run): either migrations...
$env:FLASK_APP = "wsgi.py"
flask db upgrade
# ...or the quick dev shortcut:
flask init-db
flask seed-demo               # optional sample data

python run.py                 # http://localhost:5000
```

> **DB note:** `DATABASE_URL=sqlite:///...` is only the local-dev default
> (zero-config). Production uses managed **Postgres** — set `DATABASE_URL` to
> the Neon/Supabase connection string. Same code, no changes, thanks to
> SQLAlchemy. To develop against Postgres locally too, just point
> `DATABASE_URL` at a Neon dev branch.

## Database migrations — what creates the tables

Source of truth is the models in [`app/models/`](app/models/). The tables are
created/altered by **Alembic migrations** (via Flask-Migrate), not by the app
at runtime:

```powershell
$env:FLASK_APP = "wsgi.py"
flask db migrate -m "describe change"   # generate a migration from model changes
flask db upgrade                        # APPLY it -> this builds/alters the tables
```

- `migrations/versions/*.py` (committed to git) hold the `op.create_table(...)`
  / `op.add_column(...)` calls. `flask db upgrade` runs them.
- On **Render**, `flask db upgrade` runs automatically on every deploy
  (see `render.yaml` `buildCommand`), so prod tables stay in sync.
- Dev shortcut: `flask init-db` runs `db.create_all()` straight from the models
  (no migrations). Handy locally; don't mix it with migrations in prod.

> **Troubleshooting `no such table: ...` (HTTP 500):** the local SQLite file has
> no schema yet (fresh/empty/reset DB). Fix: `flask db upgrade` (or `flask
> init-db`). The DB lives in `instance/` and is gitignored, so a clean checkout
> starts empty — always run `flask db upgrade` first.

## Deploy to Render

1. Push to GitHub.
2. Render → **New + → Blueprint**, pick this repo (`render.yaml` is detected).
3. Set secrets in the dashboard: `DATABASE_URL` (Neon/Supabase), `EDIT_PASSWORD`,
   `IMPORTANT_NOTE`. `SECRET_KEY` is generated automatically.

## Backup

Managed Postgres (Neon/Supabase) includes automatic backups. Optional extra
safety net: a scheduled `pg_dump` to object storage (Cloudflare R2 / Backblaze
B2). To scale beyond one instance, set `REDIS_URL` (SocketIO message queue) and
move presence tracking to Redis.

## Implemented since the first scaffold

- **Configurable shifts** — `SHIFTS` env var (JSON array; any count, not fixed at 2).
- **Configurable notes** — `IMPORTANT_NOTE` JSON array (type + heading level).
- **Slot-linking rules** — `RULES` env var (e.g. Friday-evening ↔ Shabbat
  mirroring); best-effort, failures are logged and skipped.
- **Recurring templates UI** — the "הגדר חזרה" button opens a recurring
  modal (name/note, from-date, until-date = forever by default); new weeks are
  pre-filled from active templates.
- **Click-to-edit** cells with automatic saving after 600 ms without typing,
  progress/success/error indicators, open editing (`OPEN_EDIT`), actor recorded as
  "unknown" until mandatory login is added.

## Open items (to finalize together)

- **Cards view** exact layout — first pass is in; refine after review.
- **Mandatory login + real identity** — when added, implement `current_actor()`
  in `app/identity.py` (currently returns "unknown").
