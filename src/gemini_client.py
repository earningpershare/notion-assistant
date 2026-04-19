from google import genai
from google.genai import types

SYSTEM_PROMPT = """你是用戶的 Notion 個人助理。用戶會用自然語言告訴你他想做什麼，你負責呼叫對應的 Notion 工具來完成任務。

規則：
- 優先理解用戶意圖，再決定要呼叫哪個工具
- 若需要先搜尋才能知道 page_id，先呼叫 search_notion
- 操作完成後，用繁體中文簡潔地回覆用戶結果
- 若找不到目標內容，主動告訴用戶並詢問是否要新建
- 不要在回覆中重複工具的原始輸出，改用自然語言摘要
"""

NOTION_FUNCTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_notion",
        description="搜尋 Notion workspace 中的頁面和資料庫。回傳符合查詢的結果清單（包含 id 和 url）。",
        parameters=types.Schema(
            type="OBJECT",
            properties={"query": types.Schema(type="STRING", description="搜尋關鍵字")},
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_page",
        description="在 Notion workspace 建立新頁面，帶有標題和初始內容。",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "title": types.Schema(type="STRING", description="頁面標題"),
                "content": types.Schema(type="STRING", description="頁面初始內容（純文字，換行用 \\n）"),
                "parent_id": types.Schema(type="STRING", description="父頁面 id（選填）"),
            },
            required=["title", "content"],
        ),
    ),
    types.FunctionDeclaration(
        name="update_page",
        description="更新現有頁面的標題。若要新增內容請用 append_to_page。",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "page_id": types.Schema(type="STRING", description="要更新的頁面 id"),
                "new_title": types.Schema(type="STRING", description="新標題"),
            },
            required=["page_id", "new_title"],
        ),
    ),
    types.FunctionDeclaration(
        name="append_to_page",
        description="在現有頁面結尾追加文字內容，不覆蓋原有內容。適合日記、會議記錄等累積性筆記。",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "page_id": types.Schema(type="STRING", description="目標頁面 id"),
                "content": types.Schema(type="STRING", description="要追加的內容（純文字，換行用 \\n）"),
            },
            required=["page_id", "content"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_page_content",
        description="讀取頁面的完整文字內容，讓你可以整理、摘要或修改後再寫回去。",
        parameters=types.Schema(
            type="OBJECT",
            properties={"page_id": types.Schema(type="STRING", description="要讀取的頁面 id")},
            required=["page_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_database",
        description="在 Notion workspace 建立新的資料庫（表格），並定義欄位結構。",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "title": types.Schema(type="STRING", description="資料庫名稱"),
                "properties": types.Schema(
                    type="OBJECT",
                    description="欄位定義，key 為欄位名稱，value 為類型（title/select/number/date/text）。必須包含一個 title 欄位。",
                ),
                "parent_page_id": types.Schema(type="STRING", description="父頁面 id（選填）"),
            },
            required=["title", "properties"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_db_entry",
        description="在現有資料庫新增一筆條目（一列資料）。title 欄位會自動偵測。",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "database_id": types.Schema(type="STRING", description="目標資料庫 id"),
                "properties": types.Schema(
                    type="OBJECT",
                    description="欄位值，key 為欄位名稱，value 為內容（字串或數字）",
                ),
            },
            required=["database_id", "properties"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_database",
        description="列出資料庫中的條目，最多 20 筆。可選擇性地依欄位值篩選。",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "database_id": types.Schema(type="STRING", description="資料庫 id"),
                "filter_prop": types.Schema(type="STRING", description="篩選欄位名稱（選填）"),
                "filter_value": types.Schema(type="STRING", description="篩選值（選填）"),
                "filter_type": types.Schema(type="STRING", description="篩選類型（選填，預設 rich_text）"),
            },
            required=["database_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="archive_page",
        description="封存（軟刪除）一個頁面或資料庫條目。封存後可在 Notion 中從垃圾桶還原。",
        parameters=types.Schema(
            type="OBJECT",
            properties={"page_id": types.Schema(type="STRING", description="要封存的頁面或條目 id")},
            required=["page_id"],
        ),
    ),
]

GEMINI_TOOLS = [types.Tool(function_declarations=NOTION_FUNCTION_DECLARATIONS)]


class GeminiClient:
    def __init__(self, api_key: str, notion):
        self._client = genai.Client(api_key=api_key)
        self._notion = notion
        self._history: list[types.Content] = []

    def chat(self, user_message: str) -> str:
        self._history.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        )
        if len(self._history) > 40:
            self._history = self._history[-40:]

        while True:
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self._history,
                config=types.GenerateContentConfig(
                    tools=GEMINI_TOOLS,
                    system_instruction=SYSTEM_PROMPT,
                ),
            )

            candidate = response.candidates[0]
            self._history.append(candidate.content)

            fn_calls = [
                p.function_call
                for p in candidate.content.parts
                if p.function_call and p.function_call.name
            ]

            if not fn_calls:
                text = next(
                    (p.text for p in candidate.content.parts if hasattr(p, "text") and p.text),
                    "(操作已完成)",
                )
                return text

            tool_parts = []
            for fc in fn_calls:
                result = self._dispatch(fc.name, dict(fc.args))
                tool_parts.append(
                    types.Part.from_function_response(
                        name=fc.name,
                        response={"result": result},
                    )
                )

            self._history.append(
                types.Content(role="user", parts=tool_parts)
            )

    def _dispatch(self, name: str, inputs: dict) -> str:
        tool_fn = getattr(self._notion, name, None)
        if tool_fn is None:
            return f"未知工具: {name}"
        try:
            return tool_fn(**inputs)
        except Exception as e:
            return f"工具執行失敗: {e}"
