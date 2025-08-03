from flask import Flask, request, jsonify
from flask_cors import CORS
from ai_engine import start_auto_cache 
from data_filter_engine import DataFilterEngine 
from chatbot_engine import ChatbotEngine 
from recommendation_module import smart_rekomendasi 
from laporan_handler import simpan_laporan
import os
import json
from datetime import datetime
import subprocess
import threading
import time

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["https://frontendnie.vercel.app"]}})


# --- Ensure folders exist (biar otomatis di Replit)
for folder in ['cache', 'laporan', 'sampahku', 'data_filtered']:
    os.makedirs(os.path.join(os.path.dirname(__file__), folder), exist_ok=True)

# --- Config
LAPORAN_DIR = os.path.join(os.path.dirname(__file__), 'laporan')
DEFAULT_LAT = -2.0
DEFAULT_LON = 118.0
DATA_FILTER_INTERVAL = 7200  # 2 jam

data_filter_instance = DataFilterEngine()
chatbot_instance = ChatbotEngine()

def scheduled_data_filter_task():
    time.sleep(10)
    while True:
        try:
            print("🚀 Memulai proses filter data...")
            data_filter_instance.run_filter_process()
            print("🔄 Memuat ulang data difilter ke ChatbotEngine...")
            chatbot_instance.load_filtered_data()
        except Exception as e:
            print(f"❌ Error filter: {e}")
        time.sleep(DATA_FILTER_INTERVAL)

# Start auto-cache
print("Starting AI Engine auto-caching...")
start_auto_cache()

# Start filter thread
filter_thread = threading.Thread(target=scheduled_data_filter_task, daemon=True)
filter_thread.start()

# Optional: skip recycle_bin_mover script kalau tidak jalan di Replit
# (Replit tidak punya pythonw.exe & D: drive)
# print("Skipping Recycle Bin mover script on Replit.")

# --- Flask endpoints
@app.route('/api/laporan', methods=['POST'])
def api_laporan():
    data = request.json
    if 'waktu' not in data:
        data['waktu'] = datetime.now().isoformat()
    if not data.get('lokasi') or not (data.get('lat') and data.get('lon')):
        data['lat'], data['lon'] = DEFAULT_LAT, DEFAULT_LON
    else:
        try:
            data['lat'] = float(data['lat'])
            data['lon'] = float(data['lon'])
        except:
            data['lat'], data['lon'] = DEFAULT_LAT, DEFAULT_LON
    try:
        simpan_laporan(data)
        return jsonify({"status": "ok", "message": "Laporan berhasil disimpan."}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal menyimpan laporan: {e}"}), 500

@app.route('/api/all_laporan', methods=['GET'])
def api_all_laporan():
    data = []
    for f in os.listdir(LAPORAN_DIR):
        if f.endswith('.json'):
            try:
                with open(os.path.join(LAPORAN_DIR, f), 'r', encoding='utf-8') as file:
                    data.append(json.load(file))
            except Exception as e:
                print(f"Error reading {f}: {e}")
    return jsonify({"laporan": data})

@app.route('/api/search', methods=['POST'])
def search():
    keyword = request.json.get('keyword', '').lower().strip()
    return jsonify({"keyword": keyword, "rekomendasi": smart_rekomendasi(keyword)})

@app.route('/api/all', methods=['GET'])
def all_lokasi():
    return jsonify({"lokasi": smart_rekomendasi('')})

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    user_input = request.json.get('keyword', '').strip()
    if not user_input:
        return jsonify({"jawaban": "Mohon berikan pertanyaan Anda."}), 400
    jawaban = chatbot_instance.process_query(user_input)
    return jsonify({"jawaban": jawaban})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
