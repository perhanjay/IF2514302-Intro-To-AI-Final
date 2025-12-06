        var map = L.map('map').setView([-1.2480, 116.8600], 13);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(map);

        var routeLayer = null;
        var markers = {};
        var globalPois = {}; 
        var currentRouteData = null;
        var currentRoutesList = []; 
        const segmentColors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#e67e22'];
        
        var iconGrey = L.icon({iconUrl: '/static/assets/marker-icon-grey.png', shadowUrl: '/static/assets/marker-shadow.png', iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]});
        var iconGreen = L.icon({iconUrl: '/static/assets/marker-icon-green.png', shadowUrl: '/static/assets/marker-shadow.png', iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]});
        var iconRed = L.icon({iconUrl: '/static/assets/marker-icon-red.png', shadowUrl: '/static/assets/marker-shadow.png', iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]});

        var tsStart, tsDest;

        let isBlockMode = false;
        let blockedMarkers = [];

        document.addEventListener('DOMContentLoaded', function() {
            const toggleBtn = document.getElementById('sidebarToggle');
            const body = document.body;
            
            function checkMobile() {
                if (window.innerWidth <= 768) body.classList.remove('sidebar-closed'); 
                else body.classList.remove('mobile-open');
            }
            checkMobile();
            window.addEventListener('resize', checkMobile);
            toggleBtn.addEventListener('click', function() {
                if (window.innerWidth <= 768) body.classList.toggle('mobile-open'); 
                else body.classList.toggle('sidebar-closed');
                setTimeout(() => map.invalidateSize(), 300);
            });
            
            // HAPUS event listener 'mode-select' karena elemennya sudah tidak ada
        });

        // --- 2. LOAD DATA ---
        fetch('/api/pois')
            .then(res => res.json())
            .then(data => { initApp(data); })
            .catch(err => console.error("Gagal load POI:", err));

        var allPoisData = []; // Simpan semua data POI disini

        function initApp(pois) {
            allPoisData = pois; // Simpan ke variabel global
            
            pois.forEach(p => {
                globalPois[String(p.id)] = p.name; 
            });

            // 1. ISI DROPDOWN KATEGORI OTOMATIS
            var categories = new Set(pois.map(p => p.category));
            var catSelect = document.getElementById('category-filter');
            
            // Urutkan abjad
            Array.from(categories).sort().forEach(cat => {
                var opt = document.createElement('option');
                opt.value = cat;
                opt.innerHTML = cat;
                catSelect.appendChild(opt);
            });

            // Event Listener saat Kategori Berubah
            catSelect.addEventListener('change', function() {
                filterPoisByCategory(this.value);
            });

            // 2. INISIALISASI TOMSELECT (KOSONG DULU ATAU ISI SEMUA)
            tsStart = new TomSelect("#start-select", {
                valueField: 'id', labelField: 'name', searchField: 'name',
                options: pois, // Default isi semua
                maxItems: 1,
                onChange: function() { updateMarkers(); }
            });

            tsDest = new TomSelect("#dest-select", {
                valueField: 'id', labelField: 'name', searchField: 'name',
                options: pois, // Default isi semua
                maxItems: 6, 
                plugins: ['remove_button'],
                onChange: function() { updateMarkers(); }
            });

            // ... (Kode Marker Cluster tetap sama) ...
            renderMarkers(pois); // Panggil fungsi render marker terpisah
        }

        // FUNGSI BARU: Filter Data
        function filterPoisByCategory(category) {
            var filtered = (category === 'all') 
                ? allPoisData 
                : allPoisData.filter(p => p.category === category);

            // Update TomSelect
            tsStart.clearOptions();
            tsStart.addOptions(filtered);
            
            tsDest.clearOptions();
            tsDest.addOptions(filtered);

            // Update Marker di Peta (Opsional, agar peta tidak penuh)
            renderMarkers(filtered);
        }

        // Refactoring: Pisahkan logika render marker agar bisa dipanggil ulang
        function renderMarkers(poisList) {
            // Hapus layer lama jika ada (perlu simpan ref ke layer dulu)
            if (window.markersLayer) map.removeLayer(window.markersLayer);
            
            window.markersLayer = L.markerClusterGroup({ disableClusteringAtZoom: 16, spiderfyOnMaxZoom: true });
            markers = {}; // Reset markers global

            poisList.forEach(p => {
                var m = L.marker([p.lat, p.lon], {icon: iconGrey}); 
                m.bindTooltip(`${p.name}<br><small>${p.category}</small>`, {direction: 'top', offset: [0,-30]}); // Tambah info kategori di tooltip
                
                // ... (Event listener click tetap sama) ...
                m.on('click', function() {
                    var idStr = String(p.id);
                    if (!tsStart.getValue()) tsStart.setValue(idStr);
                    else if (tsDest.getValue().includes(idStr)) tsDest.removeItem(idStr);
                    else if (tsStart.getValue() !== idStr) tsDest.addItem(idStr);
                });

                markers[p.id] = m;
                window.markersLayer.addLayer(m);
            });
            map.addLayer(window.markersLayer);
        }

        function updateMarkers() {
            var startId = tsStart.getValue();
            var destIds = tsDest.getValue();
            for (var id in markers) {
                var m = markers[id];
                if (id === startId) { m.setIcon(iconRed); m.setZIndexOffset(1000); } 
                else if (destIds.includes(id)) { m.setIcon(iconGreen); m.setZIndexOffset(900); } 
                else { m.setIcon(iconGrey); m.setZIndexOffset(0); }
            }
        }

        // --- 3. LOGIKA RUTE ---
        function hitungRute() {
            var startId = tsStart.getValue();
            var destIds = tsDest.getValue();
            var mode = document.getElementById('algo-select').value;

            if (!startId || destIds.length === 0) {
                alert("Pilih minimal 1 titik awal dan 1 destinasi!");
                return;
            }

            document.getElementById('loading').style.display = 'flex';
            document.getElementById('result-card').style.display = 'none';
            if(routeLayer) map.removeLayer(routeLayer);

            fetch('/api/route', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    start_id: parseInt(startId),
                    dest_ids: destIds.map(id => parseInt(id)),
                    mode: mode 
                })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                
                if (data.error) { alert("Error: " + data.error); return; }

                document.getElementById('result-card').style.display = 'block';
                var container = document.getElementById('route-options-list');
                var details = document.getElementById('route-details-placeholder');

                if (data.mode === 'compare') {
                    // MODE BANDINGKAN
                    var astar = data.astar;
                    var dijkstra = data.dijkstra;
                    
                    tampilkanPeta(astar);

                    var aTime = astar.stats.time_ms;
                    var dTime = dijkstra.stats.time_ms;
                    var aNodes = astar.stats.nodes_visited;
                    var dNodes = dijkstra.stats.nodes_visited;

                    container.innerHTML = `
                        <div style="margin-bottom:10px; font-weight:bold; color:#2c3e50;">🆚 Hasil Benchmark:</div>
                        <table class="compare-table">
                            <thead>
                                <tr>
                                    <th>Metrik</th>
                                    <th>A* (Smart)</th>
                                    <th>Dijkstra (Blind)</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Total Jarak</td>
                                    <td>${astar.total_km} km</td>
                                    <td>${dijkstra.total_km} km</td>
                                </tr>
                                <tr>
                                    <td>Waktu (Server)</td>
                                    <td class="${aTime <= dTime ? 'winner' : ''}">${aTime} ms</td>
                                    <td class="${dTime < aTime ? 'winner' : ''}">${dTime} ms</td>
                                </tr>
                                <tr>
                                    <td>Efisiensi<br><small>(Nodes Dicek)</small></td>
                                    <td class="${aNodes <= dNodes ? 'winner' : ''}">${aNodes}</td>
                                    <td class="${dNodes < aNodes ? 'winner' : ''}">${dNodes}</td>
                                </tr>
                            </tbody>
                        </table>
                        <div style="margin-top:15px; font-size:0.85em; color:#555; background:#e8f4f8; padding:10px; border-radius:6px; border-left:4px solid #3498db;">
                            💡 <b>Analisa:</b> Algoritma A* memeriksa <b>${Math.round(dNodes/aNodes)}x lebih sedikit</b> titik persimpangan dibandingkan Dijkstra untuk menemukan rute yang sama.
                        </div>
                    `;
                    details.innerHTML = ''; 

                } else {
                    // MODE BIASA (Single Route / Alternatif)
                    currentRoutesList = data.routes;
                    pilihRuteOtomatis(data.routes[0]);
                }
                
                if(window.innerWidth <= 768) document.body.classList.remove('mobile-open');
            })
            .catch(err => {
                console.error(err);
                document.getElementById('loading').style.display = 'none';
                alert("Gagal menghubungi server.");
            });
        }
        function pilihRuteOtomatis(route) {
            currentRouteData = route; 
            renderRouteButtons(currentRoutesList, route.rank); 
            renderRouteDetails(route); 
            tampilkanPeta(route); 
        }

        // --- 4. RENDER TOMBOL (TANPA WAKTU) ---
        function renderRouteButtons(allRoutes, activeRank) {
            var container = document.getElementById('route-options-list');
            if(!container) return; 

            var html = '';

            allRoutes.forEach(route => {
                // TIDAK ADA PERHITUNGAN WAKTU LAGI DISINI
                var isActive = (route.rank === activeRank) ? 'active' : '';
                
                html += `
                <div class="route-card ${isActive}" onclick='pilihRuteOtomatis(${JSON.stringify(route)})'>
                    <div class="route-info">
                        <h4>Rute ${route.rank}</h4>
                        <p>${route.sequence_ids.length - 1} Destinasi</p>
                    </div>
                    <div class="route-meta">
                        <span class="route-dist">${route.total_km} km</span>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        // --- 5. RENDER DETAIL URUTAN ---
        // Fungsi 5: Render Detail Urutan dengan Tampilan Timeline Keren
        function renderRouteDetails(route) {
            // Header
            var html = '<div class="timeline-box">';
            
            route.sequence_ids.forEach((id, idx) => {
                var name = globalPois[String(id)] || "Nama Tidak Ditemukan";
                
                // Tentukan tipe: Start (awal) atau Dest (tujuan)
                var typeClass = (idx === 0) ? "start" : "dest";
                var label = (idx === 0) ? "Titik Awal" : "Tujuan ke-" + idx;
                
                // Buat HTML item timeline
                html += `
                    <div class="timeline-item ${typeClass}">
                        <div class="timeline-marker"></div>
                        <div class="timeline-content">
                            <h4>${label}</h4>
                            <p>${name}</p>
                        </div>
                    </div>
                `;
            });
            html += '</div>';

            var container = document.getElementById('route-details-placeholder');
            if(container) {
                // Tampilkan dengan wrapper yang rapi
                container.innerHTML = `
                    <div style="margin-top:20px; border-top: 2px dashed #eee; padding-top:20px;">
                        <h3 style="font-size:1.1rem; margin-bottom:15px; color:#333;">🗺️ Detail Perjalanan</h3>
                        ${html}
                    </div>
                `;
            }
        }

        function tampilkanPeta(routeData) {
            if(routeLayer) map.removeLayer(routeLayer);

            routeLayer = L.geoJSON(routeData.geojson, {
                style: function(feature) {
                    var idx = feature.properties.segment_index;
                    var color = segmentColors[idx % segmentColors.length];
                    return { color: color, weight: 6, opacity: 0.9, lineCap: 'round' };
                },
                onEachFeature: function(feature, layer) {
                    layer.bindPopup(`Segmen Jalan ke-${feature.properties.segment_index + 1}`);
                }
            }).addTo(map);

            map.fitBounds(routeLayer.getBounds(), {padding: [50,50]});
        }

        function toggleBlockMode() {
            isBlockMode = !isBlockMode;
            const btn = document.getElementById('btn-toggle-block');
            const info = document.getElementById('block-info');
                
            if (isBlockMode) {
                btn.innerHTML = "MODE POHON TUMBANG: ON 🌲";
                btn.classList.add('active');
                document.getElementById('map').style.cursor = "crosshair";
                info.style.display = "block";
            } else {
                btn.innerHTML = "Mode Pohon Tumbang: OFF";
                btn.classList.remove('active');
                document.getElementById('map').style.cursor = "";
                info.style.display = "none";
            }
        }
        
        // Event Klik Peta
        map.on('click', function(e) {
            if (!isBlockMode) return;
        
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;
        
            // Tambah marker merah visual
            const m = L.circleMarker([lat, lng], {
                color: 'red', fillColor: '#f03', fillOpacity: 0.8, radius: 8
            }).addTo(map);
            m.bindPopup("⛔ JALAN DIBLOKIR").openPopup();
            blockedMarkers.push(m);
        
            // Kirim ke Backend
            fetch('/api/block_road', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({lat: lat, lon: lng})
            })
            .then(res => res.json())
            .then(data => {
                console.log("Blokir sukses:", data);
                // Otomatis refresh rute jika sudah ada hasil sebelumnya
                if (document.getElementById('result-card').style.display !== 'none') {
                    hitungRute(); 
                }
            });
        });
        
        function resetBlockages() {
            fetch('/api/reset_blocks', { method: 'POST' })
            .then(res => res.json())
            .then(() => {
                blockedMarkers.forEach(m => map.removeLayer(m));
                blockedMarkers = [];
                alert("Semua blokiran dihapus.");
                if(isBlockMode) toggleBlockMode(); // Matikan mode
                // Refresh rute
                if (document.getElementById('result-card').style.display !== 'none') {
                    hitungRute(); 
                }
            });
        }