from unittest.mock import MagicMock, patch, call
import pytest
from src.claude_client import ClaudeClient


@pytest.fixture
def mock_notion():
    n = MagicMock()
    n.search_notion.return_value = "- [page] 測試頁面 (id: abc)"
    n.create_page.return_value = "頁面已建立 (id: new-123, url: https://notion.so/new-123)"
    return n


@pytest.fixture
def client(mock_notion):
    with patch("src.claude_client.anthropic.Anthropic") as mock_anthropic_class:
        mock_anthropic = MagicMock()
        mock_anthropic_class.return_value = mock_anthropic
        c = ClaudeClient(api_key="fake-key", notion=mock_notion)
        c._anthropic = mock_anthropic
        yield c


def test_chat_appends_to_history(client):
    client._anthropic.messages.create.return_value = MagicMock(
        stop_reason="end_turn",
        content=[MagicMock(type="text", text="你好！")]
    )
    reply = client.chat("你好")
    assert reply == "你好！"
    assert len(client.history) == 2  # user + assistant


def test_chat_trims_history_to_40_items(client):
    client._anthropic.messages.create.return_value = MagicMock(
        stop_reason="end_turn",
        content=[MagicMock(type="text", text="ok")]
    )
    for i in range(25):
        client.chat(f"msg {i}")
    assert len(client.history) <= 40


def test_chat_handles_tool_use(client, mock_notion):
    tool_use_block = MagicMock(type="tool_use", id="tu-1")
    tool_use_block.name = "search_notion"
    tool_use_block.input = {"query": "會議"}
    text_block = MagicMock(type="text", text="找到了：測試頁面")

    client._anthropic.messages.create.side_effect = [
        MagicMock(stop_reason="tool_use", content=[tool_use_block]),
        MagicMock(stop_reason="end_turn", content=[text_block]),
    ]
    reply = client.chat("幫我找會議記錄")
    assert reply == "找到了：測試頁面"
    mock_notion.search_notion.assert_called_once_with(query="會議")


def test_chat_dispatches_all_tools(client, mock_notion):
    tool_names = [
        ("search_notion", {"query": "test"}),
        ("create_page", {"title": "T", "content": "C"}),
        ("update_page", {"page_id": "p1", "new_title": "NT"}),
        ("append_to_page", {"page_id": "p1", "content": "C"}),
        ("get_page_content", {"page_id": "p1"}),
        ("create_database", {"title": "DB", "properties": {"名稱": "title"}}),
        ("create_db_entry", {"database_id": "db1", "properties": {"名稱": "A"}}),
        ("list_database", {"database_id": "db1"}),
        ("archive_page", {"page_id": "p1"}),
    ]
    for name, inputs in tool_names:
        getattr(mock_notion, name).return_value = "ok"
        tool_block = MagicMock(type="tool_use", id="tu-x")
        tool_block.name = name
        tool_block.input = inputs
        client._anthropic.messages.create.side_effect = [
            MagicMock(stop_reason="tool_use", content=[tool_block]),
            MagicMock(stop_reason="end_turn", content=[MagicMock(type="text", text="done")]),
        ]
        client.history = []
        reply = client.chat("test")
        assert reply == "done"


def test_chat_handles_max_tokens(client):
    client._anthropic.messages.create.return_value = MagicMock(
        stop_reason="max_tokens",
        content=[MagicMock(type="text", text="partial")]
    )
    reply = client.chat("test")
    assert reply == "partial"
    assert len(client.history) == 2


def test_dispatch_unknown_tool(client):
    # Replace notion with a spec-constrained mock so getattr returns None for unknown tools
    from unittest.mock import MagicMock
    client._notion = MagicMock(spec=[])  # no attributes allowed
    result = client._dispatch("nonexistent_tool", {})
    assert "未知工具" in result


def test_dispatch_tool_exception(client, mock_notion):
    mock_notion.search_notion.side_effect = RuntimeError("API down")
    result = client._dispatch("search_notion", {"query": "x"})
    assert "工具執行失敗" in result
