# app.py
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from a_star import backend  # <--- INI KUNCINYA. Kita import file kodemu.

app = Flask(__name__)
CORS(app)

# 1. Load Data SEKALI SAJA saat aplikasi nyala
# Variabel global ini akan terus hidup di memori server
print("🚀 Menyalakan Server Flask...")
G_global, pois_global = backend.load_data_initial()

if G_global is None:
    print("❌ Gagal memuat data. Pastikan file .graphml dan .gpkg ada.")
    exit()

# 2. Route untuk Halaman Web
@app.route('/')
def index():
    return render_template('index.html')

# 3. Route untuk Mengambil Daftar POI (Untuk Dropdown)
@app.route('/api/pois')
def api_pois():
    # Kita ambil data dari pois_global yang sudah di-load backend
    data = []
    valid_pois = pois_global[pois_global['name'].notna()]
    
    for idx, row in valid_pois.iterrows():
        data.append({
            "id": int(idx),
            "name": row['name'],
            "lat": row.geometry.y,
            "lon": row.geometry.x
        })
    return jsonify(data)

# 4. Route untuk Menghitung Rute (Dipanggil saat tombol diklik)
@app.route('/api/route', methods=['POST'])
def api_route():
    # Terima data dari Frontend
    req = request.json
    start_id = req.get('start_id')
    dest_ids = req.get('dest_ids') # List [1, 5, 10]

    print(f"🤖 Permintaan Rute: Start={start_id}, Dests={dest_ids}")

    # PANGGIL LOGIKA BACKEND KAMU DI SINI
    result = backend.solve_tour(G_global, pois_global, start_id, dest_ids)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)