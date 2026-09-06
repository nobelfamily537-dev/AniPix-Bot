# AniPix Telegram OTP Bot

## Deploy on Render.com (FREE)

### Step 1: Create Web Service
1. Go to https://render.com and sign up with GitHub
2. Click **New +** → **Web Service**
3. Connect this repository (AniPix-Bot)
4. Settings:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python anipix_bot.py`

### Step 2: Add Environment Variables
In Render dashboard, add these Environment Variables:
- `BOT_TOKEN` = your Telegram bot token
- `GITHUB_TOKEN` = your GitHub personal access token
- `BOT_USERNAME` = Anipix_bot
- `GITHUB_REPO` = nobelfamily537-dev/AniPix-Walls
- `WEBHOOK_URL` = (leave empty for now, add after first deploy)

### Step 3: Deploy
1. Click **Create Web Service**
2. Wait for deploy to complete
3. Copy the URL (e.g. https://anipix-bot.onrender.com)
4. Go back to Environment Variables, set `WEBHOOK_URL` = that URL
5. Restart the service

### Step 4: Setup Admin
1. Open Telegram, go to @Anipix_bot
2. Send /setup
3. You are now admin!

## Bot Commands
- /start - Welcome message
- /help - Help
- /setup - Become admin (first time only)
- /users - List all users (admin)
- /broadcast <message> - Broadcast to all users (admin)
- /stats - Show stats (admin)
- /myotp - Check pending OTP
