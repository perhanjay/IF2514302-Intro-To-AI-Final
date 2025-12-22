# app.py
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from a_star import backend
app = Flask(__name__)
CORS(app)

print("Menyalakan Server Flask...")
G_global, pois_global = backend.load_data_initial()

if G_global is None:
    print("Gagal memuat data. Pastikan file .graphml dan .gpkg ada.")
    exit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/pois')
def api_pois():
    data = []
    valid_pois = pois_global[pois_global['name'].notna()]
    
    for idx, row in valid_pois.iterrows():
        kategori = "Lainnya"
        
        def check_col(col_name):
            val = row.get(col_name)
            if val is not None and str(val).lower() != 'nan':
                return str(val)
            return None

        val_tourism = check_col('tourism')
        val_amenity = check_col('amenity')
        val_shop = check_col('shop')
        val_leisure = check_col('leisure')

        if val_tourism:
            kategori = val_tourism
        elif val_amenity:
            kategori = val_amenity
        elif val_shop:
            kategori = "Toko/Mart"
        elif val_leisure:
            kategori = val_leisure
            
        kategori = kategori.replace('_', ' ').title()

        data.append({
            "id": int(idx),
            "name": row['name'],
            "lat": row.geometry.y,
            "lon": row.geometry.x,
            "category": kategori 
        })
    return jsonify(data)

@app.route('/api/route', methods=['POST'])
def api_route():
    req = request.json
    if not req:
        return jsonify({"error": "Invalid Request"}), 400

    start_id = req.get('start_id')
    dest_ids = req.get('dest_ids')
    mode = req.get('mode', 'astar') 

    print(f"Permintaan Rute: Start={start_id}, Mode={mode}")

    if mode == 'compare':
        result = backend.solve_tour(G_global, pois_global, start_id, dest_ids, mode)
        return jsonify(result)
    else:
        routes_list = backend.get_alternative_routes(G_global, pois_global, start_id, dest_ids, mode, k=3)
        
        if not routes_list:
             return jsonify({"error": "Gagal menemukan rute."})

        return jsonify({
            "mode": "single", 
            "routes": routes_list
        })

@app.route('/api/block_road', methods=['POST'])
def block_road():
    try:
        data = request.json
        lat = data.get('lat')
        lon = data.get('lon')

        result = backend.add_blockage_by_coord(G_global, lat, lon)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/reset_blocks', methods=['POST'])
def reset_blocks():
    try:
        result = backend.reset_blockages()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
if __name__ == '__main__':
    app.run(debug=False, port=5000)