import httpx


class TelegramBot:
    def __init__(self, token: str, owner_chat_id: str):
        self._token = token
        self._owner_chat_id = str(owner_chat_id)
        self._base = f"https://api.telegram.org/bot{token}"
        self._http = httpx.Client()

    def is_authorized(self, chat_id) -> bool:
        return str(chat_id) == self._owner_chat_id

    def send_message(self, chat_id: str, text: str) -> None:
        self._http.post(
            f"{self._base}/sendMessage",
            json={"chat_id": str(chat_id), "text": text},
        )

    def set_webhook(self, url: str) -> None:
        self._http.post(
            f"{self._base}/setWebhook",
            json={"url": url},
        )
