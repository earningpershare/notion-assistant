from unittest.mock import MagicMock, patch
import pytest
from src.notion_tools import NotionTools


@pytest.fixture
def tools():
    with patch("src.notion_tools.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        t = NotionTools(token="fake-token")
        t._client = mock_client
        yield t


def test_search_notion(tools):
    tools._client.search.return_value = {
        "results": [{"id": "abc", "object": "page", "url": "https://notion.so/abc",
                     "properties": {"title": {"title": [{"plain_text": "My Page"}]}}}]
    }
    result = tools.search_notion(query="meeting")
    assert "My Page" in result
    tools._client.search.assert_called_once_with(query="meeting", page_size=10)


def test_create_page(tools):
    tools._client.pages.create.return_value = {
        "id": "page-123", "url": "https://notion.so/page-123"
    }
    result = tools.create_page(title="Meeting Notes", content="討論了Q2計劃")
    assert "page-123" in result
    tools._client.pages.create.assert_called_once()


def test_update_page(tools):
    tools._client.pages.update.return_value = {"id": "page-123"}
    result = tools.update_page(page_id="page-123", new_title="Updated Title")
    assert "page-123" in result
    tools._client.pages.update.assert_called_once()


def test_append_to_page(tools):
    tools._client.blocks.children.append.return_value = {"results": []}
    result = tools.append_to_page(page_id="page-123", content="新增的內容")
    assert "成功" in result
    tools._client.blocks.children.append.assert_called_once()


def test_get_page_content(tools):
    tools._client.blocks.children.list.return_value = {
        "results": [
            {"type": "paragraph", "paragraph": {
                "rich_text": [{"plain_text": "Hello World"}]}}
        ]
    }
    result = tools.get_page_content(page_id="page-123")
    assert "Hello World" in result


def test_create_database(tools):
    tools._client.databases.create.return_value = {
        "id": "db-123", "url": "https://notion.so/db-123"
    }
    result = tools.create_database(
        title="讀書清單",
        properties={"書名": "title", "狀態": "select", "評分": "number"}
    )
    assert "db-123" in result


def test_create_db_entry(tools):
    tools._client.pages.create.return_value = {
        "id": "entry-123", "url": "https://notion.so/entry-123"
    }
    result = tools.create_db_entry(
        database_id="db-123",
        properties={"書名": "原子習慣", "狀態": "閱讀中"}
    )
    assert "entry-123" in result


def test_list_database(tools):
    tools._client.databases.query.return_value = {
        "results": [
            {"id": "e1", "properties": {
                "書名": {"title": [{"plain_text": "原子習慣"}]},
                "狀態": {"select": {"name": "閱讀中"}}
            }}
        ]
    }
    result = tools.list_database(database_id="db-123")
    assert "原子習慣" in result


def test_archive_page(tools):
    tools._client.pages.update.return_value = {"id": "page-123", "archived": True}
    result = tools.archive_page(page_id="page-123")
    assert "封存" in result
    tools._client.pages.update.assert_called_with(
        page_id="page-123", archived=True
    )
