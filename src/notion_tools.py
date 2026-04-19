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
        resp = self._client.search(query=query, page_size=10)
        results = resp.get("results", [])
        if not results:
            return "找不到相關內容"
        lines = []
        for r in results:
            title = ""
            props = r.get("properties", {})
            for v in props.values():
                vtype = v.get("type")
                if vtype == "title" or (vtype is None and "title" in v):
                    title = "".join(t["plain_text"] for t in v.get("title", []))
                    break
            lines.append(f"- [{r['object']}] {title} (id: {r['id']}) {r.get('url','')}")
        return "\n".join(lines)

    def create_page(self, title: str, content: str, parent_id: str = None) -> str:
        parent = {"type": "workspace", "workspace": True}
        if parent_id:
            parent = {"type": "page_id", "page_id": parent_id}
        resp = self._client.pages.create(
            parent=parent,
            properties={"title": {"title": [{"text": {"content": title}}]}},
            children=_text_to_blocks(content),
        )
        return f"頁面已建立 (id: {resp['id']}, url: {resp['url']})"

    def update_page(self, page_id: str, new_title: str) -> str:
        self._client.pages.update(
            page_id=page_id,
            properties={"title": {"title": [{"text": {"content": new_title}}]}},
        )
        return f"頁面 {page_id} 標題已更新為「{new_title}」"

    def append_to_page(self, page_id: str, content: str) -> str:
        self._client.blocks.children.append(
            block_id=page_id,
            children=_text_to_blocks(content),
        )
        return f"成功追加內容到頁面 {page_id}"

    def get_page_content(self, page_id: str) -> str:
        resp = self._client.blocks.children.list(block_id=page_id)
        text = _blocks_to_text(resp.get("results", []))
        return text if text else "(頁面內容為空)"

    def create_database(self, title: str, properties: dict) -> str:
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
        resp = self._client.databases.create(
            parent={"type": "workspace", "workspace": True},
            title=[{"type": "text", "text": {"content": title}}],
            properties=property_schema,
        )
        return f"資料庫「{title}」已建立 (id: {resp['id']}, url: {resp['url']})"

    def create_db_entry(self, database_id: str, properties: dict) -> str:
        prop_payload = {}
        for key, value in properties.items():
            if isinstance(value, str):
                prop_payload[key] = {"rich_text": [{"text": {"content": value}}]}
            elif isinstance(value, (int, float)):
                prop_payload[key] = {"number": value}
        resp = self._client.pages.create(
            parent={"type": "database_id", "database_id": database_id},
            properties=prop_payload,
        )
        return f"條目已新增 (id: {resp['id']}, url: {resp['url']})"

    def list_database(self, database_id: str, filter_prop: str = None, filter_value: str = None) -> str:
        kwargs = {"database_id": database_id, "page_size": 20}
        if filter_prop and filter_value:
            kwargs["filter"] = {
                "property": filter_prop,
                "rich_text": {"contains": filter_value},
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

    def archive_page(self, page_id: str) -> str:
        self._client.pages.update(page_id=page_id, archived=True)
        return f"頁面 {page_id} 已封存"
