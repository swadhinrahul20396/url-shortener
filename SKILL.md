---
name: url-shortener
description: Scaffolds and runs a production-quality, in-memory URL shortener API (FastAPI) with SSRF/malicious-URL validation, custom aliases, click analytics, and a pytest suite. Use when the user asks to build, run, extend, or test a URL shortener, link shortener, or short-link service.
---

# URL Shortener

A runnable FastAPI service that shortens URLs, redirects short codes to their
targets, tracks click analytics, and rejects malicious/unsafe input (SSRF
targets, dangerous URL schemes). Storage is in-memory for this prototype.

## Sync with GitHub first (source of truth)

This skill's canonical source is
[github.com/swadhinrahul20396/url-shortener](https://github.com/swadhinrahul20396/url-shortener) —
the local checkout under `~/.claude/skills/url-shortener` is a working copy,
not the authority. **Always run this exact sync step before anything else in
this skill**, so you're never running stale code:

```bash
if [ -d ~/.claude/skills/url-shortener/.git ]; then
  git -C ~/.claude/skills/url-shortener pull --ff-only origin main
else
  git clone https://github.com/swadhinrahul20396/url-shortener.git ~/.claude/skills/url-shortener
fi
cd ~/.claude/skills/url-shortener
```

If `git pull` fails because of local uncommitted changes, stop and surface
that to the user rather than discarding their edits (do not `git reset --hard`
or `git stash` without asking).

## Quick start

```bash
pip install -r scripts/requirements.txt
python scripts/app.py          # serves on http://127.0.0.1:8000
```

Shorten a URL:
```bash
curl -s -X POST http://127.0.0.1:8000/api/shorten \
  -H 'content-type: application/json' \
  -d '{"url": "https://example.com/some/path"}'
```

Follow the short link (redirects, increments click count):
```bash
curl -sI http://127.0.0.1:8000/<code>
```

## Run tests

```bash
pytest scripts/test_app.py -v
```

Covers the happy-path roundtrip, click analytics, custom aliases (including
collisions), and every malicious-input/SSRF rejection path.

## Architecture & design decisions

Data model, in-memory store design, code generation, full API surface, and
the security design (scheme allowlist, SSRF blocklist, alias rules) are in
[reference.md](reference.md). Read this before extending the service or
explaining a design choice.

## Usage examples

Concrete request/response pairs (happy path, custom alias, rejected
malicious input) and the pattern for adding a new validation rule are in
[examples.md](examples.md).

## Utility scripts (execute, not read)

All logic lives in `scripts/` as small, single-responsibility modules —
run these, don't paste their contents into context:

- **`scripts/app.py`** — the FastAPI app; run directly (`python scripts/app.py`)
  or via `uvicorn app:app --reload` for development.
- **`scripts/test_app.py`** — pytest suite; run via `pytest scripts/test_app.py -v`.
- **`scripts/validators.py`**, **`scripts/storage.py`**, **`scripts/shortener.py`**,
  **`scripts/models.py`** — imported by `app.py`; read only if you need to
  modify validation, storage, or code-generation behavior (see
  [examples.md](examples.md) §4 for the pattern to follow when adding a rule).

## Notes

- Requires Python ≥3.9.
- In-memory only: data does not survive a process restart. See
  [reference.md](reference.md) for this and other documented limitations.
