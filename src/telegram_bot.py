import httpx


class TelegramBot:
    def __init__(self, token: str, owner_chat_id: str):
        self._token = token
        self._owner_chat_id = str(owner_chat_id)
        self._base = "https://api.telegram.org"
        self._http = httpx.Client()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._http.close()

    def is_authorized(self, chat_id) -> bool:
        return str(chat_id) == self._owner_chat_id

    def send_message(self, chat_id: str, text: str) -> None:
        r = self._http.post(
            f"{self._base}/bot{self._token}/sendMessage",
            json={"chat_id": str(chat_id), "text": text},
        )
        r.raise_for_status()

    def set_webhook(self, url: str) -> None:
        r = self._http.post(
            f"{self._base}/bot{self._token}/setWebhook",
            json={"url": url},
        )
        r.raise_for_status()
