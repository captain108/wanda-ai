import os, json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from groq import Groq
import openai
from gtts import gTTS
from memory import add_memory, search_memory

# ===== CONFIG =====

BOT_NAME = "Wanda"
MASTER_USERNAME = "@captainpapaj1"

TG_TOKEN = os.getenv("TG_TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

client = Groq(api_key=GROQ_KEY)
openai.api_key = OPENAI_KEY

MEMORY_FILE = "data/chat_memory.json"
os.makedirs("data", exist_ok=True)

# ===== LOAD MEMORY =====

def load_mem():
    if os.path.exists(MEMORY_FILE):
        return json.load(open(MEMORY_FILE, "r", encoding="utf8"))
    return {}

def save_mem(m):
    json.dump(m, open(MEMORY_FILE, "w", encoding="utf8"), indent=2, ensure_ascii=False)

chat_memory = load_mem()

gf_mode = {}

# ===== /start =====

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hii 😄 main Wanda hoon — tumhari desi AI girl.\n\n"
        "DM me mujhse normally baat karo 💬\n"
        "Group me sirf 'wanda' likhne par reply karungi 🙂\n\n"
        "Girlfriend mode: /gf_on 💕\n"
        "Band karna: /gf_off\n\n"
        "Aur haan… mere Captain @captainpapaj1 hain 😌"
    )

# ===== UTIL =====

def is_image_request(t):
    keys = ["image","photo","bana","draw","picture","pic"]
    return any(k in t.lower() for k in keys)

def make_voice(text):
    tts = gTTS(text, lang="hi")
    path = "data/voice.mp3"
    tts.save(path)
    return path

# ===== AI ROUTER =====

def groq_chat(messages):
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )
    return r.choices[0].message.content

def openai_chat(text):
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":text}]
    )
    return r.choices[0].message["content"]

def ai_router(messages, fallback):
    try:
        return groq_chat(messages)
    except:
        return openai_chat(fallback)

def make_image(prompt):
    r = openai.Image.create(prompt=prompt, n=1, size="1024x1024")
    return r["data"][0]["url"]

# ===== WANDA CORE =====

def wanda_reply(uid, text):

    uid = str(uid)
    hist = chat_memory.get(uid, [])

    long_mem = search_memory(text)

    gf = gf_mode.get(uid, False)

    system = f"""
Tum Wanda ho — ek female desi AI Telegram assistant.

Master: Captain ({MASTER_USERNAME})

Hindi + Hinglish + English mix.
Friendly, caring, playful. Light teasing only.

With girls: sweet friend.
With boys: playful vibe.

Girlfriend mode gives extra caring tone (safe).

Owner reply:
"Mere Captain hi mere sab kuch hain 😌"

Style:
"acha ji 👀"
"arre yaar 😄"
"samajh gayi"
"haan bolo"
"""

    if gf:
        system += "\nGirlfriend mode ON: zyada cute + caring."

    msgs = [{"role":"system","content":system}]

    for h in hist[-6:]:
        msgs.append({"role":"user","content":h["u"]})
        msgs.append({"role":"assistant","content":h["b"]})

    if long_mem:
        msgs.append({"role":"system","content":"Yaad aaya: " + " | ".join(long_mem)})

    msgs.append({"role":"user","content":text})

    reply = ai_router(msgs, text)

    hist.append({"u":text,"b":reply})
    chat_memory[uid] = hist
    save_mem(chat_memory)

    add_memory(text + " " + reply)

    return reply

# ===== MAIN HANDLER =====

async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):

    uid = update.message.from_user.id
    text = update.message.text
    chat_type = update.message.chat.type

    # ===== GROUP FILTER =====
    if chat_type != "private":

        bot = await ctx.bot.get_me()
        bot_username = bot.username.lower()

        # Reply only if reply to Wanda OR 'wanda' mentioned
        if update.message.reply_to_message:
            if not update.message.reply_to_message.from_user or update.message.reply_to_message.from_user.username != bot_username:
                return
        elif "wanda" not in text.lower():
            return

    # ===== ADMIN =====
    if uid == ADMIN_ID:
        if text == "/stats":
            await update.message.reply_text(f"Users: {len(chat_memory)}")
            return

    # ===== GF MODE =====
    if text == "/gf_on":
        gf_mode[str(uid)] = True
        await update.message.reply_text("Girlfriend mode ON 💕")
        return

    if text == "/gf_off":
        gf_mode[str(uid)] = False
        await update.message.reply_text("Girlfriend mode OFF 🙂")
        return

    await update.message.chat.send_action("typing")

    # ===== IMAGE =====
    if is_image_request(text):
        await update.message.reply_text("Banati hoon 🎨")
        img = make_image(text)
        await update.message.reply_photo(img)
        return

    # ===== CHAT =====
    rep = wanda_reply(uid, text)
    await update.message.reply_text(rep)

    # ===== VOICE =====
    if len(rep) < 200:
        vp = make_voice(rep)
        await update.message.reply_voice(open(vp,"rb"))

# ===== RUN =====

if __name__ == "__main__":
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    print("Wanda Online")
    app.run_polling()
