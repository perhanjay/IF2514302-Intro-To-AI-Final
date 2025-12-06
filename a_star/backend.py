import osmnx as ox
import geopandas as gpd
import heapq
import math
import json
import time
from collections import defaultdict

def my_astar(G, source, target, heuristic_func, weight='length'):
    """
    Implementasi A* Generik (Bisa jadi Dijkstra jika heuristic_func return 0).
    Mengembalikan: (total_length, path, nodes_visited_count)
    """
    def reconstruct_path(current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    nodes_visited_count = 0 
    
    open_set = []
    heapq.heappush(open_set, (heuristic_func(source, target, G), source)) 
    
    came_from = {}
    g_score = defaultdict(lambda: float('inf'))
    g_score[source] = 0

    while open_set:
        _current_f_score, current = heapq.heappop(open_set)
        nodes_visited_count += 1  # <--- Hitung node yang dicek

        if current == target:
            path = reconstruct_path(current)
            total_length = g_score[target]
            return total_length, path, nodes_visited_count

        for neighbor, edge_data_dict in G.adj[current].items():
            cost = float('inf')
            if G.is_multigraph():
                cost = min(data.get(weight, float('inf')) for data in edge_data_dict.values())
            else:
                cost = edge_data_dict.get(weight, float('inf'))

            if cost == float('inf'): continue 

            tentative_g_score = g_score[current] + cost

            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score = tentative_g_score + heuristic_func(neighbor, target, G)
                heapq.heappush(open_set, (f_score, neighbor))
    
    return float('inf'), [], nodes_visited_count

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

    R = 6371000 
    distance = R * c

    return distance

def heuristic_zero(u, v, G):
    """
    Heuristik untuk Dijkstra. Selalu mengembalikan 0.
    Ini membuat A* berubah sifat menjadi Dijkstra murni (Blind Search).
    """
    return 0

def load_data_initial():
    """
    Memuat data Graph dan POI ke memori. Dipanggil oleh Flask saat startup.
    """
    print("🔄 [Backend] Memuat data graph & POI...")
    try:
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

def solve_tour(G, pois, start_id, dest_ids, algo_mode='astar'):
    """
    Fungsi Solver dengan Mode Perbandingan (Compare Mode).
    """
    print(f"🚀 [Backend] Mode: {algo_mode}. Start: {start_id}, Dest: {dest_ids}")
    
    # --- HELPER: Jalankan TSP untuk satu jenis algoritma ---
    def run_tsp(heuristic_func):
        start_time = time.time()
        total_nodes_visited = 0
        
        # 1. Snap & Matriks Jarak
        start_point = pois.iloc[start_id].geometry
        dest_points = pois.iloc[dest_ids].geometry
        all_points = [start_point] + list(dest_points)
        
        raw_nodes = ox.nearest_nodes(G, X=[p.x for p in all_points], Y=[p.y for p in all_points])
        all_nodes = [int(n) for n in raw_nodes]
        start_node = all_nodes[0]
        dest_nodes = all_nodes[1:]
        
        # Mapping POI ID -> NODE ID
        poi_to_node = {start_id: start_node}
        for pid, nid in zip(dest_ids, dest_nodes): poi_to_node[pid] = nid
            
        distances = {}
        nodes_to_calc = [start_node] + dest_nodes
        
        # 2. Hitung Matriks Jarak
        for u in nodes_to_calc:
            distances[u] = {}
            for v in nodes_to_calc:
                if u == v:
                    distances[u][v] = 0; continue
                
                length, path, visited = my_astar(G, u, v, heuristic_func)
                distances[u][v] = length if path else float('inf')
                total_nodes_visited += visited

        # 3. TSP Permutasi
        all_candidates = []
        for p in permutations(dest_ids):
            current_dist = 0
            current_poi = start_id
            valid = True
            for next_poi in p:
                d = distances[poi_to_node[current_poi]][poi_to_node[next_poi]]
                if d == float('inf'): valid = False; break
                current_dist += d
                current_poi = next_poi
            if valid:
                all_candidates.append({"order": p, "total_dist": current_dist})
        
        if not all_candidates: return None

        # Ambil terbaik
        all_candidates.sort(key=lambda x: x['total_dist'])
        best_route = all_candidates[0]
        
        # 4. Rekonstruksi GeoJSON & Full Node Path
        features = []
        path_seq = [start_id] + list(best_route['order'])
        full_poi_path = [start_id] + list(best_route['order'])
        
        full_node_path = [] # <--- TAMBAHAN PENTING 1
        
        for i in range(len(full_poi_path) - 1):
            u_node = poi_to_node[full_poi_path[i]]
            v_node = poi_to_node[full_poi_path[i+1]]
            _, seg_path, _ = my_astar(G, u_node, v_node, heuristic_func)
            
            if seg_path:
                full_node_path.extend(seg_path) # <--- TAMBAHAN PENTING 2
                coords = [[G.nodes[n]['x'], G.nodes[n]['y']] for n in seg_path]
                features.append({
                    "type": "Feature",
                    "properties": {"segment_index": i},
                    "geometry": {"type": "LineString", "coordinates": coords}
                })
        
        execution_time = (time.time() - start_time) * 1000 # ms
        
        return {
            "total_km": round(best_route['total_dist'] / 1000, 2),
            "sequence_ids": path_seq,
            "geojson": {"type": "FeatureCollection", "features": features},
            "stats": {"time_ms": round(execution_time, 2), "nodes_visited": total_nodes_visited},
            "full_nodes": full_node_path # <--- TAMBAHAN PENTING 3 (Agar bisa diakses fungsi alternatif)
        }

    # --- LOGIKA UTAMA ---
    try:
        if algo_mode == 'compare':
            # Mode Compare tetap sama
            res_astar = run_tsp(heuristic_dist)
            res_dijkstra = run_tsp(heuristic_zero)
            
            if not res_astar or not res_dijkstra:
                return {"error": "Gagal menemukan rute."}

            return {
                "mode": "compare",
                "astar": res_astar,
                "dijkstra": res_dijkstra
            }
        else:
            # Mode Single sekarang hanya mengembalikan dict biasa
            # Nanti fungsi wrapper yang akan mengurus list-nya
            func = heuristic_zero if algo_mode == 'dijkstra' else heuristic_dist
            result = run_tsp(func)
            
            if not result: return {"error": "Gagal menemukan rute."}
            return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def get_alternative_routes(G, pois, start_id, dest_ids, mode='astar', k=3):
    """
    Mencari 3 rute alternatif dengan memberi penalti pada jalan yang sudah dilewati.
    """
    results = []
    G_temp = G.copy() # Copy agar graph asli tidak rusak
    penalty_factor = 2.0 # Bobot hukuman (semakin besar, semakin 'menghindar')

    print(f"🔄 [Backend] Mencari {k} alternatif rute...")

    for i in range(k):
        # Panggil solve_tour
        res = solve_tour(G_temp, pois, start_id, dest_ids, mode)
        
        # Cek validitas hasil
        if not res or "error" in res:
            break
            
        # Tambahkan ranking untuk UI
        res['rank'] = i + 1
        results.append(res)
        
        # LOGIKA PENALTI: Hanya jalan jika kita butuh rute berikutnya (i < k-1)
        # Dan pastikan 'full_nodes' ada di hasil (dari update solve_tour tadi)
        if i < k - 1 and 'full_nodes' in res:
            path_nodes = res['full_nodes']
            # Loop setiap pasang node dalam rute
            for j in range(len(path_nodes) - 1):
                u, v = path_nodes[j], path_nodes[j+1]
                
                # Jika edge ada di graph temp, kalikan bobotnya
                if G_temp.has_edge(u, v):
                    # NetworkX MultiGraph menyimpan edge dalam dict key (biasanya 0)
                    for key in G_temp[u][v]:
                        current_len = G_temp[u][v][key].get('length', 0)
                        G_temp[u][v][key]['length'] = current_len * penalty_factor
                        
    return results

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