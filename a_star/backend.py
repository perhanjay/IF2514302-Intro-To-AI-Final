import osmnx as ox
import geopandas as gpd
import heapq
import math
import json
import time
from collections import defaultdict

BLOCKED_EDGES = []

def add_blockage_by_coord(G, lat, lon):
    #Main Logic blokir jalan

    try:
        u,v,key = ox.nearest_edges(G, X=lon, Y=lat)

        block_count = 0

        if (u,v) not in BLOCKED_EDGES:
            BLOCKED_EDGES.append((u, v))
            block_count += 1

        if (v, u) not in BLOCKED_EDGES:
            BLOCKED_EDGES.append((v, u))
            block_count += 1

        print(f"Jalan diblokir di node: {u} dan {v}")
        return {"status": "success", "blocked_nodes": [u, v]}
    
    except Exception as e:
        print(f"[Backend] Gagal memblokir: {e}")
        return {"status": "error", "message": str(e)}
    
def reset_blockages():
    global BLOCKED_EDGES
    BLOCKED_EDGES = []
    print("Semua Blokiran dihapus.")
    return {"status": "success"}


def astar(G, source, target, heuristic_func, weight='length'):
    # LOGIC A-STAR
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
    visited_order = []

    while open_set:
        _current_f_score, current = heapq.heappop(open_set)
        nodes_visited_count += 1 
        if current in G.nodes:
            nd = G.nodes[current]
            visited_order.append([nd['y'], nd['x']])

        if current == target:
            path = reconstruct_path(current)
            total_length = g_score[target]
            return total_length, path, nodes_visited_count, visited_order

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
    
    return float('inf'), [], nodes_visited_count, []

def permutations(elements):
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
    node_u_data = G.nodes[u]
    node_v_data = G.nodes[v]

    lat1, lon1 = node_u_data['y'], node_u_data['x']
    lat2, lon2 = node_v_data['y'], node_v_data['x']

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
            math.cos(phi1) * math.cos(phi2) *
            math.sin(delta_lambda / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    R = 6371000 
    distance = R * c

    return distance

def heuristic_zero(u, v, G):
    #HEURISTIC UNTUK DIJKSTRA
    return 0

def load_data_initial():
    print("Memuat data graph & POI...")
    try:
        path_graph = "data/balikpapan_jalan.graphml"
        path_pois = "data/balikpapan_pois.gpkg"

        G = ox.load_graphml(path_graph)
        pois = gpd.read_file(path_pois)
        
        pois = pois.reset_index(drop=True)
        
        return G, pois
    except Exception as e:
        print(f"Error memuat data: {e}")
        return None, None

def get_pois_for_frontend(pois_gdf):
    if pois_gdf is None: return []
    
    results = []
    valid_pois = pois_gdf
    
    for idx, row in valid_pois.iterrows():
        results.append({
            "id": int(idx),
            "name": row['name'],
            "lat": row.geometry.y,
            "lon": row.geometry.x
        })
    return results

def solve_tour(G, pois, start_id, dest_ids, algo_mode='astar'):
    print(f"Mode: {algo_mode}. Start: {start_id}, Dest: {dest_ids}")

    G_active = G

    if BLOCKED_EDGES:
        print(f"Menerapkan {len(BLOCKED_EDGES)} aturan blokir jalan...")
        G_active = G.copy()
        for u, v in BLOCKED_EDGES:
            if G_active.has_edge(u,v):
                G_active.remove_edge(u, v)
    
    def run_tsp(heuristic_func):
        start_time = time.time()
        total_nodes_visited = 0
        
        start_point = pois.iloc[start_id].geometry
        dest_points = pois.iloc[dest_ids].geometry
        all_points = [start_point] + list(dest_points)
        
        raw_nodes = ox.nearest_nodes(G_active, X=[p.x for p in all_points], Y=[p.y for p in all_points])
        all_nodes = [int(n) for n in raw_nodes]
        start_node = all_nodes[0]
        dest_nodes = all_nodes[1:]
        
        poi_to_node = {start_id: start_node}
        for pid, nid in zip(dest_ids, dest_nodes): poi_to_node[pid] = nid
            
        distances = {}
        nodes_to_calc = [start_node] + dest_nodes
        
        for u in nodes_to_calc:
            distances[u] = {}
            for v in nodes_to_calc:
                if u == v:
                    distances[u][v] = 0; continue
                
                length, path, visited, _ = astar(G_active, u, v, heuristic_func)
                distances[u][v] = length if path else float('inf')
                total_nodes_visited += visited

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

        all_candidates.sort(key=lambda x: x['total_dist'])
        best_route = all_candidates[0]
        
        features = []
        path_seq = [start_id] + list(best_route['order'])
        full_poi_path = [start_id] + list(best_route['order'])
        
        full_node_path = []
        all_visited_log = []
        
        for i in range(len(full_poi_path) - 1):
            u_node = poi_to_node[full_poi_path[i]]
            v_node = poi_to_node[full_poi_path[i+1]]
            _, seg_path, _, seg_visited = astar(G_active, u_node, v_node, heuristic_func)
            if seg_visited:
                all_visited_log.extend(seg_visited)
            
            if seg_path:
                full_node_path.extend(seg_path)
                coords = [[G_active.nodes[n]['x'], G_active.nodes[n]['y']] for n in seg_path]
                features.append({
                    "type": "Feature",
                    "properties": {"segment_index": i},
                    "geometry": {"type": "LineString", "coordinates": coords}
                })
        
        if len(all_visited_log) > 5000:
            print(f"Downsampling visualisasi dari {len(all_visited_log)} titik...")
            all_visited_log = all_visited_log[::5]
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "total_km": round(best_route['total_dist'] / 1000, 2),
            "sequence_ids": path_seq,
            "geojson": {"type": "FeatureCollection", "features": features},
            "stats": {"time_ms": round(execution_time, 2), "nodes_visited": total_nodes_visited},
            "full_nodes": full_node_path,
            "visited_coords": all_visited_log
        }

    try:
        if algo_mode == 'compare':
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
            func = heuristic_zero if algo_mode == 'dijkstra' else heuristic_dist
            result = run_tsp(func)
            
            if not result: return {"error": "Gagal menemukan rute."}
            return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def get_alternative_routes(G, pois, start_id, dest_ids, mode='astar', k=3):
    results = []
    G_temp = G.copy()

    if BLOCKED_EDGES:
        for u, v in BLOCKED_EDGES:
            if G_temp.has_edge(u, v): G_temp.remove_edge(u, v) 

    penalty_factor = 2.0

    print(f"Mencari {k} alternatif rute...")

    for i in range(k):
        res = solve_tour(G_temp, pois, start_id, dest_ids, mode)

        if not res or "error" in res:
            break

        res['rank'] = i + 1
        results.append(res)

        if i < k - 1 and 'full_nodes' in res:
            path_nodes = res['full_nodes']
            for j in range(len(path_nodes) - 1):
                u, v = path_nodes[j], path_nodes[j+1]
                
                if G_temp.has_edge(u, v):
                    for key in G_temp[u][v]:
                        current_len = G_temp[u][v][key].get('length', 0)
                        G_temp[u][v][key]['length'] = current_len * penalty_factor
                        
    return results

# DEBUGGER TEST MANUAL
def main():
    print("--- MODE MANUAL (DEBUG) ---")
    G, pois = load_data_initial()
    if G is None: return

    start_name = "Alfamidi Ahmad Yani" 
    dest_names = [
        "Warung Tudai - Sumber Rejo",
        "Yova Mart Sumber Rejo",
        "Fajar Kost Balikpapan",
        "Pantai Lamaru"
    ]
    
    print(f"Mencari rute dari {start_name} ke {len(dest_names)} tujuan...")
    
    try:
        start_id = pois[pois['name'] == start_name].index[0]
        dest_ids = pois[pois['name'].isin(dest_names)].index.tolist()
        
        result = solve_tour(G, pois, int(start_id), dest_ids)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print("--- SUKSES ---")
            print(f"Total Jarak: {result['total_km']} km")
            with open("manual_result.geojson", "w") as f:
                json.dump(result['geojson'], f)
            print("Disimpan ke 'manual_result.geojson'")
            
    except IndexError:
        print("Nama tempat tidak ditemukan di data POI.")

if __name__ == "__main__":
    main()