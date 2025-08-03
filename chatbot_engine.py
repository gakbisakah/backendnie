import os
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from fuzzywuzzy import fuzz, process
from datetime import datetime
import statistics

class ChatbotEngine:
    def __init__(self):
        self.lokasi_data = {}
        self.hewan_data = []
        self.sayuran_data = []
        self.lokasi_index = {
            'provinsi': {},
            'kotkab': {},
            'kecamatan': {},
            'desa': {},
            'alias': {}
        }
        self.loaded = False
        
    def load_data(self):
        """Load semua data dari file JSON"""
        try:
            print("Loading data lokasi...")
            self._load_lokasi_data()
            print(f"Loaded {len(self.lokasi_data)} lokasi data")
            
            print("Loading data hewan...")
            self._load_hewan_data()
            print(f"Loaded {len(self.hewan_data)} hewan data")
            
            print("Loading data sayuran...")
            self._load_sayuran_data()
            print(f"Loaded {len(self.sayuran_data)} sayuran data")
            
            self.loaded = True
            print("All data loaded successfully!")
            
        except Exception as e:
            print(f"Error loading data: {e}")
            raise
    
    def load_filtered_data(self):
        """Reload data yang sudah difilter - alias untuk load_data()"""
        # Reset data sebelum load ulang
        self.lokasi_data.clear()
        self.hewan_data.clear()
        self.sayuran_data.clear()
        for key in self.lokasi_index:
            self.lokasi_index[key].clear()
        self.loaded = False
        
        # Load ulang semua data
        self.load_data()
    
    def _load_lokasi_data(self):
        """Load ribuan file JSON lokasi dari folder data_filtered"""
        data_path = r"D:\ai-smartcare-map\backend\data_filtered"
        
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data path tidak ditemukan: {data_path}")
        
        json_files = [f for f in os.listdir(data_path) if f.endswith('.json')]
        
        for filename in json_files:
            file_path = os.path.join(data_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Validasi struktur data
                if self._validate_lokasi_structure(data):
                    # Gunakan kombinasi unique key untuk setiap lokasi
                    key = f"{data['provinsi']}_{data['kotkab']}_{data['kecamatan']}_{data['desa']}"
                    self.lokasi_data[key] = data
                    
                    # Build index untuk pencarian cepat
                    self._build_lokasi_index(key, data)
                    
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing {filename}: {e}")
                continue
    
    def _validate_lokasi_structure(self, data):
        """Validasi struktur data lokasi"""
        required_fields = ['provinsi', 'kotkab', 'kecamatan', 'desa', 'lon', 'lat', 
                          'cuaca_saat_ini', 'ringkasan_harian']
        
        if not all(field in data for field in required_fields):
            return False
            
        if not all(field in data['cuaca_saat_ini'] for field in ['suhu', 'kelembapan', 'cuaca']):
            return False
            
        if not all(field in data['ringkasan_harian'] for field in ['t_max', 't_min', 't_avg', 'hu_avg', 'cuaca_dominan']):
            return False
            
        return True
    
    def _build_lokasi_index(self, key, data):
        """Build index untuk pencarian fuzzy"""
        # Index berdasarkan level administratif
        self.lokasi_index['provinsi'].setdefault(data['provinsi'].lower(), []).append(key)
        self.lokasi_index['kotkab'].setdefault(data['kotkab'].lower(), []).append(key)
        self.lokasi_index['kecamatan'].setdefault(data['kecamatan'].lower(), []).append(key)
        self.lokasi_index['desa'].setdefault(data['desa'].lower(), []).append(key)
        
        # Index alias
        if 'alias' in data:
            for alias in data['alias']:
                self.lokasi_index['alias'].setdefault(alias.lower(), []).append(key)
    
    def _load_hewan_data(self):
        """Load data hewan dari JSON"""
        file_path = r"D:\ai-smartcare-map\backend\data\hewan_cocok.json"
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File hewan tidak ditemukan: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            self.hewan_data = json.load(f)
    
    def _load_sayuran_data(self):
        """Load data sayuran dari JSON"""
        file_path = r"D:\ai-smartcare-map\backend\data\sayuran_cocok.json"
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File sayuran tidak ditemukan: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            self.sayuran_data = json.load(f)
    
    def find_lokasi(self, nama_lokasi: str) -> Optional[Tuple[str, Dict]]:
        """Cari lokasi dengan fuzzy matching, prioritas: desa > kecamatan > kotkab > provinsi"""
        nama_lokasi = nama_lokasi.lower().strip()
        
        # Cek exact match dulu
        for level in ['desa', 'kecamatan', 'kotkab', 'provinsi', 'alias']:
            if nama_lokasi in self.lokasi_index[level]:
                key = self.lokasi_index[level][nama_lokasi][0]  # Ambil yang pertama
                return key, self.lokasi_data[key]
        
        # Fuzzy matching jika tidak ada exact match
        best_match = None
        best_score = 0
        best_key = None
        
        for level in ['desa', 'kecamatan', 'kotkab', 'provinsi', 'alias']:
            for indexed_name, keys in self.lokasi_index[level].items():
                score = fuzz.ratio(nama_lokasi, indexed_name)
                if score > best_score and score >= 70:  # Threshold 70%
                    best_score = score
                    best_match = self.lokasi_data[keys[0]]
                    best_key = keys[0]
        
        return (best_key, best_match) if best_match else (None, None)
    
    def find_hewan(self, nama_hewan: str) -> Optional[Dict]:
        """Cari hewan dengan fuzzy matching"""
        nama_hewan = nama_hewan.lower().strip()
        
        # Exact match
        for hewan in self.hewan_data:
            if hewan['nama'].lower() == nama_hewan:
                return hewan
        
        # Fuzzy matching
        hewan_names = [hewan['nama'] for hewan in self.hewan_data]
        match = process.extractOne(nama_hewan, hewan_names, scorer=fuzz.ratio)
        
        if match and match[1] >= 70:
            for hewan in self.hewan_data:
                if hewan['nama'] == match[0]:
                    return hewan
        
        return None
    
    def find_sayuran(self, nama_sayuran: str) -> Optional[Dict]:
        """Cari sayuran dengan fuzzy matching"""
        nama_sayuran = nama_sayuran.lower().strip()
        
        # Exact match
        for sayuran in self.sayuran_data:
            if sayuran['nama'].lower() == nama_sayuran:
                return sayuran
        
        # Fuzzy matching
        sayuran_names = [sayuran['nama'] for sayuran in self.sayuran_data]
        match = process.extractOne(nama_sayuran, sayuran_names, scorer=fuzz.ratio)
        
        if match and match[1] >= 70:
            for sayuran in self.sayuran_data:
                if sayuran['nama'] == match[0]:
                    return sayuran
        
        return None
    
    def process_question(self, question: str) -> str:
        """Main function untuk memproses pertanyaan"""
        if not self.loaded:
            return "Data belum dimuat. Silakan muat data terlebih dahulu."
        
        question = question.strip().lower()
        
        # Pattern matching untuk berbagai jenis pertanyaan
        
        # 1. Cuaca di [lokasi]
        if re.search(r'cuaca di (.+)', question):
            match = re.search(r'cuaca di (.+)', question)
            lokasi = match.group(1)
            return self._handle_cuaca_lokasi(lokasi)
        
        # 2. Dimana letak [lokasi]
        if re.search(r'(dimana|di mana).*(letak|lokasi|posisi) (.+)', question):
            match = re.search(r'(dimana|di mana).*(letak|lokasi|posisi) (.+)', question)
            lokasi = match.group(3)
            return self._handle_lokasi_info(lokasi)
        
        # 3. Koordinat [lokasi]
        if re.search(r'koordinat (.+)', question):
            match = re.search(r'koordinat (.+)', question)
            lokasi = match.group(1)
            return self._handle_koordinat(lokasi)
        
        # 4. Data provinsi apa saja
        if 'provinsi apa saja' in question or 'daftar provinsi' in question:
            return self._handle_daftar_provinsi()
        
        # 5. Data kota/kotkab apa saja
        if re.search(r'(kota|kotkab|kabupaten) apa saja', question):
            return self._handle_daftar_kotkab()
        
        # 6. Kecamatan apa saja
        if 'kecamatan apa saja' in question:
            return self._handle_daftar_kecamatan()
        
        # 7. Desa apa saja
        if 'desa apa saja' in question:
            return self._handle_daftar_desa()
        
        # 8. Bagaimana cuaca di [lokasi]
        if re.search(r'bagaimana cuaca.* di (.+)', question):
            match = re.search(r'bagaimana cuaca.* di (.+)', question)
            lokasi = match.group(1)
            return self._handle_cuaca_detail(lokasi)
        
        # 9. Suhu tertinggi/maksimum di [lokasi]
        if re.search(r'suhu (tertinggi|maksimum|max).* di (.+)', question):
            match = re.search(r'suhu (tertinggi|maksimum|max).* di (.+)', question)
            lokasi = match.group(2)
            return self._handle_suhu_max(lokasi)
        
        # 10. Suhu terendah/minimum di [lokasi]
        if re.search(r'suhu (terendah|minimum|min).* di (.+)', question):
            match = re.search(r'suhu (terendah|minimum|min).* di (.+)', question)
            lokasi = match.group(2)
            return self._handle_suhu_min(lokasi)
        
        # 11. Kelembapan di [lokasi]
        if re.search(r'kelembapan.* di (.+)', question):
            match = re.search(r'kelembapan.* di (.+)', question)
            lokasi = match.group(1)
            return self._handle_kelembapan(lokasi)
        
        # 12. Ringkasan cuaca di [lokasi]
        if re.search(r'(ringkasan|summary) cuaca.* di (.+)', question):
            match = re.search(r'(ringkasan|summary) cuaca.* di (.+)', question)
            lokasi = match.group(2)
            return self._handle_ringkasan_cuaca(lokasi)
        
        # 24. Daftar hewan
        if re.search(r'(daftar hewan|hewan apa saja|hewan yang dapat dicek)', question):
            return self._handle_daftar_hewan()
        
        # 25. Daftar sayuran
        if re.search(r'(daftar sayuran|sayuran apa saja)', question):
            return self._handle_daftar_sayuran()
        
        # 27. Apakah suhu cocok untuk hewan
        if re.search(r'apakah suhu.* di (.+) cocok untuk (.+)', question):
            match = re.search(r'apakah suhu.* di (.+) cocok untuk (.+)', question)
            lokasi = match.group(1)
            hewan = match.group(2)
            return self._handle_suhu_cocok_hewan(lokasi, hewan)
        
        # 28. Hewan apa saja yang cocok di [lokasi]
        if re.search(r'hewan apa saja yang cocok.* di (.+)', question):
            match = re.search(r'hewan apa saja yang cocok.* di (.+)', question)
            lokasi = match.group(1)
            return self._handle_hewan_cocok_lokasi(lokasi)
        
        # 34. Sayuran apa saja yang cocok di [lokasi]
        if re.search(r'sayuran apa saja yang cocok.* di (.+)', question):
            match = re.search(r'sayuran apa saja yang cocok.* di (.+)', question)
            lokasi = match.group(1)
            return self._handle_sayuran_cocok_lokasi(lokasi)
        
        # Tambahkan pattern lainnya...
        
        return "Maaf, saya tidak mengerti pertanyaan Anda. Silakan coba pertanyaan lain."
    
    def process_query(self, query: str) -> str:
        """Alias untuk process_question - untuk kompatibilitas dengan main.py"""
        return self.process_question(query)
    
    # Handler functions
    def _handle_cuaca_lokasi(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        cuaca = lokasi['cuaca_saat_ini']['cuaca']
        nama_lengkap = f"{lokasi['desa']}, {lokasi['kecamatan']}, {lokasi['kotkab']}, {lokasi['provinsi']}"
        
        return f"Cuaca di {nama_lengkap} saat ini adalah {cuaca}."
    
    def _handle_lokasi_info(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        return f"{nama_lokasi.title()} terletak di {lokasi['desa']}, {lokasi['kecamatan']}, {lokasi['kotkab']}, {lokasi['provinsi']} dengan koordinat {lokasi['lon']}, {lokasi['lat']}."
    
    def _handle_koordinat(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        return f"Koordinat {nama_lokasi.title()}: longitude = {lokasi['lon']}, latitude = {lokasi['lat']}."
    
    def _handle_daftar_provinsi(self) -> str:
        provinsi_list = sorted(set(data['provinsi'] for data in self.lokasi_data.values()))
        return f"Provinsi yang tersedia: {', '.join(provinsi_list)}."
    
    def _handle_daftar_kotkab(self) -> str:
        kotkab_list = sorted(set(data['kotkab'] for data in self.lokasi_data.values()))
        return f"Kota/Kabupaten yang tersedia: {', '.join(kotkab_list)}."
    
    def _handle_daftar_kecamatan(self) -> str:
        kecamatan_list = sorted(set(data['kecamatan'] for data in self.lokasi_data.values()))
        return f"Kecamatan yang tersedia: {', '.join(kecamatan_list[:50])}..." if len(kecamatan_list) > 50 else f"Kecamatan yang tersedia: {', '.join(kecamatan_list)}."
    
    def _handle_daftar_desa(self) -> str:
        desa_list = sorted(set(data['desa'] for data in self.lokasi_data.values()))
        return f"Desa yang tersedia: {', '.join(desa_list[:50])}..." if len(desa_list) > 50 else f"Desa yang tersedia: {', '.join(desa_list)}."
    
    def _handle_cuaca_detail(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        cuaca_info = lokasi['cuaca_saat_ini']
        return f"Cuaca saat ini di {nama_lokasi.title()} adalah {cuaca_info['cuaca']} dengan suhu {cuaca_info['suhu']}°C dan kelembapan {cuaca_info['kelembapan']}%."
    
    def _handle_suhu_max(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        suhu_max = lokasi['ringkasan_harian']['t_max']
        return f"Suhu tertinggi di {nama_lokasi.title()} hari ini adalah {suhu_max}°C."
    
    def _handle_suhu_min(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        suhu_min = lokasi['ringkasan_harian']['t_min']
        return f"Suhu terendah di {nama_lokasi.title()} hari ini adalah {suhu_min}°C."
    
    def _handle_kelembapan(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        kelembapan = lokasi['cuaca_saat_ini']['kelembapan']
        return f"Kelembapan di {nama_lokasi.title()} saat ini adalah {kelembapan}%."
    
    def _handle_ringkasan_cuaca(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        ringkasan = lokasi['ringkasan_harian']
        return f"Ringkasan cuaca hari ini di {nama_lokasi.title()}: suhu max {ringkasan['t_max']}°C, min {ringkasan['t_min']}°C, rata-rata {ringkasan['t_avg']}°C, kelembapan rata-rata {ringkasan['hu_avg']}%, cuaca dominan {ringkasan['cuaca_dominan']}."
    
    def _handle_daftar_hewan(self) -> str:
        hewan_names = [hewan['nama'] for hewan in self.hewan_data]
        return f"Hewan yang dapat dicek: {', '.join(hewan_names)}."
    
    def _handle_daftar_sayuran(self) -> str:
        sayuran_names = [sayuran['nama'] for sayuran in self.sayuran_data]
        return f"Sayuran yang tersedia: {', '.join(sayuran_names)}."
    
    def _handle_suhu_cocok_hewan(self, nama_lokasi: str, nama_hewan: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        hewan = self.find_hewan(nama_hewan)
        if not hewan:
            return f"Maaf, hewan '{nama_hewan}' tidak ditemukan."
        
        suhu_saat_ini = lokasi['cuaca_saat_ini']['suhu']
        kelembapan_saat_ini = lokasi['cuaca_saat_ini']['kelembapan']
        
        suhu_cocok = hewan['suhu_min'] <= suhu_saat_ini <= hewan['suhu_max']
        kelembapan_cocok = hewan['hu_min'] <= kelembapan_saat_ini <= hewan['hu_max']
        
        if suhu_cocok and kelembapan_cocok:
            return f"Ya, suhu dan kelembapan saat ini di {nama_lokasi.title()} cocok untuk {hewan['nama']}."
        else:
            alasan = []
            if not suhu_cocok:
                alasan.append(f"suhu {suhu_saat_ini}°C (ideal: {hewan['suhu_min']}-{hewan['suhu_max']}°C)")
            if not kelembapan_cocok:
                alasan.append(f"kelembapan {kelembapan_saat_ini}% (ideal: {hewan['hu_min']}-{hewan['hu_max']}%)")
            
            return f"Tidak, kondisi saat ini di {nama_lokasi.title()} tidak cocok untuk {hewan['nama']} karena {' dan '.join(alasan)}."
    
    def _handle_hewan_cocok_lokasi(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        t_avg = lokasi['ringkasan_harian']['t_avg']
        hu_avg = lokasi['ringkasan_harian']['hu_avg']
        
        hewan_cocok = []
        for hewan in self.hewan_data:
            if (hewan['suhu_min'] <= t_avg <= hewan['suhu_max'] and 
                hewan['hu_min'] <= hu_avg <= hewan['hu_max']):
                hewan_cocok.append(hewan['nama'])
        
        if hewan_cocok:
            return f"Hewan yang cocok dipelihara di {nama_lokasi.title()} berdasarkan suhu dan kelembapan rata-rata harian: {', '.join(hewan_cocok)}."
        else:
            return f"Tidak ada hewan dalam database yang cocok dengan kondisi rata-rata di {nama_lokasi.title()}."
    
    def _handle_sayuran_cocok_lokasi(self, nama_lokasi: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        suhu_saat_ini = lokasi['cuaca_saat_ini']['suhu']
        kelembapan_saat_ini = lokasi['cuaca_saat_ini']['kelembapan']
        
        sayuran_cocok = []
        for sayuran in self.sayuran_data:
            if (sayuran['suhu_min'] <= suhu_saat_ini <= sayuran['suhu_max'] and 
                sayuran['hu_min'] <= kelembapan_saat_ini <= sayuran['hu_max']):
                sayuran_cocok.append(sayuran['nama'])
        
        if sayuran_cocok:
            return f"Sayuran yang cocok ditanam di {nama_lokasi.title()} dengan kondisi saat ini: {', '.join(sayuran_cocok)}."
        else:
            return f"Tidak ada sayuran dalam database yang cocok dengan kondisi saat ini di {nama_lokasi.title()}."

# Example usage
if __name__ == "__main__":
    chatbot = ChatbotEngine()
    
    try:
        print("Memuat data...")
        chatbot.load_data()
        print("Data berhasil dimuat!")
        
        # Test beberapa pertanyaan
        test_questions = [
            "Cuaca di Jakarta",
            "Bagaimana cuaca saat ini di Bandung?",
            "Koordinat Surabaya",
            "Data provinsi apa saja yang tersedia",
            "Daftar hewan",
            "Hewan apa saja yang cocok dipelihara di Medan"
        ]
        
        for question in test_questions:
            print(f"\nQ: {question}")
            print(f"A: {chatbot.process_question(question)}")
            
    except Exception as e:
        print(f"Error: {e}")