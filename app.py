# main.py
from flask import Flask, request, jsonify
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
from flask_cors import CORS # Pastikan Anda mengimpor CORS

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app) # Mengaktifkan CORS agar frontend dapat mengakses backend

# --- Directory Configurations ---
LAPORAN_DIR = os.path.join(os.path.dirname(__file__), 'laporan')
os.makedirs(LAPORAN_DIR, exist_ok=True)

# Path to the Recycle Bin mover script (as provided)
RECYCLE_BIN_MOVER_SCRIPT = os.path.join('D:', os.sep, 'ai-smartcare-map', 'backend', 'Sistem', 'recycle_bin_mover.py')

# Default coordinates for the center of Indonesia (as provided)
DEFAULT_LAT = -2.0
DEFAULT_LON = 118.0

# Perbaiki interval: 1900 detik (31.6 menit) tampaknya terlalu lama.
# Jika Anda ingin cepat, gunakan interval yang lebih pendek.
DATA_FILTER_INTERVAL = 7200# Misalnya, setiap 5 menit

# Inisialisasi DataFilterEngine dan ChatbotEngine di luar fungsi untuk digunakan oleh thread dan endpoint
data_filter_instance = DataFilterEngine()
# Inisialisasi ChatbotEngine dipindahkan ke main block agar bisa diakses oleh scheduled_data_filter_task
chatbot_instance = ChatbotEngine()

def scheduled_data_filter_task():
    """
    Background task to continuously run the data filtering engine.
    This ensures the chatbot data in 'data_filtered' is always fresh.
    """
    # Give a short initial delay for ai_engine to start populating cache
    time.sleep(10) 
    while True:
        try:
            print("🚀 Memulai proses filter data terjadwal...")
            data_filter_instance.run_filter_process() 
            
            # PENTING: Panggil metode yang ada di chatbot_instance untuk memuat ulang data
            # Gunakan metode publik `load_filtered_data` yang baru ditambahkan
            print("🔄 Memuat ulang data yang difilter ke dalam ChatbotEngine...")
            chatbot_instance.load_filtered_data() 
            
        except Exception as e:
            print(f"❌ Error saat menjalankan pemfilteran data atau memuat ulang data: {e}")
        
        time.sleep(DATA_FILTER_INTERVAL)

# --- Application Startup Actions ---

# 1. Start the auto-caching process (AI Engine)
print("Starting AI Engine auto-caching process in background...")
start_auto_cache()

# 2. Start the scheduled data filtering process
print(f"Starting continuous data filtering task in background...")
filter_thread = threading.Thread(target=scheduled_data_filter_task, daemon=True)
filter_thread.start()

# 3. Start the Recycle Bin file mover script
print(f"Attempting to start file mover service from: {RECYCLE_BIN_MOVER_SCRIPT}")
try:
    subprocess.Popen(['pythonw.exe', RECYCLE_BIN_MOVER_SCRIPT],
                     cwd=os.path.dirname(RECYCLE_BIN_MOVER_SCRIPT),
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    print("Recycle Bin file mover service started successfully.")
except FileNotFoundError:
    print(f"ERROR: pythonw.exe or script '{RECYCLE_BIN_MOVER_SCRIPT}' not found. Ensure Python is installed and PATH is correct.")
except Exception as e:
    print(f"ERROR: Failed to start file mover service: {e}")

# --- Flask Endpoints ---

@app.route('/api/laporan', methods=['POST'])
def api_laporan():
    data = request.json
    if 'waktu' not in data:
        data['waktu'] = datetime.now().isoformat()
    if not data.get('lokasi') or not (data.get('lat') is not None and data.get('lon') is not None):
        data['lat'] = DEFAULT_LAT
        data['lon'] = DEFAULT_LON
        print(f"DEBUG: Report location undefined or lat/lon incomplete, using default: {DEFAULT_LAT}, {DEFAULT_LON}")
    else:
        try:
            data['lat'] = float(data['lat'])
            data['lon'] = float(data['lon'])
        except (ValueError, TypeError):
            data['lat'] = DEFAULT_LAT
            data['lon'] = DEFAULT_LON
            print(f"DEBUG: lat/lon conversion failed, using default: {DEFAULT_LAT}, {DEFAULT_LON}")
    try:
        simpan_laporan(data)
        return jsonify({"status": "ok", "message": "Laporan berhasil disimpan."}), 201
    except Exception as e:
        print(f"Error saving report: {e}")
        return jsonify({"status": "error", "message": f"Gagal menyimpan laporan: {str(e)}"}), 500

@app.route('/api/all_laporan', methods=['GET'])
def api_all_laporan():
    files = [f for f in os.listdir(LAPORAN_DIR) if f.endswith('.json')]
    data = []
    for file in files:
        try:
            with open(os.path.join(LAPORAN_DIR, file), 'r', encoding='utf-8') as f:
                d = json.load(f)
            data.append(d)
        except json.JSONDecodeError as e:
            print(f"Error reading JSON file {file}: {e}")
        except Exception as e:
            print(f"General error reading file {file}: {e}")
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
    
    # PERBAIKAN: Panggil metode yang benar dari ChatbotEngine
    # Metode yang benar adalah `process_query`, bukan `get_weather_info`
    jawaban = chatbot_instance.process_query(user_input) 
    
    return jsonify({"jawaban": jawaban})

if __name__ == '__main__':
    # Hapus baris ini karena inisialisasi sudah dipindahkan ke atas
    # chatbot_instance = ChatbotEngine()
    app.run(debug=True)