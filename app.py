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
    # 1. Pastikan request JSON dibaca dengan benar
    req = request.json
    if not req:
        return jsonify({"error": "Invalid Request"}), 400

    # 2. Ambil parameter
    start_id = req.get('start_id')
    dest_ids = req.get('dest_ids')
    mode = req.get('mode', 'astar') 

    print(f"🤖 Permintaan Rute: Start={start_id}, Mode={mode}")

    # 3. LOGIKA PEMILIHAN MODE
    if mode == 'compare':
        # Mode Compare: Tetap return 1 object perbandingan
        result = backend.solve_tour(G_global, pois_global, start_id, dest_ids, mode)
        return jsonify(result)
    else:
        # Mode A* atau Dijkstra: Return LIST rute (Rute 1, 2, 3)
        # Kita panggil fungsi baru get_alternative_routes
        routes_list = backend.get_alternative_routes(G_global, pois_global, start_id, dest_ids, mode, k=3)
        
        if not routes_list:
             return jsonify({"error": "Gagal menemukan rute."})

        # Format JSON harus persis seperti ini agar index.html membacanya
        return jsonify({
            "mode": "single", 
            "routes": routes_list
        })
    
if __name__ == '__main__':
    app.run(debug=True, port=5000)