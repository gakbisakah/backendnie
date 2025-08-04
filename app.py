# main.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
import subprocess
import threading
import time
import math

# Modul internal (pastikan file .py-nya tersedia)
from ai_engine import start_auto_cache 
from data_filter_engine import DataFilterEngine 
from chatbot_engine import ChatbotEngine 
from recommendation_module import smart_rekomendasi 
from laporan_handler import simpan_laporan

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app)

# --- Directory Configurations ---
LAPORAN_DIR = os.path.join(os.path.dirname(__file__), 'laporan')
os.makedirs(LAPORAN_DIR, exist_ok=True)

RECYCLE_BIN_MOVER_SCRIPT = os.path.join('D:', os.sep, 'ai-smartcare-map', 'backend', 'Sistem', 'recycle_bin_mover.py')
DEFAULT_LAT = -2.0
DEFAULT_LON = 118.0
DATA_FILTER_INTERVAL = 7200  # 2 jam

# Inisialisasi instance
data_filter_instance = DataFilterEngine()
chatbot_instance = ChatbotEngine()

# Background task untuk filter data berkala
def scheduled_data_filter_task():
    time.sleep(10)
    while True:
        try:
            print("🚀 Memulai proses filter data terjadwal...")
            data_filter_instance.run_filter_process()
            print("🔄 Memuat ulang data yang difilter ke dalam ChatbotEngine...")
            chatbot_instance.load_filtered_data()
        except Exception as e:
            print(f"❌ Error: {e}")
        time.sleep(DATA_FILTER_INTERVAL)

# Startup tasks
print("Starting AI Engine auto-caching...")
start_auto_cache()

print("Starting background data filtering...")
threading.Thread(target=scheduled_data_filter_task, daemon=True).start()

print(f"Starting file mover from: {RECYCLE_BIN_MOVER_SCRIPT}")
try:
    subprocess.Popen(['pythonw.exe', RECYCLE_BIN_MOVER_SCRIPT],
                     cwd=os.path.dirname(RECYCLE_BIN_MOVER_SCRIPT),
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    print("Recycle Bin file mover service started.")
except Exception as e:
    print(f"ERROR: {e}")

# --- Flask Endpoints ---

@app.route('/api/laporan', methods=['POST'])
def api_laporan():
    data = request.json
    if 'waktu' not in data:
        data['waktu'] = datetime.now().isoformat()

    try:
        data['lat'] = float(data.get('lat', DEFAULT_LAT))
        data['lon'] = float(data.get('lon', DEFAULT_LON))
    except (ValueError, TypeError):
        data['lat'], data['lon'] = DEFAULT_LAT, DEFAULT_LON

    try:
        simpan_laporan(data)
        return jsonify({"status": "ok", "message": "Laporan berhasil disimpan."}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal menyimpan laporan: {str(e)}"}), 500

@app.route('/api/all_laporan', methods=['GET'])
def api_all_laporan():
    files = [f for f in os.listdir(LAPORAN_DIR) if f.endswith('.json')]
    data = []
    for file in files:
        try:
            with open(os.path.join(LAPORAN_DIR, file), 'r', encoding='utf-8') as f:
                data.append(json.load(f))
        except Exception as e:
            print(f"Error reading file {file}: {e}")
    return jsonify({"laporan": data})

@app.route('/api/search', methods=['POST'])
def search():
    keyword = request.json.get('keyword', '').lower().strip()
    results = smart_rekomendasi(keyword)
    return jsonify({"keyword": keyword, "rekomendasi": results})

@app.route('/api/all', methods=['GET'])
def all_lokasi():
    results = smart_rekomendasi('')
    return jsonify({"lokasi": results})

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    user_input = request.json.get('keyword', '').strip()
    if not user_input:
        return jsonify({"jawaban": "Mohon berikan pertanyaan Anda."}), 400
    jawaban = chatbot_instance.process_query(user_input)
    return jsonify({"jawaban": jawaban})

# --- Haversine Distance ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c  # in kilometers

# --- Nearest Location & Recommendations ---
@app.route('/api/nearest-location', methods=['GET'])
def nearest_location():
    try:
        user_lat = float(request.args.get('lat'))
        user_lon = float(request.args.get('lon'))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid lat/lon"}), 400

    data_filtered_dir = os.path.join(os.path.dirname(__file__), 'data_filtered')
    data_files = [f for f in os.listdir(data_filtered_dir) if f.endswith('.json')]

    nearest = None
    min_distance = float('inf')

    for file in data_files:
        try:
            with open(os.path.join(data_filtered_dir, file), 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('lat') is not None and data.get('lon') is not None:
                distance = haversine(user_lat, user_lon, data['lat'], data['lon'])
                if distance < min_distance:
                    min_distance = distance
                    nearest = data
        except Exception as e:
            print(f"Error reading file {file}: {e}")

    if not nearest:
        return jsonify({"error": "No data found"}), 404

    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    with open(os.path.join(data_dir, 'hewan_cocok.json'), 'r', encoding='utf-8') as f:
        hewan_list = json.load(f)
    with open(os.path.join(data_dir, 'sayuran_cocok.json'), 'r', encoding='utf-8') as f:
        sayuran_list = json.load(f)

    suhu = nearest.get('cuaca_saat_ini', {}).get('suhu')
    hu = nearest.get('cuaca_saat_ini', {}).get('kelembapan')

    rekom_hewan = []
    rekom_sayur = []
    penilaian_hewan = []
    penilaian_sayur = []

    def calc_skor(item):
        if suhu is None or hu is None:
            return 0
        ideal_suhu = (item['suhu_min'] + item['suhu_max']) / 2
        ideal_hu = (item['hu_min'] + item['hu_max']) / 2
        skor = 100 - (abs(suhu - ideal_suhu) + abs(hu - ideal_hu))
        return max(min(round(skor, 2), 100), 0)

    def get_alasan(item):
        alasan = []
        if suhu is None or hu is None:
            return "data cuaca tidak lengkap"
        if item['suhu_min'] <= suhu <= item['suhu_max']:
            alasan.append("suhu sesuai")
        else:
            alasan.append("suhu tidak sesuai")
        if item['hu_min'] <= hu <= item['hu_max']:
            alasan.append("kelembapan sesuai")
        else:
            alasan.append("kelembapan tidak sesuai")
        return ", ".join(alasan)

    for h in hewan_list:
        skor = calc_skor(h)
        alasan = get_alasan(h)
        penilaian_hewan.append({"nama": h['nama'], "skor": skor, "alasan_skor": alasan})
        if skor >= 70:
            rekom_hewan.append(h['nama'])

    for s in sayuran_list:
        skor = calc_skor(s)
        alasan = get_alasan(s)
        penilaian_sayur.append({"nama": s['nama'], "skor": skor, "alasan_skor": alasan})
        if skor >= 70:
            rekom_sayur.append(s['nama'])

    return jsonify({
        "lokasi_terdekat": nearest,
        "rekomendasi": {
            "hewan": rekom_hewan,
            "sayuran": rekom_sayur
        },
        "penilaian": {
            "hewan": penilaian_hewan,
            "sayuran": penilaian_sayur
        }
    })

# --- Run the Flask app ---
if __name__ == '__main__':
    app.run(debug=True)
