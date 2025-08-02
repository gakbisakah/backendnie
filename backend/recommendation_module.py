import os
import json
import datetime
from collections import Counter
import pytz

# Import necessary components from ai_engine.py
from ai_engine import DATA_DIR, CACHE_DIR, load_json

def cocok_item(item, rata2_suhu, rata2_hu, keyword):
    """Checks if an item (animal/vegetable) is suitable based on avg temp/humidity and keyword."""
    nama = item.get("nama", "").lower()
    suhu_min = item.get("suhu_min")
    suhu_max = item.get("suhu_max")
    hu_min = item.get("hu_min")
    hu_max = item.get("hu_max")

    if not all(isinstance(v, (int, float)) for v in [suhu_min, suhu_max, hu_min, hu_max]):
        return False

    cocok_suhu = (rata2_suhu is not None) and (suhu_min <= rata2_suhu <= suhu_max)
    cocok_hu = (rata2_hu is not None) and (hu_min <= rata2_hu <= hu_max)
    cocok_keyword = (keyword in nama) or (keyword == '')

    return cocok_suhu and cocok_hu and cocok_keyword

def skor_cocok_item(item, realtime_suhu, realtime_hu, rata2_suhu, rata2_hu):
    """
    Menghitung skor kecocokan (0–100) dan memberikan alasan singkat, jelas, dan spesifik.
    Termasuk rentang suhu/kelembapan ideal untuk perbandingan.
    Mengembalikan tuple (skor, alasan_singkat).
    """
    nama = item.get("nama", "")
    suhu_min = item.get("suhu_min")
    suhu_max = item.get("suhu_max")
    hu_min = item.get("hu_min")
    hu_max = item.get("hu_max")
    
    # Pastikan data lengkap untuk parameter item
    if not all(isinstance(v, (int, float)) for v in [suhu_min, suhu_max, hu_min, hu_max]):
        return 0, "Data item tidak lengkap (min/max suhu/kelembapan)"

    # Rentang ideal item
    rentang_suhu_ideal = f"({suhu_min}-{suhu_max}°C)"
    rentang_hu_ideal = f"({hu_min}-{hu_max}%)"

    alasan_parts = []

    # --- Pengecekan Realtime ---
    realtime_ok_all = True
    realtime_suhu_kondisi = ""
    realtime_hu_kondisi = ""

    if realtime_suhu is None:
        realtime_ok_all = False
        realtime_suhu_kondisi = "suhu realtime tidak tersedia"
    elif suhu_min <= realtime_suhu <= suhu_max:
        realtime_suhu_kondisi = f"suhu realtime ({realtime_suhu}°C) sesuai"
    else:
        realtime_ok_all = False
        realtime_suhu_kondisi = f"suhu realtime ({realtime_suhu}°C) tidak sesuai"

    if realtime_hu is None:
        realtime_ok_all = False
        realtime_hu_kondisi = "kelembapan realtime tidak tersedia"
    elif hu_min <= realtime_hu <= hu_max:
        realtime_hu_kondisi = f"kelembapan realtime ({realtime_hu}%) sesuai"
    else:
        realtime_ok_all = False
        realtime_hu_kondisi = f"kelembapan realtime ({realtime_hu}%) tidak sesuai"

    # --- Pengecekan Rata-rata ---
    rata2_ok_all = True
    rata2_suhu_kondisi = ""
    rata2_hu_kondisi = ""

    if rata2_suhu is None:
        rata2_ok_all = False
        rata2_suhu_kondisi = "suhu rata-rata tidak tersedia"
    elif suhu_min <= rata2_suhu <= suhu_max:
        rata2_suhu_kondisi = f"suhu rata-rata ({rata2_suhu}°C) sesuai"
    else:
        rata2_ok_all = False
        rata2_suhu_kondisi = f"suhu rata-rata ({rata2_suhu}°C) tidak sesuai"

    if rata2_hu is None:
        rata2_ok_all = False
        rata2_hu_kondisi = "kelembapan rata-rata tidak tersedia"
    elif hu_min <= rata2_hu <= hu_max:
        rata2_hu_kondisi = f"kelembapan rata-rata ({rata2_hu}%) sesuai"
    else:
        rata2_ok_all = False
        rata2_hu_kondisi = f"kelembapan rata-rata ({rata2_hu}%) tidak sesuai"
    
    # Kumpulkan Alasan Utama
    if realtime_ok_all and rata2_ok_all:
        alasan_parts.append(f"Sangat cocok: {realtime_suhu_kondisi}, {realtime_hu_kondisi}, {rata2_suhu_kondisi}, {rata2_hu_kondisi}.")
        return 100, " ".join(alasan_parts)
    
    elif realtime_ok_all:
        alasan_parts.append(f"Cukup cocok: {realtime_suhu_kondisi}, {realtime_hu_kondisi}.")
        alasan_parts.append(f"Namun, rata-rata: {rata2_suhu_kondisi}, {rata2_hu_kondisi}.")
        alasan_parts.append(f"Idealnya: Suhu {rentang_suhu_ideal}, Kelembapan {rentang_hu_ideal}.")
        return 70, " ".join(alasan_parts)
    
    elif rata2_ok_all:
        alasan_parts.append(f"Agak cocok: {rata2_suhu_kondisi}, {rata2_hu_kondisi}.")
        alasan_parts.append(f"Namun, realtime: {realtime_suhu_kondisi}, {realtime_hu_kondisi}.")
        alasan_parts.append(f"Idealnya: Suhu {rentang_suhu_ideal}, Kelembapan {rentang_hu_ideal}.")
        return 60, " ".join(alasan_parts)

    else:
        alasan_parts.append(f"Tidak cocok: Realtime: {realtime_suhu_kondisi}, {realtime_hu_kondisi}.")
        alasan_parts.append(f"Rata-rata: {rata2_suhu_kondisi}, {rata2_hu_kondisi}.")
        alasan_parts.append(f"Idealnya: Suhu {rentang_suhu_ideal}, Kelembapan {rentang_hu_ideal}.")
        return 0, " ".join(alasan_parts)


def smart_rekomendasi(keyword):
    keyword = keyword.lower()
    hewan_list = load_json(os.path.join(DATA_DIR, 'hewan_cocok.json'))
    sayuran_list = load_json(os.path.join(DATA_DIR, 'sayuran_cocok.json'))
    results = []

    # Pastikan pakai timezone Asia/Jakarta untuk perbandingan realtime
    tz_jakarta = pytz.timezone("Asia/Jakarta")
    now_local = datetime.datetime.now(tz=tz_jakarta) 
    
    # Dapatkan tanggal hari ini dalam format YYYY-MM-DD
    today_date_str = now_local.strftime('%Y-%m-%d')

    # Define weather icon mappings
    weather_icons = {
        "hujan": "https://api-apps.bmkg.go.id/storage/icon/cuaca/hujan%20ringan-pm.svg",
        "berawan": "https://api-apps.bmkg.go.id/storage/icon/cuaca/berawan-am.svg",
        "cerah berawan": "https://api-apps.bmkg.go.id/storage/icon/cuaca/cerah%20berawan-am.svg",
        "kabut/asap/udara kabur": "https://api-apps.bmkg.go.id/storage/icon/cuaca/udara%20kabur.svg", 
       "cerah": "https://images.icon-icons.com/33/PNG/96/sunny_sunshine_weather_2778.png", 
        "default": "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png" 
    }

    # Iterate through existing cache files
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith('.json'):
            adm4 = filename[:-5] 
            cache_file = os.path.join(CACHE_DIR, filename)

            try:
                with open(cache_file, encoding='utf-8') as f:
                    data = json.load(f)

                lokasi = data.get('lokasi', {})
                data_list = data.get('data', [])

                suhu_hari_ini_values = [] 
                t_values_all = []        
                hu_values_all = []       
                descs_all = []           
                date_start, date_end = None, None 

                closest_item = None
                min_diff = float('inf')

                flat_list = []
                for d_entry in data_list:
                    cuaca_entry_list = d_entry.get('cuaca', d_entry.get('data', []))
                    for c_item in cuaca_entry_list:
                        if isinstance(c_item, list):
                            flat_list.extend(c_item)
                        elif isinstance(c_item, dict):
                            flat_list.append(c_item)

                datetimes = []
                for c_item in flat_list:
                    dt_str = c_item.get('datetime')
                    if dt_str:
                        try:
                            dt_obj = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                            datetimes.append(dt_obj)
                        except ValueError:
                            try:
                                dt_obj = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                                datetimes.append(dt_obj)
                            except Exception:
                                pass

                if datetimes:
                    datetimes_sorted = sorted(datetimes)
                    date_start = datetimes_sorted[0].strftime('%Y-%m-%d')
                    date_end = datetimes_sorted[-1].strftime('%Y-%m-%d')

                for c_item in flat_list:
                    t = c_item.get('t')
                    hu = c_item.get('hu')
                    desc = c_item.get('weather_desc')
                    local_dt_str = c_item.get('local_datetime') or c_item.get('datetime')

                    if isinstance(t, (int, float)):
                        t_values_all.append(t)
                    if isinstance(hu, (int, float)):
                        hu_values_all.append(hu)
                    if isinstance(desc, str):
                        descs_all.append(desc)

                    if local_dt_str:
                        try:
                            current_item_dt = datetime.datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            try:
                                current_item_dt = datetime.datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M")
                            except Exception:
                                current_item_dt = None 

                        if current_item_dt and current_item_dt.strftime('%Y-%m-%d') == today_date_str:
                            if isinstance(t, (int, float)):
                                suhu_hari_ini_values.append(t)

                    if local_dt_str:
                        try:
                            local_dt_obj_tz = tz_jakarta.localize(datetime.datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M:%S"))
                        except ValueError:
                            try:
                                local_dt_obj_tz = tz_jakarta.localize(datetime.datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M"))
                            except Exception:
                                continue 
                        
                        diff = abs((local_dt_obj_tz - now_local).total_seconds())

                        if diff < min_diff:
                            min_diff = diff
                            closest_item = c_item
                
                t_realtime = None
                hu_realtime = None
                cuaca_realtime = ''
                weather_icon_url = weather_icons["default"]

                if closest_item:
                    if isinstance(closest_item.get('t'), (int, float)):
                        t_realtime = round(closest_item.get('t'), 1)
                    if isinstance(closest_item.get('hu'), (int, float)):
                        hu_realtime = round(closest_item.get('hu'), 1)
                    
                    cuaca_realtime = closest_item.get('weather_desc', '') 
                    
                    cuaca_lower = cuaca_realtime.lower()
                    if "hujan" in cuaca_lower:
                        weather_icon_url = weather_icons["hujan"]
                    elif "cerah berawan" in cuaca_lower:
                        weather_icon_url = weather_icons["cerah berawan"]
                    elif "berawan" in cuaca_lower:
                        weather_icon_url = weather_icons["berawan"]
                    elif "cerah" in cuaca_lower: 
                        weather_icon_url = weather_icons["cerah"]
                    elif any(k in cuaca_lower for k in ["kabut", "asap", "udara kabur"]): 
                        weather_icon_url = weather_icons["kabut/asap/udara kabur"]

                suhu_hari_ini = {
                    "rata2": round(sum(suhu_hari_ini_values)/len(suhu_hari_ini_values),1) if suhu_hari_ini_values else None,
                    "max": round(max(suhu_hari_ini_values),1) if suhu_hari_ini_values else None,
                    "min": round(min(suhu_hari_ini_values),1) if suhu_hari_ini_values else None
                }

                rata2_suhu = round(sum(t_values_all)/len(t_values_all),1) if t_values_all else None
                rata2_hu = round(sum(hu_values_all)/len(hu_values_all),1) if hu_values_all else None

                # --- BAGIAN PERUBAHAN: Menggunakan skor_cocok_item untuk mendapatkan skor dan alasan ---
                cocok_hewan_scored, cocok_sayur_scored = [], []
                pilihan_tepat_hewan = []
                pilihan_tepat_sayuran = []

                for h in hewan_list:
                    skor, alasan_item = skor_cocok_item(h, t_realtime, hu_realtime, rata2_suhu, rata2_hu)
                    if skor > 0: # Hanya tambahkan jika skor lebih dari 0
                        cocok_hewan_scored.append( {"nama": h["nama"], "skor": skor, "alasan_skor": alasan_item} )
                        if skor >= 70  :
                            pilihan_tepat_hewan.append(h["nama"])
                for s in sayuran_list:
                    skor, alasan_item = skor_cocok_item(s, t_realtime, hu_realtime, rata2_suhu, rata2_hu)
                    if skor > 0: # Hanya tambahkan jika skor lebih dari 0
                        cocok_sayur_scored.append( {"nama": s["nama"], "skor": skor, "alasan_skor": alasan_item} )
                        if skor >= 70 :
                            pilihan_tepat_sayuran.append(s["nama"])

                # Urutkan berdasarkan skor tertinggi
                cocok_hewan_scored.sort(key=lambda x: x["skor"], reverse=True)
                cocok_sayur_scored.sort(key=lambda x: x["skor"], reverse=True)
                # --- AKHIR BAGIAN PERUBAHAN ---

                cocok_lokasi = any(keyword in (lokasi.get(k,'').lower()) for k in ['desa','kecamatan','kotkab','provinsi', 'adm4'])
                
                alasan = []
                if cocok_lokasi:
                    alasan.append("Lokasi cocok dengan keyword")
                # Perbarui alasan untuk mencerminkan skor kecocokan
                if keyword and cocok_hewan_scored:
                    for item_skor in cocok_hewan_scored:
                        if keyword in item_skor['nama'].lower():
                            alasan.append(f"Hewan '{item_skor['nama']}' cocok (Skor: {item_skor['skor']}, {item_skor['alasan_skor']})")
                            break 
                if keyword and cocok_sayur_scored:
                    for item_skor in cocok_sayur_scored:
                        if keyword in item_skor['nama'].lower():
                            alasan.append(f"Sayuran '{item_skor['nama']}' cocok (Skor: {item_skor['skor']}, {item_skor['alasan_skor']})")
                            break 
                
                # Default alasan jika tidak ada keyword dan ada rekomendasi
                if not keyword and (cocok_hewan_scored or cocok_sayur_scored):
                    alasan.append("Tidak ada keyword, menampilkan lokasi dengan rekomendasi")
                elif not alasan and (t_realtime is not None or hu_realtime is not None):
                    alasan.append("Kondisi cuaca tersedia")
                elif not alasan and not keyword:
                    alasan.append("Tidak ada keyword dan kondisi cuaca belum spesifik untuk rekomendasi")
                elif not alasan and keyword:
                    alasan.append("Keyword tidak ditemukan atau kondisi cuaca tidak cocok")


                if cocok_hewan_scored or cocok_sayur_scored or cocok_lokasi or keyword == '' or t_realtime is not None or hu_realtime is not None:
                    results.append({
                        "adm4": adm4,
                        "desa": lokasi.get('desa',''),
                        "kecamatan": lokasi.get('kecamatan',''),
                        "kotkab": lokasi.get('kotkab',''),
                        "provinsi": lokasi.get('provinsi',''),
                        "lat": lokasi.get('lat'),
                        "lon": lokasi.get('lon'),
                        "suhu_hari_ini": suhu_hari_ini, 
                        "rata2_suhu": rata2_suhu,
                        "rata2_hu": rata2_hu,
                        "suhu_realtime": t_realtime,
                        "kelembapan_realtime": hu_realtime,
                        "weather_desc": cuaca_realtime,
                        "weather_icon_url": weather_icon_url,
                        "date_start": date_start or '',
                        "date_end": date_end or '',
                        "cocok_untuk": {
                            "hewan": cocok_hewan_scored, 
                            "sayuran": cocok_sayur_scored 
                        },
                        "pilihan_tepat": { # MENAMBAHKAN BAGIAN INI
                            "hewan": pilihan_tepat_hewan,
                            "sayuran": pilihan_tepat_sayuran
                        },
                        "alasan": ", ".join(alasan) if alasan else "Informasi cuaca tersedia"
                    })
            except Exception as e:
                # print(f"❌ Gagal parsing cache {adm4}: {e}") # Debugging
                pass 

    return results

# Example of how to use smart_rekomendasi (optional)
if __name__ == '__main__':
    print("\n--- Rekomendasi untuk 'ayam' ---")
    recommendations = smart_rekomendasi("ayam")
    for rec in recommendations:
        print(f"Lokasi: {rec['desa']}, {rec['kecamatan']}, {rec['kotkab']}, {rec['provinsi']}")
        print(f"    Suhu Realtime: {rec['suhu_realtime'] if rec['suhu_realtime'] is not None else 'N/A'}°C")
        print(f"    Kelembapan Realtime: {rec['kelembapan_realtime'] if rec['kelembapan_realtime'] is not None else 'N/A'}%")
        print(f"    Cuaca Saat Ini: {rec['weather_desc'] if rec['weather_desc'] else 'Tidak ada data'}")
        
        print(f"    Suhu Hari Ini:")
        print(f"        Rata-rata: {rec['suhu_hari_ini']['rata2'] if rec['suhu_hari_ini']['rata2'] is not None else 'N/A'}°C")
        print(f"        Maksimum: {rec['suhu_hari_ini']['max'] if rec['suhu_hari_ini']['max'] is not None else 'N/A'}°C")
        print(f"        Minimum: {rec['suhu_hari_ini']['min'] if rec['suhu_hari_ini']['min'] is not None else 'N/A'}°C")
        
        print(f"    Rata-rata Suhu (Periode): {rec['rata2_suhu'] if rec['rata2_suhu'] is not None else 'N/A'}°C")
        print(f"    Rata-rata Kelembaban: {rec['rata2_hu'] if rec['rata2_hu'] is not None else 'N/A'}%")
        
        print("\n    Pilihan Tepat:") # MENAMBAHKAN BAGIAN INI
        if rec['pilihan_tepat']['hewan']:
            print("        Hewan:")
            for item_nama in rec['pilihan_tepat']['hewan']:
                print(f"        - {item_nama}")
        if rec['pilihan_tepat']['sayuran']:
            print("        Sayuran:")
            for item_nama in rec['pilihan_tepat']['sayuran']:
                print(f"        - {item_nama}")
        if not rec['pilihan_tepat']['hewan'] and not rec['pilihan_tepat']['sayuran']:
            print("        Tidak ada pilihan tepat (skor 100)")


        print(f"    Penilaian:") # MENGUBAH JUDUL
        print(f"    Cocok untuk Hewan:")
        if rec['cocok_untuk']['hewan']:
            for item in rec['cocok_untuk']['hewan']:
                print(f"        - {item['nama']} (Skor: {item['skor']}), Alasan: {item['alasan_skor']}")
        else:
            print("        Tidak ada")

        print(f"    Cocok untuk Sayuran:")
        if rec['cocok_untuk']['sayuran']:
            for item in rec['cocok_untuk']['sayuran']:
                print(f"        - {item['nama']} (Skor: {item['skor']}), Alasan: {item['alasan_skor']}")
        else:
            print("        Tidak ada")
        print(f"    Alasan: {rec['alasan']}\n")

    print("\n--- Rekomendasi umum (tanpa keyword) ---")
    recommendations_general = smart_rekomendasi("")
    for rec in recommendations_general[:3]: # Hanya tampilkan 3 contoh
        print(f"Lokasi: {rec['desa']}, {rec['kecamatan']}, {rec['kotkab']}, {rec['provinsi']}")
        print(f"    Suhu Realtime: {rec['suhu_realtime'] if rec['suhu_realtime'] is not None else 'N/A'}°C")
        print(f"    Kelembapan Realtime: {rec['kelembapan_realtime'] if rec['kelembapan_realtime'] is not None else 'N/A'}%")
        print(f"    Cuaca Saat Ini: {rec['weather_desc'] if rec['weather_desc'] else 'Tidak ada data'}")
        
        print(f"    Suhu Hari Ini:")
        print(f"        Rata-rata: {rec['suhu_hari_ini']['rata2'] if rec['suhu_hari_ini']['rata2'] is not None else 'N/A'}°C")
        print(f"        Maksimum: {rec['suhu_hari_ini']['max'] if rec['suhu_hari_ini']['max'] is not None else 'N/A'}°C")
        print(f"        Minimum: {rec['suhu_hari_ini']['min'] if rec['suhu_hari_ini']['min'] is not None else 'N/A'}°C")
        
        print("\n    Pilihan Tepat:") # MENAMBAHKAN BAGIAN INI
        if rec['pilihan_tepat']['hewan']:
            print("        Hewan:")
            for item_nama in rec['pilihan_tepat']['hewan']:
                print(f"        - {item_nama}")
        if rec['pilihan_tepat']['sayuran']:
            print("        Sayuran:")
            for item_nama in rec['pilihan_tepat']['sayuran']:
                print(f"        - {item_nama}")
        if not rec['pilihan_tepat']['hewan'] and not rec['pilihan_tepat']['sayuran']:
            print("        Tidak ada pilihan tepat (skor 100)")

        print(f"    Penilaian:") # MENGUBAH JUDUL
        print(f"    Cocok untuk Hewan:")
        if rec['cocok_untuk']['hewan']:
            for item in rec['cocok_untuk']['hewan']:
                print(f"        - {item['nama']} (Skor: {item['skor']}), Alasan: {item['alasan_skor']}")
        else:
            print("        Tidak ada")

        print(f"    Cocok untuk Sayuran:")
        if rec['cocok_untuk']['sayuran']:
            for item in rec['cocok_untuk']['sayuran']:
                print(f"        - {item['nama']} (Skor: {item['skor']}), Alasan: {item['alasan_skor']}")
        else:
            print("        Tidak ada")
        print(f"    Alasan: {rec['alasan']}\n")