import json
import logging
import datetime
import os
from pyrogram.enums import ParseMode
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# ---------------- BOT CONFIG ----------------
API_ID = 22966373
API_HASH = "dc4be1428eac263b307ef770a81e7649"
BOT_TOKEN = "7975956795:AAECLVuGj1IATyQtO5h8Sjtxup11x2r0rYE"
MAIN_CHANNEL_ID = -1003084513981
MAIN_CHANNEL_USERNAME = "kdramaspaceio"
OWNER_ID = 5871400868
DATA_FILE = "kdrama_db.json"
POSTER_DIR = "posters"
USERS_FILE = "users.json"  # to track users who used the bot
DAILY_STATS_FILE = "daily_stats.json"  # for daily/monthly counts

# --------------------------------------------

# ---------------- LOGGING -------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# --------------------------------------------

# ---------------- CLIENT --------------------
app = Client("kdrama_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- INIT ----------------------
if not os.path.exists(POSTER_DIR):
    os.makedirs(POSTER_DIR)

try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        kdrama_db = json.load(f)
except FileNotFoundError:
    kdrama_db = {}

# ---------------- HELPER FUNCTIONS ----------------
def save_db():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(kdrama_db, f, ensure_ascii=False, indent=4)

def extract_info(caption: str) -> dict:
    info = {
        "title": None,
        "original_title": None,
        "other_names": None,
        "genres": [],
        "episodes": None,
        "network": [],
        "country": None,
        "quality": None,
        "audio": None,
        "cast": [],
        "subtitles": None
    }
    lines = [line.strip() for line in caption.splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        low = line.lower()
        if info["title"] is None and not low.startswith(("genres", "title :", "native title", "also known as", "cast")):
            info["title"] = line
        elif low.startswith("genres"):
            genres_str = line.split(":", 1)[1].strip()
            info["genres"] = [g.strip() for g in genres_str.split(",") if g.strip()]
        elif low.startswith("episodes"):
            try:
                info["episodes"] = int(line.split(":", 1)[1].strip())
            except:
                info["episodes"] = None
        elif low.startswith("original network"):
            networks_str = line.split(":", 1)[1].strip()
            info["network"] = [n.strip() for n in networks_str.split(",") if n.strip()]
        elif low.startswith("country"):
            info["country"] = line.split(":", 1)[1].strip()
        elif "p version" in low:
            info["quality"] = line
        elif low.startswith("audio"):
            info["audio"] = line.split(":", 1)[1].strip()
        elif low.startswith("title :"):
            info["title"] = line.split(":", 1)[1].strip()
        elif low.startswith("native title"):
            info["original_title"] = line.split(":", 1)[1].strip()
        elif low.startswith("also known as"):
            info["other_names"] = line.split(":", 1)[1].strip()
        elif low.startswith("cast"):
            cast_str = line.split(":", 1)[1].strip()
            info["cast"] = [c.strip() for c in cast_str.split(",") if c.strip()]
        # Detect last line as subtitles if not matched already
        if idx == len(lines) - 1 and "subtitle" in line.lower():
            info["subtitles"] = line
    return info

def find_next_poster_filename():
    existing = os.listdir(POSTER_DIR)
    n = 1
    while f"poster{n}.jpg" in existing:
        n += 1
    return os.path.join(POSTER_DIR, f"poster{n}.jpg")

def find_drama(query: str):
    query = query.lower()
    matches = []
    for drama_id, data in kdrama_db.items():
        title = data.get("title", "").lower()
        original_title = (data.get("original_title") or "").lower()
        other_names = (data.get("other_names") or "").lower()
        cast_list = [c.lower() for c in data.get("cast", [])]
        if query in title or query in original_title or query in other_names or query in cast_list:
            matches.append(data)
    return matches

def build_caption(drama: dict):
    title = drama.get("title", "Unknown")
    post_link = drama.get("post_link", "")

    # Title as clickable link (HTML style)
    caption_lines = [f'🎬 <a href="{post_link}">{title}</a>\n']

    # Middle content
    middle = []
    
    if drama.get("episodes"):
        middle.append(f"⟣• Episodes: {drama['episodes']}")

    if drama.get("genres"):
        cleaned_genres = []
        for g in drama['genres']:
            g = g.replace(":", "").strip()
            if g:
                cleaned_genres.append(f"#{g}")
        if cleaned_genres:
            middle.append(f"⟣• Genres: {' '.join(cleaned_genres)}")

    if drama.get("network"):
        middle.append(f"⟣• Network: {', '.join(drama['network'])}")

    if drama.get("country"):
        middle.append(f"⟣• Country: {drama['country']}")

    middle.append(f"⟣• Quality: {drama.get('quality', 'None')}")

    audio = drama.get("audio")
    if not audio or audio.strip().lower() in ["none", "not specified", ""]:
        audio = "Korean"
    middle.append(f"⟣• Audio: {audio}")

    subtitles = drama.get("subtitles", "ENGLISH SUBTITLE")
    middle.append(f"⟣• Subtitles: {subtitles}")

    # Wrap middle section inside <pre> to make black box
    block = ["🌸━━━━━━━━━━━━━━━━━━━🌸"] + middle + ["🌸━━━━━━━━━━━━━━━━━━━🌸"]
    blockquote = "<pre>" + "\n".join(block) + "</pre>"

    caption_lines.append(blockquote)

    return "\n".join(caption_lines)
# ---------------- COMMANDS ----------------
@app.on_message(filters.command("start") & filters.private)
def start(client, message):
    # Save the user
    save_users(message.from_user.id, message.from_user.username or "N/A")

    welcome_text = (
        f"🌸 Welcome to [Kspace.io!](https://t.me/kdramaspaceio)! 🌸\n\n"
        "✨ Daily episodes & English subs\n"
        f"💌 Main channel: [Join Here](https://t.me/{MAIN_CHANNEL_USERNAME})\n"
        f"👤 powered by [androbots](https://t.me/androbots)\n"
        f"🧾 how to search: [read guide](https://telegra.ph/Searching-guide-for-kspaceio-09-03)"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search Kdrama", callback_data="search_drama")]
    ])
    message.reply_text(welcome_text, reply_markup=markup, disable_web_page_preview=False)
# ---------------- HELPER FUNCTIONS ----------------
def save_users(user_id, username):
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    except FileNotFoundError:
        users = []

    # avoid duplicates
    if not any(u["id"] == user_id for u in users):
        users.append({"id": user_id, "username": username})
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)


def save_request_stats(user_id, title):
    today = datetime.date.today().isoformat()
    try:
        with open(DAILY_STATS_FILE, "r") as f:
            stats = json.load(f)
    except FileNotFoundError:
        stats = {}

    stats.setdefault("requests", {})
    stats.setdefault("users", {})
    stats.setdefault("daily", {})
    stats.setdefault("monthly", {})

    # Track request counts
    stats["requests"][title] = stats["requests"].get(title, 0) + 1
    stats["users"][str(user_id)] = stats["users"].get(str(user_id), 0) + 1
    stats["daily"][today] = stats["daily"].get(today, 0) + 1
    month = today[:7]
    stats["monthly"][month] = stats["monthly"].get(month, 0) + 1

    with open(DAILY_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)


def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def load_stats():
    try:
        with open(DAILY_STATS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# ---------------- ADMIN PANEL ----------------
@app.on_message(filters.command("admin") & filters.private)
def admin_panel(client, message):
    if message.from_user.id != OWNER_ID:
        message.reply_text("❌ You are not authorized.")
        return

    message.reply_text(
        "🌸 Admin Panel 🌸\n\nSelect a function below:",
        reply_markup=get_admin_markup()
    )

# ---------------- HELPER FOR MARKUPS ----------------
def get_admin_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📄 Database", callback_data="admin_database")],
        [InlineKeyboardButton("🎭 Dramas", callback_data="admin_dramas")]
    ])

def get_back_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]])

# ---------------- CALLBACK HANDLER ----------------
@app.on_callback_query(filters.regex(r"admin_"))
def admin_callbacks(client, callback_query):
    if callback_query.from_user.id != OWNER_ID:
        callback_query.answer("❌ Unauthorized", show_alert=True)
        return

    data = callback_query.data
    msg = callback_query.message

    # ---------- USERS ----------
    if data == "admin_users":
        users = load_users()
        if not users:
            callback_query.answer("⚠️ No users recorded yet.", show_alert=True)
            return

        users_txt_path = "users.txt"
        with open(users_txt_path, "w", encoding="utf-8") as f:
            for u in users:
                f.write(f"{u['id']} | @{u.get('username','N/A')}\n")

        msg.edit_text("👥 Users list sent as document.", reply_markup=get_back_markup())
        msg.reply_document(users_txt_path, quote=True)
        callback_query.answer()

    # ---------- STATS ----------
    elif data == "admin_stats":
        stats = load_stats()
        top_titles = sorted(stats.get("requests", {}).items(), key=lambda x: x[1], reverse=True)[:5]
        top_users = sorted(stats.get("users", {}).items(), key=lambda x: x[1], reverse=True)[:5]
        daily_total = sum(stats.get("daily", {}).values())
        monthly_total = sum(stats.get("monthly", {}).values())
        total_users = len(load_users())

        text = "📊 Stats Panel 📊\n\n"
        text += f"Total Users: {total_users}\nDaily Requests: {daily_total}\nMonthly Requests: {monthly_total}\n\n"
        text += "Top 5 Requested Titles:\n" + "\n".join([f"{t[0]} ({t[1]})" for t in top_titles]) + "\n\n"
        text += "Best Users (Top 5 by requests):\n" + "\n".join([f"{u[0]} ({u[1]})" for u in top_users])

        msg.edit_text(text, reply_markup=get_back_markup())
        callback_query.answer()

    # ---------- DATABASE ----------
    elif data == "admin_database":
        json_path = DATA_FILE
        msg.reply_document(json_path, quote=True)
        msg.edit_text("📄 Database file sent.", reply_markup=get_back_markup())
        callback_query.answer()

    # ---------- DRAMAS ----------
    elif data == "admin_dramas":
        if not kdrama_db:
            callback_query.answer("⚠️ No dramas saved yet.", show_alert=True)
            return

        total_dramas = len(kdrama_db)
        total_casts = sum(len(d.get("cast", [])) if d.get("cast") else 0 for d in kdrama_db.values())
        total_networks = sum(len(d.get("network", [])) if d.get("network") else 0 for d in kdrama_db.values())

        # Count countries
        country_count = {}
        for d in kdrama_db.values():
            country = d.get("country") or "Unknown"
            country_count[country] = country_count.get(country, 0) + 1
        countries_text = ', '.join([f"{c} - {n}" for c, n in country_count.items()])

        text = f"🎭 Drama Stats 🎭\n\n"
        text += f"Total Dramas: {total_dramas}\n"
        text += f"Total Casts Recorded: {total_casts}\n"
        text += f"Total Networks Count: {total_networks}\n"
        text += f"Countries: {countries_text}"

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📃 List", callback_data="admin_dramas_list")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
        ])
        msg.edit_text(text, reply_markup=markup)
        callback_query.answer()

    # ---------- DRAMAS LIST ----------
    elif data == "admin_dramas_list":
        list_path = "dramas_list.txt"
        with open(list_path, "w", encoding="utf-8") as f:
            f.write("🌸━━━━━━━━━━━━━━━━━━━🌸\n")
            for d in kdrama_db.values():
                title = d.get("title", "Unknown")
                link = d.get("post_link", "#")
                f.write(f"⟣• [{title}]({link})\n")
            f.write("🌸━━━━━━━━━━━━━━━━━━━🌸\n")

        msg.reply_document(list_path, quote=True)
        msg.edit_text("📃 Drama list sent.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="admin_dramas")]
        ]))
        callback_query.answer()

    # ---------- BACK ----------
    elif data == "admin_back":
        msg.edit_text("🌸 Admin Panel 🌸\n\nSelect a function below:", reply_markup=get_admin_markup())
        callback_query.answer()
# ---------------- HANDLE FORWARDED POSTERS (OWNER ONLY) ----------------

@app.on_message(filters.forwarded & filters.private)
def handle_forward(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        message.reply_text("❌ You are not authorized to save posters.")
        return
    if not message.caption:
        message.reply_text("⚠️ Poster must have a caption.")
        return
    if not message.photo:
        message.reply_text("⚠️ Poster must be a photo.")
        return

    poster_path = find_next_poster_filename()
    message.download(file_name=poster_path)
    info = extract_info(message.caption)
    original_id = getattr(message, "forward_from_message_id", message.id)
    info["poster_path"] = poster_path
    info["post_link"] = f"https://t.me/{MAIN_CHANNEL_USERNAME}/{original_id}"
    info["files"] = []

    drama_id = f"{info['title'].lower()}_{original_id}"
    kdrama_db[drama_id] = info
    save_db()

    logger.info(f"Saved drama: {info['title']} ({original_id})")
    message.reply_text(f"✅ Saved drama: {info['title']}")

# ---------------- CALLBACK FOR SEARCH BUTTON ----------------
@app.on_callback_query(filters.regex("search_drama"))
def search_callback(client, callback_query):
    callback_query.message.reply("📺 Please type the full name of the drama:")
    callback_query.answer()

# ---------------- HANDLE SEARCH ----------------
@app.on_message(filters.text & filters.private)
def search_drama_handler(client, message):
    query = message.text.strip()

    # If admin is sending a flyer, ignore this message as a search
    if message.from_user.id == OWNER_ID:
        return  # Admin is sending flyer, not searching

    # Save user and request stats (skip admin for stats)
    if message.from_user.id != OWNER_ID:
        save_users(message.from_user.id, message.from_user.username or "N/A")
        save_request_stats(message.from_user.id, query)

    results = find_drama(query)
    if not results:
        message.reply_text(
            f"Sorry, I couldn’t find any results for: {query}.\n"
            "Please check the spelling or google for the full title.💜."
        )
        return

    exact_match = None
    for r in results:
        if query.lower() in r["title"].lower():
            exact_match = r
            break

    drama = exact_match or results[0]
    caption = build_caption(drama)

    try:
        client.send_photo(
            chat_id=message.chat.id,
            photo=drama["poster_path"],
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("➡️ Watch Now", url=drama["post_link"])]]
            ),
        )
    except Exception as e:
        logger.error(f"Error sending drama poster: {e}")
        message.reply_text(f"⚠️ Error sending drama: {e}")
# ---------------- RUN BOT ----------------
logger.info("Bot is running...")
app.run()

