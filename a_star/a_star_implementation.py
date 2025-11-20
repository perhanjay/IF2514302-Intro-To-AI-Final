import osmnx as ox
import geopandas as gpd
import itertools #masih bisa di ganti pakai pendekatan manual
import heapq
import math
from collections import defaultdict

def my_astar(G, source, target, heuristic, weight='length'):
        # --- Fungsi nested untuk membangun ulang rute ---
        def reconstruct_path(current):
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path
        # -----------------------------------------------

        # 1. Inisialisasi
        open_set = []
        heapq.heappush(open_set, (heuristic(source, target), source)) 
        
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
                    f_score = tentative_g_score + heuristic(neighbor, target)
                    heapq.heappush(open_set, (f_score, neighbor))
        
        return float('inf'), []

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

def main():
    
    print("Memuat graph dari file lokal...")
    try:
        G = ox.load_graphml("data/balikpapan_jalan.graphml")
    except FileNotFoundError:
        print("Error: File 'balikpapan_jalan.graphml' tidak ditemukan.")
        print("Pastikan Anda sudah menjalankan skrip download terlebih dahulu.")
        return

    print("Memuat POI dari file lokal...")
    try:
        pois = gpd.read_file("data/balikpapan_pois.gpkg")
    except Exception as e:
        print(f"Error: File 'balikpapan_pois.gpkg' tidak ditemukan atau error. {e}")
        return

    print("Data dimuat.")
    
    try:
        start_name = "Alfamidi Ahmad Yani" # Titik G
        dest_names = [
            "Warung Tudai - Sumber Rejo",
            "Yova Mart Sumber Rejo",
            "Fajar Kost Balikpapan",
            "Pantai Lamaru"
        ]

        start_point = pois[pois['name'] == start_name].geometry.iloc[0]
        dest_points = pois[pois['name'].isin(dest_names)].geometry
        
        all_points = [start_point] + list(dest_points)
        all_names = [start_name] + dest_names
        
    except (IndexError, AttributeError):
        print("Error: Satu atau lebih POI tidak ditemukan di file .gpkg Anda.")
        print("Pastikan nama POI di 'start_name' dan 'dest_names' sudah benar.")
        return
    
    all_lons = [p.x for p in all_points]
    all_lats = [p.y for p in all_points]

    print("Mencari node jaringan terdekat (membangun ulang indeks bersih)...")
    
    raw_nodes = ox.nearest_nodes(G, X=all_lons, Y=all_lats)
    
    all_nodes = [int(node) for node in raw_nodes]
    print("Konversi node ID ke int standar selesai.")
    
    start_node = all_nodes[0]
    dest_nodes = all_nodes[1:]
    
    print(f"Node Awal (G): {start_node} ({start_name})")
    print(f"Node Tujuan (A,B,C,D): {dest_nodes}")

    
    print("\nMengecek sistem koordinat graf untuk A*...")

    def heuristic_dist(u, v):
        node_u_data = G.nodes[u]
        node_v_data = G.nodes[v]

        lat1, lon1 = node_u_data['y'], node_u_data['x']
        lat2, lon2 = node_v_data['y'], node_v_data['x']

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        #haversine
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        R = 6371000

        distance = R * c

        return distance

    nodes_to_calc = [start_node] + dest_nodes

    distances = {} 

    print("\nMenghitung matriks jarak pairwise (menggunakan A*)...")
    for u in nodes_to_calc:
        distances[u] = {}
        for v in nodes_to_calc:
            if u == v:
                distances[u][v] = 0
                continue
            length, path = my_astar(G, source=u, target=v, heuristic=heuristic_dist, weight='length')
            if not path:
                print(f"WARNING: Tidak ada rute ditemukan antara {u} dan {v}")
                distances[u][v] = float('inf')
            else:
                distances[u][v] = length

    print("Matriks jarak selesai.")

    print("Mencari urutan rute terbaik (TSP)...")
    shortest_total_dist = float('inf')
    best_order = []

    # TO MODIFY

    all_possible_orders = permutations(dest_nodes)

    for p in all_possible_orders:
        current_dist = 0
        current_node = start_node # Mulai dari G
        
        for next_node in p:
            current_dist += distances[current_node][next_node]
            current_node = next_node
        
        if current_dist < shortest_total_dist:
            shortest_total_dist = current_dist
            best_order = p

    best_path_nodes_order = [start_node] + list(best_order)

    node_to_name_map = {node: name for node, name in zip(all_nodes, all_names)}
    
    order_names = [node_to_name_map[n] for n in best_path_nodes_order]

    print("---")
    print(f"Rute Optimal Ditemukan!")
    print(f"Total Jarak: {shortest_total_dist / 1000:.2f} km")
    print(f"Urutan: {' -> '.join(order_names)}")
    print("---")


    print("Menghasilkan rute jalan penuh (menggunakan A*)...")
    
    full_route_nodes = []
    for i in range(len(best_path_nodes_order) - 1):
        u = best_path_nodes_order[i]
        v = best_path_nodes_order[i+1]
        
        length, route_segment = my_astar(G, source=u, target=v, heuristic=heuristic_dist, weight='length')
        if not route_segment:
            print(f"WARNING: Tidak ada rute ditemukan antara {u} dan {v} saat membuat rute final.")
            continue
        
        if i == 0:
            full_route_nodes.extend(route_segment)
        else:
            full_route_nodes.extend(route_segment[1:])
    
    
    if not full_route_nodes:
        print("Error: Rute final tidak dapat dibuat. Tidak ada node dalam rute.")
        return

    route_edges_with_keys = []
    for u, v in zip(full_route_nodes[:-1], full_route_nodes[1:]):
        route_edges_with_keys.append((u, v, 0))

    G_route = G.edge_subgraph(route_edges_with_keys).copy()

    full_route_gdf = ox.graph_to_gdfs(G_route, nodes=False, edges=True)

    full_route_gdf_web = full_route_gdf.to_crs("EPSG:4326")

    output_geojson = "out/rute_optimal_final.geojson"
    full_route_gdf_web.to_file(output_geojson, driver="GeoJSON")

    print(f"Selesai! File '{output_geojson}' siap untuk divisualisasikan di web.")


if __name__ == "__main__":
    main()