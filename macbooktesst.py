# -*- coding: utf-8 -*-
import time
import random
import string
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from playwright.sync_api import sync_playwright

surnames = ['Nguyen', 'Tran', 'Le', 'Pham', 'Hoang', 'Huynh', 'Phan', 'Vu', 'Vo', 'Dang', 'Bui', 'Do', 'Ho', 'Ngo', 'Duong', 'Ly', 'Truong', 'Dinh', 'Mai', 'Trinh', 'Dao', 'Cao', 'Lam', 'Nghiem', 'Chau', 'Ta', 'Quach', 'Luong', 'Vuong', 'La', 'Tran', 'Nhan', 'Ton', 'Thach', 'Kieu', 'Mach', 'Trieu', 'Bach', 'Kim', 'Ha']
middle_names = ['Van', 'Thi', 'Huu', 'Thanh', 'Minh', 'Duc', 'Quoc', 'Ngoc', 'Hoang', 'Xuan', 'Thu', 'Hai', 'Tuan', 'Anh', 'Phuong', 'Khanh', 'Bao', 'Gia', 'Dinh', 'Trung', 'Hong', 'Kim', 'Thuy', 'My', 'Cam', 'Dieu', 'Tuyet', 'Quynh', 'Nhu', 'Bich']
first_names = ['An', 'Binh', 'Cuong', 'Dat', 'Phong', 'Giang', 'Hai', 'Kien', 'Lam', 'Anh', 'Bich', 'Chau', 'Diem', 'Phuong', 'Hien', 'Hung', 'Dung', 'Tuan', 'Nam', 'Long', 'Hoa', 'Lan', 'Mai', 'Linh', 'Trang', 'Thao', 'Nhi', 'Vy', 'Uyen', 'Trinh', 'Tam', 'Khoa', 'Thinh', 'Phuc', 'Loc', 'Tai', 'Nhan', 'Nghia', 'Tin', 'Sang', 'Quang', 'Vinh', 'Huy', 'Khang', 'Minh', 'Tien', 'Trung', 'Son', 'Duc', 'Thang', 'Thi', 'Nga', 'Huong', 'Yen', 'Nhung', 'Ha', 'Ly', 'Ngoc', 'Hanh', 'Duyen']
provinces = ["Ha Noi", "TP Ho Chi Minh", "Da Nang", "Hai Phong", "Can Tho", "An Giang", "Binh Duong", "Dong Nai", "Gia Lai", "Quang Nam"]

BASE_URL = "https://spin-form.vercel.app"

lock = Lock()
count = 0
stats = {}
winners = []
stop_flag = False
working_proxies = []

def save_winner(prize, name, phone, token):
    """Luu token ra file ngay lap tuc"""
    link = f"{BASE_URL}/spin/{token}"
    with open("winners.txt", "a", encoding="utf-8") as f:
        f.write(f"{prize} | {name} | {phone} | {link}\n")

def fetch_proxies():
    proxies = []
    sources = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    ]
    
    print("Dang tai proxy...")
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
    
    # Shuffle va lay 2000 proxy dau
    random.shuffle(proxies)
    proxies = list(set(proxies))[:2000]
    print(f"Da tai {len(proxies)} proxy")
    return proxies

def test_proxy(proxy):
    """Test proxy bang cach goi API register"""
    try:
        name = f"Test {random.randint(1000,9999)}"
        phone = f"09{random.randint(10000000,99999999)}"
        
        resp = requests.post(
            f"{BASE_URL}/api/public/register",
            json={"name": name, "phone": phone, "metadata": {"note": "", "address": "Ha Noi"}},
            proxies={"http": proxy, "https": proxy},
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/json',
                'Origin': BASE_URL,
            },
            timeout=8
        )
        if resp.status_code == 200 and 'token' in resp.text:
            return proxy
    except:
        pass
    return None

def get_working_proxies(proxies, max_workers=200, limit=50):
    working = []
    tested = 0
    print(f"Dang test {len(proxies)} proxy (can {limit} proxy tot)...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(test_proxy, p): p for p in proxies}
        for future in as_completed(futures):
            tested += 1
            result = future.result()
            if result:
                working.append(result)
                print(f"  [{len(working)}/{limit}] OK: {result}")
                if len(working) >= limit:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
            if tested % 100 == 0:
                print(f"  Da test {tested} proxy, tim duoc {len(working)} proxy tot")
    
    return working

def generate_name():
    return f"{random.choice(surnames)} {random.choice(middle_names)} {random.choice(first_names)}"

def generate_phone():
    prefix = random.choice(['090', '091', '092', '093', '094', '095', '096', '097', '098', '099'])
    return prefix + ''.join(random.choices(string.digits, k=7))

def capture_screenshot(prize, token):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(f"{BASE_URL}/spin/{token}")
            page.wait_for_timeout(3000)
            filename = f"win_{prize.replace(' ', '_')}_{int(time.time())}.png"
            page.screenshot(path=filename, full_page=True)
            print(f">>> Da luu: {filename}")
            browser.close()
    except Exception as e:
        print(f">>> Loi chup: {e}")

def spin_once(session, headers, proxy):
    global count, stats, winners, stop_flag
    if stop_flag:
        return False
    
    name = generate_name()
    phone = generate_phone()
    address = random.choice(provinces)
    proxies_dict = {"http": proxy, "https": proxy}
    
    try:
        resp = session.post(f"{BASE_URL}/api/public/register", 
            json={"name": name, "phone": phone, "metadata": {"note": "", "address": address}},
            headers=headers, proxies=proxies_dict, timeout=5)
        if resp.status_code != 200:
            return False
        token = resp.json().get('data', {}).get('token')
        if not token:
            return False
        
        spin_resp = session.post(f"{BASE_URL}/api/public/spin", 
            json={"token": token}, headers=headers, proxies=proxies_dict, timeout=5)
        if spin_resp.status_code != 200:
            return False
        
        result = spin_resp.json()
        prize_name = result.get('name', 'Unknown')
        
        with lock:
            count += 1
            stats[prize_name] = stats.get(prize_name, 0) + 1
            c = count
        
        print(f"[{c}] {prize_name}")
        
        prize_lower = prize_name.lower()
        
        # Ghi lai token so tay (khong chup anh)
        if 'sổ tay' in prize_lower or 'so tay' in prize_lower:
            with lock:
                winners.append({"name": name, "phone": phone, "prize": prize_name, "token": token})
                save_winner(prize_name, name, phone, token)
            print(f"  -> Luu token so tay: {token}")
        
        # Chup anh cho laptop, iphone, gau bong
        if any(x in prize_lower for x in ['laptop', 'iphone', 'gấu bông', 'gau bong']):
            with lock:
                winners.append({"name": name, "phone": phone, "prize": prize_name, "token": token})
                save_winner(prize_name, name, phone, token)
            print(f"\n{'='*60}")
            print(f"*** TRUNG: {prize_name} ***")
            print(f"Ten: {name} | SDT: {phone} | Token: {token}")
            print(f"{'='*60}\n")
            capture_screenshot(prize_name, token)
        return True
    except:
        return False

def worker(thread_id):
    global stop_flag, working_proxies
    session = requests.Session()
    headers = {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{random.randint(110,125)}.0.0.0',
        'Accept': '*/*',
        'Origin': BASE_URL,
        'Referer': f'{BASE_URL}/',
        'Content-Type': 'application/json',
    }
    
    proxy_index = thread_id % len(working_proxies)
    fail_count = 0
    
    while not stop_flag:
        if not working_proxies:
            time.sleep(1)
            continue
        
        proxy = working_proxies[proxy_index % len(working_proxies)]
        success = spin_once(session, headers, proxy)
        
        if not success:
            fail_count += 1
            if fail_count >= 3:
                proxy_index = (proxy_index + 1) % len(working_proxies)
                fail_count = 0
        else:
            fail_count = 0

def main():
    global stop_flag, working_proxies
    NUM_THREADS = 100  # Max threads
    
    # Fetch and test proxies
    all_proxies = fetch_proxies()
    working_proxies = get_working_proxies(all_proxies, max_workers=500, limit=100)
    
    if not working_proxies:
        print("\nKhong tim thay proxy hoat dong!")
        print("Thu lai sau hoac dung VPN.")
        return
    
    print(f"\n{'='*60}")
    print(f"SPAM VONG QUAY - {NUM_THREADS} THREADS + {len(working_proxies)} PROXIES")
    print("="*60)
    print("Nhan Ctrl+C de dung\n")
    
    executor = ThreadPoolExecutor(max_workers=NUM_THREADS)
    try:
        futures = [executor.submit(worker, i) for i in range(NUM_THREADS)]
        while not stop_flag:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n\nDang dung...")
        stop_flag = True
        executor.shutdown(wait=False, cancel_futures=True)
        print("\nTHONG KE:")
        for k, v in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")
        print(f"\nTong: {count} lan | Trung: {len(winners)} giai")
        if winners:
            print("\nDanh sach trung:")
            for w in winners:
                print(f"  - {w['prize']}: {w['name']} | {w['phone']}")

if __name__ == "__main__":
    main()
