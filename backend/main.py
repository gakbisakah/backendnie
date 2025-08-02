import os
import json
import time
from ai_engine import start_auto_cache, smart_rekomendasi, DATA_DIR

if __name__ == '__main__':
    # Ensure DATA_DIR exists
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Example data for links_api.json
    links_data_1 = [
      
    ]
    with open(os.path.join(DATA_DIR, 'links_api.json'), 'w', encoding='utf-8') as f:
        json.dump(links_data_1, f, indent=2, ensure_ascii=False)

    # Example data for additional_links.json (new file)
    links_data_2 = [
  
    ]
    with open(os.path.join(DATA_DIR, 'additional_links.json'), 'w', encoding='utf-8') as f:
        json.dump(links_data_2, f, indent=2, ensure_ascii=False)

    # Example data for hewan_cocok.json
    hewan_data = [
   
    ]
    with open(os.path.join(DATA_DIR, 'hewan_cocok.json'), 'w', encoding='utf-8') as f:
        json.dump(hewan_data, f, indent=2, ensure_ascii=False)

    # Example data for sayuran_cocok.json
    sayuran_data = [
    
    ]
    with open(os.path.join(DATA_DIR, 'sayuran_cocok.json'), 'w', encoding='utf-8') as f:
        json.dump(sayuran_data, f, indent=2, ensure_ascii=False)

    # Start the auto-cache worker
    start_auto_cache()
    
    # Give some time for the worker to fetch initial data
    print("Memulai fetching data awal. Mohon tunggu beberapa saat...")
    time.sleep(30) # Increased sleep to allow more time for initial fetches

    print("\n--- Rekomendasi untuk 'binjai' ---")
    recommendations_binjai = smart_rekomendasi("binjai")
    for rec in recommendations_binjai:
        print(f"Lokasi: {rec['desa']}, {rec['kecamatan']}, {rec['kotkab']}, {rec['provinsi']}")
        print(f"🌡 Suhu Hari Ini:")
        print(f"– Rata-rata: {rec['suhu_hari_ini']['rata2'] if rec['suhu_hari_ini']['rata2'] is not None else 'N/A'}°C")
        print(f"– Maksimum: {rec['suhu_hari_ini']['max'] if rec['suhu_hari_ini']['max'] is not None else 'N/A'}°C")
        print(f"– Minimum: {rec['suhu_hari_ini']['min'] if rec['suhu_hari_ini']['min'] is not None else 'N/A'}°C")
        print(f"🌡 Suhu rata-rata periode: {rec['rata2_suhu']}°C")
        print(f"💧 Kelembapan rata-rata: {rec['rata2_hu']}%")
        print(f"☁️ Cuaca: {rec['weather_desc']}")
        print(f"Cocok untuk Hewan: {', '.join(rec['cocok_untuk']['hewan'])}")
        print(f"Cocok untuk Sayuran: {', '.join(rec['cocok_untuk']['sayuran'])}")
        print(f"Alasan: {rec['alasan']}\n")

    print("\n--- Rekomendasi untuk 'ayam' ---")
    recommendations_ayam = smart_rekomendasi("ayam")
    for rec in recommendations_ayam:
        print(f"Lokasi: {rec['desa']}, {rec['kecamatan']}, {rec['kotkab']}, {rec['provinsi']}")
        print(f"🌡 Suhu Hari Ini:")
        print(f"– Rata-rata: {rec['suhu_hari_ini']['rata2'] if rec['suhu_hari_ini']['rata2'] is not None else 'N/A'}°C")
        print(f"– Maksimum: {rec['suhu_hari_ini']['max'] if rec['suhu_hari_ini']['max'] is not None else 'N/A'}°C")
        print(f"– Minimum: {rec['suhu_hari_ini']['min'] if rec['suhu_hari_ini']['min'] is not None else 'N/A'}°C")
        print(f"🌡 Suhu rata-rata periode: {rec['rata2_suhu']}°C")
        print(f"💧 Kelembapan rata-rata: {rec['rata2_hu']}%")
        print(f"☁️ Cuaca: {rec['weather_desc']}")
        print(f"Cocok untuk Hewan: {', '.join(rec['cocok_untuk']['hewan'])}")
        print(f"Cocok untuk Sayuran: {', '.join(rec['cocok_untuk']['sayuran'])}")
        print(f"Alasan: {rec['alasan']}\n")
    
    print("\n--- Rekomendasi untuk 'bandung' ---")
    recommendations_bandung = smart_rekomendasi("bandung")
    for rec in recommendations_bandung:
        print(f"Lokasi: {rec['desa']}, {rec['kecamatan']}, {rec['kotkab']}, {rec['provinsi']}")
        print(f"🌡 Suhu Hari Ini:")
        print(f"– Rata-rata: {rec['suhu_hari_ini']['rata2'] if rec['suhu_hari_ini']['rata2'] is not None else 'N/A'}°C")
        print(f"– Maksimum: {rec['suhu_hari_ini']['max'] if rec['suhu_hari_ini']['max'] is not None else 'N/A'}°C")
        print(f"– Minimum: {rec['suhu_hari_ini']['min'] if rec['suhu_hari_ini']['min'] is not None else 'N/A'}°C")
        print(f"🌡 Suhu rata-rata periode: {rec['rata2_suhu']}°C")
        print(f"💧 Kelembapan rata-rata: {rec['rata2_hu']}%")
        print(f"☁️ Cuaca: {rec['weather_desc']}")
        print(f"Cocok untuk Hewan: {', '.join(rec['cocok_untuk']['hewan'])}")
        print(f"Cocok untuk Sayuran: {', '.join(rec['cocok_untuk']['sayuran'])}")
        print(f"Alasan: {rec['alasan']}\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping auto cache worker.")