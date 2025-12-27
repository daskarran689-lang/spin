# -*- coding: utf-8 -*-
import os
import time
import random
import string
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Thread
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes

# ============ CONFIG ============
BOT_TOKEN = "8594188404:AAGyCFwEEeLJ5Fm92Py898GRlyYH_Uo2c5w"
ADMIN_IDS = []  # Them ID cua ban vao day, VD: [123456789]
# ================================

surnames = ['Nguyen', 'Tran', 'Le', 'Pham', 'Hoang', 'Huynh', 'Phan', 'Vu', 'Vo', 'Dang', 'Bui', 'Do', 'Ho', 'Ngo', 'Duong', 'Ly', 'Truong', 'Dinh', 'Mai', 'Trinh', 'Dao', 'Cao', 'Lam', 'Nghiem', 'Chau', 'Ta', 'Quach', 'Luong', 'Vuong', 'La']
middle_names = ['Van', 'Thi', 'Huu', 'Thanh', 'Minh', 'Duc', 'Quoc', 'Ngoc', 'Hoang', 'Xuan', 'Thu', 'Hai', 'Tuan', 'Anh', 'Phuong', 'Khanh', 'Bao', 'Gia', 'Dinh', 'Trung']
first_names = ['An', 'Binh', 'Cuong', 'Dat', 'Phong', 'Giang', 'Hai', 'Kien', 'Lam', 'Anh', 'Bich', 'Chau', 'Diem', 'Phuong', 'Hien', 'Hung', 'Dung', 'Tuan', 'Nam', 'Long', 'Hoa', 'Lan', 'Mai', 'Linh', 'Trang', 'Thao', 'Nhi', 'Vy', 'Uyen', 'Trinh']
provinces = ["Ha Noi", "TP Ho Chi Minh", "Da Nang", "Hai Phong", "Can Tho", "An Giang", "Binh Duong", "Dong Nai", "Gia Lai", "Quang Nam"]

BASE_URL = "https://spin-form.vercel.app"

# Global state
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
                    if line and ':' in line and not line.startswith('#'):
                        ip_port = line.split()[0] if ' ' in line else line
                        if not ip_port.startswith('http'):
                            ip_port = f"http://{ip_port}"
                        proxies.append(ip_port)
        except:
            pass
    
    random.shuffle(proxies)
    return list(set(proxies))[:2000]

def test_proxy(proxy):
    try:
        name = f"Test {random.randint(1000,9999)}"
        phone = f"09{random.randint(10000000,99999999)}"
        resp = requests.post(
            f"{BASE_URL}/api/public/register",
            json={"name": name, "phone": phone, "metadata": {"note": "", "address": "Ha Noi"}},
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
    with ThreadPoolExecutor(max_workers=300) as executor:
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
        if any(x in prize_lower for x in ['laptop', 'iphone', 'gấu bông', 'gau bong', 'sổ tay', 'so tay']):
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
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{random.randint(110,125)}.0.0.0',
        'Accept': '*/*',
        'Origin': BASE_URL,
        'Referer': f'{BASE_URL}/',
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

# ============ TELEGRAM HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎰 BOT SPAM VONG QUAY\n\n"
        "Lenh:\n"
        "/spam - Bat dau spam\n"
        "/stop - Dung spam\n"
        "/stats - Xem thong ke\n"
        "/winners - Xem danh sach trung\n"
        "/file - Tai file winners.txt"
    )

async def spam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global spam_running, stop_flag, count, stats, winners, working_proxies
    
    if spam_running:
        await update.message.reply_text("⚠️ Dang spam roi!")
        return
    
    await update.message.reply_text("🔄 Dang tai va test proxy...")
    
    # Reset state
    stop_flag = False
    count = 0
    stats = {}
    winners = []
    
    # Fetch proxies
    all_proxies = fetch_proxies()
    await update.message.reply_text(f"📥 Da tai {len(all_proxies)} proxy, dang test...")
    
    working_proxies = get_working_proxies(all_proxies, limit=50)
    
    if not working_proxies:
        await update.message.reply_text("❌ Khong tim thay proxy hoat dong!")
        return
    
    await update.message.reply_text(f"✅ Tim duoc {len(working_proxies)} proxy tot!\n🚀 Bat dau spam voi 50 threads...")
    
    spam_running = True
    
    # Start workers in background
    def run_spam():
        global spam_running
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
        spam_running = False
    
    Thread(target=run_spam, daemon=True).start()

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global spam_running, stop_flag
    
    if not spam_running:
        await update.message.reply_text("⚠️ Chua bat spam!")
        return
    
    stop_flag = True
    spam_running = False
    
    # Stats summary
    msg = f"🛑 Da dung spam!\n\n📊 Thong ke:\n"
    msg += f"Tong: {count} lan quay\n"
    msg += f"Trung giai: {len(winners)}\n\n"
    
    for k, v in sorted(stats.items(), key=lambda x: -x[1])[:10]:
        msg += f"• {k}: {v}\n"
    
    await update.message.reply_text(msg)

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global count, stats, winners, spam_running
    
    status = "🟢 Dang chay" if spam_running else "🔴 Da dung"
    msg = f"📊 THONG KE\n\nTrang thai: {status}\n"
    msg += f"Tong: {count} lan quay\n"
    msg += f"Trung giai: {len(winners)}\n\n"
    
    if stats:
        for k, v in sorted(stats.items(), key=lambda x: -x[1])[:10]:
            msg += f"• {k}: {v}\n"
    
    await update.message.reply_text(msg)

async def winners_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global winners
    
    if not winners:
        await update.message.reply_text("Chua trung giai nao!")
        return
    
    msg = "🏆 DANH SACH TRUNG THUONG:\n\n"
    for w in winners[-20:]:  # Last 20
        msg += f"🎁 {w['prize']}\n"
        msg += f"   {w['name']} | {w['phone']}\n"
        msg += f"   {w['link']}\n\n"
    
    await update.message.reply_text(msg)

async def file_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists("winners.txt"):
        await update.message.reply_document(
            document=open("winners.txt", "rb"),
            filename="winners.txt",
            caption="📄 File danh sach trung thuong"
        )
    else:
        await update.message.reply_text("Chua co file winners.txt!")

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Chua cau hinh BOT_TOKEN!")
        print("Mo file va thay YOUR_BOT_TOKEN_HERE bang token bot cua ban")
        return
    
    print("🤖 Dang khoi dong bot...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("spam", spam_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("winners", winners_cmd))
    app.add_handler(CommandHandler("file", file_cmd))
    
    print("✅ Bot da san sang!")
    app.run_polling()

if __name__ == "__main__":
    main()
