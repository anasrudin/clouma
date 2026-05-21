"""Predefined skill definitions for Clouma agent runtime.

Each skill is a sub-agent with specific tools and a focused instruction.
"""

from . import _register_skill

_register_skill(
    name="web_researcher",
    description="Research a topic via web search and page scraping, returning structured findings with sources.",
    instruction=(
        "You are a research assistant. When given a topic:\n"
        "1. Use web_search to find relevant sources (aim for 3-5 results).\n"
        "2. Use scrape_url on the most relevant pages to read full content.\n"
        "3. Return a structured report: key findings, source URLs, and a brief conclusion."
    ),
    tool_names=("web_search", "scrape_url"),
)

_register_skill(
    name="pdf_summarizer",
    description="Extract and summarize the content of a PDF file or URL.",
    instruction=(
        "You are a document summarizer. When given a PDF path or URL:\n"
        "1. Use pdf_extract to retrieve the text.\n"
        "2. Return a summary covering: main topics, key points, and conclusions.\n"
        "If the document is very long, focus on the most important sections."
    ),
    tool_names=("pdf_extract",),
)

_register_skill(
    name="report_writer",
    description="Generate a formatted DOCX or PPTX document from structured content.",
    instruction=(
        "You are a report generator. When given content to document:\n"
        "- For presentations: use pptx_generate with a title and slides list "
        "[{\"title\": \"...\", \"bullets\": [\"...\"]}].\n"
        "- For written reports: use docx_generate with sections "
        "[{\"heading\": \"...\", \"body\": \"...\"}].\n"
        "Always return the output file path."
    ),
    tool_names=("pptx_generate", "docx_generate"),
)

_register_skill(
    name="youtube_analyst",
    description="Fetch and summarize the transcript of a YouTube video.",
    instruction=(
        "You are a video content analyst. When given a YouTube URL:\n"
        "1. Use youtube_transcript to fetch the transcript.\n"
        "2. Return a concise summary: main topics, key insights, and notable quotes."
    ),
    tool_names=("youtube_transcript",),
)

_register_skill(
    name="data_analyst",
    description="Analyse data and compute statistics using Python code execution.",
    instruction=(
        "You are a data analyst. Use run_python to execute Python code for analysis.\n"
        "Write clean, readable Python using only the standard library or common packages "
        "(math, statistics, json, csv). Always use print() to produce output.\n"
        "Return your findings with the supporting code."
    ),
    tool_names=("run_python",),
)

_register_skill(
    name="rss_monitor",
    description="Monitor RSS feeds and return a summary of the top highlights.",
    instruction=(
        "You are a news monitor. When given one or more RSS feed URLs:\n"
        "1. Use rss_fetch for each feed.\n"
        "2. Return the top highlights: title, source URL, and a one-sentence summary per item."
    ),
    tool_names=("rss_fetch",),
)
