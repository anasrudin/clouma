# apps/api/tests/conftest.py
"""
Shared fixtures for the Clouma API test suite.

Sets required environment variables before the `api` package is imported,
so that pydantic-settings doesn't raise a ValidationError.
"""

import os
import sys

# Must be set before `api.config` (and therefore `api.main`) is imported.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "tvly-test-key")
os.environ.setdefault("TAVILY_BASE_URL", "https://api.tavily.com")

# _API_DIR  = apps/api/   → lets `import agent_runtime` work
# _APPS_DIR = apps/       → lets `import api` work (api is a package under apps/)
_API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APPS_DIR = os.path.dirname(_API_DIR)
if _APPS_DIR not in sys.path:
    sys.path.insert(0, _APPS_DIR)
if _API_DIR not in sys.path:
    sys.path.insert(1, _API_DIR)

import pytest
from fastapi.testclient import TestClient
import api.main as _api_main


@pytest.fixture(scope="session")
def api_client():
    """FastAPI TestClient for the full app."""
    with TestClient(_api_main.app, raise_server_exceptions=True) as c:
        yield c
