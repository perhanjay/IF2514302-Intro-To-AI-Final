import osmnx as ox
import geopandas as gpd
import heapq
import math
import json
from collections import defaultdict
import os

# ==========================================
# 1. ALGORITMA KUSTOM (TIDAK DIUBAH)
# ==========================================

def my_astar(G, source, target, heuristic, weight='length'):
    """
    Implementasi A* murni buatan sendiri menggunakan heapq.
    """
    # --- Fungsi nested untuk membangun ulang rute ---
    def reconstruct_path(current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    # 1. Inisialisasi
    open_set = []
    # Perhatikan: kita passing G ke heuristic sesuai kodemu
    heapq.heappush(open_set, (heuristic(source, target, G), source)) 
    
    came_from = {}
    
    g_score = defaultdict(lambda: float('inf'))
    g_score[source] = 0

    # 2. Mulai Loop
    while open_set:
        
        _current_f_score, current = heapq.heappop(open_set)

        # 3. Cek Tujuan
        if current == target:
            path = reconstruct_path(current)
            total_length = g_score[target]
            return total_length, path # <--- Return sukses

        # 4. Eksplorasi Tetangga
        for neighbor, edge_data_dict in G.adj[current].items():
            
            # Handle MultiDiGraph (ambil bobot terendah antar node yang sama)
            cost = float('inf')
            if G.is_multigraph():
                cost = min(data.get(weight, float('inf')) for data in edge_data_dict.values())
            else:
                cost = edge_data_dict.get(weight, float('inf'))

            if cost == float('inf'):
                continue 

            tentative_g_score = g_score[current] + cost

            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                # Passing G ke heuristic
                f_score = tentative_g_score + heuristic(neighbor, target, G)
                heapq.heappush(open_set, (f_score, neighbor))
    
    return float('inf'), []

def permutations(elements):
    """
    Implementasi Permutasi manual (Recursive).
    """
    if len(elements) == 1:
        return [elements]
    
    result = []
    for i in range(len(elements)):
        current_elements = elements[i]
        remaining_elements = elements[:i] + elements[i+1:]

        for p in permutations(remaining_elements):
            result.append([current_elements] + p)
    return result

def heuristic_dist(u, v, G):
    """
    Implementasi Haversine manual.
    """
    node_u_data = G.nodes[u]
    node_v_data = G.nodes[v]

    lat1, lon1 = node_u_data['y'], node_u_data['x']
    lat2, lon2 = node_v_data['y'], node_v_data['x']

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Rumus Haversine
    a = (math.sin(delta_phi / 2) ** 2 +
            math.cos(phi1) * math.cos(phi2) *
            math.sin(delta_lambda / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    R = 6371000 # Jari-jari bumi dalam meter
    distance = R * c

    return distance


# ==========================================
# 2. FUNGSI INTEGRASI FLASK & LOGIKA UTAMA
# ==========================================

def load_data_initial():
    """
    Memuat data Graph dan POI ke memori. Dipanggil oleh Flask saat startup.
    """
    print("🔄 [Backend] Memuat data graph & POI...")
    try:
        # Sesuaikan path file jika perlu (misal tambahkan 'data/' jika di folder data)
        # Cek apakah file ada di folder root atau subfolder 'data'
        path_graph = "data/balikpapan_jalan.graphml"
        path_pois = "data/balikpapan_pois.gpkg"
        
        # Fallback jika tidak ada folder data (untuk kemudahan)
        # if not os.path.exists(path_graph): path_graph = "balikpapan_jalan.graphml"
        # if not os.path.exists(path_pois): path_pois = "balikpapan_pois.gpkg"

        G = ox.load_graphml(path_graph)
        pois = gpd.read_file(path_pois)
        
        # Reset index agar kita bisa akses via ID (0, 1, 2...) dengan aman
        pois = pois.reset_index(drop=True)
        
        print("✅ [Backend] Data berhasil dimuat.")
        return G, pois
    except Exception as e:
        print(f"❌ [Backend] Error memuat data: {e}")
        return None, None

def get_pois_for_frontend(pois_gdf):
    """
    Mengubah GeoDataFrame POI menjadi list dictionary sederhana untuk Dropdown UI.
    """
    if pois_gdf is None: return []
    
    results = []
    # Filter hanya yang punya nama
    # valid_pois = pois_gdf[pois_gdf['name'].notna()]
    valid_pois = pois_gdf
    
    for idx, row in valid_pois.iterrows():
        results.append({
            "id": int(idx), # Index dataframe sebagai ID unik
            "name": row['name'],
            "lat": row.geometry.y,
            "lon": row.geometry.x
        })
    return results

def solve_tour(G, pois, start_id, dest_ids):
    """
    [HYBRID VERSION - FIXED]
    Algoritma: TETAP MANUAL (Permutations & A* buatan sendiri).
    Perbaikan: Memastikan output sequence_ids berisi POI ID (bukan Node ID)
    agar nama tempat muncul di website.
    """
    print(f"🚀 [Backend] Menghitung rute untuk Start ID: {start_id}, Dest IDs: {dest_ids}")
    
    try:
        # --- BAGIAN 1: MAPPING POI ID KE NODE ID ---
        # Kita perlu tahu: POI ID '5' itu letaknya di Node Graph '2394823' yang mana?
        
        # 1. Ambil geometri
        start_point = pois.iloc[start_id].geometry
        dest_points = pois.iloc[dest_ids].geometry
        all_points = [start_point] + list(dest_points)
        
        # 2. Snap ke Node Graph
        all_lons = [p.x for p in all_points]
        all_lats = [p.y for p in all_points]
        raw_nodes = ox.nearest_nodes(G, X=all_lons, Y=all_lats)
        all_nodes = [int(n) for n in raw_nodes]
        
        start_node = all_nodes[0]
        dest_nodes = all_nodes[1:]
        
        # 3. Buat Kamus: POI_ID -> NODE_ID
        # Agar nanti saat permutasi POI_ID, kita bisa cek jaraknya pakai NODE_ID
        poi_to_node = {start_id: start_node}
        for pid, nid in zip(dest_ids, dest_nodes):
            poi_to_node[pid] = nid
            
        # --- BAGIAN 2: HITUNG MATRIKS JARAK (TIDAK BERUBAH) ---
        nodes_to_calc = [start_node] + dest_nodes
        distances = {}
        
        for u in nodes_to_calc:
            distances[u] = {}
            for v in nodes_to_calc:
                if u == v:
                    distances[u][v] = 0
                    continue
                length, path = my_astar(G, source=u, target=v, heuristic=heuristic_dist, weight='length')
                distances[u][v] = length if path else float('inf')

        # --- BAGIAN 3: TSP SOLVER (PERBAIKAN DI SINI) ---
        # YANG KITA ACAK ADALAH "DEST_IDS" (POI ID), BUKAN NODE ID.
        all_candidates = []
        all_possible_orders = permutations(dest_ids) # <-- Mengacak ID Tempat
        
        for p in all_possible_orders:
            current_dist = 0
            current_poi = start_id
            valid_path = True
            
            for next_poi in p:
                # Ambil Node ID dari kamus yang kita buat tadi
                u_node = poi_to_node[current_poi]
                v_node = poi_to_node[next_poi]
                
                d = distances[u_node][v_node]
                if d == float('inf'):
                    valid_path = False
                    break
                current_dist += d
                current_poi = next_poi
            
            if valid_path:
                all_candidates.append({
                    "order": p, # Ini isinya sekarang POI ID (benar!)
                    "total_dist": current_dist
                })
        
        if not all_candidates:
            return {"error": "Rute terputus/tidak ditemukan."}

        # --- BAGIAN 4: FORMATTING OUTPUT ---
        all_candidates.sort(key=lambda x: x['total_dist'])
        top_routes = all_candidates[:3] 
        
        final_results = []

        for idx, route_data in enumerate(top_routes):
            best_order = route_data['order'] # List POI ID
            total_dist = route_data['total_dist']
            
            features = []
            path_sequence = [start_id] + list(best_order) # List POI ID lengkap
            
            # Estimasi Waktu (Asumsi 30 km/jam = 8.33 m/s)
            avg_speed_mps = 8.33 
            total_seconds = total_dist / avg_speed_mps
            
            # Rekonstruksi Jalur Fisik (Perlu lookup Node ID lagi)
            full_poi_path = [start_id] + list(best_order)
            
            for i in range(len(full_poi_path) - 1):
                u_poi = full_poi_path[i]
                v_poi = full_poi_path[i+1]
                
                u_node = poi_to_node[u_poi]
                v_node = poi_to_node[v_poi]
                
                _, segment_nodes = my_astar(G, source=u_node, target=v_node, heuristic=heuristic_dist)
                
                if segment_nodes:
                    coords = []
                    for node_id in segment_nodes:
                        n_data = G.nodes[node_id]
                        coords.append([n_data['x'], n_data['y']])
                    
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "segment_index": i,
                            "from_node": int(u_node),
                            "to_node": int(v_node)
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": coords
                        }
                    })

            final_results.append({
                "rank": idx + 1,
                "total_km": round(total_dist / 1000, 2),
                "est_time_min": round(total_seconds / 60),
                "sequence_ids": path_sequence, # Sekarang ini isinya benar (POI ID)
                "geojson": {
                    "type": "FeatureCollection",
                    "features": features
                }
            })

        return {"routes": final_results}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
# ==========================================
# 3. MAIN (UNTUK TESTING MANUAL)
# ==========================================

def main():
    """
    Fungsi ini tetap ada agar kamu bisa run 'python backend.py' di terminal
    tanpa menyalakan server Flask, untuk debugging.
    """
    print("--- MODE MANUAL (DEBUG) ---")
    G, pois = load_data_initial()
    if G is None: return

    # Simulasi input
    start_name = "Alfamidi Ahmad Yani" 
    dest_names = [
        "Warung Tudai - Sumber Rejo",
        "Yova Mart Sumber Rejo",
        "Fajar Kost Balikpapan",
        "Pantai Lamaru"
    ]
    
    print(f"Mencari rute dari {start_name} ke {len(dest_names)} tujuan...")
    
    # Cari ID dari nama (manual lookup)
    try:
        start_id = pois[pois['name'] == start_name].index[0]
        dest_ids = pois[pois['name'].isin(dest_names)].index.tolist()
        
        # Panggil fungsi solver kita
        result = solve_tour(G, pois, int(start_id), dest_ids)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print("--- SUKSES ---")
            print(f"Total Jarak: {result['total_km']} km")
            # Simpan ke file jika run manual
            with open("manual_result.geojson", "w") as f:
                json.dump(result['geojson'], f)
            print("Disimpan ke 'manual_result.geojson'")
            
    except IndexError:
        print("Nama tempat tidak ditemukan di data POI.")

if __name__ == "__main__":
    main()