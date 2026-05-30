"""Generate a job-prep kit: cover letter + Q&A + talking points.

Run:  python main.py prep

Reads the job you're viewing in JobRight (if that Chrome is open), or lets you
paste a job description, then writes a tailored prep kit you can copy from.
"""

from __future__ import annotations

from pathlib import Path


def _read_job_from_browser(config) -> str | None:
    """Try to read the job text from the open JobRight tab (best-effort)."""
    try:
        from ..jobs.browser import BrowserSession

        session = BrowserSession.from_config(config)
        session.start()
        try:
            session.focus("jobright")
            text = session.visible_text(max_chars=5000)
        finally:
            session.close()
        # Only use it if it looks like a job page, not the list.
        if text and len(text) > 400:
            return text
    except Exception:
        return None
    return None


def _read_job_from_paste() -> str:
    print("\nPaste the job description below. When done, type a line with just "
          "END and press Enter:\n")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def run() -> None:
    from ..brain import claude_oneshot
    from ..config import config
    from ..jobs.prep import build_prep_prompt, save_prep
    from ..jobs.profile import load_profile

    try:
        profile = load_profile(config.profile_path)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        return

    print("📋 Getting the job posting...")
    job_text = _read_job_from_browser(config)
    if job_text:
        print("✅ Read the job from your open JobRight page.")
    else:
        print("(Couldn't read JobRight automatically.)")
        job_text = _read_job_from_paste()
    if not job_text.strip():
        print("No job description provided. Try again.")
        return

    label = input("\nShort label for this job (e.g. 'UDR Data Engineer'): ").strip()

    print("\n🧠 JARVIS is writing your cover letter, answers, and talking "
          "points (this takes ~15-30s)...")
    content = claude_oneshot(build_prep_prompt(profile, job_text))
    if not content.strip():
        print("Hmm, got an empty result — check that 'claude' is logged in.")
        return

    out_dir = str(Path(config.profile_path).expanduser().parent / "applications")
    path = save_prep(content, out_dir, label or "job")
    print(f"\n✅ Prep kit saved to:\n   {path}\n")
    print("=" * 60)
    print(content)
    print("=" * 60)
    print(f"\nOpen it any time:  open '{path}'")
