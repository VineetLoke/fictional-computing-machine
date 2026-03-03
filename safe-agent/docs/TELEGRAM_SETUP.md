# Telegram Bot Setup Guide

Step-by-step instructions to create your Telegram bot and connect it to the Safe Automation Agent.

---

## Step 1: Create the Bot with @BotFather

1. Open Telegram on your phone or desktop.
2. Search for **@BotFather** and start a chat.
3. Send `/newbot`.
4. BotFather will ask for a **display name** — enter something like:
   ```
   My Safe Agent
   ```
5. BotFather will ask for a **username** (must end in `bot`) — enter something like:
   ```
   my_safe_agent_bot
   ```
6. BotFather will reply with your **bot token**:
   ```
   123456789:ABCdefGhIjKlMnOpQrStUvWxYz
   ```
7. **Copy this token** — you'll need it for the `.env` file.

---

## Step 2: Find Your Chat ID

1. Send `/start` to your new bot. (It won't reply yet — that's fine.)
2. Option A — **Use the running bot:**
   - Start the bot (see Step 4 below).
   - Send `/myid` to the bot.
   - It will reply with your chat ID.

3. Option B — **Use the Telegram API directly:**
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates" | python3 -m json.tool
   ```
   Look for `"chat": {"id": 123456789}` in the response.

---

## Step 3: Configure Environment Variables

```bash
cd safe-agent
cp .env.example .env
```

Edit `.env` with your values:

```dotenv
# Paste your bot token from Step 1
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIjKlMnOpQrStUvWxYz

# Paste your chat ID from Step 2
ALLOWED_CHAT_IDS=123456789

# Generate a secure shared secret
# Run: python -c "import secrets; print(secrets.token_urlsafe(32))"
SAFE_AGENT_TOKEN=your-generated-token-here

# Cloud agent URL (keep as localhost if running bot + agent together)
CLOUD_AGENT_URL=http://localhost:8000
```

**Multiple users?** Separate chat IDs with commas:
```dotenv
ALLOWED_CHAT_IDS=123456789,987654321
```

---

## Step 4: Start the System

### In GitHub Codespaces (recommended)

```bash
cd safe-agent

# One-command launch:
./start.sh

# Or manually:
python -m cloud.agent &
python -m telegram_bot.bot
```

### On any machine

```bash
cd safe-agent
pip install -r requirements.txt

# Terminal 1 — Cloud Agent
python -m cloud.agent

# Terminal 2 — Telegram Bot
python -m telegram_bot.bot
```

---

## Step 5: Test It

1. Open Telegram on your phone.
2. Go to your bot's chat.
3. You should see a **command menu** (tap the `/` button or the menu icon):

   ```
   /start    — Welcome message
   /status   — Laptop CPU, RAM & disk
   /ping     — Check if laptop is alive
   /logs     — View listener logs
   ...
   ```

4. Tap `/ping` — you should see:
   ```
   ✅ ping queued — waiting for laptop…
   ```
   Then either a result (if the laptop listener is running) or a timeout.

---

## Step 6: Connect Your Laptop

On your laptop, set the `CLOUD_AGENT_URL` to point at your Codespace:

```bash
cd safe-agent
pip install -r requirements-laptop.txt

export SAFE_AGENT_TOKEN="same-token-as-cloud"
export CLOUD_AGENT_URL="https://your-codespace-8000.app.github.dev"

python -m laptop.listener
```

Now try `/status` from your phone — you'll see real laptop metrics!

---

## Optional: Customize the Bot

### Change the bot's profile picture
1. Open @BotFather.
2. Send `/setuserpic`.
3. Select your bot.
4. Upload an image.

### Change the bot's description
1. Open @BotFather.
2. Send `/setdescription`.
3. Select your bot.
4. Type a description like: `Safe laptop automation agent`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot doesn't respond | Check TELEGRAM_BOT_TOKEN is correct |
| "Unauthorized" reply | Add your chat ID to ALLOWED_CHAT_IDS |
| "Cloud agent unreachable" | Make sure cloud agent is running on the same host |
| Timeout waiting for result | Start the laptop listener (`python -m laptop.listener`) |
| Commands not in menu | Restart the bot — it auto-registers commands on startup |
