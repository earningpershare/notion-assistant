from unittest.mock import MagicMock, patch, call
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
                     "properties": {"title": {"type": "title", "title": [{"plain_text": "My Page"}]}}}]
    }
    result = tools.search_notion(query="meeting")
    assert "My Page" in result
    tools._client.search.assert_called_once_with(query="meeting", page_size=10)


def test_search_notion_database_object(tools):
    """Database objects have title in r['title'], not in properties."""
    tools._client.search.return_value = {
        "results": [{"id": "db-1", "object": "database", "url": "https://notion.so/db-1",
                     "title": [{"plain_text": "My Database"}],
                     "properties": {}}]
    }
    result = tools.search_notion(query="database")
    assert "My Database" in result
    assert "database" in result


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
        ],
        "has_more": False,
    }
    result = tools.get_page_content(page_id="page-123")
    assert "Hello World" in result


def test_get_page_content_pagination(tools):
    """Should follow has_more / next_cursor to collect all blocks."""
    page1 = {
        "results": [
            {"type": "paragraph", "paragraph": {
                "rich_text": [{"plain_text": "Page 1 content"}]}}
        ],
        "has_more": True,
        "next_cursor": "cursor-abc",
    }
    page2 = {
        "results": [
            {"type": "paragraph", "paragraph": {
                "rich_text": [{"plain_text": "Page 2 content"}]}}
        ],
        "has_more": False,
        "next_cursor": None,
    }
    tools._client.blocks.children.list.side_effect = [page1, page2]
    result = tools.get_page_content(page_id="page-123")
    assert "Page 1 content" in result
    assert "Page 2 content" in result
    # Verify second call used start_cursor
    calls = tools._client.blocks.children.list.call_args_list
    assert calls[0] == call(block_id="page-123")
    assert calls[1] == call(block_id="page-123", start_cursor="cursor-abc")


def test_create_database(tools):
    tools._client.databases.create.return_value = {
        "id": "db-123", "url": "https://notion.so/db-123"
    }
    result = tools.create_database(
        title="讀書清單",
        properties={"書名": "title", "狀態": "select", "評分": "number"}
    )
    assert "db-123" in result


def test_create_database_with_parent_page(tools):
    """Should use page_id parent when parent_page_id is provided."""
    tools._client.databases.create.return_value = {
        "id": "db-456", "url": "https://notion.so/db-456"
    }
    result = tools.create_database(
        title="子資料庫",
        properties={"名稱": "title"},
        parent_page_id="parent-page-id"
    )
    assert "db-456" in result
    call_kwargs = tools._client.databases.create.call_args
    assert call_kwargs.kwargs["parent"] == {"type": "page_id", "page_id": "parent-page-id"}


def test_create_db_entry(tools):
    """Should retrieve DB schema to correctly map title property."""
    tools._client.databases.retrieve.return_value = {
        "properties": {
            "書名": {"type": "title"},
            "狀態": {"type": "rich_text"},
        }
    }
    tools._client.pages.create.return_value = {
        "id": "entry-123", "url": "https://notion.so/entry-123"
    }
    result = tools.create_db_entry(
        database_id="db-123",
        properties={"書名": "原子習慣", "狀態": "閱讀中"}
    )
    assert "entry-123" in result
    tools._client.databases.retrieve.assert_called_once_with(database_id="db-123")
    # Verify title field was mapped as title type
    call_kwargs = tools._client.pages.create.call_args
    props = call_kwargs.kwargs["properties"]
    assert "title" in props["書名"]
    assert "rich_text" in props["狀態"]


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


def test_list_database_with_filter_type(tools):
    """filter_type parameter should be passed through to the API filter."""
    tools._client.databases.query.return_value = {"results": []}
    tools.list_database(
        database_id="db-123",
        filter_prop="書名",
        filter_value="原子",
        filter_type="title"
    )
    call_kwargs = tools._client.databases.query.call_args
    assert call_kwargs.kwargs["filter"] == {
        "property": "書名",
        "title": {"contains": "原子"},
    }


def test_archive_page(tools):
    tools._client.pages.update.return_value = {"id": "page-123", "archived": True}
    result = tools.archive_page(page_id="page-123")
    assert "封存" in result
    tools._client.pages.update.assert_called_with(
        page_id="page-123", archived=True
    )


def test_api_error_handling(tools):
    """Each public method should catch exceptions and return error string."""
    tools._client.search.side_effect = Exception("connection refused")
    result = tools.search_notion(query="test")
    assert "Notion API 錯誤" in result
    assert "connection refused" in result
