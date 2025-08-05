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
    
    def _cari_entitas(self, nama_input: str, data_entitas: List[Dict]) -> Optional[Dict]:
        """Helper function untuk mencari entitas (hewan/sayuran) dengan fuzzy matching."""
        nama_input_lower = nama_input.lower().strip()
        entitas_names = [ent["nama"].lower() for ent in data_entitas]

        match = process.extractOne(nama_input_lower, entitas_names, scorer=fuzz.ratio)

        # Menggunakan threshold 75 untuk akurasi yang lebih baik
        if match and match[1] >= 75: 
            # Temukan dictionary entitas asli berdasarkan nama yang cocok
            for ent in data_entitas:
                if ent["nama"].lower() == match[0]:
                    return ent
        return None
        
    def cari_lokasi_cocok(self, entitas: Dict, lokasi_list: Dict) -> List[Dict]:
        """Fungsi untuk mencari lokasi yang cocok berdasarkan kriteria entitas"""
        hasil = []
        for lokasi_key, lokasi in lokasi_list.items():
            # Gunakan rata-rata harian untuk kecocokan jangka panjang
            suhu = lokasi["ringkasan_harian"]["t_avg"]
            kelembapan = lokasi["ringkasan_harian"]["hu_avg"]

            if (
                entitas["suhu_min"] <= suhu <= entitas["suhu_max"] and
                entitas["hu_min"] <= kelembapan <= entitas["hu_max"]
            ):
                hasil.append({
                    "desa": lokasi["desa"],
                    "kecamatan": lokasi["kecamatan"],
                    "kotkab": lokasi["kotkab"],
                    "provinsi": lokasi["provinsi"]
                })
        
        return hasil

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
        
        # 13. [Entitas] cocok di mana? (Combined handler for animal/vegetable)
        match_cocok_di_mana = re.search(r'(.+?) cocok di mana', question)
        if match_cocok_di_mana:
            nama_entitas_input = match_cocok_di_mana.group(1).strip()
            
            # Try to find in animals first
            entitas_hewan = self._cari_entitas(nama_entitas_input, self.hewan_data)
            if entitas_hewan:
                return self._handle_entitas_cocok_lokasi(nama_entitas_input, 'hewan')
            
            # If not found in animals, try in vegetables
            entitas_sayuran = self._cari_entitas(nama_entitas_input, self.sayuran_data)
            if entitas_sayuran:
                return self._handle_entitas_cocok_lokasi(nama_entitas_input, 'sayuran')
            
            # If not found in either
            return f"Maaf, **{nama_entitas_input.title()}** tidak ditemukan dalam database hewan maupun sayuran. Pastikan nama entitas sudah benar atau coba nama lain."

        # 14. [Hewan] cocok dipelihara di [lokasi]?
        if re.search(r'apakah (.+?) cocok dipelihara di (.+)\?', question):
            match = re.search(r'apakah (.+?) cocok dipelihara di (.+)\?', question)
            nama_hewan = match.group(1).strip()
            nama_lokasi = match.group(2).strip()
            return self._handle_suhu_cocok_hewan(nama_lokasi, nama_hewan)
        
        # 15. [Sayuran] cocok ditanam di [lokasi]?
        if re.search(r'apakah (.+?) cocok ditanam di (.+)\?', question):
            match = re.search(r'apakah (.+?) cocok ditanam di (.+)\?', question)
            nama_sayuran = match.group(1).strip()
            nama_lokasi = match.group(2).strip()
            return self._handle_suhu_cocok_sayuran(nama_lokasi, nama_sayuran)

        # 16. Daftar hewan
        if re.search(r'(daftar hewan|hewan apa saja|hewan yang dapat dicek)', question):
            return self._handle_daftar_hewan()
        
        # 17. Daftar sayuran
        if re.search(r'(daftar sayuran|sayuran apa saja)', question):
            return self._handle_daftar_sayuran()
        
        return "Maaf, saya tidak mengerti pertanyaan Anda. Coba tanyakan hal lain seperti 'Cuaca di Jakarta' atau 'Daftar hewan'."
    
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
    
    def _handle_entitas_cocok_lokasi(self, nama_entitas_input: str, tipe_entitas: str) -> str:
        """
        Handler untuk pertanyaan '[Entitas] cocok di mana?'
        nama_entitas_input: Nama entitas yang diekstrak dari pertanyaan
        tipe_entitas: 'hewan' atau 'sayuran'
        """
        # Ambil data yang sesuai
        if tipe_entitas.lower() == 'hewan':
            data_entitas = self.hewan_data
        elif tipe_entitas.lower() == 'sayuran':
            data_entitas = self.sayuran_data
        else:
            return "Tipe entitas tidak valid. Harus 'hewan' atau 'sayuran'."

        # Cari entitas di database menggunakan fuzzy matching
        entitas = self._cari_entitas(nama_entitas_input, data_entitas)

        if not entitas:
            # This case should ideally be handled before calling this function
            # in process_question, but as a fallback:
            return f"Maaf, **{nama_entitas_input.title()}** tidak ditemukan dalam database {tipe_entitas}. Pastikan nama entitas sudah benar atau coba nama lain."

        # Tambahkan informasi rentang lingkungan ideal dari entitas yang ditemukan
        entitas_info = (
            f"Untuk **{entitas['nama']}**, rentang suhu ideal adalah {entitas['suhu_min']}°C - {entitas['suhu_max']}°C "
            f"dan kelembapan ideal adalah {entitas['hu_min']}% - {entitas['hu_max']}%."
        )

        # Cari lokasi yang cocok
        lokasi_cocok = self.cari_lokasi_cocok(entitas, self.lokasi_data)
        
        if lokasi_cocok:
            lokasi_names = [
                f"{l['desa']}, {l['kecamatan']}, {l['kotkab']}, {l['provinsi']}"
                for l in lokasi_cocok
            ]
            # Batasi hingga 5 lokasi pertama untuk ringkasan di chat
            display_locations = ', '.join(lokasi_names[:5])
            if len(lokasi_names) > 5:
                display_locations += "..."
            return (
                f"Berdasarkan data rata-rata cuaca harian, **{entitas['nama']}** cocok di beberapa lokasi, "
                f"di antaranya: {display_locations}. "
                f"{entitas_info} " # Sertakan info di sini
                f"Untuk daftar lengkap, silakan gunakan fitur pencarian peta."
            )
        else:
            return (
                f"Maaf, tidak ada lokasi yang cocok untuk **{entitas['nama']}** berdasarkan data cuaca harian yang tersedia. "
                f"{entitas_info} " # Sertakan info di sini juga
                f"Mungkin Anda bisa mencoba mencari di lokasi lain atau dengan entitas yang berbeda."
            )
    
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

    def _handle_suhu_cocok_sayuran(self, nama_lokasi: str, nama_sayuran: str) -> str:
        key, lokasi = self.find_lokasi(nama_lokasi)
        if not lokasi:
            return f"Maaf, lokasi '{nama_lokasi}' tidak ditemukan."
        
        sayuran = self.find_sayuran(nama_sayuran)
        if not sayuran:
            return f"Maaf, sayuran '{nama_sayuran}' tidak ditemukan."

        suhu_saat_ini = lokasi['cuaca_saat_ini']['suhu']
        kelembapan_saat_ini = lokasi['cuaca_saat_ini']['kelembapan']

        suhu_cocok = sayuran['suhu_min'] <= suhu_saat_ini <= sayuran['suhu_max']
        kelembapan_cocok = sayuran['hu_min'] <= kelembapan_saat_ini <= sayuran['hu_max']

        if suhu_cocok and kelembapan_cocok:
            return f"Ya, suhu dan kelembapan saat ini di {nama_lokasi.title()} cocok untuk menanam {sayuran['nama']}."
        else:
            alasan = []
            if not suhu_cocok:
                alasan.append(f"suhu {suhu_saat_ini}°C (ideal: {sayuran['suhu_min']}-{sayuran['suhu_max']}°C)")
            if not kelembapan_cocok:
                alasan.append(f"kelembapan {kelembapan_saat_ini}% (ideal: {sayuran['hu_min']}-{sayuran['hu_max']}%)")
            
            return f"Tidak, kondisi saat ini di {nama_lokasi.title()} tidak cocok untuk menanam {sayuran['nama']} karena {' dan '.join(alasan)}."

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
            "Daftar sayuran",
            "Hewan cocok di mana?",
            "Domba cocok di mana?",
            "Sayuran cocok di mana?",
            "Cabai cocok di mana?",
            "Apakah ayam cocok dipelihara di Medan?",
            "Apakah cabai cocok ditanam di Binjai?",
            "Sapi cocok di mana?", # Test with fuzzy match for animal
            "Bayam cocok di mana?", # Test with fuzzy match for vegetable
            "Apakah padi cocok ditanam di Indramayu?",
            "Pucuk Jahe cocok di mana?", # Test the specific case
            "Burung Dara cocok di mana?", # Test the specific case
            "Pigeon cocok di mana?", # Test the specific case
            "Ayam cocok di mana?", # Test the specific case
        ]
        
        for question in test_questions:
            print(f"\nQ: {question}")
            print(f"A: {chatbot.process_question(question)}")
            
    except Exception as e:
        print(f"Error: {e}")
