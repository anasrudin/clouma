"""Tests for GET /v1/skills endpoint."""


def test_get_skills_returns_200(api_client):
    resp = api_client.get("/v1/skills")
    assert resp.status_code == 200


def test_get_skills_returns_list(api_client):
    resp = api_client.get("/v1/skills")
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 6


def test_each_skill_descriptor_has_required_fields(api_client):
    resp = api_client.get("/v1/skills")
    for skill in resp.json():
        assert "name" in skill
        assert "description" in skill
        assert "tool_names" in skill
        assert isinstance(skill["tool_names"], list)


def test_known_skill_present(api_client):
    resp = api_client.get("/v1/skills")
    names = {s["name"] for s in resp.json()}
    assert "web_researcher" in names
    assert "report_writer" in names
