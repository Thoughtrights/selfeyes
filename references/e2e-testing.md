# End-to-End Testing

## Principles

- E2E tests run against **live EC2 URLs** after deployment
- Use `pytest` + `requests` — no browser automation unless the feature is JS-heavy
- Tests must be **safe for production**: read-only, or use `_e2etest` sentinel records with cleanup
- Base URL is passed via `E2E_BASE_URL` env var — never hardcoded

## Running E2E tests

```bash
# Against production
E2E_BASE_URL=https://food.net/my-feature pytest tests/e2e/ -v

# Against local preview
E2E_BASE_URL=http://food.net.local:8080/my-feature pytest tests/e2e/ -v
```

## conftest.py for E2E (tests/e2e/conftest.py)

```python
import os
import pytest

@pytest.fixture(scope="session")
def base_url():
    url = os.environ.get("E2E_BASE_URL")
    if not url:
        raise ValueError("E2E_BASE_URL environment variable is required")
    return url.rstrip("/")

@pytest.fixture(scope="session")
def session():
    import requests
    s = requests.Session()
    # Add auth headers here if needed, e.g.:
    # s.headers.update({"X-API-Key": os.environ.get("API_KEY", "")})
    yield s
```

## Standard E2E test patterns

### Health check (always first)

```python
# tests/e2e/e2e_health.py
def test_health(base_url, session):
    r = session.get(f"{base_url}/health.api")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

### JSON response shape

```python
def test_list_endpoint(base_url, session):
    r = session.get(f"{base_url}/items.api")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("results"), list)

def test_single_item(base_url, session):
    r = session.get(f"{base_url}/item.api?id=1")
    assert r.status_code == 200
    item = r.json()
    assert "id" in item
    assert "name" in item
```

### Write operations with cleanup

```python
import pytest

SENTINEL = "_e2etest"

@pytest.fixture
def created_item(base_url, session):
    """Create a test record, yield its ID, delete it after test."""
    r = session.post(f"{base_url}/create.api", json={"name": f"test{SENTINEL}"})
    assert r.status_code == 200
    item_id = r.json()["id"]
    yield item_id
    # Teardown
    session.post(f"{base_url}/delete.api", json={"id": item_id})

def test_create_and_retrieve(base_url, session, created_item):
    r = session.get(f"{base_url}/item.api?id={created_item}")
    assert r.status_code == 200
    assert SENTINEL in r.json()["name"]
```

### Error cases

```python
def test_missing_param_returns_error(base_url, session):
    r = session.get(f"{base_url}/data.api")  # no required param
    assert r.status_code in (400, 200)       # 200 with error body is also common for CGI
    body = r.json()
    assert "error" in body

def test_not_found(base_url, session):
    r = session.get(f"{base_url}/item.api?id=999999")
    assert r.status_code in (404, 200)
    if r.status_code == 200:
        assert r.json().get("result") is None
```

## CGI-specific notes

CGI scripts often return HTTP 200 even for errors (they control the response body).
Test for both the status code and the presence/absence of `"error"` in the JSON body.

## E2E test file naming

```
tests/e2e/
├── e2e_health.py       # always include
├── e2e_read.py         # GET / read operations
├── e2e_write.py        # POST / write operations with cleanup
└── e2e_auth.py         # auth flows if applicable
```

## Running E2E as part of deploy

Add to `deploy.sh` after the smoke test:

```bash
echo "==> Running E2E tests..."
E2E_BASE_URL="https://$VHOST/$DEPLOY_PATH" pytest tests/e2e/ -v --tb=short
```
