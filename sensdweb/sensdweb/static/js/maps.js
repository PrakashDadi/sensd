const map = L.map('map').setView([40, -95], 5);

// === Custom pane for state boundaries (always on top) ===
map.createPane('statePane');
map.getPane('statePane').style.zIndex = 650;
map.getPane('statePane').style.pointerEvents = 'none';

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap Contributors'
}).addTo(map);


const layers = {
    walmart: {
        url: '/mapsapp/api/walmart/',
        color: 'green',
        label: 'Walmart',
        group: L.layerGroup()
    },
    schnucks: {
        url: '/mapsapp/api/schnucks/',
        color: 'red',
        label: 'Schnucks',
        group: L.layerGroup()
    },
    save_a_lot: {
        url: '/mapsapp/api/save_a_lot/',
        color: 'blue',
        label: 'Save A Lot',
        group: L.layerGroup()
    },
    whole_foods: {
        url: '/mapsapp/api/whole_foods/',
        color: 'gray',
        label: 'Whole Foods',
        group: L.layerGroup()
    },
    fsis_coordinates: {
        url: '/mapsapp/api/fsis_coordinates/',
        color: 'orange',
        label: 'FSIS Establishments',
        group: L.layerGroup()
    }
};

// Normalize city names for comparison
function normalizeCityName(name) {
    return name
        .toUpperCase()
        .replace(/\./g, '')
        .replace(/\bST\b/, 'SAINT')
        .trim();
}

// State abbreviation map (used in search)
const stateAbbrMap = {
    'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR', 'CALIFORNIA': 'CA',
    'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE', 'FLORIDA': 'FL', 'GEORGIA': 'GA',
    'HAWAII': 'HI', 'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
    'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
    'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS',
    'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV', 'NEW HAMPSHIRE': 'NH',
    'NEW JERSEY': 'NJ', 'NEW MEXICO': 'NM', 'NEW YORK': 'NY', 'NORTH CAROLINA': 'NC',
    'NORTH DAKOTA': 'ND', 'OHIO': 'OH', 'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA',
    'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC', 'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN',
    'TEXAS': 'TX', 'UTAH': 'UT', 'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA',
    'WEST VIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY'
};

let allMarkers = [];

const bivariate_colors = {
    // --- Numeric codes ---
    "11": "#DCDDDF", "12": "#B8BFF3", "13": "#83A0FC",
    "21": "#F39DA7", "22": "#C07C91", "23": "#8260AD",
    "31": "#F36161", "32": "#BE4362", "33": "#73124E",

    // --- Text labels ---
    "Low-Low": "#DCDDDF", "Low-Med": "#B8BFF3", "Low-High": "#83A0FC",
    "Med-Low": "#F39DA7", "Med-Med": "#C07C91", "Med-High": "#8260AD",
    "High-Low": "#F36161", "High-Med": "#BE4362", "High-High": "#73124E"
};

function getBivariateColor(cls) {
    if (!cls) return "#cccccc"; // null → gray
    return bivariate_colors[cls] || "#cccccc";
}

function bivariateStyle(feature) {
    return {
        fillColor: getBivariateColor(feature.properties.BivariateClass || feature.properties.bivariate_class),
        weight: 1,
        opacity: 1,
        color: 'white',
        dashArray: '1',
        fillOpacity: 1.0
    };
}

const countyLayer = L.geoJSON(null, {
    style: bivariateStyle,
    onEachFeature: (feature, layer) => {
        if (feature.properties) {
            const props = feature.properties;
            layer.bindPopup(`
                <b>County:</b> ${props.county_name || ""}<br>
                <b>State:</b> ${props.state_name || ""}<br>
                <b>Food Insecurity Rate:</b> ${props.Overall_Food_Insecurity ?? props.child_food_insecurity ?? "N/A"}<br>
                <b>Social Vulnerability:</b> ${props.RPL_Themes ?? props.social_vulnerability ?? "N/A"}<br>
                <b>Bivariate Class:</b> ${props.BivariateClass ?? props.bivariate_class ?? "N/A"}
            `);
        }
    }
});

// Fetch County Bivariate data
fetch('/mapsapp/api/county_bivariate/')
    .then(res => res.json())
    .then(data => {
        console.log("County features loaded:", data.features?.length || 0);
        countyLayer.addData(data);
        // default OFF → toggle in layer control
    })
    .catch(err => console.error('Failed to load county_bivariate:', err));


function getCustomIcon(color) {
    return new L.Icon({
        iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });
}

function getPopupContent(props) {
    return `
        <b>Company:</b> ${props.company || 'N/A'}<br>
        <b>Address:</b> ${props.street || 'N/A'}, ${props.city || 'N/A'}, ${props.state || 'N/A'} ${props.zip || 'N/A'}<br>
        <b>Phone:</b> ${props.phone || 'N/A'}
    `;
}

function getFsisPopupContent(props) {
    return `
        <b>Company:</b> ${props.company || 'N/A'}<br>
        <b>Establishment Number:</b> ${props.est_number || 'N/A'}<br>
        <b>City:</b> ${props.city || 'N/A'}<br>
        <b>State:</b> ${props.state || 'N/A'}<br>
        <b>Zip:</b> ${props.zip || 'N/A'}<br>
        <b>Activities:</b> ${props.activities || 'N/A'}
    `;
}



Object.entries(layers).forEach(([key, layerInfo]) => {
    fetch(layerInfo.url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Fetch failed: ${layerInfo.url} (${response.status})`);
            }
            return response.json();
        })
        .then(data => {
            const geoLayer = L.geoJSON(data, {
                pointToLayer: (feature, latlng) => {
                    const isFSIS = layerInfo.label === 'FSIS Establishments';
                    return L.circleMarker(latlng, {
                        radius: 3,
                        fillColor: layerInfo.color,
                        color: isFSIS ? "#000" : "#fff",
                        weight: 1,
                        opacity: 1,
                        fillOpacity: isFSIS ? 0.8 : 0.9
                    });
                },
                onEachFeature: (feature, layer) => {
                    if (layerInfo.label === 'FSIS Establishments') {
                        layer.bindPopup(getFsisPopupContent(feature.properties || {}));
                    } else {
                        layer.bindPopup(getPopupContent(feature.properties || {}));
                    }
                    layer._storeKey = key;
                    allMarkers.push(layer);
                }
            });
            layerInfo.group.addLayer(geoLayer);
        })
        .catch(err => {
            console.error(`Error loading layer "${layerInfo.label}":`, err);
        });
});



// --- US State Boundary Layer (outline only, always on top) ---
const stateBoundaryStyle = {
    color: "#222",      // dark gray for contrast
    weight: 1.5,        // thin but visible
    opacity: 1.2,
    fillOpacity: 0,
    pane: 'statePane'
};

const usStateLayer = L.geoJSON(null, {
    style: stateBoundaryStyle
});

// Load and keep state boundaries visible
fetch('/mapsapp/api/us_states/')
    .then(res => res.json())
    .then(data => {
        usStateLayer.addData(data);
        usStateLayer.addTo(map);
        console.log("US State boundaries loaded:", data.features?.length || 0);
    })
    .catch(err => console.error("Failed to load US State boundaries:", err));



// === Flow Color Scheme ===

// Lines: colored by From→To product type combination
const flowComboColors = {
    'Raw→Raw':               '#c0392b',  // deep red
    'Raw→Semicooked':        '#e67e22',  // orange  
    'Semicooked→Semicooked': '#f1c40f',  // yellow
    'Cooked→Cooked':         '#27ae60',  // green
};

function getFlowComboColor(typeI, typeJ) {
    const key = `${(typeI || '').trim()}→${(typeJ || '').trim()}`;
    return flowComboColors[key] || '#7f8c8d';
}

// Min/Max quantity — computed dynamically from the data
let flowMinQ = Infinity, flowMaxQ = -Infinity;

function getFlowLineWeight(quantity) {
    const minW = 1, maxW = 8;
    if (flowMaxQ === flowMinQ) return (minW + maxW) / 2; // fallback if all values equal
    return minW + ((quantity - flowMinQ) / (flowMaxQ - flowMinQ)) * (maxW - minW);
}

// === Flow Lines Layer (with arrowheads showing direction) ===
const flowLinesGroup = L.layerGroup();

fetch('/mapsapp/api/flow_line_quantity/')
    .then(res => res.json())
    .then(data => {
        // Compute min/max quantity from the actual data
        data.features.forEach(f => {
            const q = f.properties.quantity || 0;
            if (q < flowMinQ) flowMinQ = q;
            if (q > flowMaxQ) flowMaxQ = q;
        });

        L.geoJSON(data, {
            style: feature => {
                const qty = feature.properties.quantity || 0;
                return {
                    color: getFlowComboColor(
                        feature.properties.product_type_i,
                        feature.properties.product_type_j
                    ),
                    weight: getFlowLineWeight(qty),
                    opacity: 0.75
                };
            },
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                const qty = p.quantity || 0;
                layer.bindPopup(`
                    <b>Flow:</b> ${p.from_id} → ${p.to_id}<br>
                    <b>From:</b> ${p.from_node} (${p.from_city_area}, ${p.from_state})<br>
                    <b>To:</b> ${p.to_node} (${p.to_city_area}, ${p.to_state})<br>
                    <b>Product (From):</b> ${p.product_type_i}<br>
                    <b>Product (To):</b> ${p.product_type_j}<br>
                    <b>Quantity:</b> ${Number(qty).toLocaleString(undefined, {maximumFractionDigits: 1})}
                `);
                layer.on('mouseover', function () {
                    this.setStyle({ opacity: 1, weight: this.options.weight + 2 });
                });
                layer.on('mouseout', function () {
                    this.setStyle({ opacity: 0.75, weight: getFlowLineWeight(qty) });
                });

                // Draw arrowhead at the midpoint pointing toward To node
                const coords = feature.geometry.coordinates;
                const mid = Math.floor(coords.length / 2);
                const p1 = coords[mid - 1];  // [lng, lat]
                const p2 = coords[mid];

                const angle = Math.atan2(p2[1] - p1[1], p2[0] - p1[0]) * 180 / Math.PI;
                const arrowIcon = L.divIcon({
                    className: '',
                    html: `<div style="
                        width: 0; height: 0;
                        border-left: 6px solid transparent;
                        border-right: 6px solid transparent;
                        border-bottom: 12px solid ${getFlowComboColor(p.product_type_i, p.product_type_j)};
                        transform: rotate(${90 - angle}deg);
                        opacity: 0.9;
                    "></div>`,
                    iconSize: [12, 12],
                    iconAnchor: [6, 6]
                });
                L.marker([p2[1], p2[0]], { icon: arrowIcon, interactive: false })
                    .addTo(flowLinesGroup);
            }
        }).addTo(flowLinesGroup);
    })
    .catch(err => console.error('Failed to load Flow Line Quantity:', err));

// === Flow Points Layer ===
// Single color (#3a86ff), both From and To nodes, deduped by node ID
const flowPointsGroup = L.layerGroup();

fetch('/mapsapp/api/flow_with_quantity/')
    .then(res => res.json())
    .then(data => {
        const seenNodes = {};

        data.features.forEach(feature => {
            const p = feature.properties;

            // --- From node ---
            if (!seenNodes[p.from_id]) {
                seenNodes[p.from_id] = true;
                const fromMarker = L.circleMarker(
                    [p.from_latitude, p.from_longitude],
                    {
                        radius: 6,
                        fillColor: '#3a86ff',
                        color: '#fff',
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.9
                    }
                );
                fromMarker.bindPopup(`
                    <b>Node:</b> ${p.from_node} (${p.from_id})<br>
                    <b>Role:</b> From / Origin<br>
                    <b>City:</b> ${p.from_city_area}, ${p.from_state}<br>
                    <b>Product:</b> ${p.product_type_i}
                `);
                flowPointsGroup.addLayer(fromMarker);
            }

            // --- To node ---
            if (!seenNodes[p.to_id]) {
                seenNodes[p.to_id] = true;
                const toMarker = L.circleMarker(
                    [p.to_latitude, p.to_longitude],
                    {
                        radius: 6,
                        fillColor: '#3a86ff',
                        color: '#fff',
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.9
                    }
                );
                toMarker.bindPopup(`
                    <b>Node:</b> ${p.to_node} (${p.to_id})<br>
                    <b>Role:</b> To / Destination<br>
                    <b>City:</b> ${p.to_city_area}, ${p.to_state}<br>
                    <b>Product:</b> ${p.product_type_j}
                `);
                flowPointsGroup.addLayer(toMarker);
            }
        });
    })
    .catch(err => console.error('Failed to load Flow With Quantity:', err));


const overlays = {
    Walmart: layers.walmart.group,
    Schnucks: layers.schnucks.group,
    "Save A Lot": layers.save_a_lot.group,
    "Whole Foods": layers.whole_foods.group,
    "FSIS Establishments": layers.fsis_coordinates.group,
    "Flow Lines": flowLinesGroup,
    "Flow Points": flowPointsGroup,
    "US State Boundaries": usStateLayer,
    "County Bivariate": countyLayer,
};

L.control.layers(null, overlays, { collapsed: false }).addTo(map);

// === Search & Reset (Fixed) ===

// Helper to manage visibility correctly
function setMarkerVisible(marker, visible) {
    const storeKey = marker._storeKey;
    const group = layers[storeKey]?.group;
    if (!group) return;

    const inGroup = group.hasLayer(marker);
    if (visible) {
        if (map.hasLayer(group) && !inGroup) group.addLayer(marker);
    } else {
        if (inGroup) group.removeLayer(marker);
    }
}

function normalizeState(value) {
    if (!value) return "";
    const v = value.toString().trim().toUpperCase();
    if (v.length === 2) return v; // already abbreviation
    return stateAbbrMap[v] || v;
}

function filterStores() {
    const rawQuery = document.getElementById('searchBox').value.trim();
    const query = rawQuery.toUpperCase();
    const normalizedCityQuery = normalizeCityName(query);
    const queryIsZip = /^\d{5}$/.test(query);
    const queryStateAbbr = normalizeState(query);

    allMarkers.forEach(marker => {
        const storeKey = marker._storeKey;
        const group = layers[storeKey]?.group;
        if (!group) return;

        const props = marker.feature?.properties || {};
        const city = normalizeCityName((props.city || "").toString());
        const stateAbbr = normalizeState(props.state || "");
        const zip = (props.zip || "").toString().toUpperCase();
        const storeName = (props.company || "").toUpperCase();

        const match =
            (queryStateAbbr && stateAbbr === queryStateAbbr) ||
            (queryIsZip && zip === query) ||
            (city && city.includes(normalizedCityQuery)) ||
            (storeName && storeName.includes(query));

        setMarkerVisible(marker, match);
    });
}

function resetFilters() {
    const input = document.getElementById('searchBox');
    if (input) input.value = '';

    allMarkers.forEach(marker => {
        const storeKey = marker._storeKey;
        const group = layers[storeKey]?.group;
        if (!group) return;

        if (map.hasLayer(group)) {
            if (!group.hasLayer(marker)) group.addLayer(marker);
        } else {
            if (group.hasLayer(marker)) group.removeLayer(marker);
        }
    });
}

function buildBivariateLegend() {
    // 1. Target the new grid container element from index.html
    const gridDiv = document.getElementById('bivariate-grid');
    if (!gridDiv) return;

    gridDiv.innerHTML = ""; // Clear existing content

    const bivariateClasses = [
        // Row 1 (High Food Insecurity)
        "13", "23", "33",
        // Row 2 (Medium Food Insecurity)
        "12", "22", "32",
        // Row 3 (Low Food Insecurity)
        "11", "21", "31",
    ];

    // 2. Iterate and create all 9 swatches
    bivariateClasses.forEach(k => {
        const swatch = document.createElement("span");
        swatch.className = "bivariate-swatch";
        swatch.style.background = bivariate_colors[k];
        gridDiv.appendChild(swatch);
    });

}

document.addEventListener('DOMContentLoaded', buildBivariateLegend);
