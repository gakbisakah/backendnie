# ai_engine.py
import os
import json
import requests
import time
import threading
import shutil
import datetime
import random
from collections import defaultdict, Counter

# --- Directory Paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
SAMPAH_DIR = os.path.join(os.path.dirname(__file__), 'sampahku') # Folder untuk cache lama

# --- Cache Update Variables ---
_last_update_times = {}
UPDATE_INTERVAL = 3600 

# --- Rate Limiting Variables (Ditingkatkan) ---
_request_timestamps = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 20
RATE_LIMIT_WINDOW_SECONDS = 60
# --- End Rate Limiting ---

# Ensure necessary directories exist
os.makedirs(SAMPAH_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

def load_json(filepath):
    """Loads JSON data from a given file path."""
    try:
        with open(filepath, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ File {os.path.basename(filepath)} tidak ditemukan. Mengembalikan list kosong.")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Gagal decode JSON dari {os.path.basename(filepath)}: {e}")
        return []
    except Exception as e:
        print(f"❌ Gagal baca {os.path.basename(filepath)}: {e}")
        return []

def load_all_links():
    """
    Loads all links from all JSON files found in the DATA_DIR.
    Assumes each JSON file contains a list of dictionaries with 'adm4' and 'url'.
    """
    all_links = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(DATA_DIR, filename)
            data = load_json(filepath)
            if isinstance(data, list):
                valid_links = [item for item in data if isinstance(item, dict) and 'adm4' in item and 'url' in item]
                all_links.extend(valid_links)
            else:
                print(f"ℹ️ File {filename} tidak berisi list di root, dilewati.")
    print(f"✅ Ditemukan {len(all_links)} link dari semua file JSON di {DATA_DIR}.")
    return all_links

def save_cache(adm4, data):
    """Saves data to a JSON cache file in the CACHE_DIR."""
    file_path = os.path.join(CACHE_DIR, f"{adm4}.json")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        time.sleep(0.05) # Add a small delay after saving
    except Exception as e:
        print(f"❌ Gagal simpan cache {adm4}: {e}")

def get_random_user_agent():
    """Returns a random User-Agent string."""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Android 12; Mobile; rv:102.0) Gecko/102.0 Firefox/102.0',
        'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)',
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36',
        'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Mobile Safari/537.36'
    ]
    return random.choice(user_agents)

def fetch_with_retry(url, adm4=None, retries=5, initial_delay=1):
    """
    Fetches data from a URL with retries and applies rate limiting based on adm4.
    """
    headers = {'User-Agent': get_random_user_agent()}

    # --- Rate Limiting Logic ---
    if adm4:
        current_time = time.time()

        _request_timestamps[adm4] = [
            ts for ts in _request_timestamps[adm4] if current_time - ts < RATE_LIMIT_WINDOW_SECONDS
        ]

        if len(_request_timestamps[adm4]) >= RATE_LIMIT_PER_MINUTE:
            wait_time = _request_timestamps[adm4][0] + RATE_LIMIT_WINDOW_SECONDS - current_time
            if wait_time > 0:
                print(f"⏳ Rate limit hit for {adm4}. Waiting for {wait_time:.2f} seconds before retrying this ADM4...")
                time.sleep(wait_time + random.uniform(0.5, 1.5))
                current_time = time.time() # Recalculate current time after waiting
                _request_timestamps[adm4] = [
                    ts for ts in _request_timestamps[adm4] if current_time - ts < RATE_LIMIT_WINDOW_SECONDS
                ]

        _request_timestamps[adm4].append(current_time)
    # --- End Rate Limiting ---

    for i in range(retries):
        try:
            print(f"🌐 Mencoba fetch: {url} (Percobaan {i+1}/{retries})")
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.HTTPError as e:
            if res.status_code == 429:
                sleep_duration = initial_delay * (2 ** i) + random.uniform(1, 3)
                print(f"⚠️ Dibatasi oleh server (429) untuk {url}. Menunggu {sleep_duration:.2f} detik.")
                time.sleep(sleep_duration)
            elif res.status_code == 403:
                sleep_duration = initial_delay * (2 ** i) * 2 + random.uniform(5, 10)
                print(f"⛔ Akses diblokir (403) untuk {url}. Ini serius! Menunggu {sleep_duration:.2f} detik dan mengubah User-Agent.")
                time.sleep(sleep_duration)
                headers = {'User-Agent': get_random_user_agent()}
            elif i < retries - 1:
                sleep_duration = initial_delay * (i + 1) + random.uniform(0.5, 2)
                print(f"⚠️ HTTPError {res.status_code} saat fetch {url}. Menunggu {sleep_duration:.2f} detik.")
                time.sleep(sleep_duration)
            else:
                print(f"❌ Gagal total HTTPError saat fetch {url}: {e} (Status: {res.status_code})")
                break
        except requests.exceptions.ConnectionError as e:
            sleep_duration = initial_delay * (i + 1) + random.uniform(0.5, 2)
            print(f"❌ Koneksi error saat fetch {url}: {e}. Menunggu {sleep_duration:.2f} detik.")
            time.sleep(sleep_duration)
        except requests.exceptions.Timeout as e:
            sleep_duration = initial_delay * (i + 1) + random.uniform(0.5, 2)
            print(f"❌ Timeout saat fetch {url}: {e}. Menunggu {sleep_duration:.2f} detik.")
            time.sleep(sleep_duration)
        except Exception as e:
            print(f"❌ Error tak terduga saat fetch {url}: {e}")
            break
    return None

def auto_cache_worker():
    """Worker thread to periodically fetch and cache weather data.
    Versi hemat & selalu update seluruh kelurahan/desa, TANPA dummy."""
    print("🟢 Auto cache worker dimulai... (versi tanpa dummy, hemat, batch, update 2-3x sehari)")

    while True:
        links = load_all_links()
        now = time.time()

        if not links:
            print("ℹ️ Tidak ada link ditemukan. Tidur 2 jam sebelum coba lagi...")
            time.sleep(7200)
            continue

        batch_size = 50
        total = len(links)

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch = links[start:end]
            print(f"⚙️ Memproses batch {start}-{end-1} dari total {total} lokasi...")

            for item_link in batch:
                adm4 = item_link.get('adm4')
                url = item_link.get('url')
                if not adm4 or not url:
                    print(f"⚠️ Item link tidak lengkap (adm4: {adm4}, url: {url}), dilewati.")
                    continue

                last_update = _last_update_times.get(adm4, 0)
                if now - last_update < 43200:  # skip jika sudah update <12 jam lalu
                    continue

                print(f"📥 Fetching data baru untuk: {adm4} dari {url}")
                fetched_raw_data = fetch_with_retry(url, adm4=adm4)
                cache_file = os.path.join(CACHE_DIR, f"{adm4}.json")

                data_to_save = None
                flat_weather_data = []

                if fetched_raw_data:
                    if isinstance(fetched_raw_data, list) and fetched_raw_data:
                        first_entry = fetched_raw_data[0]
                        if isinstance(first_entry, dict) and 'lokasi' in first_entry and 'cuaca' in first_entry:
                            lokasi = first_entry['lokasi']
                            cuaca_nested = first_entry.get('cuaca', [])
                            for sublist in cuaca_nested:
                                if isinstance(sublist, list):
                                    flat_weather_data.extend(sublist)
                                elif isinstance(sublist, dict):
                                    flat_weather_data.append(sublist)
                            analysis_date = flat_weather_data[0].get('analysis_date') if flat_weather_data else None
                            data_to_save = {
                                "lokasi": lokasi,
                                "data": flat_weather_data,
                                "analysis_date": analysis_date or datetime.datetime.now().isoformat() + 'Z'
                            }
                        else:
                            print(f"⚠️ Respon API (list) tidak punya 'lokasi'/'cuaca'. Kosongkan data.")
                            data_to_save = {
                                "lokasi": {},
                                "data": [],
                                "analysis_date": datetime.datetime.now().isoformat() + 'Z'
                            }
                    elif isinstance(fetched_raw_data, dict) and 'lokasi' in fetched_raw_data:
                        lokasi = fetched_raw_data['lokasi']
                        flat_weather_data = fetched_raw_data.get('data', [])
                        if not isinstance(flat_weather_data, list):
                            flat_weather_data = []
                        analysis_date = fetched_raw_data.get('analysis_date') or (flat_weather_data[0].get('analysis_date') if flat_weather_data else None)
                        data_to_save = {
                            "lokasi": lokasi,
                            "data": flat_weather_data,
                            "analysis_date": analysis_date or datetime.datetime.now().isoformat() + 'Z'
                        }
                    else:
                        print(f"⚠️ Respon API bukan format dikenal. Kosongkan data.")
                        data_to_save = {
                            "lokasi": {},
                            "data": [],
                            "analysis_date": datetime.datetime.now().isoformat() + 'Z'
                        }
                else:
                    print(f"❌ Gagal ambil data dari {url}. Kosongkan data.")
                    data_to_save = {
                        "lokasi": {},
                        "data": [],
                        "analysis_date": datetime.datetime.now().isoformat() + 'Z'
                    }

                if os.path.exists(cache_file):
                    try:
                        timestamp_str = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                        shutil.move(cache_file, os.path.join(SAMPAH_DIR, f"{adm4}_{timestamp_str}.json"))
                        print(f"🗑️ Pindahkan cache lama: {adm4}.json")
                    except Exception as e:
                        print(f"⚠️ Gagal pindah cache lama: {e}")

                save_cache(adm4, data_to_save)
                _last_update_times[adm4] = now
                print(f"✅ Cache baru disimpan: {adm4}.json")

                time.sleep(random.uniform(0.2, 0.5))  # delay antar request

            print("⏳ Selesai 1 batch, tidur 60 detik untuk jaga limit...")
            time.sleep(60)  # total <60 req/menit

        print("😴 Semua lokasi selesai update. Tidur 6 jam sebelum ulang...")
        time.sleep(21600)  # update ≈2–3x sehari


def start_auto_cache():
    """Starts the auto-caching worker in a daemon thread."""
    thread = threading.Thread(target=auto_cache_worker, daemon=True)
    thread.start()
    print("✅ Auto cache worker thread started.")

if __name__ == '__main__':
    print("Starting AI Engine main process (for standalone testing)...")
    start_auto_cache()
    try:
        while True:
            time.sleep(10) # Keep main thread alive for testing
            print("AI Engine running...")
    except KeyboardInterrupt:
        print("\nAI Engine stopped.")