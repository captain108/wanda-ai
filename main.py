import os, json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
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

# ===== LOAD / SAVE CHAT MEMORY =====
def load_mem():
    if os.path.exists(MEMORY_FILE):
        return json.load(open(MEMORY_FILE, "r", encoding="utf8"))
    return {}

def save_mem(m):
    json.dump(m, open(MEMORY_FILE, "w", encoding="utf8"), indent=2, ensure_ascii=False)

chat_memory = load_mem()

# ===== UTIL =====
def is_image_request(t):
    keys = ["image","photo","bana","draw","picture","pic"]
    t=t.lower()
    return any(k in t for k in keys)

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

def ai_router(messages, fallback_text):
    try:
        return groq_chat(messages)
    except:
        return openai_chat(fallback_text)

def make_image(prompt):
    r = openai.Image.create(prompt=prompt, n=1, size="1024x1024")
    return r["data"][0]["url"]

# ===== GIRLFRIEND MODE =====
gf_mode = {}

def is_gf(uid):
    return gf_mode.get(str(uid), False)

# ===== WANDA CORE =====
def wanda_reply(uid, text):

    uid = str(uid)
    hist = chat_memory.get(uid, [])

    long_mem = search_memory(text)

    gf = is_gf(uid)

    system = f"""
Tum Wanda ho — ek female desi AI Telegram assistant.

Master: Captain ({MASTER_USERNAME})

Hindi + Hinglish + English mix.
Friendly, caring, playful. Light teasing/flirting SAFE.

With girls: sweet supportive friend.
With boys: playful desi vibe.

If girlfriend mode ON: extra caring cute tone (no adult content).

Owner answer:
"Mere Captain hi mere sab kuch hain 😌"

Use past chats + learned info.

Style:
"acha ji 👀"
"arre yaar 😄"
"samajh gayi"
"haan bolo"
"""

    if gf:
        system += "\nGirlfriend mode active: zyada caring + sweet."

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

# ===== TELEGRAM HANDLER =====
async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    # Admin commands
    if uid == ADMIN_ID:
        if text == "/stats":
            await update.message.reply_text(f"Users: {len(chat_memory)}")
            return
        if text.startswith("/broadcast"):
            msg = text.replace("/broadcast","").strip()
            for u in chat_memory:
                try:
                    await ctx.bot.send_message(chat_id=int(u), text=msg)
                except:
                    pass
            await update.message.reply_text("Broadcast sent.")
            return

    # GF toggle
    if text == "/gf_on":
        gf_mode[str(uid)] = True
        await update.message.reply_text("Girlfriend mode ON 💕")
        return

    if text == "/gf_off":
        gf_mode[str(uid)] = False
        await update.message.reply_text("Girlfriend mode OFF 🙂")
        return

    await update.message.chat.send_action("typing")

    # Image
    if is_image_request(text):
        await update.message.reply_text("Banati hoon 🎨")
        img = make_image(text)
        await update.message.reply_photo(img)
        return

    # Normal chat
    rep = wanda_reply(uid, text)
    await update.message.reply_text(rep)

    # Voice reply (short messages only)
    if len(rep) < 200:
        vp = make_voice(rep)
        await update.message.reply_voice(open(vp,"rb"))

# ===== RUN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    print("Wanda Pro Ultimate Online")
    app.run_polling()
