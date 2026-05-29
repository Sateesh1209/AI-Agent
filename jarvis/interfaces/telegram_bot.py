"""Talk to JARVIS from your phone via Telegram.

Setup:
1. Message @BotFather on Telegram, run /newbot, and copy the token.
2. Put the token in .env as TELEGRAM_BOT_TOKEN.
3. (Recommended) Set TELEGRAM_ALLOWED_USER_ID to your own numeric id so only
   you can command JARVIS. Send your bot any message and check the logs to
   find your id.
"""

from __future__ import annotations

from ..agent import Jarvis
from ..config import config


def run() -> None:
    if not config.telegram_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Add it to your .env file."
        )

    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    jarvis = Jarvis()
    allowed = config.telegram_allowed_user_id

    def _authorized(update: Update) -> bool:
        if not allowed:
            return True
        return str(update.effective_user.id) == str(allowed)

    async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"[telegram] user id = {update.effective_user.id}")
        await update.message.reply_text(
            "JARVIS online. Send me an instruction."
        )

    async def on_message(
        update: Update, _ctx: ContextTypes.DEFAULT_TYPE
    ) -> None:
        print(f"[telegram] message from id = {update.effective_user.id}")
        if not _authorized(update):
            await update.message.reply_text("Not authorized.")
            return
        reply = jarvis.ask(update.message.text)
        await update.message.reply_text(reply or "(done)")

    app = Application.builder().token(config.telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("[telegram] JARVIS bot is running. Press Ctrl+C to stop.")
    app.run_polling()
