# Unit Testing

## Stack

- `pytest` — test runner
- `pytest-cov` — coverage reporting
- `python-dotenv` — load `.env` for DB credentials and API keys in tests
- Local MySQL test database (never RDS)

## conftest.py — standard fixtures

Place this at `tests/conftest.py` in every DB-backed repo:

```python
import os
import pytest
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

TEST_DB = "test_" + os.environ.get("DB_NAME", "foodnet")

@pytest.fixture(scope="session")
def db_connection():
    """Create test DB, apply schema, yield connection, drop DB after session."""
    conn = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASS", ""),
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {TEST_DB}")
    cursor.execute(f"USE {TEST_DB}")

    # Apply schema
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path) as f:
            for statement in f.read().split(";"):
                s = statement.strip()
                if s:
                    cursor.execute(s)
    conn.commit()
    yield conn

    cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
    conn.close()

@pytest.fixture
def db(db_connection):
    """Per-test: yield connection, rollback after each test."""
    yield db_connection
    db_connection.rollback()
```

For repos with no database, omit `conftest.py` or use it only for non-DB fixtures.

## Writing unit tests

### Testing a pure function from lib/

```python
# tests/test_mylib.py
from lib.mylib import my_function

def test_basic_case():
    result = my_function("input")
    assert result == "expected"

def test_edge_case():
    result = my_function("")
    assert result is None
```

### Testing a DB-backed function

```python
# tests/test_data.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.data import insert_record, get_record

def test_insert_and_retrieve(db):
    insert_record(db, name="test item")
    result = get_record(db, name="test item")
    assert result is not None
    assert result["name"] == "test item"
```

### Testing a CGI endpoint response

For CGI files, test the underlying logic by importing helper functions — don't try to invoke the CGI binary directly in unit tests. E2E tests cover the HTTP layer.

```python
# tests/test_endpoint_logic.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.handler import process_request

def test_valid_input():
    response = process_request({"q": "test"})
    assert response["status"] == "ok"

def test_missing_param():
    response = process_request({})
    assert response["error"] == "missing q"
```

## Running tests

```bash
# All tests
pytest

# Single file
pytest tests/test_data.py

# With coverage
pytest --cov=. --cov-report=term-missing

# Verbose
pytest -v
```

## pytest.ini (optional, add to repo root)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

## Coverage target

Aim for 80%+ on `lib/` modules. CGI files are covered by E2E tests.
