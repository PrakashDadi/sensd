const map = L.map('map').setView([40, -95], 5);

// === Custom pane for state boundaries (always on top) ===
map.createPane('statePane');
map.getPane('statePane').style.zIndex = 650;  // higher than overlays
map.getPane('statePane').style.pointerEvents = 'none';  // disable mouse capture

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
        .then(response => response.json())
        .then(data => {
            L.geoJSON(data, {
                pointToLayer: (feature, latlng) => {
                    if (layerInfo.label !== 'FSIS Establishments') {
                        // Stores → circle markers or custom icons
                        return L.circleMarker(latlng, {
                            radius: 3,
                            fillColor: layerInfo.color,
                            color: "#fff",
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.9
                        });
                    } else {
                        // FSIS → small orange circles
                        return L.circleMarker(latlng, {
                            radius: 3,
                            fillColor: layerInfo.color,
                            color: "#000",
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.8
                        });
                    }
                },
                onEachFeature: (feature, layer) => {
                    if (layerInfo.label !== 'FSIS Establishments') {
                        layer.bindPopup(getPopupContent(feature.properties));
                    } else {
                        layer.bindPopup(getFsisPopupContent(feature.properties));
                    }
                    allMarkers.push(layer);
                    layer._storeKey = key;
                    layerInfo.group.addLayer(layer);
                }
            });
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


const overlays = {
    Walmart: layers.walmart.group,
    Schnucks: layers.schnucks.group,
    "Save A Lot": layers.save_a_lot.group,
    "Whole Foods": layers.whole_foods.group,
    "FSIS Establishments": layers.fsis_coordinates.group,
    "US State Boundaries": usStateLayer,
    "County Bivariate": countyLayer,

};

L.control.layers(null, overlays, { collapsed: false }).addTo(map);


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
