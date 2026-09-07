"""
AniPix Telegram Bot - v2 Complete
- Signup via bot (conversation flow)
- Signin via app (API verification, no OTP needed)
- /myprofile with edit options
- Device binding (1 phone/gmail = 1 device)
- Referral system (30 coins per referral)
- Daily login (2 coins)
- Membership management
- Push notifications
- Menu button with commands
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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Anipix_bot")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "nobelfamily537-dev/AniPix-Walls")
USERS_FILE = "users.json"
MEMBERS_FILE = "members.json"

UPI_ID = "lavkushkumar3258@nyes"
ADMIN_CONTACT = "@Lovelyanime_admin"

PLANS = {
    "4m": {"name": "4 Months", "price": 299, "days": 120},
    "2y": {"name": "2 Years", "price": 799, "days": 730},
    "3y": {"name": "3 Years", "price": 999, "days": 1095},
    "5y": {"name": "5 Years", "price": 1200, "days": 1825}
}

# Conversation state: {chat_id: {"step": "username", "data": {}}}
signup_state = {}
edit_state = {}
otp_store = {}
state_lock = threading.Lock()

# === GITHUB STORAGE ===

def load_json(filename, default):
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{filename}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return default

def save_json(filename, data):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
        resp = requests.get(url, headers=headers, timeout=10)
        sha = resp.json().get("sha") if resp.status_code == 200 else None
        content = json.dumps(data, indent=2)
        b64 = base64.b64encode(content.encode()).decode()
        payload = {"message": f"Update {filename}", "content": b64, "branch": "main"}
        if sha:
            payload["sha"] = sha
        resp = requests.put(url, headers=headers, json=payload, timeout=10)
        return resp.status_code in [200, 201]
    except Exception as e:
        print(f"Save error: {e}")
        return False

def load_users():
    return load_json(USERS_FILE, {"users": [], "admin_telegram_id": None})

def save_users(d):
    return save_json(USERS_FILE, d)

def load_members():
    return load_json(MEMBERS_FILE, {"members": []})

def save_members(d):
    return save_json(MEMBERS_FILE, d)

def send_msg(chat_id, text, keyboard=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if keyboard:
            data["reply_markup"] = json.dumps(keyboard)
        requests.post(url, json=data, timeout=10)
    except:
        pass

def get_cmd(text):
    return text.strip().split("@")[0].lower().strip()

def set_menu():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
        user_cmds = [
            {"command": "start", "description": "Start AniPix Bot"},
            {"command": "signup", "description": "Create new account"},
            {"command": "login", "description": "Login to your account"},
            {"command": "myprofile", "description": "View/edit your profile"},
            {"command": "buy", "description": "Buy Premium membership"},
            {"command": "mystatus", "description": "Check membership status"},
            {"command": "help", "description": "Get help & instructions"},
            {"command": "referral", "description": "Get your referral code"},
        ]
        requests.post(url, json={"commands": user_cmds}, timeout=10)
        users = load_users()
        admin_id = users.get("admin_telegram_id")
        if admin_id:
            admin_cmds = user_cmds + [
                {"command": "users", "description": "All users with details"},
                {"command": "pending", "description": "Pending membership requests"},
                {"command": "approve", "description": "Approve: /approve <phone>"},
                {"command": "reject", "description": "Reject: /reject <phone>"},
                {"command": "members", "description": "Active members"},
                {"command": "addmember", "description": "Add: /addmember <phone> <plan>"},
                {"command": "stats", "description": "Full statistics"},
                {"command": "broadcast", "description": "Broadcast: /broadcast <msg>"},
            ]
            requests.post(url, json={"commands": admin_cmds, "scope": {"type": "chat", "chat_id": int(admin_id)}}, timeout=10)
    except:
        pass

# === COUNTRY CODES ===
COUNTRY_CODES = {
    "91": "India", "1": "USA/Canada", "44": "UK", "92": "Pakistan",
    "880": "Bangladesh", "971": "UAE", "977": "Nepal", "94": "Sri Lanka",
    "60": "Malaysia", "65": "Singapore", "66": "Thailand", "81": "Japan",
    "82": "Korea", "86": "China", "62": "Indonesia", "63": "Philippines",
    "55": "Brazil", "49": "Germany", "33": "France", "39": "Italy",
    "34": "Spain", "7": "Russia", "27": "South Africa", "234": "Nigeria",
    "20": "Egypt", "966": "Saudi Arabia", "965": "Kuwait", "974": "Qatar",
    "968": "Oman", "973": "Bahrain", "856": "Laos", "84": "Vietnam",
    "855": "Cambodia", "95": "Myanmar", "93": "Afghanistan", "98": "Iran",
    "964": "Iraq", "962": "Jordan", "972": "Israel", "961": "Lebanon",
    "90": "Turkey", "998": "Uzbekistan", "992": "Tajikistan", "996": "Kyrgyzstan",
    "380": "Ukraine", "48": "Poland", "31": "Netherlands", "32": "Belgium",
    "41": "Switzerland", "45": "Denmark", "46": "Sweden", "47": "Norway",
    "358": "Finland", "351": "Portugal", "30": "Greece", "36": "Hungary",
    "420": "Czech", "421": "Slovakia", "40": "Romania", "385": "Croatia",
    "386": "Slovenia", "52": "Mexico", "54": "Argentina", "56": "Chile",
    "57": "Colombia", "58": "Venezuela", "51": "Peru", "591": "Bolivia",
    "595": "Paraguay", "598": "Uruguay", "53": "Cuba", "809": "Dominican",
    "61": "Australia", "64": "New Zealand", "675": "PNG", "678": "Vanuatu",
    "679": "Fiji", "682": "Cook Islands", "685": "Samoa", "686": "Kiribati",
    "687": "New Caledonia", "689": "Tahiti", "250": "Rwanda", "254": "Kenya",
    "255": "Tanzania", "256": "Uganda", "260": "Zambia", "263": "Zimbabwe",
    "265": "Malawi", "233": "Ghana", "225": "Ivory Coast", "227": "Niger",
    "228": "Togo", "229": "Benin", "221": "Senegal", "222": "Mauritania",
    "223": "Mali", "224": "Guinea", "225": "Ivory Coast", "226": "Burkina",
    "227": "Niger", "228": "Togo", "229": "Benin",
}

# === WEBHOOK HANDLER ===

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
        
        # Check if user is in signup conversation
        with state_lock:
            if chat_id in signup_state:
                return handle_signup_step(chat_id, text, user_info)
            if chat_id in edit_state:
                return handle_edit_step(chat_id, text)
        
        # === ADMIN SETUP ===
        if not admin_id:
            if cmd == "/setup":
                users["admin_telegram_id"] = str(chat_id)
                users["admin_username"] = sender_username
                save_users(users)
                send_msg(chat_id, "\u2705 <b>Admin Set!</b>\n\nCommands:\n/users - All users\n/pending - Pending requests\n/approve <phone> - Approve\n/reject <phone> - Reject\n/members - Active members\n/stats - Statistics\n/broadcast <msg> - Broadcast")
                threading.Thread(target=set_menu, daemon=True).start()
            else:
                send_msg(chat_id, "\U0001f527 Bot needs setup. Owner send /setup")
            return jsonify({"ok": True})
        
        # === USER COMMANDS ===
        
        if cmd == "/start":
            # Check if already registered
            user = find_user_by_chat(users_list, chat_id)
            if user:
                send_msg(chat_id, f"\U0001f44b Welcome back, <b>{user['username']}</b>!\n\nUse /myprofile to view your profile\nUse /buy to buy premium\nUse /help for all commands")
            else:
                send_msg(chat_id, f"""\U0001f31f <b>Welcome to AniPix Bot!</b>

To use AniPix app, you need to signup first!

<b>Signup steps:</b>
1\ufe0f\u20e3 Tap /signup below
2\ufe0f\u20e3 Enter username, gmail, phone, password
3\ufe0f\u20e3 Account created!
4\ufe0f\u20e3 Open AniPix app & login

<b>Commands:</b>
/signup - Create account
/login - Login
/myprofile - View/edit profile
/buy - Buy premium
/help - Get help

\U0001f4ac Support: {ADMIN_CONTACT}""")
        
        elif cmd == "/signup":
            user = find_user_by_chat(users_list, chat_id)
            if user:
                send_msg(chat_id, "\u2705 You already have an account! Use /myprofile to view it.")
                return jsonify({"ok": True})
            with state_lock:
                signup_state[chat_id] = {"step": "username", "data": {}}
            send_msg(chat_id, "\U0001f511 <b>Sign Up - Step 1/5</b>\n\nEnter your <b>username</b> (min 3 characters):\n\nType /cancel to cancel")
        
        elif cmd == "/login":
            user = find_user_by_chat(users_list, chat_id)
            if user:
                send_msg(chat_id, f"\u2705 You're logged in!\n\nUsername: {user['username']}\nGmail: {user['gmail']}\n\nOpen AniPix app and login with your gmail/username + password.")
            else:
                send_msg(chat_id, "\u274c You need to signup first! Tap /signup")
        
        elif cmd == "/myprofile":
            user = find_user_by_chat(users_list, chat_id)
            if not user:
                send_msg(chat_id, "\u274c No account found. Tap /signup to create one.")
                return jsonify({"ok": True})
            coins = user.get("coins", 0)
            phone = user.get("phone", "N/A")
            mem = user.get("membership", "free")
            ref_code = user.get("referral_code", user.get("phone", "N/A"))
            ref_count = user.get("referral_count", 0)
            profile = f"""\U0001f464 <b>Your Profile</b>

\U0001f194 Username: <b>{user['username']}</b>
\U0001f4e7 Gmail: <code>{user['gmail']}</code>
\U0001f4f1 Phone: <code>+{phone}</code>
\U0001f511 Password: <code>{user['password']}</code>
\U0001f4b0 Coins: <b>{coins}</b>
\u2b50 Membership: <b>{mem}</b>
\U0001f381 Referral Code: <code>{ref_code}</code>
\U0001f465 Referrals: {ref_count}

<b>Edit options:</b>
/changename - Change username
/changemail - Change gmail
/changephone - Change phone
/changepass - Change password"""
            send_msg(chat_id, profile)
        
        elif cmd == "/changename":
            user = find_user_by_chat(users_list, chat_id)
            if not user:
                send_msg(chat_id, "\u274c Signup first! /signup")
                return jsonify({"ok": True})
            with state_lock:
                edit_state[chat_id] = {"step": "changename", "user_phone": user["phone"]}
            send_msg(chat_id, "Enter new username:")
        
        elif cmd == "/changemail":
            user = find_user_by_chat(users_list, chat_id)
            if not user:
                send_msg(chat_id, "\u274c Signup first! /signup")
                return jsonify({"ok": True})
            with state_lock:
                edit_state[chat_id] = {"step": "changemail", "user_phone": user["phone"]}
            send_msg(chat_id, "Enter new gmail address:")
        
        elif cmd == "/changephone":
            user = find_user_by_chat(users_list, chat_id)
            if not user:
                send_msg(chat_id, "\u274c Signup first! /signup")
                return jsonify({"ok": True})
            with state_lock:
                edit_state[chat_id] = {"step": "changephone", "user_phone": user["phone"]}
            send_msg(chat_id, "Enter new phone number with country code (e.g., +91 8409143258):")
        
        elif cmd == "/changepass":
            user = find_user_by_chat(users_list, chat_id)
            if not user:
                send_msg(chat_id, "\u274c Signup first! /signup")
                return jsonify({"ok": True})
            with state_lock:
                edit_state[chat_id] = {"step": "changepass", "user_phone": user["phone"]}
            send_msg(chat_id, "Enter new password:")
        
        elif cmd == "/referral":
            user = find_user_by_chat(users_list, chat_id)
            if not user:
                send_msg(chat_id, "\u274c Signup first! /signup")
                return jsonify({"ok": True})
            ref_code = user.get("referral_code", user.get("phone", "N/A"))
            ref_count = user.get("referral_count", 0)
            coins = user.get("coins", 0)
            send_msg(chat_id, f"\U0001f381 <b>Referral Program</b>\n\nYour referral code: <code>{ref_code}</code>\nTotal referrals: {ref_count}\nCoins earned: {ref_count * 30}\n\nShare your code! When someone signs up with your code, you get <b>30 coins</b>!")
        
        elif cmd == "/buy":
            buy_text = f"""\u2b50 <b>AniPix Premium Membership</b>

<b>Plans:</b>
\U0001f4b0 4 Months - Rs.299
\U0001f4b0 2 Years - Rs.799
\U0001f4b0 3 Years - Rs.999
\U0001f4b0 5 Years - Rs.1200

<b>Payment Methods:</b>

\U0001f4f1 <b>UPI:</b> <code>{UPI_ID}</code>
(GPay, PhonePe, Paytm)

\U0001f381 <b>Amazon Voucher:</b> Send gift card code
\U0001f381 <b>Flipkart Voucher:** Send gift card code

<b>After Payment:</b>
1. Take screenshot
2. Send to {ADMIN_CONTACT}
3. Open AniPix app \u2192 Settings \u2192 Premium
4. Tap "Request Admin to Approve"
5. Wait for approval here!

\U0001f4ac Support: {ADMIN_CONTACT}"""
            send_msg(chat_id, buy_text)
        
        elif cmd == "/mystatus":
            user = find_user_by_chat(users_list, chat_id)
            if not user:
                send_msg(chat_id, "\u274c Signup first! /signup")
                return jsonify({"ok": True})
            members = load_members()
            member = None
            for m in members.get("members", []):
                if m.get("phone") == user.get("phone"):
                    member = m
                    break
            if member and member.get("status") == "active":
                days = max(0, int((member.get("expiry_date",0) - time.time()) / 86400))
                send_msg(chat_id, f"\u2b50 <b>Premium Active</b>\nPlan: {member.get('plan','N/A')}\nDays left: {days}")
            elif member and member.get("status") == "pending":
                send_msg(chat_id, "\u23f3 <b>Pending</b> - Waiting for admin approval")
            else:
                send_msg(chat_id, "\U0001f193 <b>Free Account</b>\nBuy premium: /buy")
        
        elif cmd == "/help":
            send_msg(chat_id, f"""\U0001f4cb <b>AniPix Bot - Help</b>

\U0001f511 <b>Signup:</b> Tap /signup to create account

\U0001f4ac <b>Login in App:</b>
After signup, open AniPix app
Login with gmail/username + password

\U0001f464 <b>Profile:</b> /myprofile
Edit: /changename /changemail /changephone /changepass

\u2b50 <b>Buy Premium:</b> /buy
\U0001f4cb <b>Status:</b> /mystatus
\U0001f381 <b>Referral:</b> /referral

\U0001f4ac <b>Need help?</b> Contact: {ADMIN_CONTACT}
Send payment screenshot to admin.""")
        
        elif cmd == "/cancel":
            with state_lock:
                signup_state.pop(chat_id, None)
                edit_state.pop(chat_id, None)
            send_msg(chat_id, "\u274c Cancelled. Tap /signup to try again.")
        
        # === ADMIN COMMANDS ===
        
        elif is_admin and cmd in ["/users", "/user"]:
            if not users_list:
                send_msg(chat_id, "\U0001f4ca No users yet.")
            else:
                lines = [f"\U0001f4ca <b>Users: {len(users_list)}</b>\n"]
                for u in users_list:
                    lines.append(f"\U0001f194 {u.get('username','N/A')}\n\U0001f4e7 {u.get('gmail','N/A')}\n\U0001f4f1 +{u.get('phone','N/A')}\n\U0001f511 {u.get('password','N/A')}\n\U0001f4ac @{u.get('telegram_username','N/A')}\n\U0001f4b0 {u.get('coins',0)} coins\n---")
                msg = "\n".join(lines)
                if len(msg) > 4000:
                    for i in range(0, len(lines), 8):
                        send_msg(chat_id, "\n".join(lines[i:i+8]))
                        time.sleep(0.1)
                else:
                    send_msg(chat_id, msg)
        
        elif is_admin and cmd == "/pending":
            members = load_members()
            pending = [m for m in members.get("members", []) if m.get("status") == "pending"]
            if not pending:
                send_msg(chat_id, "\u2705 No pending requests.")
            else:
                lines = [f"\U0001f4cb <b>Pending: {len(pending)}</b>\n"]
                for m in pending:
                    lines.append(f"\U0001f464 {m.get('username','N/A')}\n\U0001f4f1 {m.get('phone','N/A')}\n\U0001f4e7 {m.get('gmail','N/A')}\n\U0001f4b0 {m.get('plan','N/A')}\n/approve {m.get('phone','')}\n---")
                send_msg(chat_id, "\n".join(lines))
        
        elif is_admin and cmd.startswith("/approve"):
            parts = text.strip().split()
            if len(parts) < 2:
                send_msg(chat_id, "Usage: /approve <phone>")
            else:
                phone = parts[1].replace("+","").replace(" ","").replace("-","")
                members = load_members()
                for m in members.get("members", []):
                    if m.get("phone") == phone and m.get("status") == "pending":
                        m["status"] = "active"
                        m["approved_date"] = int(time.time())
                        plan = m.get("plan", "4m")
                        days = PLANS.get(plan, PLANS["4m"])["days"]
                        m["expiry_date"] = int(time.time()) + (days * 86400)
                        save_members(members)
                        send_msg(chat_id, f"\u2705 Approved! {m.get('username','')} | {phone} | {PLANS.get(plan,{}).get('name',plan)}")
                        if m.get("telegram_chat_id"):
                            send_msg(m["telegram_chat_id"], f"\u2b50 <b>Premium Activated!</b>\nPlan: {PLANS.get(plan,{}).get('name',plan)}\nValid: {days} days\n\nEnjoy! \U0001f389")
                        for u in users_list:
                            if u.get("phone") == phone:
                                u["membership"] = "active"
                                save_users(users)
                                break
                        return jsonify({"ok": True})
                send_msg(chat_id, f"\u274c No pending for {phone}")
        
        elif is_admin and cmd.startswith("/reject"):
            parts = text.strip().split()
            if len(parts) < 2:
                send_msg(chat_id, "Usage: /reject <phone>")
            else:
                phone = parts[1].replace("+","").replace(" ","").replace("-","")
                members = load_members()
                for m in members.get("members", []):
                    if m.get("phone") == phone and m.get("status") == "pending":
                        m["status"] = "rejected"
                        save_members(members)
                        send_msg(chat_id, f"\u274c Rejected {phone}")
                        if m.get("telegram_chat_id"):
                            send_msg(m["telegram_chat_id"], "\u274c Request rejected. Contact admin.")
                        return jsonify({"ok": True})
                send_msg(chat_id, f"\u274c No pending for {phone}")
        
        elif is_admin and cmd == "/members":
            members = load_members()
            active = [m for m in members.get("members", []) if m.get("status") == "active"]
            if not active:
                send_msg(chat_id, "No active members.")
            else:
                lines = [f"Active Members: {len(active)}\n"]
                for m in active[-20:]:
                    d = max(0, int((m.get("expiry_date",0) - time.time()) / 86400)) if m.get("expiry_date") else 0
                    lines.append(f"\u2b50 {m.get('username','')} | {m.get('phone','')} | {m.get('plan','')} | {d}d")
                send_msg(chat_id, "\n".join(lines))
        
        elif is_admin and cmd.startswith("/addmember"):
            parts = text.strip().split()
            if len(parts) < 3:
                send_msg(chat_id, "Usage: /addmember <phone> <plan>\nPlans: 4m,2y,3y,5y")
            else:
                phone = parts[1].replace("+","").replace(" ","").replace("-","")
                plan = parts[2].lower()
                if plan not in PLANS:
                    send_msg(chat_id, "Invalid plan. Use: 4m,2y,3y,5y")
                else:
                    members = load_members()
                    members.setdefault("members", []).append({
                        "phone": phone, "username": "manual", "plan": plan,
                        "status": "active", "approved_date": int(time.time()),
                        "expiry_date": int(time.time()) + (PLANS[plan]["days"] * 86400)
                    })
                    save_members(members)
                    send_msg(chat_id, f"\u2705 Added {phone} | {PLANS[plan]['name']}")
        
        elif is_admin and cmd == "/stats":
            members = load_members()
            ml = members.get("members", [])
            pending = sum(1 for m in ml if m.get("status") == "pending")
            active = sum(1 for m in ml if m.get("status") == "active")
            premium = sum(1 for u in users_list if u.get("membership") == "active")
            total_coins = sum(u.get("coins", 0) for u in users_list)
            total_refs = sum(u.get("referral_count", 0) for u in users_list)
            send_msg(chat_id, f"\U0001f4ca <b>AniPix Stats</b>\n\n\U0001f465 Users: {len(users_list)}\n\u2b50 Premium: {premium}\n\U0001f193 Free: {len(users_list)-premium}\n\U0001f4b0 Total Coins: {total_coins}\n\U0001f381 Referrals: {total_refs}\n\n\U0001f4cb Pending: {pending}\n\u2705 Active Members: {active}")
        
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
                send_msg(chat_id, f"\u2705 Sent to {sent}/{len(users_list)}")
        
        else:
            clean = text.strip().replace("+", "").replace(" ", "").replace("-", "")
            if clean.isdigit() and len(clean) >= 10:
                # Check OTP store for this number
                if clean in otp_store and time.time() < otp_store[clean]["expires"]:
                    od = otp_store[clean]
                    od["telegram_chat_id"] = chat_id
                    send_msg(chat_id, f"\U0001f510 OTP: <b>{od['otp']}</b>\nPhone: +{clean}\nExpires in 5 min")
                else:
                    send_msg(chat_id, "\U0001f4f1 No OTP requested. Use /signup to create account or /help for instructions.")
            else:
                send_msg(chat_id, f"\U0001f44b Use /signup to create account or /help for commands.\nSupport: {ADMIN_CONTACT}")
    
    except Exception as e:
        print(f"Webhook error: {e}")
    
    return jsonify({"ok": True})

# === HELPER FUNCTIONS ===

def find_user_by_chat(users_list, chat_id):
    for u in users_list:
        if str(u.get("telegram_chat_id", "")) == str(chat_id):
            return u
    return None

def find_user_by_phone(users_list, phone):
    for u in users_list:
        if u.get("phone") == phone:
            return u
    return None

def find_user_by_gmail(users_list, gmail):
    for u in users_list:
        if u.get("gmail", "").lower() == gmail.lower():
            return u
    return None

def handle_signup_step(chat_id, text, user_info):
    """Handle multi-step signup conversation"""
    with state_lock:
        state = signup_state.get(chat_id)
        if not state:
            return jsonify({"ok": True})
        
        step = state["step"]
        data = state["data"]
        cmd = get_cmd(text)
        
        if cmd == "/cancel":
            signup_state.pop(chat_id, None)
            send_msg(chat_id, "\u274c Signup cancelled. Tap /signup to try again.")
            return jsonify({"ok": True})
        
        if step == "username":
            username = text.strip()
            if len(username) < 3:
                send_msg(chat_id, "\u274c Username min 3 characters. Try again:")
                return jsonify({"ok": True})
            users = load_users()
            for u in users.get("users", []):
                if u.get("username", "").lower() == username.lower():
                    send_msg(chat_id, "\u274c Username taken. Enter different:")
                    return jsonify({"ok": True})
            data["username"] = username
            state["step"] = "gmail"
            send_msg(chat_id, f"\u2705 Username: {username}\n\n\U0001f511 <b>Step 2/5</b>\n\nEnter your <b>Gmail address</b>:\n\nType /cancel to cancel")
        
        elif step == "gmail":
            gmail = text.strip().lower()
            if "@" not in gmail or "gmail" not in gmail and "googlemail" not in gmail:
                if "@" not in gmail:
                    send_msg(chat_id, "\u274c Enter valid email with @. Try again:")
                    return jsonify({"ok": True})
            users = load_users()
            for u in users.get("users", []):
                if u.get("gmail", "").lower() == gmail:
                    send_msg(chat_id, "\u274c Gmail registered. Use different or /login:")
                    return jsonify({"ok": True})
            data["gmail"] = gmail
            state["step"] = "phone"
            send_msg(chat_id, f"\u2705 Gmail: {gmail}\n\n\U0001f511 <b>Step 3/5</b>\n\nEnter your <b>phone number with country code</b>:\nExample: +91 8409143258\n\nType /cancel to cancel")
        
        elif step == "phone":
            phone_raw = text.strip()
            # Parse phone number
            phone = phone_raw.replace("+", "").replace(" ", "").replace("-", "")
            if not phone.isdigit() or len(phone) < 10:
                send_msg(chat_id, "\u274c Invalid phone. Enter like: +91 8409143258")
                return jsonify({"ok": True})
            users = load_users()
            for u in users.get("users", []):
                if u.get("phone") == phone:
                    send_msg(chat_id, "\u274c Phone registered. Use different or /login:")
                    return jsonify({"ok": True})
            data["phone"] = phone
            state["step"] = "password"
            send_msg(chat_id, f"\u2705 Phone: +{phone}\n\n\U0001f511 <b>Step 4/5</b>\n\nEnter your <b>password</b> (min 4 characters):\n\nType /cancel to cancel")
        
        elif step == "password":
            password = text.strip()
            if len(password) < 4:
                send_msg(chat_id, "\u274c Password min 4 characters. Try again:")
                return jsonify({"ok": True})
            data["password"] = password
            state["step"] = "referral"
            send_msg(chat_id, f"\u2705 Password set\n\n\U0001f511 <b>Step 5/5</b>\n\nEnter <b>referral code</b> (or type 'none' if you don't have one):\n\nType /cancel to cancel")
        
        elif step == "referral":
            ref_input = text.strip()
            users = load_users()
            users_list = users.get("users", [])
            ref_user = None
            if ref_input.lower() != "none" and ref_input:
                # Find referrer by phone or username
                for u in users_list:
                    if u.get("phone") == ref_input.replace("+","").replace(" ","") or u.get("username","").lower() == ref_input.lower():
                        ref_user = u
                        break
            
            # Create account
            new_user = {
                "username": data["username"],
                "gmail": data["gmail"],
                "phone": data["phone"],
                "password": data["password"],
                "telegram_chat_id": str(chat_id),
                "telegram_username": user_info.get("username", ""),
                "membership": "free",
                "coins": 10,  # Welcome bonus
                "referral_code": data["phone"],
                "referral_count": 0,
                "referred_by": ref_user.get("phone", "") if ref_user else "",
                "device_id": "",
                "signup_date": int(time.time())
            }
            users_list.append(new_user)
            users["users"] = users_list
            save_users(users)
            
            # Give referrer 30 coins
            if ref_user:
                for u in users_list:
                    if u.get("phone") == ref_user.get("phone"):
                        u["coins"] = u.get("coins", 0) + 30
                        u["referral_count"] = u.get("referral_count", 0) + 1
                        break
                save_users(users)
                if ref_user.get("telegram_chat_id"):
                    send_msg(ref_user["telegram_chat_id"], f"\U0001f381 <b>Referral Bonus!</b>\n\n{data['username']} signed up with your code!\nYou earned <b>30 coins</b>! \U0001f4b0")
            
            signup_state.pop(chat_id, None)
            
            send_msg(chat_id, f"""\u2705 <b>Account Created!</b>

\U0001f194 Username: {data['username']}
\U0001f4e7 Gmail: {data['gmail']}
\U0001f4f1 Phone: +{data['phone']}
\U0001f511 Password: {data['password']}
\U0001f4b0 Coins: 10 (welcome bonus)
\U0001f381 Referral Code: {data['phone']}

<b>Now open AniPix app and login!</b>
Login with your gmail/username + password.

Use /myprofile to view/edit your profile.""")
            
            # Notify admin
            admin_id = users.get("admin_telegram_id")
            if admin_id:
                send_msg(admin_id, f"\U0001f195 <b>New Signup</b>\n\n\U0001f194 {data['username']}\n\U0001f4f1 +{data['phone']}\n\U0001f4e7 {data['gmail']}\n\U0001f511 {data['password']}\n\U0001f4ac @{user_info.get('username','N/A')}")
    
    return jsonify({"ok": True})

def handle_edit_step(chat_id, text):
    """Handle profile edit conversation"""
    with state_lock:
        state = edit_state.get(chat_id)
        if not state:
            return jsonify({"ok": True})
        
        step = state["step"]
        user_phone = state["user_phone"]
        cmd = get_cmd(text)
        
        if cmd == "/cancel":
            edit_state.pop(chat_id, None)
            send_msg(chat_id, "\u274c Cancelled. /myprofile to view profile.")
            return jsonify({"ok": True})
        
        users = load_users()
        users_list = users.get("users", [])
        user = find_user_by_phone(users_list, user_phone)
        if not user:
            edit_state.pop(chat_id, None)
            send_msg(chat_id, "\u274c Account not found.")
            return jsonify({"ok": True})
        
        if step == "changename":
            newname = text.strip()
            if len(newname) < 3:
                send_msg(chat_id, "\u274c Min 3 chars. Try again:")
                return jsonify({"ok": True})
            user["username"] = newname
            save_users(users)
            edit_state.pop(chat_id, None)
            send_msg(chat_id, f"\u2705 Username changed to: {newname}")
        
        elif step == "changemail":
            newmail = text.strip().lower()
            if "@" not in newmail:
                send_msg(chat_id, "\u274c Invalid email. Try again:")
                return jsonify({"ok": True})
            user["gmail"] = newmail
            save_users(users)
            edit_state.pop(chat_id, None)
            send_msg(chat_id, f"\u2705 Gmail changed to: {newmail}")
        
        elif step == "changephone":
            phone = text.strip().replace("+","").replace(" ","").replace("-","")
            if not phone.isdigit() or len(phone) < 10:
                send_msg(chat_id, "\u274c Invalid phone. Try again:")
                return jsonify({"ok": True})
            user["phone"] = phone
            user["referral_code"] = phone
            save_users(users)
            edit_state.pop(chat_id, None)
            send_msg(chat_id, f"\u2705 Phone changed to: +{phone}")
        
        elif step == "changepass":
            newpass = text.strip()
            if len(newpass) < 4:
                send_msg(chat_id, "\u274c Min 4 chars. Try again:")
                return jsonify({"ok": True})
            user["password"] = newpass
            save_users(users)
            edit_state.pop(chat_id, None)
            send_msg(chat_id, f"\u2705 Password changed!")
    
    return jsonify({"ok": True})

# === APP API ENDPOINTS ===

@app.route("/api/login", methods=["POST"])
def api_login():
    """App calls this to verify login (no OTP needed)"""
    try:
        data = request.json
        login_input = data.get("login", "").strip()
        password = data.get("password", "").strip()
        device_id = data.get("device_id", "")
        
        if not login_input or not password:
            return jsonify({"success": False, "error": "Enter gmail/username and password"})
        
        users = load_users()
        users_list = users.get("users", [])
        
        user = None
        for u in users_list:
            if u.get("gmail", "").lower() == login_input.lower() or u.get("username", "").lower() == login_input.lower() or u.get("phone") == login_input.replace("+","").replace(" ",""):
                if u.get("password") == password:
                    user = u
                    break
        
        if not user:
            return jsonify({"success": False, "error": "Wrong credentials. Signup via bot first."})
        
        # Check device binding
        if device_id and user.get("device_id") and user["device_id"] != device_id:
            return jsonify({"success": False, "error": "This account is linked to another device."})
        
        # Set device ID if not set
        if device_id and not user.get("device_id"):
            user["device_id"] = device_id
            save_users(users)
        
        return jsonify({
            "success": True,
            "user": {
                "username": user.get("username"),
                "gmail": user.get("gmail"),
                "phone": user.get("phone"),
                "membership": user.get("membership", "free"),
                "coins": user.get("coins", 0)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/daily-login", methods=["POST"])
def api_daily_login():
    """App calls this on startup for daily login reward"""
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+","").replace(" ","").replace("-","")
        
        users = load_users()
        users_list = users.get("users", [])
        
        for u in users_list:
            if u.get("phone") == phone:
                today = time.strftime("%Y-%m-%d")
                last_login = u.get("last_daily_login", "")
                if last_login != today:
                    u["coins"] = u.get("coins", 0) + 2
                    u["last_daily_login"] = today
                    save_users(users)
                    return jsonify({"success": True, "coins": u["coins"], "reward": 2})
                return jsonify({"success": True, "coins": u.get("coins", 0), "reward": 0})
        
        return jsonify({"success": False, "error": "User not found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/request-otp", methods=["POST"])
def request_otp():
    """Legacy OTP for password reset verification"""
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+","").replace(" ","").replace("-","")
        purpose = data.get("purpose", "reset")
        
        users = load_users()
        for u in users.get("users", []):
            if u.get("phone") == phone:
                otp = str(random.randint(100000, 999999))
                otp_store[phone] = {
                    "otp": otp, "expires": time.time() + 300,
                    "purpose": purpose, "telegram_chat_id": None
                }
                return jsonify({"success": True, "message": f"Send your number to @{BOT_USERNAME} to get OTP"})
        
        return jsonify({"success": False, "error": "Phone not registered. Signup via bot first."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/request-membership", methods=["POST"])
def request_membership():
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+","").replace(" ","").replace("-","")
        gmail = data.get("gmail", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        plan = data.get("plan", "").strip()
        payment_method = data.get("payment_method", "").strip()
        
        members = load_members()
        ml = members.get("members", [])
        
        for m in ml:
            if m.get("phone") == phone:
                if m.get("status") == "active":
                    return jsonify({"success": False, "error": "Already active member."})
                if m.get("status") == "pending":
                    return jsonify({"success": False, "error": "Already pending."})
        
        users = load_users()
        tg_chat_id = None
        for u in users.get("users", []):
            if u.get("phone") == phone:
                tg_chat_id = u.get("telegram_chat_id")
                break
        
        ml.append({
            "phone": phone, "gmail": gmail, "username": username,
            "password": password, "plan": plan, "payment_method": payment_method,
            "telegram_chat_id": tg_chat_id, "status": "pending",
            "request_date": int(time.time())
        })
        members["members"] = ml
        save_members(members)
        
        admin_id = users.get("admin_telegram_id")
        if admin_id:
            send_msg(admin_id, f"\U0001f4cb <b>Membership Request</b>\n\n\U0001f464 {username}\n\U0001f4f1 {phone}\n\U0001f4e7 {gmail}\n\U0001f511 {password}\n\U0001f4b0 {plan}\n\U0001f4b3 {payment_method}\n\n/approve {phone}")
        
        return jsonify({"success": True, "message": "Request sent! Admin will approve via Telegram."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/check-membership", methods=["POST"])
def check_membership():
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+","").replace(" ","").replace("-","")
        members = load_members()
        for m in members.get("members", []):
            if m.get("phone") == phone:
                return jsonify({"status": m.get("status","free"), "plan": m.get("plan",""), "expiry_date": m.get("expiry_date",0)})
        return jsonify({"status": "free", "plan": "", "expiry_date": 0})
    except:
        return jsonify({"status": "free"})

@app.route("/api/get-coins", methods=["POST"])
def get_coins():
    try:
        data = request.json
        phone = data.get("phone", "").strip().replace("+","").replace(" ","").replace("-","")
        users = load_users()
        for u in users.get("users", []):
            if u.get("phone") == phone:
                return jsonify({"coins": u.get("coins", 0)})
        return jsonify({"coins": 0})
    except:
        return jsonify({"coins": 0})

@app.route("/setwebhook", methods=["GET"])
def set_webhook_manual():
    base_url = request.host_url.rstrip("/")
    if base_url.startswith("http://"):
        base_url = "https://" + base_url[7:]
    webhook_path = f"{base_url}/webhook/{BOT_TOKEN}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    try:
        resp = requests.post(url, json={"url": webhook_path}, timeout=10)
        threading.Thread(target=set_menu, daemon=True).start()
        return f"Webhook set! URL: {webhook_path}<br>Response: {resp.text}"
    except Exception as e:
        return f"Error: {e}"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "AniPix v2"})

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "alive"})

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
        set_menu()
    except Exception as e:
        print(f"Webhook error: {e}")

if __name__ == "__main__":
    threading.Thread(target=set_webhook_on_startup, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
