"""Tests for the SKILL_REGISTRY and predefined skill catalog."""
from __future__ import annotations


EXPECTED_SKILLS = {
    "web_researcher", "pdf_summarizer", "report_writer",
    "youtube_analyst", "data_analyst", "rss_monitor",
}


def test_registry_has_all_predefined_skills():
    from agent_runtime.skills import SKILL_REGISTRY
    missing = EXPECTED_SKILLS - SKILL_REGISTRY.keys()
    assert not missing, f"Missing skills: {missing}"


def test_each_skill_has_required_fields():
    from agent_runtime.skills import SKILL_REGISTRY
    for name, entry in SKILL_REGISTRY.items():
        assert entry.name == name
        assert entry.description
        assert entry.instruction
        assert isinstance(entry.tool_names, tuple)
        assert len(entry.tool_names) > 0, f"Skill '{name}' has no tools"


def test_skill_tool_names_exist_in_tool_registry():
    from agent_runtime.skills import SKILL_REGISTRY
    from agent_runtime.tools import TOOL_REGISTRY
    for name, entry in SKILL_REGISTRY.items():
        for tool_name in entry.tool_names:
            assert tool_name in TOOL_REGISTRY, (
                f"Skill '{name}' references unknown tool '{tool_name}'"
            )


def test_duplicate_skill_registration_raises():
    import pytest
    from agent_runtime.skills import _register_skill, SKILL_REGISTRY

    sentinel = "_test_duplicate_skill_xyzzy"
    assert sentinel not in SKILL_REGISTRY

    _register_skill(
        name=sentinel,
        description="test",
        instruction="test instruction",
        tool_names=("current_time",),
    )
    with pytest.raises(ValueError, match=sentinel):
        _register_skill(
            name=sentinel,
            description="duplicate",
            instruction="duplicate instruction",
            tool_names=("current_time",),
        )
    SKILL_REGISTRY.pop(sentinel, None)


def test_web_researcher_uses_search_and_scrape():
    from agent_runtime.skills import SKILL_REGISTRY
    entry = SKILL_REGISTRY["web_researcher"]
    assert "web_search" in entry.tool_names
    assert "scrape_url" in entry.tool_names


def test_report_writer_uses_document_tools():
    from agent_runtime.skills import SKILL_REGISTRY
    entry = SKILL_REGISTRY["report_writer"]
    assert "pptx_generate" in entry.tool_names or "docx_generate" in entry.tool_names
