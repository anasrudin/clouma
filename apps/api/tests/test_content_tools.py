"""Tests for content tools: write_file, rss_fetch, youtube_transcript,
pdf_extract, pptx_generate, docx_generate."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_write_file_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.txt")
        from agent_runtime.tools.builtin import write_file
        result = write_file(path, "hello world")
    assert result == path


def test_write_file_content_matches():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.txt")
        from agent_runtime.tools.builtin import write_file
        write_file(path, "hello world")
        assert Path(path).read_text() == "hello world"


def test_write_file_append_mode():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.txt")
        from agent_runtime.tools.builtin import write_file
        write_file(path, "line1\n", mode="w")
        write_file(path, "line2\n", mode="a")
        assert Path(path).read_text() == "line1\nline2\n"


def test_write_file_registered():
    from agent_runtime.tools import TOOL_REGISTRY
    assert "write_file" in TOOL_REGISTRY
    schema = TOOL_REGISTRY["write_file"].input_schema
    assert "path" in schema.get("required", [])
    assert "content" in schema.get("required", [])


def test_rss_fetch_returns_list():
    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(title="Entry 1", link="https://a.com", summary="Sum 1", published="Mon"),
        MagicMock(title="Entry 2", link="https://b.com", summary="Sum 2", published="Tue"),
    ]
    for e in mock_feed.entries:
        e.get = lambda k, d="", _e=e: getattr(_e, k, d)

    with patch("feedparser.parse", return_value=mock_feed):
        from agent_runtime.tools.builtin import rss_fetch
        result = rss_fetch("https://example.com/feed.xml", max_items=5)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["title"] == "Entry 1"
    assert result[0]["url"] == "https://a.com"


def test_rss_fetch_respects_max_items():
    mock_feed = MagicMock()
    mock_feed.entries = [MagicMock() for _ in range(20)]
    for e in mock_feed.entries:
        e.get = lambda k, d="": d

    with patch("feedparser.parse", return_value=mock_feed):
        from agent_runtime.tools.builtin import rss_fetch
        result = rss_fetch("https://example.com/feed.xml", max_items=3)

    assert len(result) == 3


def test_rss_fetch_registered():
    from agent_runtime.tools import TOOL_REGISTRY
    assert "rss_fetch" in TOOL_REGISTRY


def test_youtube_transcript_extracts_video_id():
    mock_transcript = [{"text": "Hello"}, {"text": "world"}]

    with patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript",
               return_value=mock_transcript) as mock_get:
        from agent_runtime.tools.builtin import youtube_transcript
        result = youtube_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    mock_get.assert_called_once_with("dQw4w9WgXcQ", languages=["en"])
    assert result == "Hello world"


def test_youtube_transcript_short_url():
    mock_transcript = [{"text": "Hi"}]
    with patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript",
               return_value=mock_transcript):
        from agent_runtime.tools.builtin import youtube_transcript
        result = youtube_transcript("https://youtu.be/dQw4w9WgXcQ")
    assert result == "Hi"


def test_youtube_transcript_invalid_url():
    from agent_runtime.tools.builtin import youtube_transcript
    result = youtube_transcript("https://example.com/not-a-video")
    assert result.startswith("[error]")


def test_youtube_transcript_registered():
    from agent_runtime.tools import TOOL_REGISTRY
    assert "youtube_transcript" in TOOL_REGISTRY


def test_pdf_extract_from_local_file():
    mock_page = MagicMock()
    mock_page.get_text.return_value = "PDF content here"
    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
    mock_doc.close = MagicMock()

    with patch("fitz.open", return_value=mock_doc):
        from agent_runtime.tools.builtin import pdf_extract
        result = pdf_extract("/tmp/test.pdf")

    assert "PDF content here" in result
    mock_doc.close.assert_called_once()


def test_pdf_extract_from_url():
    mock_response = MagicMock()
    mock_response.content = b"%PDF fake"
    mock_response.raise_for_status = MagicMock()

    mock_page = MagicMock()
    mock_page.get_text.return_value = "Remote PDF content"
    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
    mock_doc.close = MagicMock()

    with patch("httpx.get", return_value=mock_response), \
         patch("fitz.open", return_value=mock_doc):
        from agent_runtime.tools.builtin import pdf_extract
        result = pdf_extract("https://example.com/doc.pdf")

    assert "Remote PDF content" in result


def test_pdf_extract_registered():
    from agent_runtime.tools import TOOL_REGISTRY
    assert "pdf_extract" in TOOL_REGISTRY


def test_pptx_generate_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "out.pptx")
        from agent_runtime.tools.builtin import pptx_generate
        result = pptx_generate(
            title="My Presentation",
            slides=[{"title": "Slide 1", "bullets": ["Point A", "Point B"]}],
            output_path=output,
        )
        assert result == output
        assert Path(output).exists()


def test_pptx_generate_empty_slides():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "out.pptx")
        from agent_runtime.tools.builtin import pptx_generate
        result = pptx_generate(title="Empty", slides=[], output_path=output)
    assert result == output


def test_pptx_generate_registered():
    from agent_runtime.tools import TOOL_REGISTRY
    assert "pptx_generate" in TOOL_REGISTRY
    schema = TOOL_REGISTRY["pptx_generate"].input_schema
    assert "title" in schema.get("required", [])
    assert "output_path" in schema.get("required", [])


def test_docx_generate_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "out.docx")
        from agent_runtime.tools.builtin import docx_generate
        result = docx_generate(
            sections=[{"heading": "Intro", "body": "This is the introduction."}],
            output_path=output,
        )
        assert result == output
        assert Path(output).exists()


def test_docx_generate_registered():
    from agent_runtime.tools import TOOL_REGISTRY
    assert "docx_generate" in TOOL_REGISTRY
    schema = TOOL_REGISTRY["docx_generate"].input_schema
    assert "sections" in schema.get("required", [])
    assert "output_path" in schema.get("required", [])
