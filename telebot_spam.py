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

BOT_TOKEN = "8594188404:AAGyCFwEEeLJ5Fm92Py898GRlyYH_Uo2c5w"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

SUPABASE_URL = "https://xlsqhhniznmjgzqgwywq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhsc3FoaG5pem5tamd6cWd3eXdxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4MTM3MDYsImV4cCI6MjA4MjM4OTcwNn0.RxzefQNzdDWFuNIpE7pez9gZlzA7NmBmOkxw26Bji9s"

surnames = ['Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Huỳnh', 'Phan', 'Vũ', 'Võ', 'Đặng', 'Bùi', 'Đỗ', 'Hồ', 'Ngô', 'Dương', 'Lý', 'Trương', 'Đinh', 'Mai', 'Trịnh', 'Đào', 'Cao', 'Lâm', 'Nghiêm', 'Châu', 'Tạ', 'Quách', 'Lương', 'Vương', 'La', 'Nhân', 'Tôn', 'Thạch', 'Kiều', 'Mạch', 'Triệu', 'Bạch', 'Kim', 'Hà', 'Tống']
middle_names = ['Văn', 'Thị', 'Hữu', 'Thanh', 'Minh', 'Đức', 'Quốc', 'Ngọc', 'Hoàng', 'Xuân', 'Thu', 'Hải', 'Tuấn', 'Anh', 'Phương', 'Khánh', 'Bảo', 'Gia', 'Đình', 'Trung', 'Hồng', 'Kim', 'Thùy', 'Mỹ', 'Cẩm', 'Diệu', 'Tuyết', 'Quỳnh', 'Như', 'Bích']
first_names = ['An', 'Bình', 'Cường', 'Đạt', 'Phong', 'Giang', 'Hải', 'Kiên', 'Lâm', 'Ánh', 'Bích', 'Châu', 'Diễm', 'Phương', 'Hiền', 'Hùng', 'Dũng', 'Tuấn', 'Nam', 'Long', 'Hoa', 'Lan', 'Mai', 'Linh', 'Trang', 'Thảo', 'Nhi', 'Vy', 'Uyên', 'Trinh', 'Tâm', 'Khoa', 'Thịnh', 'Phúc', 'Lộc', 'Tài', 'Nhân', 'Nghĩa', 'Tín', 'Sáng', 'Quang', 'Vinh', 'Huy', 'Khang', 'Minh', 'Tiến', 'Trung', 'Sơn', 'Đức', 'Thắng']
provinces = ["Hà Nội", "TP Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", "An Giang", "Bình Dương", "Đồng Nai", "Gia Lai", "Quảng Nam"]

BASE_URL = "https://spin-form.vercel.app"

lock = Lock()
spam_running = False
stop_flag = False
count = 0
stats = {}
winners = []
working_proxies = []
status_msg_id = None
status_chat_id = None

def generate_name():
    return f"{random.choice(surnames)} {random.choice(middle_names)} {random.choice(first_names)}"

def generate_phone():
    prefix = random.choice(['090', '091', '092', '093', '094', '095', '096', '097', '098', '099'])
    return prefix + ''.join(random.choices(string.digits, k=7))

def save_winner(prize, name, phone, token):
    link = f"{BASE_URL}/spin/{token}"
    with open("winners.txt", "a", encoding="utf-8") as f:
        f.write(f"{prize} | {name} | {phone} | {link}\n")
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/winners",
            json={"prize": prize, "name": name, "phone": phone, "link": link},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"},
            timeout=5
        )
    except:
        pass
    return link

def get_winners_from_db():
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/winners?order=created_at.desc&limit=20",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return []

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
            json={"name": "Test", "phone": "0901234567", "metadata": {"note": "", "address": "Hà Nội"}},
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
    global count, stats, winners, stop_flag, status_msg_id, status_chat_id
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
        if any(x in prize_lower for x in ['laptop', 'iphone', 'gấu bông', 'sổ tay']):
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

def update_status():
    global status_msg_id, status_chat_id, spam_running, count, stats, winners, stop_flag
    last_count = 0
    while spam_running and not stop_flag:
        time.sleep(5)
        if status_msg_id and status_chat_id and count != last_count:
            last_count = count
            try:
                msg = f"""
🎰 <b>ĐANG QUAY...</b>

━━━━━━━━━━━━━━━━━━━━━━━━
📊 Tổng lượt: <code>{count}</code>
🏆 Trúng giải: <code>{len(winners)}</code>
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>THỐNG KÊ:</b>
"""
                for k, v in sorted(stats.items(), key=lambda x: -x[1])[:5]:
                    msg += f"  • {k}: <code>{v}</code>\n"
                msg += "\n⏳ <i>Cập nhật mỗi 5 giây...</i>"
                bot.edit_message_text(msg, status_chat_id, status_msg_id)
            except:
                pass

@bot.message_handler(commands=['start'])
def start(message):
    msg = """
🎰 <b>BOT SPAM VÒNG QUAY MAY MẮN</b> 🎰

━━━━━━━━━━━━━━━━━━━━━━━━

📋 <b>DANH SÁCH LỆNH:</b>

  🚀 /spam   ➜  Bắt đầu quay
  🛑 /stop   ➜  Dừng quay
  📊 /stats  ➜  Xem thống kê
  🏆 /winners ➜  Danh sách trúng
  📄 /file   ➜  Tải file kết quả

━━━━━━━━━━━━━━━━━━━━━━━━

💡 <i>Bot sẽ tự động thông báo khi trúng giải lớn!</i>
🎁 <i>Giải theo dõi: Laptop, iPhone, Gấu bông, Sổ tay</i>
"""
    bot.reply_to(message, msg)

@bot.message_handler(commands=['spam'])
def spam_cmd(message):
    global spam_running, stop_flag, count, stats, winners, working_proxies, status_msg_id, status_chat_id
    
    if spam_running:
        bot.reply_to(message, "⚠️ <b>Bot đang chạy rồi!</b>\n\n💡 Dùng /stop để dừng trước.")
        return
    
    status_chat_id = message.chat.id
    msg = bot.reply_to(message, "🔄 <b>Đang tải danh sách proxy...</b>\n\n⏳ <i>Vui lòng chờ...</i>")
    status_msg_id = msg.message_id
    
    stop_flag = False
    count = 0
    stats = {}
    winners = []
    
    all_proxies = fetch_proxies()
    bot.edit_message_text(f"""📥 Đã tải <b>{len(all_proxies)}</b> proxy

🔍 <b>Đang kiểm tra proxy...</b>
⏳ <i>Quá trình này mất khoảng 1-2 phút</i>""", status_chat_id, status_msg_id)
    
    working_proxies = get_working_proxies(all_proxies, limit=50)
    
    if not working_proxies:
        bot.edit_message_text("""❌ <b>KHÔNG TÌM THẤY PROXY!</b>

😔 Tất cả proxy đều không hoạt động.
💡 Vui lòng thử lại sau ít phút.""", status_chat_id, status_msg_id)
        return
    
    msg = f"""
✅ <b>SẴN SÀNG QUAY!</b>

━━━━━━━━━━━━━━━━━━━━━━━━
🌐 <b>Proxy:</b> <code>{len(working_proxies)}</code> hoạt động
🚀 <b>Threads:</b> <code>50</code> luồng
━━━━━━━━━━━━━━━━━━━━━━━━

🎰 <b>ĐANG QUAY...</b>

📊 Tổng lượt: <code>0</code>
🏆 Trúng giải: <code>0</code>

⏳ <i>Cập nhật mỗi 5 giây...</i>
"""
    bot.edit_message_text(msg, status_chat_id, status_msg_id)
    
    spam_running = True
    
    def run_spam():
        global spam_running
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
        spam_running = False
    
    Thread(target=run_spam, daemon=True).start()
    Thread(target=update_status, daemon=True).start()

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    global spam_running, stop_flag, status_msg_id, status_chat_id
    
    if not spam_running:
        bot.reply_to(message, "⚠️ <b>Bot chưa chạy!</b>\n\n💡 Dùng /spam để bắt đầu.")
        return
    
    stop_flag = True
    spam_running = False
    
    msg = f"""
🛑 <b>ĐÃ DỪNG QUAY!</b>

━━━━━━━━━━━━━━━━━━━━━━━━
📊 Tổng lượt quay: <code>{count}</code>
🏆 Số giải trúng: <code>{len(winners)}</code>
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>THỐNG KÊ CHI TIẾT:</b>
"""
    for k, v in sorted(stats.items(), key=lambda x: -x[1])[:10]:
        msg += f"  • {k}: <code>{v}</code>\n"
    
    msg += "\n💡 <i>Dùng /winners để xem danh sách trúng thưởng</i>"
    
    if status_msg_id and status_chat_id:
        try:
            bot.edit_message_text(msg, status_chat_id, status_msg_id)
        except:
            bot.reply_to(message, msg)
    else:
        bot.reply_to(message, msg)

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    status = "🟢 <b>ĐANG CHẠY</b>" if spam_running else "🔴 <b>ĐÃ DỪNG</b>"
    msg = f"""
📊 <b>THỐNG KÊ HIỆN TẠI</b>

━━━━━━━━━━━━━━━━━━━━━━━━
{status}
━━━━━━━━━━━━━━━━━━━━━━━━

📈 Tổng lượt quay: <code>{count}</code>
🏆 Số giải trúng: <code>{len(winners)}</code>

📋 <b>CHI TIẾT GIẢI:</b>
"""
    if stats:
        for k, v in sorted(stats.items(), key=lambda x: -x[1])[:10]:
            msg += f"  • {k}: <code>{v}</code>\n"
    else:
        msg += "  <i>Chưa có dữ liệu</i>\n"
    bot.reply_to(message, msg)

@bot.message_handler(commands=['winners'])
def winners_cmd(message):
    db_winners = get_winners_from_db()
    data = db_winners if db_winners else winners
    
    if not data:
        bot.reply_to(message, "📭 Chưa có giải nào!")
        return
    
    msg = "🏆 <b>TRÚNG THƯỞNG</b>\n\n"
    for i, w in enumerate(data[:20], 1):
        msg += f"{i}. {w['prize']} | <code>{w['phone']}</code> | <a href=\"{w['link']}\">Link</a>\n"
    bot.reply_to(message, msg, disable_web_page_preview=True)

@bot.message_handler(commands=['file'])
def file_cmd(message):
    if os.path.exists("winners.txt"):
        with open("winners.txt", "rb") as f:
            bot.send_document(message.chat.id, f, caption="📄 <b>Danh sách trúng thưởng đầy đủ</b>\n\n💡 <i>File chứa tất cả giải đã trúng</i>")
    else:
        bot.reply_to(message, "📭 <b>Chưa có file!</b>\n\n💡 <i>Dùng /spam để bắt đầu quay</i>")

def main():
    Thread(target=run_flask, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()
    print("🤖 Bot đang khởi động...")
    
    # Xóa webhook cũ và pending updates để tránh conflict
    try:
        bot.delete_webhook(drop_pending_updates=True)
        print("✅ Đã xóa webhook cũ")
    except:
        pass
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ Lỗi polling: {e}")
            print("🔄 Thử lại sau 5 giây...")
            time.sleep(5)

if __name__ == "__main__":
    main()
