"""
AniPix Telegram OTP Bot Server
- Handles signup/signin OTP verification via Telegram
- Admin commands: /setup, /users, /broadcast, /stats
- Stores users in users.json on GitHub (AniPix-Walls repo)
- REST API for app to request/verify OTP
"""

import os
import json
import random
import time
import base64
import threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ALL SECRETS FROM ENVIRONMENT VARIABLES - set these on Render.com
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Anipix_bot")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "nobelfamily537-dev/AniPix-Walls")
USERS_FILE = "users.json"

# In-memory OTP storage: {phone_number: {otp, expires, purpose, telegram_chat_id}}
otp_store = {}
otp_lock = threading.Lock()

def load_users():
    """Load users.json from GitHub"""
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{USERS_FILE}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {"users": [], "admin_telegram_id": None}

def save_users(users_data):
    """Save users.json to GitHub"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{USERS_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        sha = resp.json().get("sha") if resp.status_code == 200 else None
        
        content = json.dumps(users_data, indent=2)
        content_b64 = base64.b64encode(content.encode()).decode()
        
        data = {
            "message": "Update users.json via bot",
            "content": content_b64,
            "branch": "main"
        }
        if sha:
            data["sha"] = sha
        
        resp = requests.put(url, headers=headers, json=data, timeout=10)
        if resp.status_code in [200, 201]:
            return True
        else:
            return False
    except Exception as e:
        print(f"Save users error: {e}")
        return False

MEMBERS_FILE = "members.json"

def load_members():
    """Load members.json from GitHub"""
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{MEMBERS_FILE}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {"members": []}

def save_members(members_data):
    """Save members.json to GitHub"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{MEMBERS_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        sha = resp.json().get("sha") if resp.status_code == 200 else None
        
        content = json.dumps(members_data, indent=2)
        content_b64 = base64.b64encode(content.encode()).decode()
        
        data = {
            "message": "Update members.json via bot",
            "content": content_b64,
            "branch": "main"
        }
        if sha:
            data["sha"] = sha
        
        resp = requests.put(url, headers=headers, json=data, timeout=10)
        return resp.status_code in [200, 201]
    except Exception as e:
        print(f"Save members error: {e}")
        return False

def send_telegram_message(chat_id, text, keyboard=None):
    """Send message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    try:
        requests.post(url, json=data, timeout=10)
    except:
        pass

def send_otp_to_telegram(chat_id, phone, otp, purpose):
    """Send OTP to user's Telegram"""
    purpose_text = "Signup" if purpose == "signup" else "Signin"
    msg = f"""\U0001f510 <b>AniPix OTP - {purpose_text}</b>

Your OTP for AniPix app {purpose_text}:

<b>{otp}</b>

\U0001f4f1 Phone: +{phone}

Enter this OTP in the AniPix app to complete your {purpose_text}.

\u26a0\ufe0f Do not share this OTP with anyone.
\u23f0 Expires in 5 minutes."""
    send_telegram_message(chat_id, msg)

# === TELEGRAM BOT WEBHOOK ===

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    """Handle incoming Telegram messages"""
    try:
        data = request.json
        if not data or "message" not in data:
            return jsonify({"ok": True})
        
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user_info = msg.get("from", {})
        
        users = load_users()
        
        if not users.get("admin_telegram_id"):
            if text.strip().split("@")[0].lower() == "/setup":
                sender_username = user_info.get("username", "")
                users["admin_telegram_id"] = str(chat_id)
                users["admin_username"] = sender_username
                save_users(users)
                send_telegram_message(chat_id, "\u2705 <b>Admin Set!</b>\n\nYou are now the admin of AniPix bot.\n\nCommands:\n/users - List all users\n/broadcast <message> - Send message to all users\n/stats - Show user stats\n/help - Show all commands")
                return jsonify({"ok": True})
            else:
                send_telegram_message(chat_id, "\U0001f527 Bot needs admin setup. Send /setup to become admin.")
                return jsonify({"ok": True})
        
        is_admin = str(chat_id) == str(users.get("admin_telegram_id"))
        
        if text.strip().split("@")[0] == "/start":
            welcome = f"""\U0001f31f <b>Welcome to AniPix Bot!</b>

This bot helps you verify your phone number for AniPix app signup/signin.

<b>How to get OTP:</b>
1\ufe0f\u20e3 Open AniPix app
2\ufe0f\u20e3 Enter your phone number in signup/signin
3\ufe0f\u20e3 Tap "Get OTP" button
4\ufe0f\u20e3 Then tap "Open AniPix Bot" button
5\ufe0f\u20e3 Send your phone number here
6\ufe0f\u20e3 You will receive OTP instantly!
7\ufe0f\u20e3 Enter OTP in the app

<b>Commands:</b>
/help - Show this message
/myotp - Check if you have a pending OTP

Enjoy AniPix! \U0001f389"""
            send_telegram_message(chat_id, welcome)
        
        elif text.strip().split("@")[0] == "/help":
            if is_admin:
                send_telegram_message(chat_id, "\U0001f4cb <b>AniPix Bot - Admin Help</b>\n\n<b>User Commands:</b>\n/help - Show help\n/myotp - Check pending OTP\n\n<b>Admin Commands:</b>\n/users - List all users\n/broadcast <message> - Broadcast to all users\n/stats - Show stats")
            else:
                send_telegram_message(chat_id, "\U0001f4cb <b>AniPix Bot - Help</b>\n\n1. Open AniPix app\n2. Enter phone number in signup/signin\n3. Tap 'Get OTP'\n4. Tap 'Open AniPix Bot'\n5. Send your phone number here\n6. Enter OTP in app\n\nCommands:\n/help - Show help\n/myotp - Check pending OTP")
        
        elif text.strip().split("@")[0] == "/myotp":
            found = False
            with otp_lock:
                for phone, otp_data in otp_store.items():
                    if otp_data.get("telegram_chat_id") == chat_id and time.time() < otp_data["expires"]:
                        purpose_text = "Signup" if otp_data["purpose"] == "signup" else "Signin"
                        remaining = int((otp_data["expires"] - time.time()) / 60)
                        send_telegram_message(chat_id, f"\U0001f510 Your pending OTP: <b>{otp_data['otp']}</b>\n\U0001f4f1 Phone: +{phone}\n\U0001f504 Purpose: {purpose_text}\n\u23f0 Expires in {remaining} minutes")
                        found = True
                        break
            if not found:
                send_telegram_message(chat_id, "\u274c No pending OTP. Request OTP from the AniPix app first.")
        
        elif is_admin and text.strip().split("@")[0] in ["/users", "/user"]:
            users_list = users.get("users", [])
            if not users_list:
                send_telegram_message(chat_id, "\U0001f4ca No users registered yet.")
            else:
                msg_lines = [f"\U0001f4ca <b>Total Users: {len(users_list)}</b>\n"]
                for u in users_list[-20:]:
                    phone = u.get("phone", "N/A")
                    gmail = u.get("gmail", "N/A")
                    uname = u.get("username", "N/A")
                    mem = u.get("membership", "free")
                    mem_icon = "\u2b50" if mem == "active" else "\U0001f193"
                    msg_lines.append(f"{mem_icon} {uname} | +{phone} | {gmail}")
                if len(users_list) > 20:
                    msg_lines.append(f"\n... and {len(users_list) - 20} more")
                send_telegram_message(chat_id, "\n".join(msg_lines))
        
        elif is_admin and text.strip().split("@")[0].startswith("/broadcast"):
            message = text.replace("/broadcast", "", 1).strip()
            if not message:
                send_telegram_message(chat_id, "Usage: /broadcast <message>")
                return jsonify({"ok": True})
            users_list = users.get("users", [])
            sent = 0
            for u in users_list:
                if u.get("telegram_chat_id"):
                    send_telegram_message(u["telegram_chat_id"], f"\U0001f4e2 <b>AniPix Update</b>\n\n{message}")
                    sent += 1
                    time.sleep(0.05)
            send_telegram_message(chat_id, f"\u2705 Broadcast sent to {sent}/{len(users_list)} users.")
        
        elif is_admin and text.strip().split("@")[0] == "/stats":
            users_list = users.get("users", [])
            premium_count = sum(1 for u in users_list if u.get("membership") == "active")
            free_count = len(users_list) - premium_count
            msg = f"\U0001f4ca <b>AniPix Stats</b>\n\n\U0001f465 Total Users: {len(users_list)}\n\u2b50 Premium: {premium_count}\n\U0001f193 Free: {free_count}"
            send_telegram_message(chat_id, msg)
        
        elif is_admin and text.strip().split("@")[0] == "/pending":
            # Show pending membership requests
            members = load_members()
            pending = [m for m in members.get("members", []) if m.get("status") == "pending"]
            if not pending:
                send_telegram_message(chat_id, "\u2705 No pending membership requests.")
            else:
                msg_lines = [f"\U0001f4cb <b>Pending Requests: {len(pending)}</b>\n"]
                for m in pending:
                    phone = m.get("phone", "N/A")
                    gmail = m.get("gmail", "N/A")
                    uname = m.get("username", "N/A")
                    plan = m.get("plan", "N/A")
                    method = m.get("payment_method", "N/A")
                    msg_lines.append(f"\U0001f4f1 {phone}\n\U0001f464 {uname}\n\U0001f4e7 {gmail}\n\U0001f4b0 {plan} ({method})\n---")
                send_telegram_message(chat_id, "\n".join(msg_lines))
        
        elif is_admin and text.strip().split("@")[0].startswith("/approve"):
            # Approve a membership request
            parts = text.strip().split()
            if len(parts) < 2:
                send_telegram_message(chat_id, "Usage: /approve <phone_number>\nExample: /approve 918409143258")
            else:
                phone = parts[1].replace("+", "").replace(" ", "").replace("-", "")
                members = load_members()
                for m in members.get("members", []):
                    if m.get("phone") == phone and m.get("status") == "pending":
                        m["status"] = "active"
                        m["approved_date"] = int(time.time())
                        plan_days = {"4m": 120, "2y": 730, "3y": 1095, "5y": 1825}.get(m.get("plan", ""), 120)
                        m["expiry_date"] = int(time.time()) + (plan_days * 86400)
                        save_members(members)
                        send_telegram_message(chat_id, f"\u2705 <b>Approved!</b>\n\n\U0001f464 {m.get('username', 'N/A')}\n\U0001f4f1 {phone}\n\U0001f4b0 Plan: {m.get('plan', 'N/A')}\n\u23f0 Valid for {plan_days} days")
                        # Notify user if they have telegram
                        if m.get("telegram_chat_id"):
                            send_telegram_message(m["telegram_chat_id"], f"\u2b50 <b>Premium Activated!</b>\n\nYour AniPix Premium membership is now active!\nPlan: {m.get('plan', 'N/A')}\nEnjoy premium wallpapers! \U0001f389")
                        break
                else:
                    send_telegram_message(chat_id, f"\u274c No pending request found for {phone}.")
        
        elif is_admin and text.strip().split("@")[0].startswith("/reject"):
            # Reject a membership request
            parts = text.strip().split()
            if len(parts) < 2:
                send_telegram_message(chat_id, "Usage: /reject <phone_number>")
            else:
                phone = parts[1].replace("+", "").replace(" ", "").replace("-", "")
                members = load_members()
                for m in members.get("members", []):
                    if m.get("phone") == phone and m.get("status") == "pending":
                        m["status"] = "rejected"
                        m["rejected_date"] = int(time.time())
                        save_members(members)
                        send_telegram_message(chat_id, f"\u274c <b>Rejected</b>\n\n\U0001f4f1 {phone}\n\U0001f464 {m.get('username', 'N/A')}")
                        break
                else:
                    send_telegram_message(chat_id, f"\u274c No pending request found for {phone}.")
        
        elif is_admin and text.strip().split("@")[0] == "/members":
            # Show all active members
            members = load_members()
            active = [m for m in members.get("members", []) if m.get("status") == "active"]
            if not active:
                send_telegram_message(chat_id, "\U0001f4ca No active members yet.")
            else:
                msg_lines = [f"\U0001f4ca <b>Active Members: {len(active)}</b>\n"]
                for m in active[-20:]:
                    phone = m.get("phone", "N/A")
                    uname = m.get("username", "N/A")
                    plan = m.get("plan", "N/A")
                    msg_lines.append(f"\u2b50 {uname} | {phone} | {plan}")
                if len(active) > 20:
                    msg_lines.append(f"\n... and {len(active) - 20} more")
                send_telegram_message(chat_id, "\n".join(msg_lines))
        
        elif is_admin and text.strip().split("@")[0].startswith("/addmember"):
            # Direct add member: /addmember <phone> <plan>
            parts = text.strip().split()
            if len(parts) < 3:
                send_telegram_message(chat_id, "Usage: /addmember <phone> <plan>\nPlans: 4m, 2y, 3y, 5y\nExample: /addmember 918409143258 4m")
            else:
                phone = parts[1].replace("+", "").replace(" ", "").replace("-", "")
                plan = parts[2].lower()
                plan_days = {"4m": 120, "2y": 730, "3y": 1095, "5y": 1825}.get(plan)
                if not plan_days:
                    send_telegram_message(chat_id, "Invalid plan. Use: 4m, 2y, 3y, or 5y")
                else:
                    members = load_members()
                    new_member = {
                        "phone": phone,
                        "username": "manual_add",
                        "gmail": "",
                        "plan": plan,
                        "status": "active",
                        "payment_method": "manual",
                        "approved_date": int(time.time()),
                        "expiry_date": int(time.time()) + (plan_days * 86400)
                    }
                    members.setdefault("members", []).append(new_member)
                    save_members(members)
                    send_telegram_message(chat_id, f"\u2705 <b>Member Added!</b>\n\n\U0001f4f1 {phone}\n\U0001f4b0 Plan: {plan} ({plan_days} days)")
        
        else:
            clean_text = text.strip().replace("+", "").replace(" ", "").replace("-", "")
            if clean_text.isdigit() and len(clean_text) >= 10:
                phone = clean_text
                with otp_lock:
                    if phone in otp_store and time.time() < otp_store[phone]["expires"]:
                        otp_data = otp_store[phone]
                        otp_data["telegram_chat_id"] = chat_id
                        send_otp_to_telegram(chat_id, phone, otp_data["otp"], otp_data["purpose"])
                    else:
                        send_telegram_message(chat_id, "\U0001f4f1 No OTP requested for this number.\n\nPlease go to AniPix app, enter your phone number in signup/signin, and tap 'Get OTP' first.\n\nThen come back here and send your phone number to receive the OTP.")
            else:
                send_telegram_message(chat_id, "\U0001f44b Send your phone number to get OTP, or /help for instructions.\n\nExample: 919876543210 or +919876543210")
    except Exception as e:
        print(f"Webhook error: {e}")
    
    return jsonify({"ok": True})

# === APP API ENDPOINTS ===

@app.route("/api/request-otp", methods=["POST"])
def request_otp():
    """App calls this to request OTP for a phone number"""
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
        purpose = data.get("purpose", "signup")
        
        if not phone or len(phone) < 10:
            return jsonify({"success": False, "error": "Invalid phone number"})
        
        users = load_users()
        users_list = users.get("users", [])
        
        if purpose == "signup":
            user_exists = any(u.get("phone") == phone for u in users_list)
            if user_exists:
                return jsonify({"success": False, "error": "This phone number is already registered. Please signin instead."})
        
        otp = str(random.randint(100000, 999999))
        
        with otp_lock:
            otp_store[phone] = {
                "otp": otp,
                "expires": time.time() + 300,
                "purpose": purpose,
                "telegram_chat_id": None
            }
        
        return jsonify({
            "success": True,
            "message": f"OTP requested! Open Telegram bot @{BOT_USERNAME} and send your phone number {phone} to receive OTP."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    """App calls this to verify OTP and complete signup/signin"""
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
        otp = data.get("otp", "").strip()
        gmail = data.get("gmail", "").strip()
        password = data.get("password", "").strip()
        username = data.get("username", "").strip()
        purpose = data.get("purpose", "signup")
        
        with otp_lock:
            if phone not in otp_store:
                return jsonify({"success": False, "error": "No OTP requested. Please request OTP first."})
            
            otp_data = otp_store[phone]
            
            if time.time() > otp_data["expires"]:
                del otp_store[phone]
                return jsonify({"success": False, "error": "OTP expired. Please request a new OTP."})
            
            if not otp_data.get("telegram_chat_id"):
                return jsonify({"success": False, "error": f"OTP not yet delivered. Please open Telegram bot @{BOT_USERNAME} and send your phone number to receive OTP."})
            
            if otp_data["otp"] != otp:
                return jsonify({"success": False, "error": "Wrong OTP. Please check and try again."})
            
            telegram_chat_id = otp_data["telegram_chat_id"]
            del otp_store[phone]
        
        users = load_users()
        users_list = users.get("users", [])
        
        if purpose == "signup":
            for u in users_list:
                if u.get("phone") == phone:
                    return jsonify({"success": False, "error": "Phone number already registered."})
                if u.get("gmail") == gmail:
                    return jsonify({"success": False, "error": "Gmail already registered."})
            
            new_user = {
                "phone": phone,
                "gmail": gmail,
                "username": username,
                "password": password,
                "telegram_chat_id": telegram_chat_id,
                "membership": "free",
                "signup_date": int(time.time())
            }
            users_list.append(new_user)
            users["users"] = users_list
            save_users(users)
            
            if users.get("admin_telegram_id"):
                send_telegram_message(users["admin_telegram_id"], f"\U0001f195 <b>New Signup</b>\n\n\U0001f464 {username}\n\U0001f4f1 +{phone}\n\U0001f4e7 {gmail}")
            
            return jsonify({"success": True, "message": "Signup successful!", "user": {"username": username, "gmail": gmail, "phone": phone, "membership": "free"}})
        
        elif purpose == "signin":
            user = None
            for u in users_list:
                if u.get("phone") == phone or u.get("gmail") == gmail:
                    if u.get("password") == password:
                        user = u
                        break
            
            if not user:
                return jsonify({"success": False, "error": "Invalid credentials."})
            
            return jsonify({"success": True, "message": "Signin successful!", "user": {"username": user.get("username"), "gmail": user.get("gmail"), "phone": user.get("phone"), "membership": user.get("membership", "free")}})
        
        return jsonify({"success": False, "error": "Invalid request"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/check-phone", methods=["POST"])
def check_phone():
    """Check if phone number is registered"""
    data = request.json
    phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
    
    users = load_users()
    users_list = users.get("users", [])
    user_exists = any(u.get("phone") == phone for u in users_list)
    
    return jsonify({"exists": user_exists})


@app.route("/setwebhook", methods=["GET"])
def set_webhook_manual():
    """Manually set webhook - visit this URL in browser"""
    import requests
    base_url = request.host_url.rstrip("/")
    if base_url.startswith("http://"):
        base_url = "https://" + base_url[7:]
    webhook_path = f"{base_url}/webhook/{BOT_TOKEN}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    try:
        resp = requests.post(url, json={"url": webhook_path}, timeout=10)
        return f"Webhook set! URL: {webhook_path}<br>Response: {resp.text}"
    except Exception as e:
        return f"Error: {e}"

@app.route("/getwebhook", methods=["GET"])  
def get_webhook_info():
    """Check webhook status"""
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    try:
        resp = requests.get(url, timeout=10)
        return f"<pre>{resp.text}</pre>"
    except Exception as e:
        return f"Error: {e}"

@app.route("/api/request-membership", methods=["POST"])
def request_membership():
    """App calls this when user requests membership"""
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
        gmail = data.get("gmail", "").strip()
        username = data.get("username", "").strip()
        plan = data.get("plan", "").strip()
        payment_method = data.get("payment_method", "").strip()
        telegram_chat_id = data.get("telegram_chat_id")
        
        if not phone or not plan:
            return jsonify({"success": False, "error": "Missing phone or plan"})
        
        members = load_members()
        member_list = members.get("members", [])
        
        # Check if already pending or active
        for m in member_list:
            if m.get("phone") == phone:
                if m.get("status") == "active":
                    return jsonify({"success": False, "error": "You already have an active membership."})
                if m.get("status") == "pending":
                    return jsonify({"success": False, "error": "Your request is already pending. Please wait for approval."})
        
        # Add new pending request
        new_request = {
            "phone": phone,
            "gmail": gmail,
            "username": username,
            "plan": plan,
            "payment_method": payment_method,
            "telegram_chat_id": telegram_chat_id,
            "status": "pending",
            "request_date": int(time.time())
        }
        member_list.append(new_request)
        members["members"] = member_list
        save_members(members)
        
        # Notify admin
        users = load_users()
        if users.get("admin_telegram_id"):
            send_telegram_message(users["admin_telegram_id"], f"\U0001f4cb <b>New Membership Request</b>\n\n\U0001f464 {username}\n\U0001f4f1 {phone}\n\U0001f4e7 {gmail}\n\U0001f4b0 Plan: {plan}\n\U0001f4b3 Payment: {payment_method}\n\nUse: /approve {phone}")
        
        return jsonify({"success": True, "message": "Membership request sent! Admin will approve soon."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/check-membership", methods=["POST"])
def check_membership():
    """App calls this to check membership status"""
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
        
        members = load_members()
        for m in members.get("members", []):
            if m.get("phone") == phone:
                return jsonify({
                    "status": m.get("status", "free"),
                    "plan": m.get("plan", ""),
                    "expiry_date": m.get("expiry_date", 0)
                })
        
        return jsonify({"status": "free", "plan": "", "expiry_date": 0})
    except Exception as e:
        return jsonify({"status": "free", "error": str(e)})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "AniPix OTP Bot", "bot_username": BOT_USERNAME})

# === SET WEBHOOK ON STARTUP ===

def set_webhook():
    """Set Telegram webhook to this server"""
    webhook_url = os.environ.get("WEBHOOK_URL", "")
    if not webhook_url:
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    if webhook_url.startswith("http://"):
        webhook_url = "https://" + webhook_url[7:]
    webhook_path = f"{webhook_url}/webhook/{BOT_TOKEN}"
    try:
        resp = requests.post(url, json={"url": webhook_path}, timeout=10)
        print(f"Webhook set: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Webhook set error: {e}")

if __name__ == "__main__":
    threading.Thread(target=set_webhook, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
