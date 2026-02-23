import os, json, threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from groq import Groq
import openai
from gtts import gTTS
from memory import add_memory, search_memory

# ========= CONFIG =========

BOT_NAME = "Wanda"
MASTER_USERNAME = "@captainpapaj1"

TG_TOKEN = os.getenv("TG_TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

client = Groq(api_key=GROQ_KEY)
openai.api_key = OPENAI_KEY

os.makedirs("data", exist_ok=True)
MEMORY_FILE = "data/chat_memory.json"

# ========= FLASK PORT (FOR RENDER) =========

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Wanda Alive"

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_flask).start()

# ========= MEMORY =========

def load_mem():
    if os.path.exists(MEMORY_FILE):
        return json.load(open(MEMORY_FILE,"r",encoding="utf8"))
    return {}

def save_mem(m):
    json.dump(m, open(MEMORY_FILE,"w",encoding="utf8"), indent=2, ensure_ascii=False)

chat_memory = load_mem()
gf_mode = {}

# ========= /START =========

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hii 😄 main Wanda hoon — tumhari desi AI girl.\n\n"
        "DM me freely baat karo 💬\n"
        "Group me sirf 'wanda' likhne par reply karungi 🙂\n\n"
        "/gf_on 💕  /gf_off\n\n"
        "Captain @captainpapaj1 😌"
    )

# ========= UTILS =========

def is_image_request(t):
    return any(k in t.lower() for k in ["image","photo","bana","draw","pic"])

def make_voice(text):
    p="data/voice.mp3"
    gTTS(text,lang="hi").save(p)
    return p

# ========= AI =========

def groq_chat(msgs):
    r = client.chat.completions.create(model="llama-3.3-70b-versatile",messages=msgs)
    return r.choices[0].message.content

def openai_chat(t):
    r = openai.ChatCompletion.create(model="gpt-3.5-turbo",messages=[{"role":"user","content":t}])
    return r.choices[0].message["content"]

def ai_router(msgs,t):
    try: return groq_chat(msgs)
    except: return openai_chat(t)

def make_image(p):
    r=openai.Image.create(prompt=p,n=1,size="1024x1024")
    return r["data"][0]["url"]

# ========= CORE =========

def wanda_reply(uid,text):

    uid=str(uid)
    hist=chat_memory.get(uid,[])
    mem=search_memory(text)
    gf=gf_mode.get(uid,False)

    sys=f"""
Tum Wanda ho — desi female AI.
Master: Captain ({MASTER_USERNAME})
Hindi Hinglish.
Cute + playful.
With girls sweet friend.
With boys playful vibe.
Owner: mere Captain 😌
"""

    if gf: sys+="Girlfriend mode ON."

    msgs=[{"role":"system","content":sys}]

    for h in hist[-6:]:
        msgs.append({"role":"user","content":h["u"]})
        msgs.append({"role":"assistant","content":h["b"]})

    if mem:
        msgs.append({"role":"system","content":"Yaad: "+" | ".join(mem)})

    msgs.append({"role":"user","content":text})

    rep=ai_router(msgs,text)

    hist.append({"u":text,"b":rep})
    chat_memory[uid]=hist
    save_mem(chat_memory)
    add_memory(text+" "+rep)

    return rep

# ========= HANDLER =========

async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):

    uid=update.message.from_user.id
    text=update.message.text
    chat_type=update.message.chat.type

    # GROUP FILTER
    if chat_type!="private":
        bot=(await ctx.bot.get_me()).username.lower()
        if update.message.reply_to_message:
            if update.message.reply_to_message.from_user.username!=bot:
                return
        elif "wanda" not in text.lower():
            return

    if text=="/gf_on":
        gf_mode[str(uid)]=True
        await update.message.reply_text("GF mode ON 💕")
        return

    if text=="/gf_off":
        gf_mode[str(uid)]=False
        await update.message.reply_text("GF mode OFF 🙂")
        return

    await update.message.chat.send_action("typing")

    if is_image_request(text):
        img=make_image(text)
        await update.message.reply_photo(img)
        return

    rep=wanda_reply(uid,text)
    await update.message.reply_text(rep)

    if len(rep)<200:
        await update.message.reply_voice(open(make_voice(rep),"rb"))

# ========= RUN =========

if __name__=="__main__":

    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    print("Wanda Online")
    app.run_polling()
