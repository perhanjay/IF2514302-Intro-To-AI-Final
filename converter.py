import geopandas as gpd
import os

def convert_gpkg_to_geojson(input_file, output_file, specific_layer=None):
    print(f"🔄 Membaca file: {input_file}...")
    
    try:
        # 1. Membaca file GeoPackage
        # Jika gpkg memiliki banyak layer, kita bisa spesifikasikan nama layernya
        if specific_layer:
            gdf = gpd.read_file(input_file, layer=specific_layer)
        else:
            gdf = gpd.read_file(input_file)

        # 2. Cek dan Ubah Proyeksi (Reprojection) ke EPSG:4326 (WGS 84)
        # Peta web (Leaflet/Mapbox) membutuhkan Lat/Long (EPSG:4326)
        if gdf.crs != "EPSG:4326":
            print("🌍 Mengubah sistem koordinat ke EPSG:4326 (WGS 84) untuk kompatibilitas web...")
            gdf = gdf.to_crs("EPSG:4326")
        
        # 3. Opsional: Memilih kolom tertentu saja (agar file ringan di web)
        # Hapus tanda pagar (#) di bawah jika ingin memfilter kolom
        # kolom_yang_diambil = ['id', 'nama_poi', 'kategori', 'geometry']
        # gdf = gdf[kolom_yang_diambil]

        # 4. Menyimpan ke GeoJSON
        print(f"💾 Menyimpan ke: {output_file}...")
        gdf.to_file(output_file, driver='GeoJSON')
        
        print("✅ Konversi Berhasil!")

    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")

# --- KONFIGURASI ---
# Ganti nama file sesuai dengan file Anda
input_gpkg = "data/balikpapan_pois.gpkg"   
output_json = "poi_balikpapan_copy.geojson"

# Jalankan fungsi
if __name__ == "__main__":
    # Pastikan file input ada
    if os.path.exists(input_gpkg):
        convert_gpkg_to_geojson(input_gpkg, output_json)
    else:
        print(f"File {input_gpkg} tidak ditemukan.")