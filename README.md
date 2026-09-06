# AniPix Telegram OTP Bot

## Deploy on Render.com

1. Go to https://render.com and sign up with GitHub
2. Click **New +** → **Web Service**
3. Connect this repository (AniPix-Bot)
4. Settings:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python anipix_bot.py`
5. Add Environment Variable:
   - Key: `WEBHOOK_URL`
   - Value: (your render URL, e.g. https://anipix-bot.onrender.com)
6. Click **Create Web Service**
7. Wait for deploy to complete
8. Copy the URL (e.g. https://anipix-bot.onrender.com)
9. Go to Telegram, open @Anipix_bot, send /setup to become admin

## Bot Commands
- /start - Welcome message
- /help - Help
- /setup - Become admin (first time only)
- /users - List all users (admin)
- /broadcast <message> - Broadcast to all users (admin)
- /stats - Show stats (admin)
- /myotp - Check pending OTP
