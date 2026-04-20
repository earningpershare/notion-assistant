import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from src.notion_tools import NotionTools
from src.gemini_client import GeminiClient
from src.telegram_bot import TelegramBot

load_dotenv()

_bot: TelegramBot = None
_claude: GeminiClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot, _claude
    notion = NotionTools(token=os.environ["NOTION_TOKEN"])
    _claude = GeminiClient(api_key=os.environ["GEMINI_API_KEY"], notion=notion)
    _bot = TelegramBot(
        token=os.environ["TELEGRAM_TOKEN"],
        owner_chat_id=os.environ["TELEGRAM_OWNER_CHAT_ID"],
    )
    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        _bot.set_webhook(f"{webhook_url}/webhook")
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
        message = body.get("message") or body.get("edited_message")
        if not message or _bot is None or _claude is None:
            return Response(status_code=200)

        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "").strip()

        if not _bot.is_authorized(chat_id) or not text:
            return Response(status_code=200)

        try:
            reply = _claude.chat(text)
        except Exception as e:
            import traceback
            err_detail = traceback.format_exc()[-300:]
            reply = f"AI 錯誤: {type(e).__name__}: {str(e)[:100]}"

        try:
            _bot.send_message(chat_id=chat_id, text=reply)
        except Exception:
            pass

    except Exception:
        pass

    return Response(status_code=200)


@app.get("/health")
def health():
    return {"status": "ok"}
