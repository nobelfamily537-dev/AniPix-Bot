"""
AniPix Telegram Bot - Complete Version
Features:
- OTP signup/signin via Telegram
- Membership management (/pending, /approve, /reject, /members, /addmember)
- Payment options (/buy command shows UPI, Amazon, Flipkart)
- User management (/users shows username, gmail, password, telegram username)
- Password reset (/resetpass)
- Device binding (1 number = 1 device)
- Stats (/stats, /statsapp)
- Menu button with all commands
- Beautiful /help for users
- Admin notifications for new signups, membership requests
- User notifications for approval/rejection
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

# ALL SECRETS FROM ENVIRONMENT VARIABLES
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Anipix_bot")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "nobelfamily537-dev/AniPix-Walls")
ADMIN_TELEGRAM = os.environ.get("ADMIN_USERNAME", "Lovelyanime_admin")
USERS_FILE = "users.json"
MEMBERS_FILE = "members.json"

otp_store = {}
otp_lock = threading.Lock()

# Payment info
UPI_ID = "lavkushkumar3258@nyes"
ADMIN_CONTACT = "@Lovelyanime_admin"

PLANS = {
    "4m": {"name": "4 Months", "price": 299, "days": 120},
    "2y": {"name": "2 Years", "price": 799, "days": 730},
    "3y": {"name": "3 Years", "price": 999, "days": 1095},
    "5y": {"name": "5 Years", "price": 1200, "days": 1825}
}

# === GITHUB STORAGE ===

def load_json_file(filename):
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{filename}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    if filename == USERS_FILE:
        return {"users": [], "admin_telegram_id": None}
    if filename == MEMBERS_FILE:
        return {"members": []}
    return {}

def save_json_file(filename, data):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
        resp = requests.get(url, headers=headers, timeout=10)
        sha = resp.json().get("sha") if resp.status_code == 200 else None
        content = json.dumps(data, indent=2)
        content_b64 = base64.b64encode(content.encode()).decode()
        payload = {"message": f"Update {filename}", "content": content_b64, "branch": "main"}
        if sha:
            payload["sha"] = sha
        resp = requests.put(url, headers=headers, json=payload, timeout=10)
        return resp.status_code in [200, 201]
    except Exception as e:
        print(f"Save error: {e}")
        return False

def load_users():
    return load_json_file(USERS_FILE)

def save_users(data):
    return save_json_file(USERS_FILE, data)

def load_members():
    return load_json_file(MEMBERS_FILE)

def save_members(data):
    return save_json_file(MEMBERS_FILE, data)

def send_msg(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    try:
        requests.post(url, json=data, timeout=10)
    except:
        pass

def send_otp(chat_id, phone, otp, purpose):
    ptext = "Signup" if purpose == "signup" else "Signin"
    msg = f"\U0001f510 <b>AniPix OTP - {ptext}</b>\n\nYour OTP: <b>{otp}</b>\n\n\U0001f4f1 Phone: +{phone}\n\nEnter this in AniPix app.\n\u26a0\ufe0f Do not share with anyone.\n\u23f0 Expires in 5 min."
    send_msg(chat_id, msg)

def get_cmd(text):
    """Extract command from text, handling @bot suffix"""
    return text.strip().split("@")[0].lower().strip()

def get_admin_id():
    users = load_users()
    return users.get("admin_telegram_id")

# === MENU BUTTON ===

def set_menu_button():
    """Set bot menu button with all commands"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton"
    menu = {
        "menu_button": {
            "type": "web_app",
            "text": "Commands",
            "web_app": {"url": ""}
        }
    }
    # Actually use commands list
    commands_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
    commands = [
        {"command": "start", "description": "Start AniPix Bot"},
        {"command": "help", "description": "Get help & instructions"},
        {"command": "buy", "description": "Buy Premium membership"},
        {"command": "myotp", "description": "Check pending OTP"},
        {"command": "mystatus", "description": "Check your membership status"},
        {"command": "resetpass", "description": "Reset your password"},
    ]
    admin_commands = [
        {"command": "start", "description": "Start AniPix Bot"},
        {"command": "help", "description": "Get help & instructions"},
        {"command": "buy", "description": "Buy Premium membership"},
        {"command": "myotp", "description": "Check pending OTP"},
        {"command": "mystatus", "description": "Check your membership status"},
        {"command": "resetpass", "description": "Reset your password"},
        {"command": "users", "description": "List all users with details"},
        {"command": "pending", "description": "Show pending membership requests"},
        {"command": "approve", "description": "Approve membership: /approve <phone>"},
        {"command": "reject", "description": "Reject membership: /reject <phone>"},
        {"command": "members", "description": "Show active members"},
        {"command": "addmember", "description": "Add member: /addmember <phone> <plan>"},
        {"command": "stats", "description": "Show full statistics"},
        {"command": "broadcast", "description": "Broadcast: /broadcast <message>"},
    ]
    try:
        # Set default commands for all users
        requests.post(commands_url, json={"commands": commands}, timeout=10)
        # Set admin commands
        admin_id = get_admin_id()
        if admin_id:
            requests.post(commands_url, json={"commands": admin_commands, "scope": {"type": "chat", "chat_id": int(admin_id)}}, timeout=10)
    except:
        pass

# === TELEGRAM WEBHOOK ===

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.json
        if not data or "message" not in data:
            return jsonify({"ok": True})
        
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user_info = msg.get("from", {})
        sender_username = user_info.get("username", "")
        
        users = load_users()
        users_list = users.get("users", [])
        admin_id = users.get("admin_telegram_id")
        is_admin = str(chat_id) == str(admin_id)
        cmd = get_cmd(text)
        
        # === ADMIN SETUP (only first time) ===
        if not admin_id:
            if cmd == "/setup":
                users["admin_telegram_id"] = str(chat_id)
                users["admin_username"] = sender_username
                save_users(users)
                send_msg(chat_id, "\u2705 <b>Admin Set!</b>\n\nYou are now admin of AniPix bot.\n\nCommands:\n/users - All users with details\n/pending - Pending requests\n/approve <phone> - Approve membership\n/reject <phone> - Reject membership\n/members - Active members\n/addmember <phone> <plan> - Add member\n/stats - Full statistics\n/broadcast <msg> - Broadcast message\n/help - Help")
                # Set menu commands
                threading.Thread(target=set_menu_button, daemon=True).start()
                return jsonify({"ok": True})
            else:
                send_msg(chat_id, "\U0001f527 Bot needs admin setup. Owner send /setup")
                return jsonify({"ok": True})
        
        # === USER COMMANDS ===
        
        if cmd == "/start":
            welcome = f"""\U0001f31f <b>Welcome to AniPix Bot!</b>

This bot helps you with:
\U0001f510 OTP verification for signup/signin
\u2b50 Buy Premium membership
\U0001f4cb Check membership status
\U0001f511 Reset password

<b>How to get OTP:</b>
1\ufe0f\u20e3 Open AniPix app
2\ufe0f\u20e3 Enter phone number in signup/signin
3\ufe0f\u20e3 Tap "Get OTP" button
4\ufe0f\u20e3 Come here & send your phone number
5\ufe0f\u20e3 You'll get OTP instantly!

<b>Need help?</b>
Tap /help or use menu button

\U0001f4ac Support: {ADMIN_CONTACT}"""
            send_msg(chat_id, welcome)
        
        elif cmd == "/help":
            help_text = f"""\U0001f4cb <b>AniPix Bot - Help</b>

\U0001f510 <b>OTP for Signup/Signin:</b>
1. Open AniPix app
2. Enter phone number in signup/signin
3. Tap "Get OTP" button in app
4. Come back here, send your phone number
5. Enter OTP in app

\u2b50 <b>Buy Premium:</b>
Tap /buy to see plans & payment options

\U0001f4cb <b>Check Status:</b>
Tap /mystatus to check your membership

\U0001f511 <b>Reset Password:</b>
Tap /resetpass if you forgot your password

\U0001f4ac <b>Need more help?</b>
Contact admin: {ADMIN_CONTACT}
Send screenshot/payment proof to admin."""
            send_msg(chat_id, help_text)
        
        elif cmd == "/buy":
            buy_text = f"""\u2b50 <b>AniPix Premium Membership</b>

<b>Plans:</b>
\U0001f4b0 4 Months - Rs.299
\U0001f4b0 2 Years - Rs.799
\U0001f4b0 3 Years - Rs.999
\U0001f4b0 5 Years - Rs.1200

<b>Payment Methods:</b>

\U0001f4f1 <b>UPI Payment:</b>
Pay to: <code>{UPI_ID}</code>
(GPay, PhonePe, Paytm)

\U0001f381 <b>Amazon Voucher:</b>
Send Amazon gift card code

\U0001f381 <b>Flipkart Voucher:</b>
Send Flipkart gift card code

<b>After Payment:</b>
1. Take screenshot of payment
2. Send screenshot to {ADMIN_CONTACT}
3. Open AniPix app → Settings → Premium
4. Tap "Request Admin to Approve"
5. Wait for approval notification here!

\U0001f4ac Support: {ADMIN_CONTACT}"""
            send_msg(chat_id, buy_text)
        
        elif cmd == "/myotp":
            found = False
            with otp_lock:
                for phone, od in otp_store.items():
                    if od.get("telegram_chat_id") == chat_id and time.time() < od["expires"]:
                        remaining = int((od["expires"] - time.time()) / 60)
                        send_msg(chat_id, f"\U0001f510 Your OTP: <b>{od['otp']}</b>\n\U0001f4f1 +{phone}\n\u23f0 {remaining} min left")
                        found = True
                        break
            if not found:
                send_msg(chat_id, "\u274c No pending OTP. Request from AniPix app first.")
        
        elif cmd == "/mystatus":
            # Find user by chat_id
            user = None
            for u in users_list:
                if str(u.get("telegram_chat_id", "")) == str(chat_id):
                    user = u
                    break
            if not user:
                # Try by phone - user should send phone after this
                send_msg(chat_id, "\U0001f4f1 Send your phone number to check membership status.\nExample: 918409143258")
                return jsonify({"ok": True})
            
            members = load_members()
            member = None
            for m in members.get("members", []):
                if m.get("phone") == user.get("phone"):
                    member = m
                    break
            
            if member and member.get("status") == "active":
                expiry = member.get("expiry_date", 0)
                days_left = max(0, int((expiry - time.time()) / 86400)) if expiry else 0
                send_msg(chat_id, f"\u2b50 <b>Premium Active</b>\n\n\U0001f464 {user.get('username','N/A')}\n\U0001f4b0 Plan: {member.get('plan','N/A')}\n\u23f0 Days left: {days_left}")
            elif member and member.get("status") == "pending":
                send_msg(chat_id, f"\u23f3 <b>Pending Approval</b>\n\nYour membership request is waiting for admin approval.")
            else:
                send_msg(chat_id, f"\U0001f193 <b>Free Account</b>\n\nBuy premium with /buy")
        
        elif cmd.startswith("/resetpass"):
            parts = text.strip().split()
            if len(parts) < 4:
                send_msg(chat_id, "<b>Password Reset</b>\n\nFormat:\n/resetpass gmail phone newpassword\n\nExample:\n/resetpass my@gmail.com 918409143258 newpass123")
            else:
                gmail = parts[1].lower()
                phone = parts[2].replace("+", "").replace("-", "").replace(" ", "")
                newpass = parts[3]
                # Find user
                found_user = None
                for u in users_list:
                    if u.get("gmail", "").lower() == gmail and u.get("phone") == phone:
                        found_user = u
                        break
                if found_user:
                    found_user["password"] = newpass
                    save_users(users)
                    send_msg(chat_id, f"\u2705 <b>Password Reset!</b>\n\nUsername: {found_user.get('username','N/A')}\nNew password set. Login in AniPix app.")
                else:
                    send_msg(chat_id, "\u274c No account found with that gmail & phone.")
        
        # === ADMIN COMMANDS ===
        
        elif is_admin and cmd in ["/users", "/user"]:
            if not users_list:
                send_msg(chat_id, "\U0001f4ca No users registered yet.")
            else:
                lines = [f"\U0001f4ca <b>Total Users: {len(users_list)}</b>\n"]
                for u in users_list:
                    uname = u.get("username", "N/A")
                    gmail = u.get("gmail", "N/A")
                    phone = u.get("phone", "N/A")
                    pw = u.get("password", "N/A")
                    tg = "@" + u.get("telegram_username", "N/A") if u.get("telegram_username") else "N/A"
                    mem = u.get("membership", "free")
                    lines.append(f"\U0001f464 <b>{uname}</b>\n\U0001f4e7 {gmail}\n\U0001f4f1 {phone}\n\U0001f511 {pw}\n\U0001f4ac {tg}\n\U0001f4b0 {mem}\n---")
                # Send in chunks to avoid message length limit
                msg_text = "\n".join(lines)
                if len(msg_text) > 4000:
                    # Split into chunks
                    for i in range(0, len(lines), 10):
                        chunk = "\n".join(lines[i:i+10])
                        send_msg(chat_id, chunk)
                        time.sleep(0.1)
                else:
                    send_msg(chat_id, msg_text)
        
        elif is_admin and cmd == "/pending":
            members = load_members()
            pending = [m for m in members.get("members", []) if m.get("status") == "pending"]
            if not pending:
                send_msg(chat_id, "\u2705 No pending requests.")
            else:
                lines = [f"\U0001f4cb <b>Pending: {len(pending)}</b>\n"]
                for m in pending:
                    lines.append(f"\U0001f464 {m.get('username','N/A')}\n\U0001f4f1 {m.get('phone','N/A')}\n\U0001f4e7 {m.get('gmail','N/A')}\n\U0001f4b0 {m.get('plan','N/A')} ({m.get('payment_method','N/A')})\n\u2705 /approve {m.get('phone','')}\n\u274c /reject {m.get('phone','')}\n---")
                send_msg(chat_id, "\n".join(lines))
        
        elif is_admin and cmd.startswith("/approve"):
            parts = text.strip().split()
            if len(parts) < 2:
                send_msg(chat_id, "Usage: /approve <phone>\nExample: /approve 918409143258")
            else:
                phone = parts[1].replace("+", "").replace(" ", "").replace("-", "")
                members = load_members()
                for m in members.get("members", []):
                    if m.get("phone") == phone and m.get("status") == "pending":
                        m["status"] = "active"
                        m["approved_date"] = int(time.time())
                        plan = m.get("plan", "4m")
                        days = PLANS.get(plan, PLANS["4m"])["days"]
                        m["expiry_date"] = int(time.time()) + (days * 86400)
                        save_members(members)
                        send_msg(chat_id, f"\u2705 <b>Approved!</b>\n\n\U0001f464 {m.get('username','N/A')}\n\U0001f4f1 {phone}\n\U0001f4b0 {PLANS.get(plan,{}).get('name',plan)} ({days} days)")
                        # Notify user
                        if m.get("telegram_chat_id"):
                            send_msg(m["telegram_chat_id"], f"\u2b50 <b>Premium Activated!</b>\n\nPlan: {PLANS.get(plan,{}).get('name',plan)}\nValid for {days} days\n\nEnjoy premium wallpapers! \U0001f389")
                        # Also update users.json
                        for u in users_list:
                            if u.get("phone") == phone:
                                u["membership"] = "active"
                                save_users(users)
                                break
                        return jsonify({"ok": True})
                send_msg(chat_id, f"\u274c No pending request for {phone}")
        
        elif is_admin and cmd.startswith("/reject"):
            parts = text.strip().split()
            if len(parts) < 2:
                send_msg(chat_id, "Usage: /reject <phone>")
            else:
                phone = parts[1].replace("+", "").replace(" ", "").replace("-", "")
                members = load_members()
                for m in members.get("members", []):
                    if m.get("phone") == phone and m.get("status") == "pending":
                        m["status"] = "rejected"
                        m["rejected_date"] = int(time.time())
                        save_members(members)
                        send_msg(chat_id, f"\u274c <b>Rejected</b>\n\U0001f4f1 {phone}\n\U0001f464 {m.get('username','N/A')}")
                        if m.get("telegram_chat_id"):
                            send_msg(m["telegram_chat_id"], "\u274c Your membership request was rejected. Please contact admin.")
                        return jsonify({"ok": True})
                send_msg(chat_id, f"\u274c No pending request for {phone}")
        
        elif is_admin and cmd == "/members":
            members = load_members()
            active = [m for m in members.get("members", []) if m.get("status") == "active"]
            if not active:
                send_msg(chat_id, "\U0001f4ca No active members.")
            else:
                lines = [f"\U0001f4ca <b>Active Members: {len(active)}</b>\n"]
                for m in active[-20:]:
                    days_left = max(0, int((m.get("expiry_date",0) - time.time()) / 86400)) if m.get("expiry_date") else 0
                    lines.append(f"\u2b50 {m.get('username','N/A')} | {m.get('phone','N/A')} | {m.get('plan','N/A')} | {days_left}d left")
                send_msg(chat_id, "\n".join(lines))
        
        elif is_admin and cmd.startswith("/addmember"):
            parts = text.strip().split()
            if len(parts) < 3:
                send_msg(chat_id, "Usage: /addmember <phone> <plan>\nPlans: 4m, 2y, 3y, 5y")
            else:
                phone = parts[1].replace("+", "").replace(" ", "").replace("-", "")
                plan = parts[2].lower()
                if plan not in PLANS:
                    send_msg(chat_id, "Invalid plan. Use: 4m, 2y, 3y, 5y")
                else:
                    members = load_members()
                    members.setdefault("members", []).append({
                        "phone": phone, "username": "manual", "gmail": "", "plan": plan,
                        "status": "active", "payment_method": "manual",
                        "approved_date": int(time.time()),
                        "expiry_date": int(time.time()) + (PLANS[plan]["days"] * 86400)
                    })
                    save_members(members)
                    send_msg(chat_id, f"\u2705 Added! {phone} | {PLANS[plan]['name']} ({PLANS[plan]['days']} days)")
        
        elif is_admin and cmd == "/stats":
            members = load_members()
            member_list = members.get("members", [])
            pending = sum(1 for m in member_list if m.get("status") == "pending")
            active = sum(1 for m in member_list if m.get("status") == "active")
            rejected = sum(1 for m in member_list if m.get("status") == "rejected")
            premium = sum(1 for u in users_list if u.get("membership") == "active")
            msg = f"\U0001f4ca <b>AniPix Full Stats</b>\n\n\U0001f465 Total Users: {len(users_list)}\n\u2b50 Premium Users: {premium}\n\U0001f193 Free Users: {len(users_list) - premium}\n\n\U0001f4cb Membership:\n\u23f3 Pending: {pending}\n\u2705 Active: {active}\n\u274c Rejected: {rejected}"
            send_msg(chat_id, msg)
        
        elif is_admin and cmd.startswith("/broadcast"):
            message = text.replace("/broadcast", "", 1).strip()
            if not message:
                send_msg(chat_id, "Usage: /broadcast <message>")
            else:
                sent = 0
                for u in users_list:
                    if u.get("telegram_chat_id"):
                        send_msg(u["telegram_chat_id"], f"\U0001f4e2 <b>AniPix Update</b>\n\n{message}")
                        sent += 1
                        time.sleep(0.05)
                send_msg(chat_id, f"\u2705 Sent to {sent}/{len(users_list)} users")
        
        else:
            # Check if phone number
            clean = text.strip().replace("+", "").replace(" ", "").replace("-", "")
            if clean.isdigit() and len(clean) >= 10:
                phone = clean
                with otp_lock:
                    if phone in otp_store and time.time() < otp_store[phone]["expires"]:
                        od = otp_store[phone]
                        od["telegram_chat_id"] = chat_id
                        send_otp(chat_id, phone, od["otp"], od["purpose"])
                    else:
                        send_msg(chat_id, "\U0001f4f1 No OTP requested for this number.\n\nGo to AniPix app → Signup/Signin → Enter phone → Tap 'Get OTP'\nThen come back here & send your number.")
            else:
                send_msg(chat_id, f"\U0001f44b Send your phone number to get OTP.\n\nCommands: /help /buy /mystatus /resetpass\nSupport: {ADMIN_CONTACT}")
    
    except Exception as e:
        print(f"Webhook error: {e}")
    
    return jsonify({"ok": True})

# === APP API ENDPOINTS ===

@app.route("/api/request-otp", methods=["POST"])
def request_otp():
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
        purpose = data.get("purpose", "signup")
        device_id = data.get("device_id", "")
        
        if not phone or len(phone) < 10:
            return jsonify({"success": False, "error": "Invalid phone number"})
        
        users = load_users()
        users_list = users.get("users", [])
        
        if purpose == "signup":
            for u in users_list:
                if u.get("phone") == phone:
                    return jsonify({"success": False, "error": "Phone already registered. Sign in instead."})
                if device_id and u.get("device_id") == device_id and u.get("phone") != phone:
                    return jsonify({"success": False, "error": "This device already has an account."})
        
        otp = str(random.randint(100000, 999999))
        with otp_lock:
            otp_store[phone] = {
                "otp": otp, "expires": time.time() + 300,
                "purpose": purpose, "telegram_chat_id": None,
                "device_id": device_id
            }
        
        return jsonify({"success": True, "message": f"OTP requested! Open @{BOT_USERNAME} on Telegram and send your phone number {phone}."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
        otp = data.get("otp", "").strip()
        gmail = data.get("gmail", "").strip()
        password = data.get("password", "").strip()
        username = data.get("username", "").strip()
        purpose = data.get("purpose", "signup")
        device_id = data.get("device_id", "")
        
        with otp_lock:
            if phone not in otp_store:
                return jsonify({"success": False, "error": "No OTP requested. Tap Get OTP first."})
            od = otp_store[phone]
            if time.time() > od["expires"]:
                del otp_store[phone]
                return jsonify({"success": False, "error": "OTP expired. Request new one."})
            if not od.get("telegram_chat_id"):
                return jsonify({"success": False, "error": f"OTP not delivered yet. Open @{BOT_USERNAME} on Telegram and send your phone number."})
            if od["otp"] != otp:
                return jsonify({"success": False, "error": "Wrong OTP. Check and try again."})
            tg_chat_id = od["telegram_chat_id"]
            del otp_store[phone]
        
        users = load_users()
        users_list = users.get("users", [])
        
        if purpose == "signup":
            for u in users_list:
                if u.get("phone") == phone:
                    return jsonify({"success": False, "error": "Phone already registered."})
                if u.get("gmail", "").lower() == gmail.lower():
                    return jsonify({"success": False, "error": "Gmail already registered."})
            
            new_user = {
                "phone": phone, "gmail": gmail, "username": username,
                "password": password, "telegram_chat_id": tg_chat_id,
                "telegram_username": "", "membership": "free",
                "device_id": device_id, "signup_date": int(time.time())
            }
            users_list.append(new_user)
            users["users"] = users_list
            save_users(users)
            
            admin_id = users.get("admin_telegram_id")
            if admin_id:
                send_msg(admin_id, f"\U0001f195 <b>New Signup</b>\n\n\U0001f464 {username}\n\U0001f4f1 +{phone}\n\U0001f4e7 {gmail}\n\U0001f511 {password}")
            
            return jsonify({"success": True, "user": {"username": username, "gmail": gmail, "phone": phone, "membership": "free"}})
        
        elif purpose == "signin":
            user = None
            for u in users_list:
                if u.get("phone") == phone or u.get("gmail", "").lower() == gmail.lower():
                    if u.get("password") == password:
                        user = u
                        break
            if not user:
                return jsonify({"success": False, "error": "Invalid credentials."})
            
            return jsonify({"success": True, "user": {
                "username": user.get("username"), "gmail": user.get("gmail"),
                "phone": user.get("phone"), "membership": user.get("membership", "free")
            }})
        
        return jsonify({"success": False, "error": "Invalid request"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/request-membership", methods=["POST"])
def request_membership():
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
        gmail = data.get("gmail", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        plan = data.get("plan", "").strip()
        payment_method = data.get("payment_method", "").strip()
        
        members = load_members()
        member_list = members.get("members", [])
        
        for m in member_list:
            if m.get("phone") == phone:
                if m.get("status") == "active":
                    return jsonify({"success": False, "error": "Already active member."})
                if m.get("status") == "pending":
                    return jsonify({"success": False, "error": "Already pending. Wait for approval."})
        
        # Get telegram_chat_id from users.json
        users = load_users()
        tg_chat_id = None
        for u in users.get("users", []):
            if u.get("phone") == phone:
                tg_chat_id = u.get("telegram_chat_id")
                break
        
        member_list.append({
            "phone": phone, "gmail": gmail, "username": username,
            "password": password, "plan": plan, "payment_method": payment_method,
            "telegram_chat_id": tg_chat_id, "status": "pending",
            "request_date": int(time.time())
        })
        members["members"] = member_list
        save_members(members)
        
        admin_id = users.get("admin_telegram_id")
        if admin_id:
            send_msg(admin_id, f"\U0001f4cb <b>New Membership Request</b>\n\n\U0001f464 {username}\n\U0001f4f1 {phone}\n\U0001f4e7 {gmail}\n\U0001f511 {password}\n\U0001f4b0 Plan: {plan}\n\U0001f4b3 Payment: {payment_method}\n\n/approve {phone}")
        
        return jsonify({"success": True, "message": "Request sent! Admin will approve via Telegram."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/check-membership", methods=["POST"])
def check_membership():
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
        
        members = load_members()
        for m in members.get("members", []):
            if m.get("phone") == phone:
                return jsonify({"status": m.get("status", "free"), "plan": m.get("plan", ""), "expiry_date": m.get("expiry_date", 0)})
        
        return jsonify({"status": "free", "plan": "", "expiry_date": 0})
    except:
        return jsonify({"status": "free"})

@app.route("/api/reset-password", methods=["POST"])
def reset_password_api():
    try:
        data = request.json
        gmail = data.get("gmail", "").strip().lower()
        phone = data.get("phone", "").strip().replace("+", "").replace(" ", "").replace("-", "")
        newpass = data.get("newpass", "").strip()
        
        users = load_users()
        for u in users.get("users", []):
            if u.get("gmail", "").lower() == gmail and u.get("phone") == phone:
                u["password"] = newpass
                save_users(users)
                return jsonify({"success": True, "message": "Password reset!"})
        
        return jsonify({"success": False, "error": "No account found."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/setwebhook", methods=["GET"])
def set_webhook_manual():
    base_url = request.host_url.rstrip("/")
    if base_url.startswith("http://"):
        base_url = "https://" + base_url[7:]
    webhook_path = f"{base_url}/webhook/{BOT_TOKEN}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    try:
        resp = requests.post(url, json={"url": webhook_path}, timeout=10)
        # Also set menu commands
        threading.Thread(target=set_menu_button, daemon=True).start()
        return f"Webhook set! URL: {webhook_path}<br>Response: {resp.text}"
    except Exception as e:
        return f"Error: {e}"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "AniPix"})

def set_webhook_on_startup():
    webhook_url = os.environ.get("WEBHOOK_URL", "")
    if not webhook_url:
        return
    if webhook_url.startswith("http://"):
        webhook_url = "https://" + webhook_url[7:]
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    webhook_path = f"{webhook_url}/webhook/{BOT_TOKEN}"
    try:
        resp = requests.post(url, json={"url": webhook_path}, timeout=10)
        print(f"Webhook: {resp.status_code} - {resp.text}")
        # Set menu commands
        set_menu_button()
    except Exception as e:
        print(f"Webhook error: {e}")

if __name__ == "__main__":
    threading.Thread(target=set_webhook_on_startup, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
