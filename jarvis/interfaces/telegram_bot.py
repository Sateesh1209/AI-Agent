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

import re
import threading

from ..agent import Jarvis
from ..config import config
from ..notify import TelegramNotifier

# Guard so only one job-application run happens at a time.
_apply_running = threading.Lock()


def _looks_like_apply(text: str) -> int | None:
    """If the message is an 'apply to jobs' command, return how many jobs."""
    t = text.lower().strip()
    if not t.startswith(("apply", "/apply")):
        return None
    m = re.search(r"\d+", t)
    return int(m.group(0)) if m else 1


def _run_apply_agent(count: int, notifier) -> None:
    """Run the autonomous job agent (in a background thread) for ``count`` jobs."""
    from ..brain import claude_oneshot
    from ..jobs.browser import BrowserSession
    from ..jobs.webagent import JOBRIGHT_GOAL, WebAgent

    if not _apply_running.acquire(blocking=False):
        notifier.send("I'm already applying to jobs — let me finish this one. 🙂")
        return
    try:
        session = BrowserSession.from_config(config)
        try:
            session.start()
        except Exception as exc:  # noqa: BLE001
            notifier.send(
                "I couldn't reach your Chrome. On your laptop run "
                "'python main.py login https://jobright.ai' and keep that window "
                f"open, then try again.\n({exc})"
            )
            return
        session.focus("jobright")
        agent = WebAgent(session, decide=claude_oneshot, notifier=notifier,
                         use_vision=True)
        for n in range(count):
            notifier.send(f"🤖 Working on job {n + 1} of {count}…")
            try:
                result = agent.run(JOBRIGHT_GOAL, max_steps=30)
                notifier.send(f"Job {n + 1}: {result[:350]}")
            except Exception as exc:  # noqa: BLE001
                notifier.send(f"⚠️ Hit a problem on job {n + 1}: {exc}")
            try:
                session.focus("jobright")
                session.goto("https://jobright.ai/jobs/recommend")
                session.page.wait_for_timeout(2000)
            except Exception:
                pass
        notifier.send("✅ Done with this batch. Review the browser when you can.")
        try:
            session.close()
        except Exception:
            pass
    finally:
        _apply_running.release()


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

        # "apply jobs" / "apply 3 jobs" -> launch the autonomous job agent.
        count = _looks_like_apply(update.message.text)
        if count is not None:
            await update.message.reply_text(
                f"On it — I'll apply to {count} job(s) and ask you here if I "
                "need a login or your OK. 🚀"
            )
            threading.Thread(
                target=_run_apply_agent, args=(count, notifier), daemon=True
            ).start()
            return

        reply = jarvis.ask(update.message.text)
        await update.message.reply_text(reply or "(done)")

    app = Application.builder().token(config.telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("[telegram] JARVIS bot is running. Press Ctrl+C to stop.")
    app.run_polling()
