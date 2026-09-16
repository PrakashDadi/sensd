// Enhanced Data Mapping Tool JavaScript - v2.0
console.log('=== SENSD Mapping Tool v2.0 Loaded ===');

// --- Global Initialization ---
const map = L.map('map', {
    zoomControl: false
}).setView([40, -95], 5);

const tileConfig = window.SENSD_MAP_TILE_CONFIG || {};
if (tileConfig.url) {
    L.tileLayer(tileConfig.url, {
        maxZoom: Number(tileConfig.maxZoom) || 19,
        attribution: tileConfig.attribution || ''
    }).addTo(map);
}

L.control.zoom({
    position: 'bottomright'
}).addTo(map);

// Store loaded layers with their styling options
const loadedLayers = {};
const layerStyles = {};
const layerData = {};

let selectedFile = null;
let fileColumns = [];
let currentStyleLayerId = null;

// Predefined color palette for categories
const colorPalette = [
    '#1E88E5', '#E53935', '#43A047', '#FB8C00', '#8E24AA',
    '#00ACC1', '#FDD835', '#3949AB', '#F4511E', '#6D4C41'
];

function getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

// --- Status and Loading Functions ---
function showStatus(message, type) {
    const status = document.getElementById('statusMessage');
    status.textContent = message;
    status.className = `status-message show ${type}`;
    setTimeout(() => {
        status.className = 'status-message';
    }, 3000);
}

function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

// --- Enhanced Marker Creation ---
function sensdMarker(color = "#1E88E5") {
    return L.divIcon({
        className: "",
        iconSize: [12, 12],
        html: `
        <svg width="12" height="12" viewBox="0 0 12 12">
            <circle cx="6" cy="6" r="5" fill="${color}22" />
            <circle cx="6" cy="6" r="3.5"
                fill="${color}"
                stroke="white"
                stroke-width="1.5"
            />
        </svg>
        `
    });
}

// --- Color Scheme Functions ---
function getColorScheme(schemeName) {
    const schemes = {
        blues: ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'],
        reds: ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d'],
        greens: ['#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b', '#74c476', '#41ab5d', '#238b45', '#006d2c', '#00441b'],
        purples: ['#fcfbfd', '#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#807dba', '#6a51a3', '#54278f', '#3f007d'],
        oranges: ['#fff5eb', '#fee6ce', '#fdd0a2', '#fdae6b', '#fd8d3c', '#f16913', '#d94801', '#a63603', '#7f2704'],
        redblue: ['#67001f', '#b2182b', '#d6604d', '#f4a582', '#fddbc7', '#d1e5f0', '#92c5de', '#4393c3', '#2166ac', '#053061'],
        spectral: ['#9e0142', '#d53e4f', '#f46d43', '#fdae61', '#fee08b', '#e6f598', '#abdda4', '#66c2a5', '#3288bd', '#5e4fa2']
    };
    return schemes[schemeName] || schemes.blues;
}

function getColorForValue(value, min, max, colorScheme = 'blues') {
    console.log('getColorForValue called:', { value, min, max, colorScheme });

    // Parse value to number
    const numValue = Number(value);
    const numMin = Number(min);
    const numMax = Number(max);

    // Check if valid number
    if (!isFinite(numValue) || !isFinite(numMin) || !isFinite(numMax)) {
        console.warn('Invalid value for coloring:', value);
        return '#CCCCCC';
    }

    // Handle edge cases
    if (numMin === numMax) return getColorScheme(colorScheme)[4];

    // Normalize value between 0 and 1
    const normalized = (numValue - numMin) / (numMax - numMin);
    const clampedNorm = Math.max(0, Math.min(1, normalized));

    const colors = getColorScheme(colorScheme);
    const index = Math.floor(clampedNorm * (colors.length - 1));

    console.log('Color result:', { normalized, index, color: colors[index] });
    return colors[index];
}

// Bivariate color schemes
function getBivariateColorScheme(schemeName) {
    const schemes = {
        bluepink: [
            ['#DCDDDF', '#B8BFF3', '#83A0FC'],
            ['#F39DA7', '#C07C91', '#8260AD'],
            ['#F36161', '#BE4362', '#73124E']
        ],
        bluered: [
            ['#e8e8e8', '#b8d0e8', '#73a0d8'],
            ['#e8b8b8', '#b8b8c8', '#8898c8'],
            ['#d87373', '#b86888', '#884488']
        ],
        greenblue: [
            ['#e8e8e8', '#c8e8c8', '#98d898'],
            ['#c8d8e8', '#b8c8c8', '#98c8b8'],
            ['#98b8d8', '#8898a8', '#688898']
        ],
        purpleorange: [
            ['#e8e8e8', '#e8d8c8', '#e8c898'],
            ['#d8c8e8', '#c8c8c8', '#c8b898'],
            ['#b898d8', '#a888a8', '#986838']
        ]
    };
    return schemes[schemeName] || schemes.bluepink;
}

function getBivariateColor(valueX, valueY, minX, maxX, minY, maxY, scheme = 'bluepink') {
    console.log('getBivariateColor called:', { valueX, valueY, minX, maxX, minY, maxY });

    const numX = Number(valueX);
    const numY = Number(valueY);
    const nMinX = Number(minX);
    const nMaxX = Number(maxX);
    const nMinY = Number(minY);
    const nMaxY = Number(maxY);

    if (!isFinite(numX) || !isFinite(numY)) {
        console.warn('Invalid bivariate values:', valueX, valueY);
        return '#CCCCCC';
    }

    // Normalize
    const normX = nMinX === nMaxX ? 0.5 : (numX - nMinX) / (nMaxX - nMinX);
    const normY = nMinY === nMaxY ? 0.5 : (numY - nMinY) / (nMaxY - nMinY);

    const clampX = Math.max(0, Math.min(1, normX));
    const clampY = Math.max(0, Math.min(1, normY));

    // Classify into 3x3 grid
    const classX = Math.min(2, Math.floor(clampX * 3));
    const classY = Math.min(2, Math.floor(clampY * 3));

    const matrix = getBivariateColorScheme(scheme);
    const color = matrix[classY][classX];

    console.log('Bivariate result:', { normX, normY, classX, classY, color });
    return color;
}

function getBivariateClassColor(bivariateClass, scheme = 'bluepink') {
    const colorMap = {
        1: [0, 0], 2: [1, 0], 3: [2, 0],
        4: [0, 1], 5: [1, 1], 6: [2, 1],
        7: [0, 2], 8: [1, 2], 9: [2, 2],
        11: [0, 0], 12: [1, 0], 13: [2, 0],
        21: [0, 1], 22: [1, 1], 23: [2, 1],
        31: [0, 2], 32: [1, 2], 33: [2, 2]
    };

    const textMap = {
        'Low-Low': [0, 0], 'Low-Med': [1, 0], 'Low-High': [2, 0],
        'Med-Low': [0, 1], 'Med-Med': [1, 1], 'Med-High': [2, 1],
        'High-Low': [0, 2], 'High-Med': [1, 2], 'High-High': [2, 2]
    };

    let coords = colorMap[bivariateClass] || textMap[bivariateClass] || textMap[String(bivariateClass)];

    if (!coords) return '#CCCCCC';

    const matrix = getBivariateColorScheme(scheme);
    return matrix[coords[1]][coords[0]];
}

// Classification methods
function classifyData(values, method, numClasses) {
    const validValues = values.filter(v => isFinite(Number(v))).map(v => Number(v)).sort((a, b) => a - b);

    if (validValues.length === 0) return [];

    const breaks = [];

    if (method === 'quantile') {
        for (let i = 1; i < numClasses; i++) {
            const index = Math.floor((validValues.length * i) / numClasses);
            breaks.push(validValues[index]);
        }
    } else if (method === 'equal') {
        const min = validValues[0];
        const max = validValues[validValues.length - 1];
        const interval = (max - min) / numClasses;
        for (let i = 1; i < numClasses; i++) {
            breaks.push(min + interval * i);
        }
    } else if (method === 'natural') {
        for (let i = 1; i < numClasses; i++) {
            const index = Math.floor((validValues.length * i) / numClasses);
            breaks.push(validValues[index]);
        }
    }

    return [validValues[0], ...breaks, validValues[validValues.length - 1]];
}

// --- Layer Management ---
function loadLayers() {
    showLoading(true);
    fetch('/mapsapp/api/layers/')
        .then(response => response.json())
        .then(data => {
            showLoading(false);
            const layersList = document.getElementById('layersList');
            const bufferSelect = document.getElementById('bufferLayerSelect');

            layersList.innerHTML = '';
            bufferSelect.innerHTML = '<option value="">-- Select Layer --</option>';

            if (data.layers.length === 0) {
                layersList.innerHTML = '<li style="padding: 1rem; text-align: center; color: #666;">No layers uploaded yet.</li>';
                return;
            }

            data.layers.forEach(layer => {
                const li = document.createElement('li');
                const isLoaded = loadedLayers[layer.id];

                li.className = 'layer-item';
                li.innerHTML = `
                    <div class="layer-name">${layer.name}</div>
                    <div class="layer-info">${layer.feature_count} features • ${layer.type || 'Unknown'}</div>
                    <div class="layer-actions">
                        <button class="layer-action-btn ${isLoaded ? 'btn-warning' : 'btn-success'}" onclick="toggleLayer(${layer.id})">
                            ${isLoaded ? '<i class="bi bi-eye-slash"></i> Hide' : '<i class="bi bi-eye"></i> Show'}
                        </button>
                        <button class="layer-action-btn btn-info" onclick="openStyleModal(${layer.id})" ${!isLoaded ? 'disabled' : ''}>
                            <i class="bi bi-palette"></i> Style
                        </button>
                        <button class="layer-action-btn delete-btn btn-danger" onclick="deleteLayer(${layer.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                `;
                layersList.appendChild(li);

                if (isLoaded) {
                    const option = document.createElement('option');
                    option.value = layer.id;
                    option.textContent = layer.name;
                    bufferSelect.appendChild(option);
                }
            });
        })
        .catch(error => {
            showLoading(false);
            console.error('Error loading layers:', error);
            showStatus('Error fetching layer list.', 'error');
        });
}

function toggleLayer(layerId) {
    console.log('toggleLayer called:', layerId);

    if (loadedLayers[layerId]) {
        map.removeLayer(loadedLayers[layerId]);
        delete loadedLayers[layerId];
        delete layerData[layerId];
        loadLayers();
    } else {
        showLoading(true);
        fetch(`/mapsapp/api/layers/${layerId}/`)
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch GeoJSON.');
                return response.json();
            })
            .then(geojson => {
                console.log('GeoJSON loaded:', geojson);
                showLoading(false);
                layerData[layerId] = geojson;

                // Initialize default style
                if (!layerStyles[layerId]) {
                    const firstFeature = geojson.features && geojson.features[0];
                    const geometryType = firstFeature && firstFeature.geometry ? firstFeature.geometry.type : 'Point';

                    layerStyles[layerId] = {
                        type: geometryType,
                        pointColor: '#1E88E5',
                        polygonFillColor: '#b8bff3',
                        polygonBorderColor: '#ffffff',
                        polygonFillOpacity: 1,
                        polygonBorderWidth: 1,
                        categoryColumn: null,
                        categoryColors: {},
                        symbologyType: 'single',
                        graduatedField: null,
                        colorScheme: 'blues',
                        classificationMethod: 'quantile',
                        numClasses: 5,
                        bivariateFieldX: null,
                        bivariateFieldY: null,
                        bivariateScheme: 'bluepink'
                    };
                }

                renderLayer(layerId);
                loadLayers();
            })
            .catch(error => {
                showLoading(false);
                console.error('Error loading layer GeoJSON:', error);
                showStatus('Error loading layer: ' + error.message, 'error');
            });
    }
}

function renderLayer(layerId) {
    console.log('=== RENDER LAYER START ===', layerId);
    const geojson = layerData[layerId];
    const style = layerStyles[layerId];

    console.log('Style configuration:', style);

    // Remove existing layer
    if (loadedLayers[layerId]) {
        map.removeLayer(loadedLayers[layerId]);
    }

    // Remove existing legend
    if (loadedLayers[layerId + '_legend']) {
        map.removeControl(loadedLayers[layerId + '_legend']);
    }

    // Pre-calculate min/max for graduated colors
    let graduatedMin, graduatedMax;
    if (style.symbologyType === 'graduated' && style.graduatedField) {
        const values = geojson.features
            .map(f => f.properties ? Number(f.properties[style.graduatedField]) : NaN)
            .filter(v => isFinite(v));
        graduatedMin = Math.min(...values);
        graduatedMax = Math.max(...values);
        console.log('Graduated min/max:', { field: style.graduatedField, min: graduatedMin, max: graduatedMax, count: values.length });
    }

    // Pre-calculate min/max for bivariate
    let bivariateMinX, bivariateMaxX, bivariateMinY, bivariateMaxY;
    if (style.symbologyType === 'bivariate' && style.bivariateFieldX && style.bivariateFieldY) {
        const valuesX = geojson.features
            .map(f => f.properties ? Number(f.properties[style.bivariateFieldX]) : NaN)
            .filter(v => isFinite(v));
        const valuesY = geojson.features
            .map(f => f.properties ? Number(f.properties[style.bivariateFieldY]) : NaN)
            .filter(v => isFinite(v));

        bivariateMinX = Math.min(...valuesX);
        bivariateMaxX = Math.max(...valuesX);
        bivariateMinY = Math.min(...valuesY);
        bivariateMaxY = Math.max(...valuesY);

        console.log('Bivariate min/max:', {
            fieldX: style.bivariateFieldX, minX: bivariateMinX, maxX: bivariateMaxX,
            fieldY: style.bivariateFieldY, minY: bivariateMinY, maxY: bivariateMaxY
        });
    }

    const layer = L.geoJSON(geojson, {
        pointToLayer: function (feature, latlng) {
            let color = style.pointColor;

            if (style.categoryColumn && feature.properties && feature.properties[style.categoryColumn]) {
                const category = feature.properties[style.categoryColumn];
                color = style.categoryColors[category] || style.pointColor;
            }

            return L.marker(latlng, {
                icon: sensdMarker(color)
            });
        },
        style: function (feature) {
            let fillColor = style.polygonFillColor;

            try {
                if (style.symbologyType === 'graduated' && style.graduatedField && feature.properties) {
                    const value = feature.properties[style.graduatedField];
                    fillColor = getColorForValue(value, graduatedMin, graduatedMax, style.colorScheme);
                } else if (style.symbologyType === 'bivariate' && feature.properties) {
                    // Check for BivariateClass field first
                    const bivClassFields = ['BivariateClass', 'bivariate_class', 'bivariateClass'];
                    const bivClassField = bivClassFields.find(f => feature.properties[f] !== undefined);

                    if (bivClassField) {
                        fillColor = getBivariateClassColor(feature.properties[bivClassField], style.bivariateScheme);
                    } else if (style.bivariateFieldX && style.bivariateFieldY) {
                        const valueX = feature.properties[style.bivariateFieldX];
                        const valueY = feature.properties[style.bivariateFieldY];
                        fillColor = getBivariateColor(valueX, valueY, bivariateMinX, bivariateMaxX, bivariateMinY, bivariateMaxY, style.bivariateScheme);
                    }
                }
            } catch (error) {
                console.error('Style error:', error);
                fillColor = '#CCCCCC';
            }

            return {
                fillColor: fillColor,
                fillOpacity: style.polygonFillOpacity,
                color: style.polygonBorderColor,
                weight: style.polygonBorderWidth,
                opacity: 1
            };
        },
        onEachFeature: function (feature, layer) {
            if (!feature || !feature.properties) return;

            const props = feature.properties;
            const entries = Object.entries(props).slice(0, 10);
            const popupContent = entries
                .map(([key, value]) => `<strong>${key}:</strong> ${value}`)
                .join('<br>');

            if (popupContent) {
                layer.bindPopup(popupContent);
                layer.on('click', () => layer.openPopup());
            }
        }
    }).addTo(map);

    loadedLayers[layerId] = layer;

    // Add legend
    if (style.symbologyType === 'graduated' && style.graduatedField) {
        addGraduatedLegend(layerId, geojson, style, graduatedMin, graduatedMax);
    } else if (style.symbologyType === 'bivariate') {
        addBivariateLegend(layerId, style);
    }

    try {
        map.fitBounds(layer.getBounds(), { padding: [50, 50] });
    } catch (e) {
        console.warn('Could not fit bounds:', e);
    }

    console.log('=== RENDER LAYER END ===');
}

function addGraduatedLegend(layerId, geojson, style, min, max) {
    const legend = L.control({ position: 'bottomleft' });

    legend.onAdd = function () {
        const div = L.DomUtil.create('div', 'legend');
        const breaks = classifyData(
            geojson.features.map(f => f.properties ? f.properties[style.graduatedField] : null),
            style.classificationMethod,
            parseInt(style.numClasses)
        );

        div.innerHTML = `<div class="legend-title">${style.graduatedField}</div>`;

        for (let i = 0; i < breaks.length - 1; i++) {
            const from = Number(breaks[i]).toFixed(3);
            const to = Number(breaks[i + 1]).toFixed(3);
            const color = getColorForValue(breaks[i], min, max, style.colorScheme);

            div.innerHTML += `
                <div class="legend-item">
                    <div class="legend-color" style="background:${color}"></div>
                    <span>${from} - ${to}</span>
                </div>
            `;
        }

        return div;
    };

    legend.addTo(map);
    loadedLayers[layerId + '_legend'] = legend;
}

function addBivariateLegend(layerId, style) {
    const legend = L.control({ position: 'bottomleft' });

    legend.onAdd = function () {
        const div = L.DomUtil.create('div', 'legend');
        const fieldX = style.bivariateFieldX || 'Variable X';
        const fieldY = style.bivariateFieldY || 'Variable Y';

        div.innerHTML = `
            <div class="legend-title">Bivariate Map</div>
            <div class="bivariate-legend" id="bivariate-legend-${layerId}"></div>
            <div style="font-size: 10px; margin-top: 5px;">
                <div>${fieldX} →</div>
                <div>${fieldY} ↑</div>
            </div>
        `;

        return div;
    };

    legend.addTo(map);

    setTimeout(() => {
        const grid = document.getElementById(`bivariate-legend-${layerId}`);
        if (grid) {
            const matrix = getBivariateColorScheme(style.bivariateScheme);
            for (let y = 2; y >= 0; y--) {
                for (let x = 0; x < 3; x++) {
                    const cell = document.createElement('div');
                    cell.className = 'bivariate-cell';
                    cell.style.backgroundColor = matrix[y][x];
                    grid.appendChild(cell);
                }
            }
        }
    }, 100);

    loadedLayers[layerId + '_legend'] = legend;
}

function deleteLayer(layerId) {
    if (!confirm('Delete this layer? This action cannot be undone.')) return;

    showLoading(true);
    fetch(`/mapsapp/api/layers/${layerId}/delete/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
        .then(response => {
            if (!response.ok) throw new Error('Server error on delete.');
            return response.json();
        })
        .then(data => {
            showLoading(false);
            if (data.success) {
                if (loadedLayers[layerId]) {
                    map.removeLayer(loadedLayers[layerId]);
                    delete loadedLayers[layerId];
                    delete layerData[layerId];
                    delete layerStyles[layerId];
                }
                showStatus('✓ Layer deleted', 'success');
                loadLayers();
            } else {
                showStatus('Error deleting layer', 'error');
            }
        })
        .catch(error => {
            showLoading(false);
            console.error('Delete error:', error);
            showStatus('Error: ' + error.message, 'error');
        });
}

// Style Modal Functions
function openStyleModal(layerId) {
    console.log('Opening style modal for layer:', layerId);
    currentStyleLayerId = layerId;
    const style = layerStyles[layerId];
    const geojson = layerData[layerId];

    const modal = document.getElementById('styleModal');
    const pointOptions = document.getElementById('pointStyleOptions');
    const polygonOptions = document.getElementById('polygonStyleOptions');

    const isPoint = style.type.includes('Point');

    pointOptions.style.display = isPoint ? 'block' : 'none';
    polygonOptions.style.display = !isPoint ? 'block' : 'none';

    if (!isPoint && geojson.features.length > 0) {
        const properties = Object.keys(geojson.features[0].properties || {});
        const numericFields = properties.filter(prop => {
            const value = geojson.features[0].properties[prop];
            return isFinite(Number(value));
        });

        // Populate graduated field
        const graduatedSelect = document.getElementById('graduatedField');
        graduatedSelect.innerHTML = '<option value="">-- Select Field --</option>';
        numericFields.forEach(field => {
            const option = document.createElement('option');
            option.value = field;
            option.textContent = field;
            if (style.graduatedField === field) option.selected = true;
            graduatedSelect.appendChild(option);
        });

        // Populate bivariate fields
        const bivX = document.getElementById('bivariateFieldX');
        const bivY = document.getElementById('bivariateFieldY');
        bivX.innerHTML = '<option value="">-- Select Field --</option>';
        bivY.innerHTML = '<option value="">-- Select Field --</option>';

        numericFields.forEach(field => {
            const optX = document.createElement('option');
            optX.value = field;
            optX.textContent = field;
            if (style.bivariateFieldX === field) optX.selected = true;
            bivX.appendChild(optX);

            const optY = document.createElement('option');
            optY.value = field;
            optY.textContent = field;
            if (style.bivariateFieldY === field) optY.selected = true;
            bivY.appendChild(optY);
        });

        // Set values
        document.getElementById('symbologyType').value = style.symbologyType || 'single';
        document.getElementById('polygonFillColor').value = style.polygonFillColor;
        document.getElementById('polygonBorderColor').value = style.polygonBorderColor;
        document.getElementById('polygonFillOpacity').value = Math.round(style.polygonFillOpacity * 100);
        document.getElementById('fillOpacityValue').textContent = Math.round(style.polygonFillOpacity * 100) + '%';
        document.getElementById('polygonBorderWidth').value = style.polygonBorderWidth;
        document.getElementById('borderWidthValue').textContent = style.polygonBorderWidth + 'px';

        document.getElementById('colorScheme').value = style.colorScheme || 'blues';
        document.getElementById('classificationMethod').value = style.classificationMethod || 'quantile';
        document.getElementById('numClasses').value = style.numClasses || 5;
        document.getElementById('bivariateScheme').value = style.bivariateScheme || 'bluepink';

        updateSymbologyOptions();

        document.getElementById('symbologyType').onchange = updateSymbologyOptions;
        document.getElementById('polygonFillOpacity').oninput = function () {
            document.getElementById('fillOpacityValue').textContent = this.value + '%';
        };
        document.getElementById('polygonBorderWidth').oninput = function () {
            document.getElementById('borderWidthValue').textContent = this.value + 'px';
        };
    }

    modal.style.display = 'flex';
}

function updateSymbologyOptions() {
    const symbologyType = document.getElementById('symbologyType').value;

    document.getElementById('singleColorOptions').style.display = symbologyType === 'single' ? 'block' : 'none';
    document.getElementById('graduatedColorOptions').style.display = symbologyType === 'graduated' ? 'block' : 'none';
    document.getElementById('bivariateColorOptions').style.display = symbologyType === 'bivariate' ? 'block' : 'none';
}

function applyLayerStyle() {
    console.log('=== APPLY STYLE START ===');
    const layerId = currentStyleLayerId;
    const style = layerStyles[layerId];

    // Get symbology settings
    style.symbologyType = document.getElementById('symbologyType').value;
    style.polygonFillColor = document.getElementById('polygonFillColor').value;
    style.polygonBorderColor = document.getElementById('polygonBorderColor').value;
    style.polygonFillOpacity = parseFloat(document.getElementById('polygonFillOpacity').value) / 100;
    style.polygonBorderWidth = parseInt(document.getElementById('polygonBorderWidth').value);

    if (style.symbologyType === 'graduated') {
        style.graduatedField = document.getElementById('graduatedField').value;
        style.colorScheme = document.getElementById('colorScheme').value;
        style.classificationMethod = document.getElementById('classificationMethod').value;
        style.numClasses = parseInt(document.getElementById('numClasses').value);
        console.log('Graduated style:', style.graduatedField, style.colorScheme);
    } else if (style.symbologyType === 'bivariate') {
        style.bivariateFieldX = document.getElementById('bivariateFieldX').value;
        style.bivariateFieldY = document.getElementById('bivariateFieldY').value;
        style.bivariateScheme = document.getElementById('bivariateScheme').value;
        console.log('Bivariate style:', style.bivariateFieldX, style.bivariateFieldY, style.bivariateScheme);
    }

    console.log('Final style:', style);

    renderLayer(layerId);
    closeStyleModal();
    showStatus('✓ Style applied successfully', 'success');
    console.log('=== APPLY STYLE END ===');
}

function closeStyleModal() {
    const modal = document.getElementById('styleModal');
    if (modal) modal.style.display = 'none';
    currentStyleLayerId = null;
}

// File Upload Functions
function readFileColumns(file) {
    Papa.parse(file, {
        header: true,
        preview: 1,
        complete: function (results) {
            if (results.meta.fields) {
                fileColumns = results.meta.fields;
            } else {
                showStatus('Error reading CSV columns.', 'error');
                return;
            }

            const latSelect = document.getElementById('latColumn');
            const lngSelect = document.getElementById('lngColumn');
            const categorySelect = document.getElementById('categoryColumn');

            latSelect.innerHTML = '';
            lngSelect.innerHTML = '';
            categorySelect.innerHTML = '<option value="">-- None --</option>';

            fileColumns.forEach(col => {
                latSelect.add(new Option(col, col));
                lngSelect.add(new Option(col, col));
                categorySelect.add(new Option(col, col));
            });

            const latCandidates = ['latitude', 'lat', 'y'];
            const lngCandidates = ['longitude', 'lng', 'lon', 'x'];

            let latIndex = -1;
            let lngIndex = -1;

            fileColumns.forEach((col, idx) => {
                const colLower = col.toLowerCase();
                if (latIndex === -1 && latCandidates.some(c => colLower.includes(c))) {
                    latIndex = idx;
                }
                if (lngIndex === -1 && lngCandidates.some(c => colLower.includes(c))) {
                    lngIndex = idx;
                }
            });

            if (latIndex !== -1) latSelect.selectedIndex = latIndex;
            if (lngIndex !== -1) lngSelect.selectedIndex = lngIndex;

            document.getElementById('columnSelector').style.display = 'block';
        },
        error: function (err) {
            showStatus('Error parsing CSV file.', 'error');
            console.error(err);
        }
    });
}

function processFile() {
    uploadFile();
}

function uploadFile() {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);

    let latCol = document.getElementById('latColumn')?.value;
    let lngCol = document.getElementById('lngColumn')?.value;
    let catCol = document.getElementById('categoryColumn')?.value;

    formData.append('lat_column', latCol || "Latitude");
    formData.append('lng_column', lngCol || "Longitude");
    if (catCol) formData.append('category_column', catCol);

    showLoading(true);

    fetch('/mapsapp/api/upload/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            showLoading(false);
            if (data.success) {
                showStatus(`✓ Uploaded ${data.features_created} features`, 'success');
                toggleLayer(data.layer_id);
                document.getElementById('columnSelector').style.display = 'none';
                document.getElementById('fileInput').value = '';
            } else {
                showStatus('Upload failed: ' + data.error, 'error');
            }
        })
        .catch(error => {
            showLoading(false);
            console.error('Upload error:', error);
            showStatus('Upload error: ' + error.message, 'error');
        });
}

document.getElementById('fileInput').addEventListener('change', function (e) {
    selectedFile = e.target.files[0];

    if (selectedFile) {
        const extension = selectedFile.name.split('.').pop().toLowerCase();

        document.getElementById('columnSelector').style.display = 'none';

        if (extension === 'csv') {
            readFileColumns(selectedFile);
        }
        else if (['xlsx', 'xls'].includes(extension)) {
            uploadFile();
        }
        else if (['geojson', 'json'].includes(extension)) {
            uploadFile();
        }
        else {
            showStatus('Unsupported file format', 'error');
        }
    }
});

// Buffer Analysis
function createBuffer() {
    const layerId = parseInt(document.getElementById('bufferLayerSelect').value);
    const distance = parseFloat(document.getElementById('bufferDistance').value);

    if (!layerId || !distance) {
        showStatus('Please select a layer and enter buffer distance', 'error');
        return;
    }

    const geojson = layerData[layerId];
    if (!geojson) {
        showStatus('Layer data not found', 'error');
        return;
    }

    showLoading(true);

    try {
        const bufferedFeatures = geojson.features.map(feature => {
            return turf.buffer(feature, distance, { units: 'meters' });
        });

        const bufferedCollection = turf.featureCollection(bufferedFeatures);

        const bufferLayer = L.geoJSON(bufferedCollection, {
            style: {
                color: '#FF6B6B',
                weight: 2,
                opacity: 0.8,
                fillColor: '#FF6B6B',
                fillOpacity: 0.2,
                dashArray: '5, 5'
            },
            onEachFeature: function (feature, layer) {
                layer.bindPopup(`<strong>Buffer Zone</strong><br>Distance: ${distance}m`);
            }
        }).addTo(map);

        const bufferLayerId = 'buffer_' + layerId + '_' + Date.now();
        loadedLayers[bufferLayerId] = bufferLayer;

        showLoading(false);
        showStatus('✓ Buffer created successfully', 'success');

    } catch (error) {
        showLoading(false);
        console.error('Buffer error:', error);
        showStatus('Error creating buffer: ' + error.message, 'error');
    }
}

// Search Functionality
document.getElementById('searchInput').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        const query = this.value;
        if (!query) return;

        showLoading(true);
        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`)
            .then(response => response.json())
            .then(data => {
                showLoading(false);
                map.eachLayer(function (layer) {
                    if (layer.options && layer.options.isSearchMarker) {
                        map.removeLayer(layer);
                    }
                });

                if (data.length > 0) {
                    const result = data[0];
                    const lat = parseFloat(result.lat);
                    const lon = parseFloat(result.lon);

                    map.setView([lat, lon], 13);

                    L.marker([lat, lon], { isSearchMarker: true })
                        .addTo(map)
                        .bindPopup(`<b>Search Result:</b><br>${result.display_name}`)
                        .openPopup();

                    showStatus('✓ Location found', 'success');
                } else {
                    showStatus('Location not found', 'error');
                }
            })
            .catch(error => {
                showLoading(false);
                console.error('Search error:', error);
                showStatus('Search error', 'error');
            });
    }
});

// Initial Load
document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM Content Loaded - Initializing');
    loadLayers();
});

// Expose functions globally
window.toggleLayer = toggleLayer;
window.deleteLayer = deleteLayer;
window.openStyleModal = openStyleModal;
window.closeStyleModal = closeStyleModal;
window.applyLayerStyle = applyLayerStyle;
window.processFile = processFile;
window.createBuffer = createBuffer;

console.log('=== All functions loaded and exposed ===');
