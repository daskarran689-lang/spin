# -*- coding: utf-8 -*-
import os
import time
import random
import string
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Thread
import telebot
from flask import Flask

# Flask app
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

@flask_app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port, threaded=True)

def keep_alive():
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    while True:
        time.sleep(600)
        if render_url:
            try:
                requests.get(f"{render_url}/health", timeout=10)
            except:
                pass

# ============ CONFIG ============
BOT_TOKEN = "8594188404:AAGyCFwEEeLJ5Fm92Py898GRlyYH_Uo2c5w"
# ================================

bot = telebot.TeleBot(BOT_TOKEN)

surnames = ['Nguyen', 'Tran', 'Le', 'Pham', 'Hoang', 'Huynh', 'Phan', 'Vu', 'Vo', 'Dang', 'Bui', 'Do', 'Ho', 'Ngo', 'Duong', 'Ly', 'Truong', 'Dinh', 'Mai', 'Trinh']
middle_names = ['Van', 'Thi', 'Huu', 'Thanh', 'Minh', 'Duc', 'Quoc', 'Ngoc', 'Hoang', 'Xuan', 'Thu', 'Hai', 'Tuan', 'Anh', 'Phuong']
first_names = ['An', 'Binh', 'Cuong', 'Dat', 'Phong', 'Giang', 'Hai', 'Kien', 'Lam', 'Anh', 'Bich', 'Chau', 'Diem', 'Phuong', 'Hien', 'Hung', 'Dung', 'Tuan', 'Nam', 'Long']
provinces = ["Ha Noi", "TP Ho Chi Minh", "Da Nang", "Hai Phong", "Can Tho", "An Giang", "Binh Duong", "Dong Nai", "Gia Lai", "Quang Nam"]

BASE_URL = "https://spin-form.vercel.app"

lock = Lock()
spam_running = False
stop_flag = False
count = 0
stats = {}
winners = []
working_proxies = []

def generate_name():
    return f"{random.choice(surnames)} {random.choice(middle_names)} {random.choice(first_names)}"

def generate_phone():
    prefix = random.choice(['090', '091', '092', '093', '094', '095', '096', '097', '098', '099'])
    return prefix + ''.join(random.choices(string.digits, k=7))

def save_winner(prize, name, phone, token):
    link = f"{BASE_URL}/spin/{token}"
    with open("winners.txt", "a", encoding="utf-8") as f:
        f.write(f"{prize} | {name} | {phone} | {link}\n")
    return link

def fetch_proxies():
    proxies = []
    sources = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    ]
    for url in sources:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                for line in resp.text.strip().split('\n'):
                    line = line.strip()
                    if line and ':' in line:
                        if not line.startswith('http'):
                            line = f"http://{line}"
                        proxies.append(line)
        except:
            pass
    random.shuffle(proxies)
    return list(set(proxies))[:2000]

def test_proxy(proxy):
    try:
        resp = requests.post(
            f"{BASE_URL}/api/public/register",
            json={"name": "Test", "phone": "0901234567", "metadata": {"note": "", "address": "Ha Noi"}},
            proxies={"http": proxy, "https": proxy},
            headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json', 'Origin': BASE_URL},
            timeout=8
        )
        if resp.status_code == 200 and 'token' in resp.text:
            return proxy
    except:
        pass
    return None

def get_working_proxies(proxies, limit=50):
    working = []
    with ThreadPoolExecutor(max_workers=200) as executor:
        futures = {executor.submit(test_proxy, p): p for p in proxies}
        for future in as_completed(futures):
            result = future.result()
            if result:
                working.append(result)
                if len(working) >= limit:
                    break
    return working

def spin_once(session, headers, proxy):
    global count, stats, winners, stop_flag
    if stop_flag:
        return None
    
    name = generate_name()
    phone = generate_phone()
    address = random.choice(provinces)
    proxies_dict = {"http": proxy, "https": proxy}
    
    try:
        resp = session.post(f"{BASE_URL}/api/public/register", 
            json={"name": name, "phone": phone, "metadata": {"note": "", "address": address}},
            headers=headers, proxies=proxies_dict, timeout=5)
        if resp.status_code != 200:
            return None
        token = resp.json().get('data', {}).get('token')
        if not token:
            return None
        
        spin_resp = session.post(f"{BASE_URL}/api/public/spin", 
            json={"token": token}, headers=headers, proxies=proxies_dict, timeout=5)
        if spin_resp.status_code != 200:
            return None
        
        result = spin_resp.json()
        prize_name = result.get('name', 'Unknown')
        
        with lock:
            count += 1
            stats[prize_name] = stats.get(prize_name, 0) + 1
        
        prize_lower = prize_name.lower()
        if any(x in prize_lower for x in ['laptop', 'iphone', 'gau bong', 'so tay', 'sổ tay', 'gấu bông']):
            link = save_winner(prize_name, name, phone, token)
            with lock:
                winners.append({"prize": prize_name, "name": name, "phone": phone, "link": link})
            return {"prize": prize_name, "name": name, "phone": phone, "link": link}
        return {"prize": prize_name}
    except:
        return None

def worker():
    global stop_flag, working_proxies
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Origin': BASE_URL,
        'Content-Type': 'application/json',
    }
    proxy_index = random.randint(0, max(0, len(working_proxies)-1))
    while not stop_flag:
        if not working_proxies:
            time.sleep(1)
            continue
        proxy = working_proxies[proxy_index % len(working_proxies)]
        spin_once(session, headers, proxy)
        proxy_index = (proxy_index + 1) % len(working_proxies)

# ============ BOT HANDLERS ============

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🎰 BOT SPAM VONG QUAY\n\n"
        "/spam - Bat dau spam\n"
        "/stop - Dung spam\n"
        "/stats - Xem thong ke\n"
        "/winners - Danh sach trung\n"
        "/file - Tai file winners.txt"
    )

@bot.message_handler(commands=['spam'])
def spam_cmd(message):
    global spam_running, stop_flag, count, stats, winners, working_proxies
    
    if spam_running:
        bot.reply_to(message, "⚠️ Dang spam roi!")
        return
    
    bot.reply_to(message, "🔄 Dang tai va test proxy...")
    
    stop_flag = False
    count = 0
    stats = {}
    winners = []
    
    all_proxies = fetch_proxies()
    bot.send_message(message.chat.id, f"📥 Da tai {len(all_proxies)} proxy, dang test...")
    
    working_proxies = get_working_proxies(all_proxies, limit=50)
    
    if not working_proxies:
        bot.send_message(message.chat.id, "❌ Khong tim thay proxy!")
        return
    
    bot.send_message(message.chat.id, f"✅ {len(working_proxies)} proxy OK!\n🚀 Bat dau spam...")
    
    spam_running = True
    
    def run_spam():
        global spam_running
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
        spam_running = False
    
    Thread(target=run_spam, daemon=True).start()

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    global spam_running, stop_flag
    
    if not spam_running:
        bot.reply_to(message, "⚠️ Chua bat spam!")
        return
    
    stop_flag = True
    spam_running = False
    
    msg = f"🛑 Da dung!\n\nTong: {count} lan\nTrung: {len(winners)}\n\n"
    for k, v in sorted(stats.items(), key=lambda x: -x[1])[:10]:
        msg += f"• {k}: {v}\n"
    
    bot.reply_to(message, msg)

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    status = "🟢 Dang chay" if spam_running else "🔴 Da dung"
    msg = f"📊 THONG KE\n\n{status}\nTong: {count}\nTrung: {len(winners)}\n\n"
    for k, v in sorted(stats.items(), key=lambda x: -x[1])[:10]:
        msg += f"• {k}: {v}\n"
    bot.reply_to(message, msg)

@bot.message_handler(commands=['winners'])
def winners_cmd(message):
    if not winners:
        bot.reply_to(message, "Chua trung giai nao!")
        return
    msg = "🏆 TRUNG THUONG:\n\n"
    for w in winners[-15:]:
        msg += f"🎁 {w['prize']}\n{w['name']} | {w['phone']}\n{w['link']}\n\n"
    bot.reply_to(message, msg)

@bot.message_handler(commands=['file'])
def file_cmd(message):
    if os.path.exists("winners.txt"):
        with open("winners.txt", "rb") as f:
            bot.send_document(message.chat.id, f, caption="📄 Winners")
    else:
        bot.reply_to(message, "Chua co file!")

def main():
    # Start Flask
    Thread(target=run_flask, daemon=True).start()
    # Start keep-alive
    Thread(target=keep_alive, daemon=True).start()
    
    print("🤖 Bot starting...")
    bot.infinity_polling()

if __name__ == "__main__":
    main()
