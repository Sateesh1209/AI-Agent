"""Talk to JARVIS from your phone via Telegram — and have JARVIS reach YOU.

This interface is two-way:
* You -> JARVIS: send it instructions from anywhere.
* JARVIS -> You: it proactively messages you when a reminder or scheduled task
  fires, even while you're away from the laptop.

Setup:
1. Message @BotFather on Telegram, run /newbot, and copy the token.
2. Put the token in .env as TELEGRAM_BOT_TOKEN.
3. (Recommended) Set TELEGRAM_ALLOWED_USER_ID to your own numeric id so only
   you can command JARVIS. The first time you message the bot, its id is also
   printed in the logs and captured for proactive messages.
"""

from __future__ import annotations

from ..agent import Jarvis
from ..config import config
from ..notify import TelegramNotifier


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

    # Notifier JARVIS uses to message the user (reminders, task results).
    notifier = TelegramNotifier(config.telegram_token, config.telegram_allowed_user_id)
    jarvis = Jarvis(notifier=notifier)
    jarvis.start_background()

    allowed = config.telegram_allowed_user_id

    def _authorized(update: Update) -> bool:
        if not allowed:
            return True
        return str(update.effective_user.id) == str(allowed)

    def _remember_chat(update: Update) -> None:
        # Capture chat id so proactive notifications can reach this user.
        if not notifier.chat_id:
            notifier.chat_id = update.effective_chat.id

    async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"[telegram] user id = {update.effective_user.id}")
        _remember_chat(update)
        await update.message.reply_text(
            "JARVIS online. Send me an instruction — I can also remind you and "
            "run scheduled tasks while you're away."
        )

    async def on_message(
        update: Update, _ctx: ContextTypes.DEFAULT_TYPE
    ) -> None:
        print(f"[telegram] message from id = {update.effective_user.id}")
        if not _authorized(update):
            await update.message.reply_text("Not authorized.")
            return
        _remember_chat(update)

        # If JARVIS is mid-task and waiting on an answer, this reply IS the answer.
        from ..runtime import RUNTIME

        pending = RUNTIME.pending_question
        if pending is not None:
            pending.respond(update.message.text)
            await update.message.reply_text("Got it — continuing. 👍")
            return

        reply = jarvis.ask(update.message.text)
        await update.message.reply_text(reply or "(done)")

    app = Application.builder().token(config.telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("[telegram] JARVIS bot is running. Press Ctrl+C to stop.")
    app.run_polling()
