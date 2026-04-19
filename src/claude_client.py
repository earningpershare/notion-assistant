import anthropic
from src.tool_definitions import NOTION_TOOLS

SYSTEM_PROMPT = """你是用戶的 Notion 個人助理。用戶會用自然語言告訴你他想做什麼，你負責呼叫對應的 Notion 工具來完成任務。

規則：
- 優先理解用戶意圖，再決定要呼叫哪個工具
- 若需要先搜尋才能知道 page_id，先呼叫 search_notion
- 操作完成後，用繁體中文簡潔地回覆用戶結果
- 若找不到目標內容，主動告訴用戶並詢問是否要新建
- 不要在回覆中重複工具的原始輸出，改用自然語言摘要
"""


class ClaudeClient:
    def __init__(self, api_key: str, notion):
        self._anthropic = anthropic.Anthropic(api_key=api_key)
        self._notion = notion
        self.history: list[dict] = []

    def _trim_history(self) -> None:
        if len(self.history) > 40:
            self.history = self.history[-40:]

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        self._trim_history()

        while True:
            response = self._anthropic.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=NOTION_TOOLS,
                messages=self.history,
            )

            if response.stop_reason == "end_turn":
                text = next(
                    (b.text for b in response.content if b.type == "text"), ""
                )
                self.history.append({"role": "assistant", "content": text or "(操作已完成)"})
                self._trim_history()
                return text or "(操作已完成)"

            if response.stop_reason != "tool_use":
                text = next(
                    (b.text for b in response.content if b.type == "text"), ""
                )
                self.history.append({"role": "assistant", "content": text or f"(stop_reason: {response.stop_reason})"})
                self._trim_history()
                return text or f"(stop_reason: {response.stop_reason})"

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                name = block.name
                result = self._dispatch(name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

            try:
                content = [b.model_dump() for b in response.content]
            except AttributeError:
                content = response.content  # fallback for tests
            self.history.append({"role": "assistant", "content": content})
            self._trim_history()
            self.history.append({"role": "user", "content": tool_results})
            self._trim_history()

    def _dispatch(self, name: str, inputs: dict) -> str:
        tool_fn = getattr(self._notion, name, None)
        if tool_fn is None:
            return f"未知工具: {name}"
        try:
            return tool_fn(**inputs)
        except Exception as e:
            return f"工具執行失敗: {e}"
