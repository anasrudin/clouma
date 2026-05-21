"""
Tests for scrape_url and run_python tools.

scrape_url:
  1. Returns clean text from mocked HTML response
  2. Removes script, style, nav, footer tags
  3. Truncates output at 8 000 chars
  4. Propagates HTTP errors (4xx/5xx)
  5. Registered in TOOL_REGISTRY

run_python:
  1. Returns stdout for valid code
  2. Returns error message on non-zero exit
  3. Returns timeout message when code hangs
  4. Multi-line code works
  5. Registered in TOOL_REGISTRY
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ===========================================================================
# scrape_url
# ===========================================================================

def _mock_response(html: str, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.text = html
    r.status_code = status
    r.raise_for_status = MagicMock(
        side_effect=None if status < 400 else Exception(f"HTTP {status}")
    )
    return r


def test_scrape_url_returns_clean_text():
    html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
    with patch("httpx.get", return_value=_mock_response(html)):
        from agent_runtime.tools.builtin import scrape_url
        result = scrape_url("https://example.com")
    assert "Hello" in result
    assert "World" in result
    assert "<h1>" not in result
    assert "<p>" not in result


def test_scrape_url_removes_noise_tags():
    html = """
    <html><body>
      <nav>Nav links</nav>
      <script>alert('xss')</script>
      <style>body { color: red }</style>
      <main><p>Main content</p></main>
      <footer>Footer text</footer>
    </body></html>
    """
    with patch("httpx.get", return_value=_mock_response(html)):
        from agent_runtime.tools.builtin import scrape_url
        result = scrape_url("https://example.com")
    assert "Main content" in result
    assert "Nav links" not in result
    assert "alert" not in result
    assert "color: red" not in result
    assert "Footer text" not in result


def test_scrape_url_truncates_at_8000_chars():
    long_text = "x" * 20_000
    html = f"<html><body><p>{long_text}</p></body></html>"
    with patch("httpx.get", return_value=_mock_response(html)):
        from agent_runtime.tools.builtin import scrape_url
        result = scrape_url("https://example.com")
    assert len(result) <= 8_000


def test_scrape_url_propagates_http_errors():
    with patch("httpx.get", return_value=_mock_response("", status=404)):
        from agent_runtime.tools.builtin import scrape_url
        with pytest.raises(Exception, match="HTTP 404"):
            scrape_url("https://example.com/missing")


def test_scrape_url_registered():
    from agent_runtime.tools import TOOL_REGISTRY
    assert "scrape_url" in TOOL_REGISTRY
    schema = TOOL_REGISTRY["scrape_url"].input_schema
    assert "url" in schema.get("required", [])


# ===========================================================================
# run_python — subprocess provider (default)
# ===========================================================================

def test_run_python_subprocess_returns_stdout():
    with patch("api.config.settings") as s:
        s.python_sandbox = "subprocess"
        from agent_runtime.tools.builtin import run_python
        result = run_python("print('hello world')")
    assert result.strip() == "hello world"


def test_run_python_subprocess_error_on_nonzero_exit():
    with patch("api.config.settings") as s:
        s.python_sandbox = "subprocess"
        from agent_runtime.tools.builtin import run_python
        result = run_python("raise ValueError('boom')")
    assert result.startswith("[error]")
    assert "ValueError" in result or "1" in result


def test_run_python_subprocess_timeout():
    import subprocess as _sp
    with patch("api.config.settings") as s, \
         patch("agent_runtime.tools.builtin.subprocess") as mock_sp:
        s.python_sandbox = "subprocess"
        mock_sp.run.side_effect = _sp.TimeoutExpired(cmd="python", timeout=10)
        mock_sp.TimeoutExpired = _sp.TimeoutExpired
        from agent_runtime.tools.builtin import run_python
        result = run_python("import time; time.sleep(999)")
    assert "timed out" in result.lower()


def test_run_python_subprocess_multiline():
    with patch("api.config.settings") as s:
        s.python_sandbox = "subprocess"
        from agent_runtime.tools.builtin import run_python
        result = run_python("x = 6\ny = 7\nprint(x * y)")
    assert result.strip() == "42"


# ===========================================================================
# run_python — docker provider
# ===========================================================================

def test_run_python_docker_returns_stdout():
    import subprocess as _sp
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "docker output\n"
    mock_result.stderr = ""

    with patch("api.config.settings") as s, \
         patch("agent_runtime.tools.builtin.subprocess") as mock_sp:
        s.python_sandbox = "docker"
        mock_sp.run.return_value = mock_result
        mock_sp.TimeoutExpired = _sp.TimeoutExpired
        mock_sp.FileNotFoundError = FileNotFoundError
        from agent_runtime.tools.builtin import run_python
        result = run_python("print('docker output')")

    assert result == "docker output\n"
    call_args = mock_sp.run.call_args[0][0]
    assert "docker" in call_args
    assert "--network=none" in call_args
    assert "--memory=128m" in call_args


def test_run_python_docker_missing_daemon():
    import subprocess as _sp
    with patch("api.config.settings") as s, \
         patch("agent_runtime.tools.builtin.subprocess") as mock_sp:
        s.python_sandbox = "docker"
        mock_sp.run.side_effect = FileNotFoundError
        mock_sp.TimeoutExpired = _sp.TimeoutExpired
        mock_sp.FileNotFoundError = FileNotFoundError
        from agent_runtime.tools.builtin import run_python
        result = run_python("print('x')")
    assert "[error]" in result
    assert "Docker not found" in result


def test_run_python_docker_timeout():
    import subprocess as _sp
    with patch("api.config.settings") as s, \
         patch("agent_runtime.tools.builtin.subprocess") as mock_sp:
        s.python_sandbox = "docker"
        mock_sp.run.side_effect = _sp.TimeoutExpired(cmd="docker", timeout=30)
        mock_sp.TimeoutExpired = _sp.TimeoutExpired
        mock_sp.FileNotFoundError = FileNotFoundError
        from agent_runtime.tools.builtin import run_python
        result = run_python("import time; time.sleep(999)")
    assert "timed out" in result.lower()


# ===========================================================================
# run_python — e2b provider
# ===========================================================================

def _make_e2b_module(execution: MagicMock) -> MagicMock:
    """Inject a fake e2b_code_interpreter module into sys.modules."""
    import sys
    mock_sbx = MagicMock()
    mock_sbx.__enter__ = MagicMock(return_value=mock_sbx)
    mock_sbx.__exit__ = MagicMock(return_value=False)
    mock_sbx.run_code.return_value = execution

    mock_module = MagicMock()
    mock_module.Sandbox.return_value = mock_sbx

    sys.modules["e2b_code_interpreter"] = mock_module
    return mock_module


def test_run_python_e2b_returns_output():
    import sys
    mock_execution = MagicMock()
    mock_execution.error = None
    mock_execution.text = "e2b result"

    _make_e2b_module(mock_execution)
    try:
        with patch("api.config.settings") as s:
            s.python_sandbox = "e2b"
            s.e2b_api_key = "e2b-test-key"
            from agent_runtime.tools.builtin import run_python
            result = run_python("print('e2b result')")
    finally:
        sys.modules.pop("e2b_code_interpreter", None)

    assert result == "e2b result"


def test_run_python_e2b_no_api_key():
    with patch("api.config.settings") as s:
        s.python_sandbox = "e2b"
        s.e2b_api_key = ""
        from agent_runtime.tools.builtin import run_python
        result = run_python("print('x')")
    assert "[error]" in result
    assert "E2B_API_KEY" in result


def test_run_python_e2b_execution_error():
    import sys
    mock_error = MagicMock()
    mock_error.name = "NameError"
    mock_error.value = "name 'x' is not defined"

    mock_execution = MagicMock()
    mock_execution.error = mock_error

    _make_e2b_module(mock_execution)
    try:
        with patch("api.config.settings") as s:
            s.python_sandbox = "e2b"
            s.e2b_api_key = "e2b-test-key"
            from agent_runtime.tools.builtin import run_python
            result = run_python("print(x)")
    finally:
        sys.modules.pop("e2b_code_interpreter", None)

    assert "[error]" in result
    assert "NameError" in result


# ===========================================================================
# registry
# ===========================================================================

def test_run_python_registered():
    from agent_runtime.tools import TOOL_REGISTRY
    assert "run_python" in TOOL_REGISTRY
    schema = TOOL_REGISTRY["run_python"].input_schema
    assert "code" in schema.get("required", [])
