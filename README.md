# 🎓 Pareeksha Gurukul Refund Bot

A production-ready, fully async Telegram bot for managing student refund requests — with admin panel, plan management, analytics, and one-tap button navigation.

---

## ✨ Features

### 👨‍🎓 Student Side
- Fully button-driven, mobile-friendly flow
- 5-step guided refund application
- Upload payment screenshot
- Real-time status tracking by Ticket ID
- Instant confirmation with Ticket ID
- Cancel/back/home navigation at every step

### 👑 Admin Side
- Forward all requests to admin group with action buttons
- Approve / Decline with one tap
- Enter UTR and send confirmation to user automatically
- Add internal notes, ban users
- Manage plans (add/edit/delete/toggle)
- Analytics dashboard
- Export all data as CSV
- Broadcast messages to all users
- Manage multiple admins
- Customise all bot messages without editing code
- Toggle refund on/off instantly
- Search by Ticket ID / Mobile / Name

---

## 🗂️ Project Structure

```
pg_refund_bot/
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── nixpacks.toml            # Railway build config
├── railway.toml             # Railway deploy config
├── .env.example             # Environment variable template
├── .gitignore
│
├── config/
│   └── config.py            # All config, env vars, FSM states
│
├── database/
│   └── db.py                # SQLite layer (all CRUD operations)
│
├── handlers/
│   ├── user_handlers.py     # Student flow handlers
│   └── admin_handlers.py    # Admin panel + notify function
│
├── keyboards/
│   └── keyboards.py         # All InlineKeyboard + ReplyKeyboard builders
│
├── middlewares/
│   └── rate_limit.py        # Anti-spam rate limiting
│
└── utils/
    └── messages.py          # All message templates
```

---

## ⚙️ Setup Guide

### Step 1 — Create Bot on Telegram

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Enter bot name: `Pareeksha Gurukul Refund Bot`
4. Enter username: `pg_refund_bot` (or any available)
5. Copy the **Bot Token**

### Step 2 — Get Your Admin IDs

1. Open [@userinfobot](https://t.me/userinfobot)
2. Send `/start`
3. Copy your **User ID** (a number like `123456789`)

### Step 3 — Create Admin Group

1. Create a new Telegram group
2. Add your bot to the group
3. Make the bot an **Admin** (so it can send messages)
4. Get the group ID:
   - Add [@RawDataBot](https://t.me/RawDataBot) temporarily
   - It will show the chat ID (a negative number like `-1001234567890`)
   - Remove RawDataBot after noting the ID

### Step 4 — Configure Environment

```bash
# Clone the project or copy files
cd pg_refund_bot

# Copy and edit the .env file
cp .env.example .env
nano .env
```

Fill in your `.env`:
```env
BOT_TOKEN=7123456789:AAHxxx...
ADMIN_IDS=123456789
ADMIN_GROUP_ID=-1001234567890
```

### Step 5 — Install & Run Locally

```bash
# Install Python 3.11+ first
python --version  # should be 3.11+

# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

You should see:
```
✅ Database ready
✅ Handlers registered
🤖 Bot is polling...
```

---

## 🚂 Deploy on Railway.app

### Option A — GitHub Auto-Deploy (Recommended)

1. Push this folder to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/pg-refund-bot
   git push -u origin main
   ```

2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub Repo**

3. Select your repository

4. Go to **Variables** tab in Railway and add:
   | Key | Value |
   |-----|-------|
   | `BOT_TOKEN` | Your bot token |
   | `ADMIN_IDS` | Your Telegram user ID |
   | `ADMIN_GROUP_ID` | Admin group ID (negative number) |

5. Railway will auto-detect `nixpacks.toml` and deploy

6. Go to **Deployments** tab — wait for green ✅

### Option B — Railway CLI

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

Then add variables in the Railway dashboard.

---

## 🤖 Bot Commands

### User Commands
| Command | Action |
|---------|--------|
| `/start` | Show welcome screen |
| `/refund` | Start refund application |
| `/status` | Check your refund requests |
| `/help` | Help & support info |
| `/cancel` | Cancel current action |

### Admin Commands
| Command | Action |
|---------|--------|
| `/admin` | Open admin panel |
| `/stats` | Quick analytics |
| `/plans` | Manage plans |
| `/broadcast` | Send message to all users |
| `/export` | Download CSV of all requests |
| `/requests` | View all requests |

---

## 📋 Database Tables

| Table | Purpose |
|-------|---------|
| `users` | Student profiles, ban status |
| `refund_requests` | All refund submissions |
| `plans` | Available plans with amounts |
| `admins` | Admin user IDs |
| `settings` | Customisable bot messages |
| `logs` | Admin action audit trail |
| `sessions` | Persistent FSM state (restart-safe) |

---

## 🔐 Security Features

- All admin IDs loaded from environment variables
- SQL injection protection via parameterised queries
- File validation (images only for screenshots)
- UPI format validation with regex
- Rate limiting to prevent spam
- Banned user detection
- Admin action audit logs
- Sessions persisted in DB (restart-safe)

---

## 🔄 Refund Status Flow

```
[Student Submits] → Pending
        ↓
[Admin Reviews]
    ↙        ↘
Approved    Declined
    ↓
[UTR Entered]
    ↓
[User Notified]
```

---

## 🛠️ Customisation

### Add More Plans
Use `/admin` → **Manage Plans** → **Add Plan** in the bot.

### Change Bot Messages
Use `/admin` → **Settings** in the bot. No code editing needed.

### Add More Admins
Use `/admin` → **Manage Admins** → **Add Admin** in the bot.
Or add their ID to `ADMIN_IDS` in `.env`.

---

## 🐛 Troubleshooting

**Bot not responding?**
- Check `BOT_TOKEN` is correct in `.env`
- Check the bot is running: `python main.py`
- Check `bot.log` for errors

**Admin notifications not working?**
- Make sure bot is admin in the group
- Check `ADMIN_GROUP_ID` is correct (negative number)
- Try sending `/start` in the group to register it

**Railway deployment failing?**
- Check Python version: `nixpacks.toml` pins Python 3.11
- Check all environment variables are set in Railway dashboard
- View logs in Railway → Deployments → View Logs

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pyTelegramBotAPI` | 4.22.1 | Telegram Bot framework (async) |
| `aiosqlite` | 0.20.0 | Async SQLite database |
| `python-dotenv` | 1.0.1 | Environment variable loading |

---

## 👨‍💻 Built For

**Pareeksha Gurukul** — India's government exam prep platform for Hindi-speaking aspirants.
Covering: IB SA, KVS, NVS, EMRS, DSSSB and more.

---

*Version 1.0.0 — Production Ready*
