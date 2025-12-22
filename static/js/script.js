        var cartoLight = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        });

        var esriSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        });

        var openTopoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
            maxZoom: 17,
            attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
        });

        var map = L.map('map', {
            center: [-1.2480, 116.8600],
            zoom: 13,
            layers: [cartoLight], 
            zoomControl: false    
        });

        L.control.zoom({
            position: 'topright'
        }).addTo(map);

        var baseMaps = {
            "Peta Standar": cartoLight,
            "Satelit": esriSatellite,
            "Terrain (Topografi)": openTopoMap
        };

        L.control.layers(baseMaps).addTo(map);

        var routeLayer = null;
        var animationLayer = L.layerGroup().addTo(map);
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
            
        });

        //LOAD DATA
        fetch('/api/pois')
            .then(res => res.json())
            .then(data => { initApp(data); })
            .catch(err => console.error("Gagal load POI:", err));

        var allPoisData = []; 

        function initApp(pois) {
            allPoisData = pois; 
            
            pois.forEach(p => {
                globalPois[String(p.id)] = p.name; 
            });

            var categories = new Set(pois.map(p => p.category));
            var catSelect = document.getElementById('category-filter');
            
            Array.from(categories).sort().forEach(cat => {
                var opt = document.createElement('option');
                opt.value = cat;
                opt.innerHTML = cat;
                catSelect.appendChild(opt);
            });

            catSelect.addEventListener('change', function() {
                filterPoisByCategory(this.value);
            });

            tsStart = new TomSelect("#start-select", {
                valueField: 'id', labelField: 'name', searchField: 'name',
                options: pois, 
                maxItems: 1,
                onChange: function() { updateMarkers(); }
            });

            tsDest = new TomSelect("#dest-select", {
                valueField: 'id', labelField: 'name', searchField: 'name',
                options: pois, 
                maxItems: 6, 
                plugins: ['remove_button'],
                onChange: function() { updateMarkers(); }
            });

            renderMarkers(pois);
        }

        //Filter Data
        function filterPoisByCategory(category) {
            var filtered = (category === 'all') 
                ? allPoisData 
                : allPoisData.filter(p => p.category === category);

            // Update TomSelect
            tsStart.clearOptions();
            tsStart.addOptions(filtered);
            
            tsDest.clearOptions();
            tsDest.addOptions(filtered);

            renderMarkers(filtered);
        }

        // Logika render marker
        function renderMarkers(poisList) {
            if (window.markersLayer) map.removeLayer(window.markersLayer);
            
            window.markersLayer = L.markerClusterGroup({ disableClusteringAtZoom: 16, spiderfyOnMaxZoom: true });
            markers = {}; 

            poisList.forEach(p => {
                var m = L.marker([p.lat, p.lon], {icon: iconGrey}); 
                m.bindTooltip(`${p.name}<br><small>${p.category}</small>`, {direction: 'top', offset: [0,-30]}); // Tambah info kategori di tooltip
                
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

        //Logika Rute
        function hitungRute() {
            var startId = tsStart.getValue();
            var destIds = tsDest.getValue();
            var mode = document.getElementById('algo-select').value;

            var useAnimation = false;
            var toggleEl = document.getElementById('toggle-animation');
            if (toggleEl) useAnimation = toggleEl.checked;

            if (!startId || destIds.length === 0) {
                alert("Pilih minimal 1 titik awal dan 1 destinasi!");
                return;
            }

            document.getElementById('loading').style.display = 'flex';
            document.getElementById('result-card').style.display = 'none';
            if(routeLayer) map.removeLayer(routeLayer);
            
            if(typeof animationLayer !== 'undefined') animationLayer.clearLayers();

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

                if (data.mode === 'compare') {
                    var astarData = data.astar;
                    var dijkstraData = data.dijkstra;

                    if (useAnimation && typeof playSearchAnimation === 'function') {
                        
                        var p1 = playSearchAnimation(dijkstraData.visited_coords, '#e74c3c'); 
                        var p2 = playSearchAnimation(astarData.visited_coords, '#3498db');

                        Promise.all([p1, p2]).then(() => {
                            document.getElementById('result-card').style.display = 'block';
                            renderCompareResult(data);
                        });

                    } else {
                        document.getElementById('result-card').style.display = 'block';
                        renderCompareResult(data);
                    }

                } else {
                    currentRoutesList = data.routes;
                    var bestRoute = data.routes[0];

                    if (useAnimation && bestRoute.visited_coords && typeof playSearchAnimation === 'function') {
                        playSearchAnimation(bestRoute.visited_coords, '#3498db').then(() => {
                            document.getElementById('result-card').style.display = 'block';
                            pilihRuteOtomatis(bestRoute);
                        });
                    } else {
                        document.getElementById('result-card').style.display = 'block';
                        pilihRuteOtomatis(bestRoute);
                    }
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

        function renderRouteButtons(allRoutes, activeRank) {
            var container = document.getElementById('route-options-list');
            if(!container) return; 

            var html = '';

            allRoutes.forEach(route => {
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

        function renderRouteDetails(route) {
            var html = '<div class="timeline-box">';
            
            route.sequence_ids.forEach((id, idx) => {
                var name = globalPois[String(id)] || "Nama Tidak Ditemukan";
                
                var typeClass = (idx === 0) ? "start" : "dest";
                var label = (idx === 0) ? "Titik Awal" : "Tujuan ke-" + idx;
                
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
                    // 1. Bind Popup seperti biasa
                    layer.bindPopup(`Segmen Jalan ke-${feature.properties.segment_index + 1}`);

                    layer.on('click', function(e) {
                        if (isBlockMode) {
                            L.DomEvent.stopPropagation(e);
                            
                            layer.closePopup();

                            prosesBlokir(e.latlng.lat, e.latlng.lng);
                        }
                    });
                }
            }).addTo(map);

            map.fitBounds(routeLayer.getBounds(), {padding: [50,50]});
        }

        function prosesBlokir(lat, lng) {
            const m = L.circleMarker([lat, lng], {
                color: 'red', fillColor: '#f03', fillOpacity: 0.8, radius: 8
            }).addTo(map);
            m.bindPopup("⛔ JALAN DIBLOKIR").openPopup();
            blockedMarkers.push(m);

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
        }

        map.on('click', function(e) {
            if (!isBlockMode) return;
            prosesBlokir(e.latlng.lat, e.latlng.lng);
        });

        function toggleBlockMode() {
            isBlockMode = !isBlockMode;
            const btn = document.getElementById('btn-toggle-block');
            const info = document.getElementById('block-info');
                
            if (isBlockMode) {
                btn.innerHTML = "MODE BLOKIR JALAN: ON";
                btn.classList.add('active');
                document.getElementById('map').style.cursor = "crosshair";
                info.style.display = "block";
            } else {
                btn.innerHTML = "MODE BLOKIR JALAN: OFF";
                btn.classList.remove('active');
                document.getElementById('map').style.cursor = "";
                info.style.display = "none";
            }
        }
        
        
        function resetBlockages() {
            fetch('/api/reset_blocks', { method: 'POST' })
            .then(res => res.json())
            .then(() => {
                blockedMarkers.forEach(m => map.removeLayer(m));
                blockedMarkers = [];
                alert("Semua blokiran dihapus.");
                if(isBlockMode) toggleBlockMode();
                if (document.getElementById('result-card').style.display !== 'none') {
                    hitungRute(); 
                }
            });
        }

    
        function playSearchAnimation(coordList, colorHex) {
            return new Promise((resolve) => {
                if (!coordList || coordList.length === 0) {
                    resolve();
                    return;
                }

                const batchSize = 50;
                let index = 0;

                function drawBatch() {
                    for (let i = 0; i < batchSize; i++) {
                        if (index >= coordList.length) {
                            resolve();
                            return;
                        }

                        const latlng = coordList[index];
                        
                        L.circleMarker(latlng, {
                            radius: 4,
                            fillColor: colorHex,
                            fillOpacity: 0.6,
                            stroke: false,
                            interactive: false
                        }).addTo(animationLayer);

                        index++;
                    }
                    requestAnimationFrame(drawBatch);
                }

                drawBatch();
            });
        }
                
        function renderCompareResult(data) {
            var container = document.getElementById('route-options-list');
            var details = document.getElementById('route-details-placeholder');
            
            var astar = data.astar;
            var dijkstra = data.dijkstra;

            tampilkanPeta(astar);

            var aTime = astar.stats.time_ms;
            var dTime = dijkstra.stats.time_ms;
            var aNodes = astar.stats.nodes_visited;
            var dNodes = dijkstra.stats.nodes_visited;

            container.innerHTML = `
                <div style="margin-bottom:10px; font-weight:bold; color:#2c3e50;">Hasil Benchmark:</div>
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
                    <b>Analisa:</b> Algoritma A* memeriksa <b>${Math.round(dNodes/aNodes)}x lebih sedikit</b> titik persimpangan dibandingkan Dijkstra untuk menemukan rute yang sama.
                </div>
            `;
            
            details.innerHTML = ''; 
        }


    const collapseBtn = document.getElementById('btn-collapse-sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    const body = document.body;

    if(collapseBtn) {
        collapseBtn.addEventListener('click', function() {
            body.classList.add('sidebar-hidden');
            // Opsional: Invalidasi ukuran peta agar merender ulang area yang tertutup
            setTimeout(() => map.invalidateSize(), 300);
        });
    }

    if(toggleBtn) {
        toggleBtn.onclick = function() { 
            
            if (window.innerWidth <= 768) {
                body.classList.toggle('mobile-open');
            } else {
                body.classList.remove('sidebar-hidden');
            }
            
            setTimeout(() => map.invalidateSize(), 300);
        };
    }