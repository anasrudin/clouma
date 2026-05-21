"""Tests for the credentials runtime module."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_get_agent_secret_returns_value():
    from agent_runtime.credentials import get_agent_secret
    from api.models.agent_secret import AgentSecret

    mock_secret = MagicMock(spec=AgentSecret)
    mock_secret.value = "my-token-123"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_secret

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await get_agent_secret(mock_db, "agent-1", "telegram", "bot_token")
    assert result == "my-token-123"


@pytest.mark.asyncio
async def test_get_agent_secret_returns_none_when_missing():
    from agent_runtime.credentials import get_agent_secret

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await get_agent_secret(mock_db, "agent-1", "telegram", "bot_token")
    assert result is None
