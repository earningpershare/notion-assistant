from notion_client import Client


def _blocks_to_text(blocks: list) -> str:
    lines = []
    for block in blocks:
        btype = block.get("type", "")
        rich = block.get(btype, {}).get("rich_text", [])
        lines.append("".join(r.get("plain_text", "") for r in rich))
    return "\n".join(lines)


def _text_to_blocks(text: str) -> list:
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            },
        }
        for chunk in text.split("\n") if chunk.strip()
    ]


class NotionTools:
    def __init__(self, token: str):
        self._client = Client(auth=token)

    def search_notion(self, query: str) -> str:
        try:
            resp = self._client.search(query=query, page_size=10)
            results = resp.get("results", [])
            if not results:
                return "找不到相關內容"
            lines = []
            for r in results:
                title = ""
                if r.get("object") == "database":
                    title = "".join(t.get("plain_text", "") for t in r.get("title", []))
                else:
                    props = r.get("properties", {})
                    for v in props.values():
                        if v.get("type") == "title":
                            title = "".join(t["plain_text"] for t in v.get("title", []))
                            break
                lines.append(f"- [{r['object']}] {title} (id: {r['id']}) {r.get('url','')}")
            return "\n".join(lines)
        except Exception as e:
            return f"Notion API 錯誤: {e}"

    def create_page(self, title: str, content: str, parent_id: str = None) -> str:
        try:
            parent = {"type": "workspace", "workspace": True}
            if parent_id:
                parent = {"type": "page_id", "page_id": parent_id}
            resp = self._client.pages.create(
                parent=parent,
                properties={"title": {"title": [{"text": {"content": title}}]}},
                children=_text_to_blocks(content),
            )
            return f"頁面已建立 (id: {resp['id']}, url: {resp['url']})"
        except Exception as e:
            return f"Notion API 錯誤: {e}"

    def update_page(self, page_id: str, new_title: str) -> str:
        try:
            self._client.pages.update(
                page_id=page_id,
                properties={"title": {"title": [{"text": {"content": new_title}}]}},
            )
            return f"頁面 {page_id} 標題已更新為「{new_title}」"
        except Exception as e:
            return f"Notion API 錯誤: {e}"

    def append_to_page(self, page_id: str, content: str) -> str:
        try:
            self._client.blocks.children.append(
                block_id=page_id,
                children=_text_to_blocks(content),
            )
            return f"成功追加內容到頁面 {page_id}"
        except Exception as e:
            return f"Notion API 錯誤: {e}"

    def get_page_content(self, page_id: str) -> str:
        try:
            all_blocks = []
            cursor = None
            while True:
                kwargs = {"block_id": page_id}
                if cursor:
                    kwargs["start_cursor"] = cursor
                resp = self._client.blocks.children.list(**kwargs)
                all_blocks.extend(resp.get("results", []))
                if not resp.get("has_more"):
                    break
                cursor = resp.get("next_cursor")
            text = _blocks_to_text(all_blocks)
            return text if text else "(頁面內容為空)"
        except Exception as e:
            return f"Notion API 錯誤: {e}"

    def create_database(self, title: str, properties: dict, parent_page_id: str = None) -> str:
        try:
            property_schema = {}
            for name, ptype in properties.items():
                if ptype == "title":
                    property_schema[name] = {"title": {}}
                elif ptype == "select":
                    property_schema[name] = {"select": {}}
                elif ptype == "number":
                    property_schema[name] = {"number": {}}
                elif ptype == "date":
                    property_schema[name] = {"date": {}}
                else:
                    property_schema[name] = {"rich_text": {}}
            if not any(v == "title" for v in properties.values()):
                first_key = next(iter(property_schema))
                property_schema[first_key] = {"title": {}}
            parent = {"type": "workspace", "workspace": True}
            if parent_page_id:
                parent = {"type": "page_id", "page_id": parent_page_id}
            resp = self._client.databases.create(
                parent=parent,
                title=[{"type": "text", "text": {"content": title}}],
                properties=property_schema,
            )
            return f"資料庫「{title}」已建立 (id: {resp['id']}, url: {resp['url']})"
        except Exception as e:
            return f"Notion API 錯誤: {e}"

    def create_db_entry(self, database_id: str, properties: dict) -> str:
        try:
            # Get database schema to find title property
            db = self._client.databases.retrieve(database_id=database_id)
            title_prop = next(
                (name for name, prop in db["properties"].items() if prop["type"] == "title"),
                None
            )
            prop_payload = {}
            for key, value in properties.items():
                if key == title_prop and isinstance(value, str):
                    prop_payload[key] = {"title": [{"text": {"content": value}}]}
                elif isinstance(value, str):
                    prop_payload[key] = {"rich_text": [{"text": {"content": value}}]}
                elif isinstance(value, (int, float)):
                    prop_payload[key] = {"number": value}
            resp = self._client.pages.create(
                parent={"type": "database_id", "database_id": database_id},
                properties=prop_payload,
            )
            return f"條目已新增 (id: {resp['id']}, url: {resp['url']})"
        except Exception as e:
            return f"Notion API 錯誤: {e}"

    def list_database(self, database_id: str, filter_prop: str = None, filter_value: str = None, filter_type: str = "rich_text") -> str:
        try:
            kwargs = {"database_id": database_id, "page_size": 20}
            if filter_prop and filter_value:
                kwargs["filter"] = {
                    "property": filter_prop,
                    filter_type: {"contains": filter_value},
                }
            resp = self._client.databases.query(**kwargs)
            results = resp.get("results", [])
            if not results:
                return "資料庫目前沒有條目"
            lines = []
            for r in results:
                parts = []
                for key, val in r.get("properties", {}).items():
                    vtype = val.get("type")
                    # Fall back to key-based detection when "type" is absent (e.g. mocks)
                    if vtype is None:
                        if "title" in val:
                            vtype = "title"
                        elif "rich_text" in val:
                            vtype = "rich_text"
                        elif "select" in val:
                            vtype = "select"
                        elif "number" in val:
                            vtype = "number"
                    if vtype == "title":
                        text = "".join(t["plain_text"] for t in val.get("title", []))
                    elif vtype == "rich_text":
                        text = "".join(t["plain_text"] for t in val.get("rich_text", []))
                    elif vtype == "select":
                        text = (val.get("select") or {}).get("name", "")
                    elif vtype == "number":
                        text = str(val.get("number", ""))
                    else:
                        text = ""
                    if text:
                        parts.append(f"{key}: {text}")
                lines.append(f"- {' | '.join(parts)} (id: {r['id']})")
            return "\n".join(lines)
        except Exception as e:
            return f"Notion API 錯誤: {e}"

    def archive_page(self, page_id: str) -> str:
        try:
            self._client.pages.update(page_id=page_id, archived=True)
            return f"頁面 {page_id} 已封存"
        except Exception as e:
            return f"Notion API 錯誤: {e}"
