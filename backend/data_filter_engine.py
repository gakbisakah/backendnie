# data_filter_engine.py
import os
import json
import datetime
import shutil # Import shutil for file operations
from collections import Counter
import re # Import re for regex in normalize_weather_description
import concurrent.futures # Import for parallel processing

# --- Directory Paths ---
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
DATA_FILTERED_DIR = os.path.join(os.path.dirname(__file__), 'data_filtered')
SAMPAH_DIR = os.path.join(os.path.dirname(__file__), 'sampahku') # Define SAMPAH_DIR here as well

# Ensure output directories exist
os.makedirs(DATA_FILTERED_DIR, exist_ok=True)
os.makedirs(SAMPAH_DIR, exist_ok=True) # Ensure sampahku directory exists

class DataFilterEngine:
    def __init__(self, cache_folder=CACHE_DIR, filtered_folder=DATA_FILTERED_DIR, sampah_folder=SAMPAH_DIR):
        self.cache_folder = cache_folder
        self.filtered_folder = filtered_folder
        self.sampah_folder = sampah_folder
        self._ensure_folders_exist()

    def _ensure_folders_exist(self):
        os.makedirs(self.cache_folder, exist_ok=True)
        os.makedirs(self.filtered_folder, exist_ok=True)
        os.makedirs(self.sampah_folder, exist_ok=True)

    def run_filter_process(self):
        print(f"--- Memulai tugas terjadwal: Pemfilteran Data ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
        print("🚀 Memulai proses filter data...")

        raw_files = self._load_raw_data()
        if not raw_files:
            print("✅ Ditemukan 0 data mentah di folder cache.")
            return

        print(f"✅ Ditemukan {len(raw_files)} data mentah di folder cache.")

        # Tahap 1: Pengambilan Data Awal (Sudah dilakukan di _load_raw_data dan hanya mengambil yang relevan)
        # Data sudah dalam memori, tidak perlu disimpan lagi sebagai file di sini.

        # Tahap 2: Filter Validasi Lokasi
        print("\n--- Tahap 2: Filter Validasi Lokasi Dimulai ---")
        valid_location_data = self._filter_valid_locations(raw_files)
        print(f"✅ Tahap 2 Selesai. Tersisa {len(valid_location_data)} lokasi yang valid.")

        # Tahap 3: Filter Validasi Data Cuaca
        print("\n--- Tahap 3: Filter Validasi Data Cuaca Dimulai ---")
        valid_weather_data = self._filter_valid_weather_data(valid_location_data)
        print(f"✅ Tahap 3 Selesai. Tersisa {len(valid_weather_data)} lokasi dengan data cuaca valid & terbaru.")

        # Tahap 4: Pengolahan Data Ringkasan
        print("\n--- Tahap 4: Pengolahan Data Ringkasan Dimulai ---")
        summarized_data = self._summarize_weather_data(valid_weather_data)
        print(f"✅ Tahap 4 Selesai. {len(summarized_data)} lokasi telah memiliki ringkasan data cuaca.")

        # Tahap 5: Penyelarasan Bahasa & Pengetahuan Chatbot
        print("\n--- Tahap 5: Penyelarasan Bahasa & Pengetahuan Chatbot Dimulai ---")
        final_filtered_data = self._normalize_and_alias_data(summarized_data)
        print(f"✅ Tahap 5 Selesai. {len(final_filtered_data)} lokasi telah dinormalisasi dan memiliki alias.")

        # Menyimpan Hasil
        print("\n--- Menyimpan Hasil Filter & Ringkasan ---")
        self._save_filtered_data(final_filtered_data)


    def _read_json_file(self, filepath):
        """Helper function to read and process a single JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'lokasi' in data and 'data' in data:
                    extracted_lokasi = data.get('lokasi', {})
                    extracted_cuaca = []
                    
                    if data.get('data') and isinstance(data['data'], list) and data['data'][0] and isinstance(data['data'][0], dict):
                        nested_cuaca = data['data'][0].get('cuaca', [])
                        for sublist in nested_cuaca:
                            if isinstance(sublist, list):
                                extracted_cuaca.extend(sublist)
                            elif isinstance(sublist, dict):
                                extracted_cuaca.append(sublist)

                    return {
                        "lokasi": extracted_lokasi,
                        "cuaca": extracted_cuaca,
                        "analysis_date": data.get("analysis_date")
                    }
                else:
                    print(f"⚠️ File cache {os.path.basename(filepath)} tidak dalam format yang diharapkan. Dilewati.")
                    return None
        except json.JSONDecodeError as e:
            print(f"❌ Gagal decode JSON dari {os.path.basename(filepath)}: {e}. Dilewati.")
            return None
        except Exception as e:
            print(f"❌ Gagal baca file {os.path.basename(filepath)}: {e}. Dilewati.")
            return None

    def _load_raw_data(self):
        """
        Loads raw JSON data from the cache directory using parallel processing.
        This function is highly optimized for fast, non-blocking (I/O-wise) file reading.
        Returns a list of dictionaries, where each dict contains 'lokasi', 'cuaca', and 'analysis_date'.
        """
        all_raw_data = []
        json_files_to_read = []
        
        # Collect all JSON file paths
        if os.path.exists(self.cache_folder):
            for filename in os.listdir(self.cache_folder):
                if filename.endswith('.json'):
                    json_files_to_read.append(os.path.join(self.cache_folder, filename))
        
        if not json_files_to_read:
            return []

        # Use ThreadPoolExecutor for concurrent file reading
        # max_workers can be adjusted based on system resources and number of files.
        # os.cpu_count() * 2 is a good heuristic for I/O-bound tasks.
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
            # Map the _read_json_file function to all file paths
            # results will contain the return values from _read_json_file (either dict or None)
            results = executor.map(self._read_json_file, json_files_to_read)
            
            # Filter out None values (for files that failed to load or were malformed)
            all_raw_data = [data for data in results if data is not None]
            
        return all_raw_data

    def _filter_valid_locations(self, raw_data_list):
        valid_locations = []
        # Valid timezones for Indonesia based on standard offsets from UTC
        valid_timezone_offsets = ["+07:00", "+08:00", "+09:00"]

        for entry in raw_data_list:
            lokasi = entry.get('lokasi', {})
            adm4_id = lokasi.get('adm4', 'N/A')
            
            # Check for complete location data
            required_location_fields = ["provinsi", "kotkab", "kecamatan", "desa"]
            if not all(lokasi.get(k) for k in required_location_fields):
                continue

            # Check for valid coordinates (Indonesia: lon 95-141, lat -11-6)
            lon = lokasi.get('lon')
            lat = lokasi.get('lat')
            if not (isinstance(lon, (int, float)) and 95 <= lon <= 141 and
                    isinstance(lat, (int, float)) and -11 <= lat <= 6):
                continue

            # Check for valid timezone string and normalize it
            timezone_raw = lokasi.get('timezone', '').strip()
            is_timezone_valid = False
            normalized_timezone = ""

            if timezone_raw.startswith('+') and ':' in timezone_raw and timezone_raw in valid_timezone_offsets:
                normalized_timezone = timezone_raw
                is_timezone_valid = True
            elif timezone_raw.lower() == 'asia/jakarta' or timezone_raw == '+0700':
                normalized_timezone = '+07:00'
                is_timezone_valid = True
            elif timezone_raw.lower() == 'asia/makassar' or timezone_raw == '+0800':
                normalized_timezone = '+08:00'
                is_timezone_valid = True
            elif timezone_raw.lower() == 'asia/jayapura' or timezone_raw == '+0900':
                normalized_timezone = '+09:00'
                is_timezone_valid = True
            
            if not is_timezone_valid:
                continue
            
            entry['lokasi']['timezone'] = normalized_timezone
            
            valid_locations.append(entry)
        return valid_locations

    def _filter_valid_weather_data(self, location_filtered_data):
        final_filtered_data = []
        current_time_utc = datetime.datetime.now(datetime.timezone.utc) 
        
        for entry in location_filtered_data:
            weather_data = entry.get('cuaca', []) # 'cuaca' is now the flattened list
            adm4_id = entry.get('lokasi', {}).get('adm4', 'N/A')
            
            cleaned_weather = []
            location_has_recent_data = False # Flag to check if at least one recent data point exists

            for hour_data in weather_data:
                t = hour_data.get('t')
                hu = hour_data.get('hu')

                # Suhu wajar (10-40°C)
                if not (isinstance(t, (int, float)) and 10 <= t <= 40):
                    continue
                
                # Kelembapan wajar (30-100%)
                if not (isinstance(hu, (int, float)) and 30 <= hu <= 100):
                    continue
                
                # Analysis date terbaru (<24 jam dari sekarang)
                analysis_date_str = hour_data.get('analysis_date') or entry.get('analysis_date') 
                if analysis_date_str:
                    try:
                        # Ensure analysis_date_str is consistently parsed as UTC-aware
                        if analysis_date_str.endswith('Z'):
                            analysis_date_str = analysis_date_str[:-1] + '+00:00'
                        elif len(analysis_date_str) == 19 and 'T' in analysis_date_str:
                            # If it's a naive datetime string without 'Z', assume it's UTC and make it aware
                            analysis_date_str += '+00:00'
                        
                        # Parse the analysis_date as timezone-aware
                        analysis_date = datetime.datetime.fromisoformat(analysis_date_str).astimezone(datetime.timezone.utc)
                        
                        # Now both current_time_utc and analysis_date are timezone-aware UTC
                        if (current_time_utc - analysis_date).total_seconds() <= (24 * 3600):
                            location_has_recent_data = True # Found at least one recent data point
                            cleaned_weather.append(hour_data)
                        # else: print(f"DEBUG: Data item terlalu lama untuk {adm4_id}.")
                    except ValueError as e:
                        print(f"⚠️ Gagal parse analysis_date '{analysis_date_str}' untuk {adm4_id}: {e}. Dilewati item.")
                        continue
                # else: print(f"DEBUG: Tidak ada analysis_date untuk item cuaca, dilewati item.")
            
            # Data cukup (minimal 6-8 jam data) from the cleaned list
            if len(cleaned_weather) < 6: 
                # print(f"DEBUG: Data cuaca bersih kurang dari 6 jam untuk {adm4_id}, dilewati lokasi.")
                continue

            if location_has_recent_data: # Only add if at least one recent data point was found and cleaned_weather has enough data
                entry['cuaca'] = cleaned_weather # Update with cleaned and recent weather data
                final_filtered_data.append(entry)
            # else: print(f"DEBUG: Lokasi {adm4_id} tidak memiliki data cuaca terbaru yang valid.")
            
        return final_filtered_data

    def _summarize_weather_data(self, filtered_data):
        processed_data = []
        for entry in filtered_data:
            loc = entry["lokasi"]
            weather_data = entry["cuaca"] # This is the cleaned and recent weather data

            temperatures = [d['t'] for d in weather_data if 't' in d and isinstance(d['t'], (int, float))]
            humidities = [d['hu'] for d in weather_data if 'hu' in d and isinstance(d['hu'], (int, float))]
            weather_descs = [d['weather_desc'] for d in weather_data if 'weather_desc' in d and isinstance(d['weather_desc'], str)]

            t_max = max(temperatures) if temperatures else None
            t_min = min(temperatures) if temperatures else None
            t_avg = round(sum(temperatures) / len(temperatures), 1) if temperatures else None
            hu_avg = round(sum(humidities) / len(humidities), 1) if humidities else None

            from collections import Counter
            cuaca_dominan = None
            if weather_descs:
                cuaca_dominan = Counter(weather_descs).most_common(1)[0][0]

            cuaca_saat_ini = None
            if weather_data:
                valid_weather_data_with_local_datetime = [d for d in weather_data if d.get('local_datetime')]
                if valid_weather_data_with_local_datetime:
                    sorted_weather = sorted(valid_weather_data_with_local_datetime, 
                                            key=lambda x: datetime.datetime.strptime(x['local_datetime'], "%Y-%m-%d %H:%M:%S"), 
                                            reverse=True)
                    latest_data = sorted_weather[0]
                    cuaca_saat_ini = {
                        "local_datetime": latest_data.get("local_datetime"),
                        "suhu": latest_data.get("t"),
                        "kelembapan": latest_data.get("hu"),
                        "cuaca": latest_data.get("weather_desc"),
                        "ikon": latest_data.get("image")
                    }

            # Prepare the data in the desired final format
            processed_entry = {
                "provinsi": loc.get("provinsi"),
                "kotkab": loc.get("kotkab"),
                "kecamatan": loc.get("kecamatan"),
                "desa": loc.get("desa"),
                "lon": loc.get("lon"),
                "lat": loc.get("lat"),
                "timezone": loc.get("timezone"),
                "adm4": loc.get("adm4"), # Ensure adm4 is carried to the root level
                "analysis_date": entry.get("analysis_date"), 
                "cuaca_saat_ini": cuaca_saat_ini,
                "ringkasan_harian": {
                    "t_max": t_max,
                    "t_min": t_min,
                    "t_avg": t_avg,
                    "hu_avg": hu_avg,
                    "cuaca_dominan": cuaca_dominan
                }
            }
            processed_data.append(processed_entry)
            
        return processed_data

    def _normalize_and_alias_data(self, summary_data):
        final_data_with_alias = []
        for entry in summary_data:
            # Normalisasi nama lokasi
            provinsi = re.sub(r'\s+', ' ', entry.get('provinsi', '').replace('KABUPATEN ', '').replace('KOTA ', '').title()).strip()
            kotkab = re.sub(r'\s+', ' ', entry.get('kotkab', '').replace('KABUPATEN ', '').replace('KOTA ', '').title()).strip()
            kecamatan = re.sub(r'\s+', ' ', entry.get('kecamatan', '').title()).strip()
            desa = re.sub(r'\s+', ' ', entry.get('desa', '').title()).strip()

            entry["provinsi"] = provinsi
            entry["kotkab"] = kotkab
            entry["kecamatan"] = kecamatan
            entry["desa"] = desa

            # Normalisasi weather_desc (from cuaca_saat_ini and cuaca_dominan)
            if entry.get('cuaca_saat_ini') and entry['cuaca_saat_ini'].get('cuaca'):
                entry['cuaca_saat_ini']['cuaca'] = self._normalize_weather_description(entry['cuaca_saat_ini']['cuaca'])
            if entry.get('ringkasan_harian') and entry['ringkasan_harian'].get('cuaca_dominan'):
                entry['ringkasan_harian']['cuaca_dominan'] = self._normalize_weather_description(entry['ringkasan_harian']['cuaca_dominan'])
            
            aliases = []
            
            # 1. Add the most specific name (desa)
            if desa:
                aliases.append(desa)

            # 2. Add combinations of desa + kecamatan
            if desa and kecamatan:
                aliases.append(f"{desa} {kecamatan}")
                aliases.append(f"{desa}, {kecamatan}") # With comma for natural language

            # 3. Add combinations of desa + kecamatan + kotkab
            if desa and kecamatan and kotkab:
                aliases.append(f"{desa} {kecamatan} {kotkab}")
                aliases.append(f"{desa}, {kecamatan}, {kotkab}") # With commas

            # 4. Add combinations of desa + kecamatan + kotkab + provinsi
            if desa and kecamatan and kotkab and provinsi:
                aliases.append(f"{desa} {kecamatan} {kotkab} {provinsi}")
                aliases.append(f"{desa}, {kecamatan}, {kotkab}, {provinsi}") # With commas

            # 5. Add ADM4 code as a guaranteed unique identifier
            if entry.get('adm4'):
                aliases.append(entry['adm4'])

            # Filter out empty or redundant aliases and ensure uniqueness within this list
            # By making these aliases highly specific, we reduce collisions when chatbot searches.
            entry['alias'] = list(set([a.strip() for a in aliases if a and a.strip()])) 

            final_data_with_alias.append(entry)

        return final_data_with_alias

    def _normalize_weather_description(self, desc):
        """Normalizes weather descriptions to consistent terms."""
        desc_lower = desc.lower()
        if "cerah berawan" in desc_lower: return "Cerah Berawan"
        elif "cerah" in desc_lower or "sunny" in desc_lower: return "Cerah"
        elif "berawan tebal" in desc_lower: return "Berawan Tebal"
        elif "berawan" in desc_lower or "cloudy" in desc_lower: return "Berawan"
        elif "hujan petir" in desc_lower or "thunderstorm" in desc_lower: return "Hujan Petir"
        elif "hujan ringan" in desc_lower: return "Hujan Ringan"
        elif "hujan sedang" in desc_lower: return "Hujan Sedang"
        elif "hujan lebat" in desc_lower: return "Hujan Lebat"
        elif "hujan lokal" in desc_lower: return "Hujan Lokal"
        elif "kabut" in desc_lower or "fog" in desc_lower: return "Berkabut"
        elif "asap" in desc_lower or "smoke" in desc_lower: return "Asap"
        return desc.capitalize() 

    def _save_filtered_data(self, filtered_data_list):
        print("\n--- Menyimpan Hasil Filter & Ringkasan ---")
        saved_count = 0
        for data_item in filtered_data_list:
            adm4 = data_item.get('adm4')
            if not adm4:
                print(f"⚠️ Tidak dapat menyimpan data: Tidak ada 'adm4' di item data. Dilewati.")
                continue
            
            # Use adm4 as the unique identifier for the filename
            filename = f"{adm4}.json"
            filepath = os.path.join(self.filtered_folder, filename)

            # Check if an older file with the same ADM4 exists in data_filtered
            if os.path.exists(filepath):
                try:
                    timestamp_str = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                    # Move the old file to sampahku folder
                    shutil.move(filepath, os.path.join(self.sampah_folder, f"{adm4}_{timestamp_str}.json"))
                    print(f"🗑️ Memindahkan data lama untuk {adm4}.json ke folder sampahku.")
                except Exception as e:
                    print(f"⚠️ Gagal memindahkan data lama ({filepath}) ke folder sampahku: {e}")

            # Save the new (updated) data
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data_item, f, indent=2, ensure_ascii=False)
                saved_count += 1
                # print(f"✅ Data tersimpan: {adm4}.json") # Too verbose if many files
            except Exception as e:
                print(f"❌ Gagal menyimpan {adm4}.json: {e}")
        print(f"✅ Selesai menyimpan {saved_count} file hasil filter.")

# This part is for standalone testing of the filter engine
if __name__ == '__main__':
    filter_engine = DataFilterEngine()
    filter_engine.run_filter_process()
