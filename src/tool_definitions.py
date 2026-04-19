NOTION_TOOLS = [
    {
        "name": "search_notion",
        "description": "搜尋 Notion workspace 中的頁面和資料庫。回傳符合查詢的結果清單（包含 id 和 url）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜尋關鍵字"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_page",
        "description": "在 Notion workspace 建立新頁面，帶有標題和初始內容。",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "頁面標題"},
                "content": {"type": "string", "description": "頁面初始內容（純文字，換行用 \\n）"},
                "parent_id": {"type": "string", "description": "父頁面 id（選填，不填則放在 workspace 根目錄）"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "update_page",
        "description": "更新現有頁面的標題。若要新增內容請用 append_to_page。",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "要更新的頁面 id"},
                "new_title": {"type": "string", "description": "新標題"},
            },
            "required": ["page_id", "new_title"],
        },
    },
    {
        "name": "append_to_page",
        "description": "在現有頁面結尾追加文字內容，不覆蓋原有內容。適合日記、會議記錄等累積性筆記。",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "目標頁面 id"},
                "content": {"type": "string", "description": "要追加的內容（純文字，換行用 \\n）"},
            },
            "required": ["page_id", "content"],
        },
    },
    {
        "name": "get_page_content",
        "description": "讀取頁面的完整文字內容，讓你可以整理、摘要或修改後再寫回去。",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "要讀取的頁面 id"},
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "create_database",
        "description": "在 Notion workspace 建立新的資料庫（表格），並定義欄位結構。",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "資料庫名稱"},
                "properties": {
                    "type": "object",
                    "description": "欄位定義，key 為欄位名稱，value 為類型（title/select/number/date/text）。必須包含一個 title 欄位。",
                    "additionalProperties": {"type": "string"},
                },
                "parent_page_id": {"type": "string", "description": "父頁面 id（選填，不填則建在 workspace 根目錄）"},
            },
            "required": ["title", "properties"],
        },
    },
    {
        "name": "create_db_entry",
        "description": "在現有資料庫新增一筆條目（一列資料）。title 欄位會自動偵測。",
        "input_schema": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string", "description": "目標資料庫 id"},
                "properties": {
                    "type": "object",
                    "description": "欄位值，key 為欄位名稱，value 為內容（字串或數字）",
                    "additionalProperties": True,
                },
            },
            "required": ["database_id", "properties"],
        },
    },
    {
        "name": "list_database",
        "description": "列出資料庫中的條目，最多 20 筆。可選擇性地依欄位值篩選。",
        "input_schema": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string", "description": "資料庫 id"},
                "filter_prop": {"type": "string", "description": "篩選欄位名稱（選填）"},
                "filter_value": {"type": "string", "description": "篩選值（選填，與 filter_prop 搭配使用）"},
                "filter_type": {"type": "string", "description": "篩選類型（選填，預設 rich_text；title 欄位用 title）"},
            },
            "required": ["database_id"],
        },
    },
    {
        "name": "archive_page",
        "description": "封存（軟刪除）一個頁面或資料庫條目。封存後可在 Notion 中從垃圾桶還原。",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "要封存的頁面或條目 id"},
            },
            "required": ["page_id"],
        },
    },
]
