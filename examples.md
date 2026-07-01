# Usage Examples

## 1. Shorten a URL and follow the redirect

**Input:**
```bash
curl -s -X POST http://127.0.0.1:8000/api/shorten \
  -H 'content-type: application/json' \
  -d '{"url": "https://example.com/some/long/path"}'
```

**Output:**
```json
{
  "code": "aZ3kQ9x",
  "short_url": "http://127.0.0.1:8000/aZ3kQ9x",
  "long_url": "https://example.com/some/long/path",
  "created_at": "2026-07-01T10:15:00+00:00",
  "expires_at": null
}
```

Following the short link redirects (307) to the original URL and increments
its click count:
```bash
curl -sI http://127.0.0.1:8000/aZ3kQ9x
# HTTP/1.1 307 Temporary Redirect
# location: https://example.com/some/long/path
```

## 2. Custom alias — happy path and collision

**Input:**
```bash
curl -s -X POST http://127.0.0.1:8000/api/shorten \
  -H 'content-type: application/json' \
  -d '{"url": "https://example.com/pricing", "custom_alias": "pricing"}'
```

**Output:** `201` with `"code": "pricing"`.

Requesting the same alias again for a different URL:
```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/api/shorten \
  -H 'content-type: application/json' \
  -d '{"url": "https://example.com/other", "custom_alias": "pricing"}'
# 409
```

## 3. Rejected malicious input

**Input:**
```bash
curl -s -X POST http://127.0.0.1:8000/api/shorten \
  -H 'content-type: application/json' \
  -d '{"url": "javascript:alert(1)"}'
```

**Output:**
```json
{"detail": "scheme 'javascript' is not allowed; use http or https"}
```
(HTTP `422`)

**Input:**
```bash
curl -s -X POST http://127.0.0.1:8000/api/shorten \
  -H 'content-type: application/json' \
  -d '{"url": "http://169.254.169.254/latest/meta-data/"}'
```

**Output:**
```json
{"detail": "target address 169.254.169.254 is a private/loopback/link-local address and cannot be shortened (SSRF protection)"}
```
(HTTP `422`)

## 4. Adding a new validation rule

To add a new rejection rule (e.g. blocking a specific domain), follow the
existing pattern in `scripts/validators.py`:

1. Add the check inside `validate_url()` (or a new helper it calls), raising
   `ValueError` with a specific, human-readable reason — never a generic
   "invalid URL".
2. Add a corresponding case to the `@pytest.mark.parametrize` list for
   `test_disallowed_schemes_rejected` or `test_ssrf_targets_rejected` in
   `scripts/test_app.py` (or a new test function if the rule is a new
   category), and re-run `pytest scripts/test_app.py -v`.

Example — blocking a specific domain:
```python
BLOCKED_DOMAINS = {"malicious-example.test"}

def validate_url(url: str) -> str:
    ...
    if hostname.lower() in BLOCKED_DOMAINS:
        raise ValueError(f"domain '{hostname}' is blocked")
    ...
```
