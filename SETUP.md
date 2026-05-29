# Setting up & testing JARVIS on your Mac (free / Ollama)

A beginner-friendly, copy-paste guide. We'll use **Ollama** — a free, private AI
brain that runs on your own Mac (no API key, no cost).

> 🎯 Goal of this guide: get JARVIS talking to you in **text mode** and prove
> the core works (brain + computer actions + reminders). Voice, Telegram, and
> job-applying come later, once the core is confirmed.

---

## What you need
- A Mac
- About 15 minutes
- ~5 GB free disk space (for the AI model)

Everything below is typed into the **Terminal** app
(press `Cmd+Space`, type "Terminal", hit Enter).

---

## Step 1 — Install the basics (one time)

Check you have Python 3.10+:
```bash
python3 --version
```
If it's missing or older than 3.10, install it from https://www.python.org/downloads/ .

---

## Step 2 — Get JARVIS's code
```bash
git clone https://github.com/Sateesh1209/AI-Agent.git
cd AI-Agent
git checkout claude/blissful-newton-drZx8
```

> If `git` asks you to install developer tools, click **Install** and wait, then
> run the commands again.

---

## Step 3 — Install JARVIS's Python parts
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 💡 You'll need to run `source .venv/bin/activate` again every time you open a
> new Terminal window before starting JARVIS.

---

## Step 4 — Install the free brain (Ollama)

1. Download Ollama from **https://ollama.com/download** and install the app
   (drag it to Applications, open it once — it runs quietly in the menu bar).
2. Download a model that can use tools (this is what lets JARVIS *do things*):
   ```bash
   ollama pull llama3.1
   ```
   This downloads ~4.7 GB the first time. Later it's instant.

> Keep the Ollama app running while you use JARVIS.

---

## Step 5 — Tell JARVIS to use the free brain
```bash
cp .env.example .env
```
Now open the `.env` file (e.g. `open -e .env`) and make sure this line says:
```
JARVIS_BACKEND=ollama
```
Save and close. That's it — no API key needed.

---

## Step 6 — Run the self-check ✅
```bash
python main.py check
```
You're looking for:
- ✅ **Ollama** backend
- ✅ tools loaded
- ✅ **"JARVIS is working!"** at the bottom

If something shows ❌, see **Troubleshooting** below.

---

## Step 7 — Talk to JARVIS! (text mode)
```bash
python main.py text
```
Now type these one at a time and watch what it does:

| Type this | What it proves |
|-----------|----------------|
| `What time is it and what operating system am I on?` | brain + a tool |
| `List the files in this folder` | reading your computer |
| `Create a file called hello.txt that says hi` | writing files |
| `Remind me to stretch in 1 minute` | ⏰ scheduling |
| *(wait ~1 minute)* | the reminder pops up 🔔 |
| `What tasks do you have scheduled?` | it remembers tasks |

Type `quit` to exit.

✅ **If those work, the core of JARVIS is working!** Tell me and we'll move on to
voice / Telegram / job-applying.

---

## Troubleshooting

**`python main.py check` says Ollama isn't working / connection refused**
- Make sure the **Ollama app is open** (check the menu bar).
- Confirm the model is there: `ollama list` (you should see `llama3.1`).
- Test Ollama directly: `ollama run llama3.1 "hello"` — it should reply.

**JARVIS replies but doesn't actually DO things (ignores tools)**
- Small free models can be inconsistent with tools. Try a bigger one:
  ```bash
  ollama pull llama3.1:70b      # only if your Mac has lots of RAM
  ```
  and set `OLLAMA_MODEL=llama3.1:70b` in `.env`. Otherwise `llama3.1` (8B) is fine
  for testing — and Claude (paid) is the most reliable if you want top quality later.

**`command not found: python3`**
- Install Python from https://www.python.org/downloads/ and reopen Terminal.

**`pip install` errors**
- Make sure you ran `source .venv/bin/activate` first (you should see `(.venv)`
  at the start of your Terminal line).

---

## What's next (after the core works)
- 🎤 **Voice:** `pip install pyaudio` (needs `brew install portaudio` first), then
  `python main.py voice`.
- 📲 **Telegram:** create a bot with @BotFather, put the token in `.env`, then
  `python main.py telegram`.
- 💼 **Job applications:** `playwright install chromium`, fill in
  `~/.jarvis/profile.json`, `python main.py login <site>`, then ask JARVIS to apply.

We'll set those up together once you've confirmed the core is working.
