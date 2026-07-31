// ============================================================
//  SENSD FLOW DASHBOARD — flow_analysis.js
//  Completely independent from maps.js
// ============================================================

// ── MAP INIT ──────────────────────────────────────────────
const map = L.map('dashboard-map', {
    zoomControl: true,
    minZoom: 2,
    maxZoom: 18,
    worldCopyJump: false,
    maxBounds: [[-90, -180], [90, 180]],
    maxBoundsViscosity: 1.0
}).setView([40, -95], 5);

const basemaps = {
    osm:       L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }),
    satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: '© Esri' }),
    light:     L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { attribution: '© CartoDB' }),
    dark:      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '© CartoDB' }),
};

let currentBasemap = 'osm';
basemaps.osm.addTo(map);

// ── FLOW COMBO COLORS (matches main maps.js) ──────────────
const flowComboColors = {
    'Raw→Raw':               '#c0392b',
    'Raw→Semicooked':        '#e67e22',
    'Semicooked→Semicooked': '#f1c40f',
    'Cooked→Cooked':         '#27ae60',
};

function getFlowComboColor(ti, tj) {
    const key = `${(ti||'').trim()}→${(tj||'').trim()}`;
    return flowComboColors[key] || '#4f8ef7';
}

// ── UPLOADED LAYERS REGISTRY ──────────────────────────────
// { layerKey: { group, geojson, filename, style, visible } }
const uploadedLayers = {};

// ── BASEMAP CONTROLS ──────────────────────────────────────
document.querySelectorAll('.basemap-option').forEach(el => {
    el.addEventListener('click', () => {
        const bm = el.dataset.basemap;
        if (bm === currentBasemap) return;
        map.removeLayer(basemaps[currentBasemap]);
        if (document.getElementById('basemap-toggle').checked) {
            basemaps[bm].addTo(map);
        }
        currentBasemap = bm;
        document.querySelectorAll('.basemap-option').forEach(o => o.classList.remove('active'));
        el.classList.add('active');
    });
});

document.getElementById('basemap-toggle').addEventListener('change', function () {
    if (this.checked) {
        basemaps[currentBasemap].addTo(map);
    } else {
        map.removeLayer(basemaps[currentBasemap]);
    }
});

// ── PANEL COLLAPSE ────────────────────────────────────────
document.getElementById('toc-collapse-btn').addEventListener('click', () => {
    document.getElementById('toc-panel').classList.toggle('collapsed');
});

document.getElementById('toolbox-collapse-btn').addEventListener('click', () => {
    document.getElementById('toolbox-panel').classList.toggle('collapsed');
});

// ── SECTION ACCORDION ─────────────────────────────────────
document.querySelectorAll('.toc-section-title').forEach(title => {
    title.classList.add('open');
    title.addEventListener('click', () => {
        const body = document.getElementById(title.dataset.target);
        const isOpen = body.style.display !== 'none';
        body.style.display = isOpen ? 'none' : 'block';
        title.classList.toggle('open', !isOpen);
    });
});

document.querySelectorAll('.tool-title').forEach(title => {
    title.addEventListener('click', () => {
        const body = document.getElementById(title.dataset.target);
        const isOpen = body.style.display !== 'none';
        body.style.display = isOpen ? 'none' : 'block';
        title.classList.toggle('open', !isOpen);
    });
});

// Open upload tool by default
document.getElementById('tool-upload').style.display = 'block';
document.querySelector('[data-target="tool-upload"]').classList.add('open');

// ── UPLOAD ────────────────────────────────────────────────
const dropZone   = document.getElementById('upload-drop-zone');
const fileInput  = document.getElementById('dash-file-input');
const fileNameEl = document.getElementById('upload-file-name');
const uploadBtn  = document.getElementById('dash-upload-btn');
const statusEl   = document.getElementById('dash-upload-status');

// Drag & drop visual feedback
dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        onFileSelected();
    }
});

fileInput.addEventListener('change', onFileSelected);

function onFileSelected() {
    if (!fileInput.files.length) return;
    const name = fileInput.files[0].name;
    fileNameEl.textContent = `📄 ${name}`;
    uploadBtn.disabled = false;
    statusEl.textContent = '';
    statusEl.className = '';
}

// ── Upload mode switch ─────────────────────────────────────
let currentUploadMode = 'flow';

function switchUploadMode(mode) {
    currentUploadMode = mode;
    document.getElementById('mode-btn-flow').classList.toggle('active', mode === 'flow');
    document.getElementById('mode-btn-display').classList.toggle('active', mode === 'display');
    document.getElementById('upload-hint-flow').style.display    = mode === 'flow'    ? 'block' : 'none';
    document.getElementById('upload-hint-display').style.display = mode === 'display' ? 'block' : 'none';
    document.getElementById('display-col-config').style.display  = mode === 'display' ? 'block' : 'none';
    // Reset file selection
    fileInput.value = '';
    fileNameEl.textContent = '';
    uploadBtn.disabled = true;
    statusEl.textContent = '';
    statusEl.className = '';
}

uploadBtn.addEventListener('click', () => {
    if (!fileInput.files.length) return;

    if (currentUploadMode === 'flow') {
        // ── Flow upload ──────────────────────────────────────
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        uploadBtn.disabled = true;
        statusEl.textContent = 'Processing…';
        statusEl.className = '';

        fetch('/mapsapp/api/upload_flow/', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if (!data.success) {
                    statusEl.textContent = `Error: ${data.error}`;
                    statusEl.className = 'error';
                    uploadBtn.disabled = false;
                    return;
                }
                statusEl.textContent = `✓ ${data.rows_loaded} flows rendered.`;
                renderLayer(data.geojson, data.filename);
                fileInput.value = '';
                fileNameEl.textContent = '';
                uploadBtn.disabled = true;
            })
            .catch(() => {
                statusEl.textContent = 'Upload failed — check the server.';
                statusEl.className = 'error';
                uploadBtn.disabled = false;
            });

    } else {
        // ── Display upload — process client-side ─────────────
        const file = fileInput.files[0];
        const ext  = file.name.split('.').pop().toLowerCase();
        uploadBtn.disabled = true;
        statusEl.textContent = 'Processing…';
        statusEl.className = '';

        const reader = new FileReader();

        reader.onload = function (e) {
            try {
                if (ext === 'geojson' || ext === 'json') {
                    const geojson = JSON.parse(e.target.result);
                    renderDisplayLayer(geojson, file.name);
                    statusEl.textContent = `✓ ${geojson.features?.length || 0} features rendered.`;

                } else if (ext === 'csv' || ext === 'xlsx' || ext === 'xls') {
                    // Send to server for tabular → GeoJSON conversion
                    const latCol = document.getElementById('display-lat-col').value.trim() || 'Latitude';
                    const lonCol = document.getElementById('display-lon-col').value.trim() || 'Longitude';
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('lat_column', latCol);
                    formData.append('lng_column', lonCol);

                    fetch('/mapsapp/api/upload/', { method: 'POST', body: formData })
                        .then(res => res.json())
                        .then(data => {
                            if (!data.success) {
                                statusEl.textContent = `Error: ${data.error}`;
                                statusEl.className = 'error';
                                uploadBtn.disabled = false;
                                return;
                            }
                            // Fetch the stored GeoJSON back
                            return fetch(`/mapsapp/api/layers/${data.layer_id}/`);
                        })
                        .then(res => res?.json())
                        .then(geojson => {
                            if (!geojson) return;
                            renderDisplayLayer(geojson, file.name);
                            statusEl.textContent = `✓ ${geojson.features?.length || 0} features rendered.`;
                            fileInput.value = '';
                            fileNameEl.textContent = '';
                            uploadBtn.disabled = true;
                        })
                        .catch(() => {
                            statusEl.textContent = 'Upload failed — check the server.';
                            statusEl.className = 'error';
                            uploadBtn.disabled = false;
                        });
                    return; // async path exits here

                } else {
                    statusEl.textContent = 'Only GeoJSON, CSV, or Excel supported.';
                    statusEl.className = 'error';
                    uploadBtn.disabled = false;
                    return;
                }

                fileInput.value = '';
                fileNameEl.textContent = '';
                uploadBtn.disabled = true;

            } catch (err) {
                statusEl.textContent = `Parse error: ${err.message}`;
                statusEl.className = 'error';
                uploadBtn.disabled = false;
            }
        };

        if (ext === 'geojson' || ext === 'json') {
            reader.readAsText(file);
        } else {
            reader.readAsArrayBuffer(file); // not used — handled via fetch above
        }
    }
});

// ── RENDER DISPLAY LAYER ──────────────────────────────────
// Renders any GeoJSON as-is: points → circles, lines → polylines, polygons → filled
const displayLayerColors = [
    '#e74c3c','#3498db','#2ecc71','#9b59b6','#f39c12','#1abc9c','#e67e22','#34495e'
];
let displayColorIndex = 0;

function renderDisplayLayer(geojson, filename) {
    if (!geojson.features || !geojson.features.length) {
        statusEl.textContent = 'No features found in file.';
        return;
    }

    const layerKey = `display_${Date.now()}`;
    const color    = displayLayerColors[displayColorIndex % displayLayerColors.length];
    displayColorIndex++;

    const group = L.geoJSON(geojson, {
        style: () => ({ color, weight: 2, opacity: 0.8, fillColor: color, fillOpacity: 0.2 }),
        pointToLayer: (feature, latlng) => L.circleMarker(latlng, {
            radius: 6, fillColor: color, color: '#fff',
            weight: 1.5, opacity: 1, fillOpacity: 0.85
        }),
        onEachFeature: (feature, layer) => {
            if (!feature.properties) return;
            const props = feature.properties;
            const rows  = Object.entries(props)
                .filter(([, v]) => v !== null && v !== '')
                .map(([k, v]) => `<b>${k}:</b> ${v}`)
                .join('<br>');
            if (rows) layer.bindPopup(`<div style="max-height:200px;overflow-y:auto;font-size:12px;">${rows}</div>`);
        }
    }).addTo(map);

    // Detect geometry type for TOC icon
    const geomType = geojson.features[0]?.geometry?.type || 'Unknown';
    const geomIcon = geomType.includes('Point') ? '🔵' :
                     geomType.includes('Line')  ? '〰️' : '🟩';

    // Store as display layer
    uploadedLayers[layerKey] = {
        displayGroup: group,
        isDisplay: true,
        geojson,
        filename,
        color,
        visible: true
    };

    addDisplayTocRow(layerKey, filename, color, geomIcon, geojson.features.length);
    addLayerToSelects(layerKey, filename);

    // Fit bounds
    try {
        const b = group.getBounds();
        if (b.isValid()) map.fitBounds(b, { padding: [40, 40], maxZoom: 14 });
    } catch(e) {}
}

// ── LABEL SYSTEM ─────────────────────────────────────────
// labelState: { layerKey: { field, size, visible, labelGroup } }
const labelState = {};

function buildLabelPanel(layerKey, geojson) {
    // Get all property keys from first feature
    const props    = geojson.features?.[0]?.properties || {};
    const fields   = Object.keys(props);
    const optionsHtml = fields.map(f =>
        `<option value="${f}">${f}</option>`
    ).join('');

    const panel = document.createElement('div');
    panel.className = 'label-panel';
    panel.id = `label-panel-${layerKey}`;
    panel.style.display = 'none';
    panel.innerHTML = `
        <div class="label-panel-inner">
            <div class="label-row">
                <label class="toc-toggle-label" style="flex-shrink:0;">
                    <input type="checkbox" id="label-toggle-${layerKey}">
                    <span class="toc-toggle-slider"></span>
                </label>
                <span style="font-size:11px;color:var(--text-muted);">Show Labels</span>
            </div>
            <div class="label-row" style="margin-top:6px;">
                <span style="font-size:11px;color:var(--text-muted);width:60px;flex-shrink:0;">Field</span>
                <select id="label-field-${layerKey}" style="flex:1;background:var(--panel-b);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;">
                    ${optionsHtml}
                </select>
            </div>
            <div class="label-row" style="margin-top:6px;">
                <span style="font-size:11px;color:var(--text-muted);width:60px;flex-shrink:0;">Size <span id="label-size-val-${layerKey}">11</span>px</span>
                <input type="range" id="label-size-${layerKey}" min="8" max="20" value="11"
                    style="flex:1;accent-color:var(--accent);">
            </div>
            <button class="tool-btn" style="margin-top:8px;padding:5px;" onclick="applyLabels('${layerKey}')">
                <i class="fa fa-check"></i> Apply
            </button>
        </div>
    `;

    // Live size label update
    panel.querySelector(`#label-size-${layerKey}`).addEventListener('input', function () {
        document.getElementById(`label-size-val-${layerKey}`).textContent = this.value;
    });

    // Toggle show/hide existing labels
    panel.querySelector(`#label-toggle-${layerKey}`).addEventListener('change', function () {
        const state = labelState[layerKey];
        if (!state?.labelGroup) return;
        if (this.checked) {
            state.labelGroup.addTo(map);
            state.visible = true;
        } else {
            map.removeLayer(state.labelGroup);
            state.visible = false;
        }
    });

    return panel;
}

function toggleLabelPanel(layerKey) {
    const panel = document.getElementById(`label-panel-${layerKey}`);
    if (!panel) return;
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

function applyLabels(layerKey) {
    const entry = uploadedLayers[layerKey];
    if (!entry) return;

    const field    = document.getElementById(`label-field-${layerKey}`)?.value;
    const fontSize = document.getElementById(`label-size-${layerKey}`)?.value || 11;

    if (!field) return;

    // Remove existing label group
    if (labelState[layerKey]?.labelGroup) {
        map.removeLayer(labelState[layerKey].labelGroup);
    }

    const labelGroup = L.layerGroup().addTo(map);

    // Collect unique point locations from geojson
    const seenCoords = new Set();

    entry.geojson.features.forEach(feature => {
        const props = feature.properties;
        const labelText = props[field];
        if (!labelText && labelText !== 0) return;

        // For flow layers — label From and To nodes
        // For display layers — use geometry coordinates
        const points = [];

        if (entry.isDisplay) {
            const geom = feature.geometry;
            if (!geom) return;
            if (geom.type === 'Point') {
                points.push([geom.coordinates[1], geom.coordinates[0]]);
            } else if (geom.type === 'MultiPoint') {
                geom.coordinates.forEach(c => points.push([c[1], c[0]]));
            } else if (geom.type === 'Polygon' || geom.type === 'MultiPolygon') {
                // Label at centroid approximation
                try {
                    const bounds = L.geoJSON(feature).getBounds();
                    points.push([bounds.getCenter().lat, bounds.getCenter().lng]);
                } catch(e) {}
            }
        } else {
            // Flow layer — label From node
            if (props.from_latitude && props.from_longitude) {
                points.push([props.from_latitude, props.from_longitude]);
            }
        }

        points.forEach(([lat, lon]) => {
            const key = `${lat.toFixed(5)},${lon.toFixed(5)}`;
            if (seenCoords.has(key)) return;
            seenCoords.add(key);

            L.marker([lat, lon], {
                icon: L.divIcon({
                    className: '',
                    html: `<div style="
                        font-size:${fontSize}px;
                        font-family:'DM Sans',sans-serif;
                        font-weight:500;
                        color:#1a1d27;
                        white-space:nowrap;
                        text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff,
                                     -1px 1px 0 #fff,  1px  1px 0 #fff;
                        pointer-events:none;
                        transform:translate(8px,-50%);
                    ">${labelText}</div>`,
                    iconSize: [0, 0],
                    iconAnchor: [0, 0]
                }),
                interactive: false,
                zIndexOffset: -100
            }).addTo(labelGroup);
        });
    });

    labelState[layerKey] = { field, fontSize, visible: true, labelGroup };

    // Sync toggle to checked
    const toggle = document.getElementById(`label-toggle-${layerKey}`);
    if (toggle) toggle.checked = true;
}

function removeLayerLabels(layerKey) {
    if (labelState[layerKey]?.labelGroup) {
        map.removeLayer(labelState[layerKey].labelGroup);
        delete labelState[layerKey];
    }
    const panel = document.getElementById(`label-panel-${layerKey}`);
    if (panel) panel.remove();
}

function addDisplayTocRow(layerKey, filename, color, geomIcon, count) {
    const emptyMsg = document.getElementById('toc-flow-empty');
    if (emptyMsg) emptyMsg.style.display = 'none';

    const container = document.getElementById('toc-flow-layers');
    const row       = document.createElement('div');
    row.className   = 'toc-row';
    row.id          = `toc-row-${layerKey}`;
    row.innerHTML   = `
        <label class="toc-toggle-label">
            <input type="checkbox" checked id="toc-toggle-${layerKey}">
            <span class="toc-toggle-slider"></span>
        </label>
        <div class="layer-dot" style="background:${color}"></div>
        <span class="toc-layer-name" title="${filename}">${geomIcon} ${filename} <span style="color:var(--text-muted);font-size:10px;">(${count})</span></span>
        <div class="toc-layer-actions">
            <button class="toc-action-btn" title="Labels" onclick="toggleLabelPanel('${layerKey}')">
                <i class="fa fa-tag"></i>
            </button>
            <button class="toc-action-btn" title="Remove" onclick="removeLayer('${layerKey}')">
                <i class="fa fa-trash"></i>
            </button>
        </div>
    `;
    container.appendChild(row);

    // Label panel (injected after row) — read geojson from registry
    const labelPanel = buildLabelPanel(layerKey, uploadedLayers[layerKey].geojson);
    container.appendChild(labelPanel);

    document.getElementById(`toc-toggle-${layerKey}`).addEventListener('change', function () {
        const entry = uploadedLayers[layerKey];
        if (!entry) return;
        this.checked ? entry.displayGroup.addTo(map) : map.removeLayer(entry.displayGroup);
        entry.visible = this.checked;
    });
}

// ── Arrow helper — draws a chevron polyline in pixel space ─
// Converts to/from latlng using map projection so angle is always exact.
// The chevron redraws on zoom/move to stay aligned with the line.
function addFlowArrow(fromLat, fromLon, toLat, toLon, color, group) {
    const size = 8;  // half-width of chevron arms in pixels

    function buildChevron() {
        const fromPx = map.latLngToLayerPoint([fromLat, fromLon]);
        const toPx   = map.latLngToLayerPoint([toLat,   toLon]);

        // Midpoint in layer pixels
        const mx = (fromPx.x + toPx.x) / 2;
        const my = (fromPx.y + toPx.y) / 2;

        // Angle of the line in radians
        const angle = Math.atan2(toPx.y - fromPx.y, toPx.x - fromPx.x);

        // Two arms of the chevron, pointing back from midpoint
        const armAngle1 = angle + Math.PI - 0.5;  // ~150° from direction
        const armAngle2 = angle + Math.PI + 0.5;

        const arm1End = {
            x: mx + size * Math.cos(armAngle1),
            y: my + size * Math.sin(armAngle1)
        };
        const arm2End = {
            x: mx + size * Math.cos(armAngle2),
            y: my + size * Math.sin(armAngle2)
        };

        // Convert back to latlng for Leaflet polyline
        const midLL  = map.layerPointToLatLng([mx,       my]);
        const arm1LL = map.layerPointToLatLng([arm1End.x, arm1End.y]);
        const arm2LL = map.layerPointToLatLng([arm2End.x, arm2End.y]);

        return [arm1LL, midLL, arm2LL];
    }

    // Create chevron as a polyline
    const chevron = L.polyline(buildChevron(), {
        color,
        weight: 1.5,
        opacity: 0.85,
        interactive: false
    });

    // Rebuild on zoom/move to keep aligned
    const onMapChange = () => {
        if (map.hasLayer(chevron)) {
            chevron.setLatLngs(buildChevron());
        }
    };

    chevron.on('add',    () => map.on('zoomend moveend', onMapChange));
    chevron.on('remove', () => map.off('zoomend moveend', onMapChange));

    group.addLayer(chevron);
}

function renderLayer(geojson, filename) {
    if (!geojson.features || !geojson.features.length) {
        statusEl.textContent = 'No valid rows found.';
        return;
    }

    const layerKey = `layer_${Date.now()}`;

    const style = {
        lineColor:  null,
        pointColor: '#3a86ff',
        weight:     null,
        radius:     6,
        opacity:    0.75,
    };

    const quantities = geojson.features.map(f => f.properties.quantity || 0);
    const minQ = Math.min(...quantities);
    const maxQ = Math.max(...quantities);

    function calcWeight(qty) {
        if (maxQ === minQ) return 3;
        return 1 + ((qty - minQ) / (maxQ - minQ)) * 7;
    }

    // ── Build sub-layer groups ──────────────────────────────
    // 1. Points group (all nodes deduped)
    const pointsGroup = L.layerGroup().addTo(map);

    // 2. One line group per product type combo
    const comboGroups = {};  // { 'Raw→Raw': L.layerGroup, ... }

    // Collect unique combos first
    geojson.features.forEach(f => {
        const combo = `${(f.properties.product_type_i||'').trim()}→${(f.properties.product_type_j||'').trim()}`;
        if (!comboGroups[combo]) {
            comboGroups[combo] = L.layerGroup().addTo(map);
        }
    });

    // Draw lines + arrows into their combo group
    geojson.features.forEach(feature => {
        const p     = feature.properties;
        const qty   = p.quantity || 0;
        const combo = `${(p.product_type_i||'').trim()}→${(p.product_type_j||'').trim()}`;
        const color = style.lineColor || getFlowComboColor(p.product_type_i, p.product_type_j);
        const w     = style.weight    || calcWeight(qty);

        const line = L.polyline(
            [[p.from_latitude, p.from_longitude], [p.to_latitude, p.to_longitude]],
            { color, weight: w, opacity: style.opacity }
        );
        line.bindPopup(`
            <b>Flow:</b> ${p.from_id} → ${p.to_id}<br>
            <b>From:</b> ${p.from_node || p.from_id} (${p.from_city_area || ''}, ${p.from_state || ''})<br>
            <b>To:</b> ${p.to_node || p.to_id} (${p.to_city_area || ''}, ${p.to_state || ''})<br>
            <b>Product:</b> ${p.product_type_i || '—'} → ${p.product_type_j || '—'}<br>
            <b>Quantity:</b> ${Number(qty).toLocaleString(undefined, {maximumFractionDigits:1})}<br>
            <i style="color:#888">📂 ${filename}</i>
        `);
        line.on('mouseover', function () { this.setStyle({ opacity: 1, weight: w + 2 }); });
        line.on('mouseout',  function () { this.setStyle({ opacity: style.opacity, weight: w }); });
        line._flowProps = p;
        comboGroups[combo].addLayer(line);

        // Arrowhead — pixel-accurate angle via helper
        addFlowArrow(p.from_latitude, p.from_longitude, p.to_latitude, p.to_longitude, color, comboGroups[combo]);
    });

    // Draw deduplicated points into pointsGroup
    const seenNodes = {};
    geojson.features.forEach(feature => {
        const p = feature.properties;
        [[p.from_id, p.from_latitude, p.from_longitude, p.from_node, p.from_city_area, p.from_state, p.product_type_i, 'Origin'],
         [p.to_id,   p.to_latitude,   p.to_longitude,   p.to_node,   p.to_city_area,   p.to_state,   p.product_type_j, 'Destination']]
        .forEach(([id, lat, lon, node, city, state, type, role]) => {
            if (seenNodes[id]) return;
            seenNodes[id] = true;
            const m = L.circleMarker([lat, lon], {
                radius: style.radius,
                fillColor: style.pointColor,
                color: '#fff', weight: 1.5, opacity: 1, fillOpacity: 0.9
            });
            m.bindPopup(`
                <b>Node:</b> ${node || id} (${id})<br>
                <b>Role:</b> ${role}<br>
                <b>City:</b> ${city || '—'}, ${state || '—'}<br>
                <b>Product:</b> ${type || '—'}
            `);
            m._nodeId = id;
            pointsGroup.addLayer(m);
        });
    });

    // Store in registry with sub-layers
    uploadedLayers[layerKey] = {
        pointsGroup,
        comboGroups,
        geojson,
        filename,
        style,
        visible: true,
        minQ,
        maxQ
    };

    // Add to TOC with sub-layers
    addTocRow(layerKey, filename);

    // Add to symbology + analysis selects
    addLayerToSelects(layerKey, filename);

    // Fit map to layer
    const bounds = geojson.features.reduce((b, f) => {
        const p = f.properties;
        return b.extend([[p.from_latitude, p.from_longitude], [p.to_latitude, p.to_longitude]]);
    }, L.latLngBounds([]));
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
}

// ── TOC ROW ───────────────────────────────────────────────
function addTocRow(layerKey, filename) {
    const emptyMsg = document.getElementById('toc-flow-empty');
    if (emptyMsg) emptyMsg.style.display = 'none';

    const entry     = uploadedLayers[layerKey];
    const container = document.getElementById('toc-flow-layers');

    // ── Parent row ──────────────────────────────────────────
    const parent = document.createElement('div');
    parent.className = 'toc-tree-parent';
    parent.id = `toc-row-${layerKey}`;
    parent.innerHTML = `
        <div class="toc-tree-header">
            <span class="toc-tree-toggle-btn" id="toc-tree-btn-${layerKey}">
                <i class="fa fa-chevron-down" style="font-size:10px;"></i>
            </span>
            <label class="toc-toggle-label">
                <input type="checkbox" checked id="toc-toggle-${layerKey}">
                <span class="toc-toggle-slider"></span>
            </label>
            <i class="fa fa-folder-open" style="color:var(--warning);font-size:12px;"></i>
            <span class="toc-layer-name" title="${filename}">${filename}</span>
            <div class="toc-layer-actions">
                <button class="toc-action-btn" title="Labels" onclick="toggleLabelPanel('${layerKey}')">
                    <i class="fa fa-tag"></i>
                </button>
                <button class="toc-action-btn" title="Remove layer" onclick="removeLayer('${layerKey}')">
                    <i class="fa fa-trash"></i>
                </button>
            </div>
        </div>
        <div class="toc-tree-children" id="toc-children-${layerKey}"></div>
    `;
    container.appendChild(parent);

    // Expand/collapse children
    document.getElementById(`toc-tree-btn-${layerKey}`).addEventListener('click', () => {
        const children = document.getElementById(`toc-children-${layerKey}`);
        const icon     = document.querySelector(`#toc-tree-btn-${layerKey} i`);
        const isOpen   = children.style.display !== 'none';
        children.style.display = isOpen ? 'none' : 'block';
        icon.className = isOpen ? 'fa fa-chevron-right' : 'fa fa-chevron-down';
        icon.style.fontSize = '10px';
    });

    // Parent toggle — shows/hides all children
    document.getElementById(`toc-toggle-${layerKey}`).addEventListener('change', function () {
        const isOn = this.checked;
        entry.visible = isOn;

        // Toggle points
        isOn ? entry.pointsGroup.addTo(map) : map.removeLayer(entry.pointsGroup);

        // Toggle all combo groups
        Object.values(entry.comboGroups).forEach(g => {
            isOn ? g.addTo(map) : map.removeLayer(g);
        });

        // Sync all child checkboxes
        document.querySelectorAll(`#toc-children-${layerKey} input[type=checkbox]`).forEach(cb => {
            cb.checked = isOn;
        });
    });

    // ── Points sub-row ──────────────────────────────────────
    const childrenEl = document.getElementById(`toc-children-${layerKey}`);
    addSubRow(childrenEl, `${layerKey}_points`, '🔵 Points', '#3a86ff', entry.pointsGroup);

    // ── One sub-row per product combo ───────────────────────
    Object.entries(entry.comboGroups).forEach(([combo, group]) => {
        const color = getFlowComboColor(...combo.split('→'));
        addSubRow(childrenEl, `${layerKey}_${combo}`, `── ${combo || '(untyped)'}`, color, group);
    });

    // ── Label panel (for flow points) ───────────────────────
    const labelPanel = buildLabelPanel(layerKey, entry.geojson);
    container.appendChild(labelPanel);
}

function addSubRow(container, subKey, label, color, layerGroup) {
    const row = document.createElement('div');
    row.className = 'toc-row toc-sub-row';
    row.id = `toc-sub-${subKey}`;
    row.innerHTML = `
        <label class="toc-toggle-label">
            <input type="checkbox" checked id="toc-toggle-sub-${subKey}">
            <span class="toc-toggle-slider"></span>
        </label>
        <div class="layer-dot" style="background:${color};border-radius:2px;"></div>
        <span class="toc-layer-name">${label}</span>
    `;
    container.appendChild(row);

    document.getElementById(`toc-toggle-sub-${subKey}`).addEventListener('change', function () {
        this.checked ? layerGroup.addTo(map) : map.removeLayer(layerGroup);
    });
}

function removeLayer(layerKey) {
    const entry = uploadedLayers[layerKey];
    if (!entry) return;

    if (entry.isDisplay) {
        // Display layer — single group
        if (entry.displayGroup) map.removeLayer(entry.displayGroup);
    } else {
        // Flow layer — sub-groups
        if (entry.pointsGroup) map.removeLayer(entry.pointsGroup);
        if (entry.comboGroups) Object.values(entry.comboGroups).forEach(g => map.removeLayer(g));
    }

    delete uploadedLayers[layerKey];

    const row = document.getElementById(`toc-row-${layerKey}`);
    if (row) row.remove();

    if (!Object.keys(uploadedLayers).length) {
        document.getElementById('toc-flow-empty').style.display = 'block';
    }

    removeLayerFromSelects(layerKey);
    removeLayerLabels(layerKey);
}

// ── LAYER SELECTS (symbology + analysis) ─────────────────
function addLayerToSelects(layerKey, filename) {
    [document.getElementById('sym-layer-select'),
     document.getElementById('analysis-layer-select')]
    .forEach(sel => {
        const opt = document.createElement('option');
        opt.value = layerKey;
        opt.textContent = filename;
        opt.id = `opt-${layerKey}`;
        sel.appendChild(opt.cloneNode(true));
    });

    // Show sym/analysis controls if previously hidden
    document.getElementById('sym-empty-msg').style.display = 'none';
    document.getElementById('analysis-empty-msg').style.display = 'none';
}

function removeLayerFromSelects(layerKey) {
    document.querySelectorAll(`#opt-${layerKey}, option[value="${layerKey}"]`).forEach(o => o.remove());
    if (!Object.keys(uploadedLayers).length) {
        document.getElementById('sym-empty-msg').style.display = 'block';
        document.getElementById('sym-controls').style.display = 'none';
        document.getElementById('analysis-empty-msg').style.display = 'block';
        document.getElementById('analysis-results').style.display = 'none';
    }
}

// ── SYMBOLOGY ─────────────────────────────────────────────
const symSelect  = document.getElementById('sym-layer-select');
const symControls = document.getElementById('sym-controls');

symSelect.addEventListener('change', () => {
    if (!symSelect.value) { symControls.style.display = 'none'; return; }
    const entry = uploadedLayers[symSelect.value];
    if (!entry) return;
    symControls.style.display = 'block';
    document.getElementById('sym-line-color').value  = entry.style.lineColor  || '#4f8ef7';
    document.getElementById('sym-point-color').value = entry.style.pointColor || '#3a86ff';
    document.getElementById('sym-weight').value       = entry.style.weight    || 3;
    document.getElementById('sym-opacity').value      = Math.round((entry.style.opacity || 0.75) * 100);
    document.getElementById('sym-radius').value       = entry.style.radius    || 6;
    updateSymLabels();
});

['sym-weight', 'sym-opacity', 'sym-radius'].forEach(id => {
    document.getElementById(id).addEventListener('input', updateSymLabels);
});

function updateSymLabels() {
    document.getElementById('sym-weight-val').textContent  = document.getElementById('sym-weight').value;
    document.getElementById('sym-opacity-val').textContent = document.getElementById('sym-opacity').value;
    document.getElementById('sym-radius-val').textContent  = document.getElementById('sym-radius').value;
}

document.getElementById('sym-apply-btn').addEventListener('click', () => {
    const key   = symSelect.value;
    const entry = uploadedLayers[key];
    if (!entry) return;

    entry.style.lineColor  = document.getElementById('sym-line-color').value;
    entry.style.pointColor = document.getElementById('sym-point-color').value;
    entry.style.weight     = parseFloat(document.getElementById('sym-weight').value);
    entry.style.opacity    = parseFloat(document.getElementById('sym-opacity').value) / 100;
    entry.style.radius     = parseFloat(document.getElementById('sym-radius').value);

    // Re-render all sub-layers with new style
    map.removeLayer(entry.pointsGroup);
    Object.values(entry.comboGroups).forEach(g => map.removeLayer(g));
    entry.pointsGroup = L.layerGroup().addTo(map);
    entry.comboGroups = {};
    rebuildLayer(key);

    // Update TOC sub-row dots
    document.querySelectorAll(`#toc-children-${key} .layer-dot`).forEach(dot => {
        if (dot.closest('.toc-sub-row')?.id?.includes('_points')) {
            dot.style.background = entry.style.pointColor;
        }
    });
});

document.getElementById('sym-reset-btn').addEventListener('click', () => {
    const key   = symSelect.value;
    const entry = uploadedLayers[key];
    if (!entry) return;

    entry.style = { lineColor: null, pointColor: '#3a86ff', weight: null, radius: 6, opacity: 0.75 };
    map.removeLayer(entry.pointsGroup);
    Object.values(entry.comboGroups).forEach(g => map.removeLayer(g));
    entry.pointsGroup = L.layerGroup().addTo(map);
    entry.comboGroups = {};
    rebuildLayer(key);

    symSelect.dispatchEvent(new Event('change'));
});

function rebuildLayer(layerKey) {
    const entry = uploadedLayers[layerKey];
    if (!entry) return;

    const { geojson, style, minQ, maxQ } = entry;

    function calcWeight(qty) {
        if (maxQ === minQ) return style.weight || 3;
        if (style.weight) return style.weight;
        return 1 + ((qty - minQ) / (maxQ - minQ)) * 7;
    }

    // Rebuild combo groups
    geojson.features.forEach(f => {
        const combo = `${(f.properties.product_type_i||'').trim()}→${(f.properties.product_type_j||'').trim()}`;
        if (!entry.comboGroups[combo]) {
            entry.comboGroups[combo] = L.layerGroup().addTo(map);
        }
    });

    geojson.features.forEach(feature => {
        const p     = feature.properties;
        const qty   = p.quantity || 0;
        const combo = `${(p.product_type_i||'').trim()}→${(p.product_type_j||'').trim()}`;
        const color = style.lineColor || getFlowComboColor(p.product_type_i, p.product_type_j);
        const w     = calcWeight(qty);

        const line = L.polyline(
            [[p.from_latitude, p.from_longitude], [p.to_latitude, p.to_longitude]],
            { color, weight: w, opacity: style.opacity }
        );
        line.bindPopup(`
            <b>Flow:</b> ${p.from_id} → ${p.to_id}<br>
            <b>Product:</b> ${p.product_type_i||'—'} → ${p.product_type_j||'—'}<br>
            <b>Quantity:</b> ${Number(qty).toLocaleString(undefined, {maximumFractionDigits:1})}
        `);
        line.on('mouseover', function () { this.setStyle({ opacity: 1, weight: w + 2 }); });
        line.on('mouseout',  function () { this.setStyle({ opacity: style.opacity, weight: w }); });
        entry.comboGroups[combo].addLayer(line);

        addFlowArrow(p.from_latitude, p.from_longitude, p.to_latitude, p.to_longitude, color, entry.comboGroups[combo]);
    });

    // Rebuild points
    const seenNodes = {};
    geojson.features.forEach(feature => {
        const p = feature.properties;
        [[p.from_id, p.from_latitude, p.from_longitude, p.from_node, p.product_type_i, 'Origin'],
         [p.to_id,   p.to_latitude,   p.to_longitude,   p.to_node,   p.product_type_j, 'Destination']]
        .forEach(([id, lat, lon, node, type, role]) => {
            if (seenNodes[id]) return;
            seenNodes[id] = true;
            L.circleMarker([lat, lon], {
                radius: style.radius,
                fillColor: style.pointColor,
                color: '#fff', weight: 1.5, opacity: 1, fillOpacity: 0.9
            }).bindPopup(`<b>${node || id}</b><br>Role: ${role}<br>Product: ${type||'—'}`)
              .addTo(entry.pointsGroup);
        });
    });

    // Re-wire sub-row toggles to new groups
    Object.entries(entry.comboGroups).forEach(([combo, group]) => {
        const subKey = `${layerKey}_${combo}`;
        const cb = document.getElementById(`toc-toggle-sub-${subKey}`);
        if (cb) {
            cb.replaceWith(cb.cloneNode(true)); // remove old listener
            const newCb = document.getElementById(`toc-toggle-sub-${subKey}`);
            if (newCb) newCb.addEventListener('change', function () {
                this.checked ? group.addTo(map) : map.removeLayer(group);
            });
        }
    });
}

// ── FLOW ANALYSIS ─────────────────────────────────────────
document.getElementById('run-analysis-btn').addEventListener('click', () => {
    const key   = document.getElementById('analysis-layer-select').value;
    const entry = uploadedLayers[key];
    if (!entry) return;

    const features = entry.geojson.features;
    const results  = document.getElementById('analysis-results');
    results.style.display = 'block';

    const quantities = features.map(f => f.properties.quantity || 0);
    const total      = quantities.reduce((a, b) => a + b, 0);
    const avg        = total / quantities.length;
    const maxQ       = Math.max(...quantities);

    document.getElementById('stat-total-flows').textContent = features.length.toLocaleString();
    document.getElementById('stat-total-qty').textContent   = formatQty(total);
    document.getElementById('stat-avg-qty').textContent     = formatQty(avg);
    document.getElementById('stat-max-qty').textContent     = formatQty(maxQ);

    // Product mix
    const productCounts = {};
    features.forEach(f => {
        const combo = `${(f.properties.product_type_i||'').trim()}→${(f.properties.product_type_j||'').trim()}`;
        productCounts[combo] = (productCounts[combo] || 0) + 1;
    });

    const mixEl = document.getElementById('product-mix-chart');
    mixEl.innerHTML = '';
    const mixRow = document.createElement('div');
    mixRow.className = 'product-mix-row';
    Object.entries(productCounts).sort((a,b) => b[1]-a[1]).forEach(([combo, count]) => {
        const pill = document.createElement('div');
        pill.className = 'product-pill active';
        pill.innerHTML = `
            <div class="product-pill-dot" style="background:${getFlowComboColor(...combo.split('→'))}"></div>
            ${combo} <b>(${count})</b>
        `;
        mixRow.appendChild(pill);
    });
    mixEl.appendChild(mixRow);

    // Top 5 flows by quantity
    const top5 = [...features]
        .sort((a, b) => (b.properties.quantity||0) - (a.properties.quantity||0))
        .slice(0, 5);

    const topEl  = document.getElementById('top-flows-chart');
    topEl.innerHTML = '';
    const topMax = top5[0]?.properties.quantity || 1;

    top5.forEach(f => {
        const p   = f.properties;
        const qty = p.quantity || 0;
        const row = document.createElement('div');
        row.className = 'bar-row';
        row.innerHTML = `
            <div class="bar-label" title="${p.from_id}→${p.to_id}">${p.from_id}→${p.to_id}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:${(qty/topMax*100).toFixed(1)}%; background:${getFlowComboColor(p.product_type_i, p.product_type_j)}"></div>
            </div>
            <div class="bar-val">${formatQty(qty)}</div>
        `;
        topEl.appendChild(row);
    });

    // Filter pills
    const filterEl = document.getElementById('product-filter-row');
    filterEl.innerHTML = '<span style="font-size:11px;color:var(--text-muted);width:100%;margin-bottom:4px;">Click to filter visible flows:</span>';

    const allCombos = [...new Set(features.map(f =>
        `${(f.properties.product_type_i||'').trim()}→${(f.properties.product_type_j||'').trim()}`
    ))];

    const activeFilters = new Set(allCombos);

    allCombos.forEach(combo => {
        const pill = document.createElement('div');
        pill.className = 'filter-pill active';
        pill.textContent = combo || '(untyped)';
        pill.addEventListener('click', () => {
            if (activeFilters.has(combo)) {
                activeFilters.delete(combo);
                pill.classList.remove('active');
            } else {
                activeFilters.add(combo);
                pill.classList.add('active');
            }
            applyProductFilter(key, activeFilters);
        });
        filterEl.appendChild(pill);
    });
});

function applyProductFilter(layerKey, activeFilters) {
    const entry = uploadedLayers[layerKey];
    if (!entry) return;

    Object.entries(entry.comboGroups).forEach(([combo, group]) => {
        if (activeFilters.has(combo)) {
            group.addTo(map);
        } else {
            map.removeLayer(group);
        }
        // Sync sub-row checkbox
        const subKey = `${layerKey}_${combo}`;
        const cb = document.getElementById(`toc-toggle-sub-${subKey}`);
        if (cb) cb.checked = activeFilters.has(combo);
    });
}

function formatQty(n) {
    if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
    if (n >= 1000)    return (n/1000).toFixed(1) + 'K';
    return n.toFixed(0);
}
