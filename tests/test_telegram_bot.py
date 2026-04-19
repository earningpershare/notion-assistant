from unittest.mock import MagicMock, patch
import pytest
from src.telegram_bot import TelegramBot


@pytest.fixture
def bot():
    with patch("src.telegram_bot.httpx.Client"):
        b = TelegramBot(token="fake-token", owner_chat_id="12345")
        b._http = MagicMock()
        yield b


def test_is_authorized_owner(bot):
    assert bot.is_authorized("12345") is True


def test_is_authorized_stranger(bot):
    assert bot.is_authorized("99999") is False


def test_is_authorized_int_chat_id(bot):
    assert bot.is_authorized(12345) is True


def test_send_message(bot):
    bot._http.post.return_value = MagicMock(raise_for_status=MagicMock())
    bot.send_message(chat_id="12345", text="Hello")
    bot._http.post.assert_called_once_with(
        "https://api.telegram.org/botfake-token/sendMessage",
        json={"chat_id": "12345", "text": "Hello"},
    )


def test_set_webhook(bot):
    bot._http.post.return_value = MagicMock(raise_for_status=MagicMock())
    bot.set_webhook("https://example.com/webhook")
    bot._http.post.assert_called_once_with(
        "https://api.telegram.org/botfake-token/setWebhook",
        json={"url": "https://example.com/webhook"},
    )


def test_send_message_raises_on_http_error(bot):
    from httpx import HTTPStatusError, Request, Response
    bot._http.post.return_value = MagicMock(
        raise_for_status=MagicMock(side_effect=HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock(status_code=401)
        ))
    )
    with pytest.raises(HTTPStatusError):
        bot.send_message(chat_id="12345", text="Hello")
