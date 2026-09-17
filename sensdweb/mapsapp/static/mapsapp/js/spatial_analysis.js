// ============================================================
// SENSD FLOW ANALYSIS DASHBOARD
// geosens/static/js/flow_analysis.js
// ============================================================


// ============================================================
// GENERAL HELPERS
// ============================================================

function getEl(id) {
    return document.getElementById(id);
}


function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatNumber(
    value,
    maximumFractionDigits = 2
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "—";
    }

    const numericValue =
        Number(value);

    if (
        !Number.isFinite(
            numericValue
        )
    ) {
        return "—";
    }

    return numericValue.toLocaleString(
        undefined,
        {
            maximumFractionDigits
        }
    );
}


function setStatus(
    element,
    message,
    type = ""
) {

    if (!element) {
        return;
    }

    element.textContent =
        message || "";

    element.className =
        "spatial-analysis-status";

    if (type) {

        element.classList.add(
            type
        );
    }
}


async function readJsonResponse(
    response
) {

    let data;

    try {

        data =
            await response.json();

    } catch (error) {

        throw new Error(
            `Server returned an invalid response (${response.status}).`
        );
    }

    if (
        !response.ok ||
        data.success === false
    ) {

        throw new Error(
            data.error ||
            `Request failed with status ${response.status}.`
        );
    }

    return data;
}


function fileExtension(
    filename
) {

    if (
        !filename ||
        !filename.includes(".")
    ) {
        return "";
    }

    return filename
        .split(".")
        .pop()
        .toLowerCase();
}


function normalizedFieldName(
    value
) {

    return String(
        value || ""
    )
        .toLowerCase()
        .replace(
            /[^a-z0-9]/g,
            ""
        );
}


function populateSelect(
    select,
    fields,
    {
        placeholder =
            "— select field —",

        optional =
            false
    } = {}
) {

    if (!select) {
        return;
    }

    select.innerHTML = "";

    const emptyOption =
        document.createElement(
            "option"
        );

    emptyOption.value = "";

    emptyOption.textContent =
        optional
            ? "— optional —"
            : placeholder;

    select.appendChild(
        emptyOption
    );

    fields.forEach(
        field => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                field;

            option.textContent =
                field;

            select.appendChild(
                option
            );
        }
    );
}


function populateMultiSelect(
    select,
    fields
) {

    if (!select) {
        return;
    }

    select.innerHTML = "";

    fields.forEach(
        field => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                field;

            option.textContent =
                field;

            select.appendChild(
                option
            );
        }
    );
}


function autoSelectField(
    select,
    fields,
    aliases
) {

    if (!select) {
        return;
    }

    const normalizedAliases =
        aliases.map(
            normalizedFieldName
        );

    for (
        const field
        of fields
    ) {

        const normalizedField =
            normalizedFieldName(
                field
            );

        if (
            normalizedAliases.includes(
                normalizedField
            )
        ) {

            select.value =
                field;

            return;
        }
    }
}


function uniqueLayerKey(
    prefix
) {

    return (
        `${prefix}_${Date.now()}_` +
        Math.random()
            .toString(36)
            .slice(2, 7)
    );
}


function safeFitBounds(
    layer
) {

    if (
        !layer ||
        typeof layer.getBounds !==
            "function"
    ) {
        return;
    }

    try {

        const bounds =
            layer.getBounds();

        if (
            bounds &&
            bounds.isValid()
        ) {

            map.fitBounds(
                bounds,
                {
                    padding:
                        [35, 35],

                    maxZoom:
                        13
                }
            );
        }

    } catch (error) {

        console.warn(
            "Could not fit layer bounds:",
            error
        );
    }
}


function getSelectedOptions(
    select
) {

    if (!select) {
        return [];
    }

    return Array.from(
        select.selectedOptions ||
        []
    )
        .map(
            option =>
                option.value
        )
        .filter(Boolean);
}


// ============================================================
// MAP
// ============================================================

const map =
    L.map(
        "dashboard-map",
        {
            zoomControl:
                true,

            minZoom:
                2,

            maxZoom:
                18,

            worldCopyJump:
                false,

            maxBounds: [
                [-90, -180],
                [90, 180]
            ],

            maxBoundsViscosity:
                1
        }
    )
    .setView(
        [38.5, -92.5],
        5
    );


// ============================================================
// BASEMAPS
// ============================================================

const tileConfigElement = document.getElementById("map-tile-config");
const tileConfig = tileConfigElement
    ? JSON.parse(tileConfigElement.textContent)
    : {};
const basemapLayers = {};

function statesBasemapStyle() {
    return {
        color: "#64748b",
        weight: 1,
        opacity: 0.9,
        fillColor: "#e2e8f0",
        fillOpacity: 0.72
    };
}

basemapLayers.states = L.geoJSON(
    null,
    {
        style: statesBasemapStyle,
        onEachFeature(feature, layer) {
            const stateName = feature.properties?.state_name || "State";

            layer.bindTooltip(stateName, {
                className: "sensd-state-tooltip",
                direction: "top",
                sticky: true
            });

            layer.on({
                mouseover(event) {
                    event.target.setStyle({
                        color: "#2563eb",
                        weight: 2,
                        fillColor: "#bfdbfe",
                        fillOpacity: 0.88
                    });
                    event.target.bringToFront();
                },
                mouseout(event) {
                    basemapLayers.states.resetStyle(event.target);
                },
                click(event) {
                    map.fitBounds(event.target.getBounds(), {
                        animate: true,
                        padding: [24, 24]
                    });
                }
            });
        }
    }
);

if (tileConfig.url) {
    basemapLayers.configured = L.tileLayer(
        tileConfig.url,
        {
            attribution: tileConfig.attribution || "",
            maxZoom: Number(tileConfig.maxZoom) || 19,
            updateWhenIdle: true,
            keepBuffer: 2
        }
    );

    let tileErrorCount = 0;

    basemapLayers.configured.on("tileerror", () => {
        tileErrorCount += 1;

        if (tileErrorCount === 3 && map.hasLayer(basemapLayers.configured)) {
            console.warn(
                "OpenStreetMap tiles are unavailable; using SENSD state boundaries."
            );
            setBasemap("states");

            const basemapSelect = getEl("basemap-select");
            if (basemapSelect) {
                basemapSelect.value = "states";
            }
        }
    });
}

let activeBasemapLayer = basemapLayers.configured || basemapLayers.states;

if (activeBasemapLayer) {
    activeBasemapLayer.addTo(map);
}

L.control.scale({
    imperial: true,
    metric: true,
    position: "bottomleft"
}).addTo(map);

async function loadStatesBasemap() {
    try {
        const response = await fetch(SENSD_API.usStates);

        if (!response.ok) {
            throw new Error(`State boundary request failed (${response.status}).`);
        }

        const stateData = await response.json();

        if (!Array.isArray(stateData.features) || stateData.features.length === 0) {
            throw new Error("No state boundary features are available.");
        }

        basemapLayers.states.addData(stateData);

        if (map.hasLayer(basemapLayers.states)) {
            basemapLayers.states.bringToBack();
        }
    } catch (error) {
        console.error("Unable to load the SENSD states basemap:", error);
    }
}

loadStatesBasemap();


function setBasemap(
    basemapName
) {

    if (
        activeBasemapLayer &&
        map.hasLayer(
            activeBasemapLayer
        )
    ) {

        map.removeLayer(
            activeBasemapLayer
        );
    }

    activeBasemapLayer =
        null;

    if (
        basemapName !==
            "none" &&

        basemapLayers[
            basemapName
        ]
    ) {

        activeBasemapLayer =
            basemapLayers[
                basemapName
            ];

        activeBasemapLayer
            .addTo(map);

        if (
            typeof activeBasemapLayer
                .bringToBack ===
            "function"
        ) {

            activeBasemapLayer
                .bringToBack();
        }
    }
}


getEl(
    "basemap-select"
)
?.addEventListener(
    "change",
    event => {

        setBasemap(
            event.target.value
        );
    }
);


// ============================================================
// SIDEBAR ELEMENTS
// ============================================================

const tocPanel =
    getEl("toc-panel");

const toolboxPanel =
    getEl("toolbox-panel");

const tocCollapseBtn =
    getEl("toc-collapse-btn");

const toolboxCollapseBtn =
    getEl("toolbox-collapse-btn");

const tocRestoreBtn =
    getEl("toc-restore-btn");

const toolboxRestoreBtn =
    getEl("toolbox-restore-btn");

const tocResizeHandle =
    getEl("toc-resize-handle");

const toolboxResizeHandle =
    getEl("toolbox-resize-handle");


// ============================================================
// MAP RESIZE SAFETY
// ============================================================

let resizeFrame =
    null;


function scheduleMapResize() {

    if (
        resizeFrame !==
        null
    ) {

        cancelAnimationFrame(
            resizeFrame
        );
    }

    resizeFrame =
        requestAnimationFrame(
            () => {

                map.invalidateSize(
                    false
                );

                resizeFrame =
                    null;
            }
        );
}


function refreshMapAfterSidebarChange() {

    scheduleMapResize();

    setTimeout(
        () => {

            map.invalidateSize(
                true
            );
        },
        300
    );
}


// ============================================================
// SIDEBAR COLLAPSE / RESTORE
// ============================================================

tocCollapseBtn
?.addEventListener(
    "click",
    event => {

        event.preventDefault();

        event.stopPropagation();

        tocPanel
            ?.classList.add(
                "collapsed"
            );

        if (
            tocRestoreBtn
        ) {

            tocRestoreBtn
                .style
                .display =
                "flex";
        }

        if (
            tocResizeHandle
        ) {

            tocResizeHandle
                .classList.add(
                    "hidden"
                );
        }

        refreshMapAfterSidebarChange();
    }
);


tocRestoreBtn
?.addEventListener(
    "click",
    event => {

        event.preventDefault();

        event.stopPropagation();

        tocPanel
            ?.classList.remove(
                "collapsed"
            );

        tocRestoreBtn
            .style
            .display =
            "none";

        if (
            tocResizeHandle
        ) {

            tocResizeHandle
                .classList.remove(
                    "hidden"
                );
        }

        refreshMapAfterSidebarChange();
    }
);


toolboxCollapseBtn
?.addEventListener(
    "click",
    event => {

        event.preventDefault();

        event.stopPropagation();

        toolboxPanel
            ?.classList.add(
                "collapsed"
            );

        if (
            toolboxRestoreBtn
        ) {

            toolboxRestoreBtn
                .style
                .display =
                "flex";
        }

        if (
            toolboxResizeHandle
        ) {

            toolboxResizeHandle
                .classList.add(
                    "hidden"
                );
        }

        refreshMapAfterSidebarChange();
    }
);


toolboxRestoreBtn
?.addEventListener(
    "click",
    event => {

        event.preventDefault();

        event.stopPropagation();

        toolboxPanel
            ?.classList.remove(
                "collapsed"
            );

        toolboxRestoreBtn
            .style
            .display =
            "none";

        if (
            toolboxResizeHandle
        ) {

            toolboxResizeHandle
                .classList.remove(
                    "hidden"
                );
        }

        refreshMapAfterSidebarChange();
    }
);


// ============================================================
// SIDEBAR RESIZING
// ============================================================

const LEFT_MIN_WIDTH =
    175;

const LEFT_MAX_WIDTH =
    500;

const RIGHT_MIN_WIDTH =
    240;

const RIGHT_MAX_WIDTH =
    600;


function clamp(
    value,
    min,
    max
) {

    return Math.min(
        Math.max(
            value,
            min
        ),
        max
    );
}


function setLeftPanelWidth(
    width
) {

    const safeWidth =
        clamp(
            width,
            LEFT_MIN_WIDTH,
            LEFT_MAX_WIDTH
        );

    document
        .documentElement
        .style
        .setProperty(
            "--sensd-left-width",
            `${safeWidth}px`
        );

    scheduleMapResize();
}


function setRightPanelWidth(
    width
) {

    const safeWidth =
        clamp(
            width,
            RIGHT_MIN_WIDTH,
            RIGHT_MAX_WIDTH
        );

    document
        .documentElement
        .style
        .setProperty(
            "--sensd-right-width",
            `${safeWidth}px`
        );

    scheduleMapResize();
}


// ============================================================
// LEFT PANEL DRAG
// ============================================================

tocResizeHandle
?.addEventListener(
    "pointerdown",
    event => {

        if (
            tocPanel
                ?.classList.contains(
                    "collapsed"
                )
        ) {
            return;
        }

        event.preventDefault();

        event.stopPropagation();

        const startX =
            event.clientX;

        const startWidth =
            tocPanel
                .getBoundingClientRect()
                .width;

        document
            .body
            .classList.add(
                "sensd-resizing"
            );

        tocResizeHandle
            .classList.add(
                "dragging"
            );

        try {

            tocResizeHandle
                .setPointerCapture(
                    event.pointerId
                );

        } catch (error) {

            console.warn(
                "Unable to capture left resize pointer.",
                error
            );
        }

        const onMove =
            moveEvent => {

                const difference =
                    moveEvent.clientX -
                    startX;

                setLeftPanelWidth(
                    startWidth +
                    difference
                );
            };


        const onEnd =
            endEvent => {

                document
                    .body
                    .classList.remove(
                        "sensd-resizing"
                    );

                tocResizeHandle
                    .classList.remove(
                        "dragging"
                    );

                tocResizeHandle
                    .removeEventListener(
                        "pointermove",
                        onMove
                    );

                tocResizeHandle
                    .removeEventListener(
                        "pointerup",
                        onEnd
                    );

                tocResizeHandle
                    .removeEventListener(
                        "pointercancel",
                        onEnd
                    );

                try {

                    tocResizeHandle
                        .releasePointerCapture(
                            endEvent.pointerId
                        );

                } catch (error) {
                    // pointer may already be released
                }

                map.invalidateSize(
                    true
                );
            };


        tocResizeHandle
            .addEventListener(
                "pointermove",
                onMove
            );

        tocResizeHandle
            .addEventListener(
                "pointerup",
                onEnd
            );

        tocResizeHandle
            .addEventListener(
                "pointercancel",
                onEnd
            );
    }
);


// ============================================================
// RIGHT PANEL DRAG
// ============================================================

toolboxResizeHandle
?.addEventListener(
    "pointerdown",
    event => {

        if (
            toolboxPanel
                ?.classList.contains(
                    "collapsed"
                )
        ) {
            return;
        }

        event.preventDefault();

        event.stopPropagation();

        const startX =
            event.clientX;

        const startWidth =
            toolboxPanel
                .getBoundingClientRect()
                .width;

        document
            .body
            .classList.add(
                "sensd-resizing"
            );

        toolboxResizeHandle
            .classList.add(
                "dragging"
            );

        try {

            toolboxResizeHandle
                .setPointerCapture(
                    event.pointerId
                );

        } catch (error) {

            console.warn(
                "Unable to capture toolbox resize pointer.",
                error
            );
        }

        const onMove =
            moveEvent => {

                const difference =
                    startX -
                    moveEvent.clientX;

                setRightPanelWidth(
                    startWidth +
                    difference
                );
            };


        const onEnd =
            endEvent => {

                document
                    .body
                    .classList.remove(
                        "sensd-resizing"
                    );

                toolboxResizeHandle
                    .classList.remove(
                        "dragging"
                    );

                toolboxResizeHandle
                    .removeEventListener(
                        "pointermove",
                        onMove
                    );

                toolboxResizeHandle
                    .removeEventListener(
                        "pointerup",
                        onEnd
                    );

                toolboxResizeHandle
                    .removeEventListener(
                        "pointercancel",
                        onEnd
                    );

                try {

                    toolboxResizeHandle
                        .releasePointerCapture(
                            endEvent.pointerId
                        );

                } catch (error) {
                    // pointer may already be released
                }

                map.invalidateSize(
                    true
                );
            };


        toolboxResizeHandle
            .addEventListener(
                "pointermove",
                onMove
            );

        toolboxResizeHandle
            .addEventListener(
                "pointerup",
                onEnd
            );

        toolboxResizeHandle
            .addEventListener(
                "pointercancel",
                onEnd
            );
    }
);


// ============================================================
// LEFT TOC ACCORDION
// ============================================================

document
    .querySelectorAll(
        ".toc-section-title"
    )
    .forEach(
        title => {

            title.addEventListener(
                "click",
                () => {

                    const target =
                        getEl(
                            title.dataset
                                .target
                        );

                    if (!target) {
                        return;
                    }

                    const isOpen =
                        target
                            .style
                            .display !==
                        "none";

                    target.style.display =
                        isOpen
                            ? "none"
                            : "block";

                    const chevron =
                        title.querySelector(
                            ".toc-chevron"
                        );

                    if (chevron) {

                        chevron.className =
                            !isOpen
                                ? "fa fa-chevron-down toc-chevron"
                                : "fa fa-chevron-right toc-chevron";
                    }
                }
            );
        }
    );


// ============================================================
// TOOLBOX TREE
// ============================================================

document
    .querySelectorAll(
        ".toolbox-tree-parent"
    )
    .forEach(
        parent => {

            parent.addEventListener(
                "click",
                event => {

                    event.preventDefault();

                    const targetId =
                        parent.dataset
                            .treeTarget;

                    const children =
                        getEl(
                            targetId
                        );

                    if (!children) {
                        return;
                    }

                    const currentlyOpen =
                        children
                            .style
                            .display !==
                        "none";

                    children.style.display =
                        currentlyOpen
                            ? "none"
                            : "block";

                    parent.classList.toggle(
                        "open",
                        !currentlyOpen
                    );

                    const chevron =
                        parent.querySelector(
                            ".toolbox-tree-chevron"
                        );

                    if (chevron) {

                        chevron.className =
                            !currentlyOpen
                                ? "fa fa-chevron-down toolbox-tree-chevron"
                                : "fa fa-chevron-right toolbox-tree-chevron";
                    }
                }
            );
        }
    );


// ============================================================
// TOOLBOX PAGE NAVIGATION
// ============================================================

function openToolPage(
    toolName,
    title
) {

    const page =
        getEl(
            `page-${toolName}`
        );

    if (!page) {

        console.warn(
            `Tool page not found: page-${toolName}`
        );

        return;
    }

    document
        .querySelectorAll(
            ".tool-page"
        )
        .forEach(
            toolPage => {

                toolPage.style.display =
                    "none";
            }
        );

    document
        .querySelectorAll(
            ".toolbox-tree-leaf"
        )
        .forEach(
            leaf => {

                leaf.classList.remove(
                    "active"
                );
            }
        );

    const selectedLeaf =
        document.querySelector(
            `.toolbox-tree-leaf[data-tool="${toolName}"]`
        );

    selectedLeaf
        ?.classList.add(
            "active"
        );

    const listView =
        getEl(
            "toolbox-list-view"
        );

    const detailView =
        getEl(
            "toolbox-detail-view"
        );

    if (listView) {

        listView.style.display =
            "none";
    }

    if (detailView) {

        detailView.style.display =
            "block";
    }

    page.style.display =
        "block";

    const detailTitle =
        getEl(
            "toolbox-detail-title"
        );

    if (detailTitle) {

        detailTitle.textContent =
            title ||
            toolName;
    }

    setTimeout(
        () => {

            map.invalidateSize();
        },
        100
    );
}


document
    .querySelectorAll(
        ".toolbox-tree-leaf"
    )
    .forEach(
        leaf => {

            leaf.addEventListener(
                "click",
                () => {

                    openToolPage(
                        leaf.dataset
                            .tool,

                        leaf.dataset
                            .title ||

                        leaf.textContent
                            .trim()
                    );
                }
            );
        }
    );


getEl(
    "toolbox-back-btn"
)
?.addEventListener(
    "click",
    () => {

        const detailView =
            getEl(
                "toolbox-detail-view"
            );

        const listView =
            getEl(
                "toolbox-list-view"
            );

        if (detailView) {

            detailView.style.display =
                "none";
        }

        if (listView) {

            listView.style.display =
                "block";
        }

        document
            .querySelectorAll(
                ".toolbox-tree-leaf"
            )
            .forEach(
                leaf => {

                    leaf.classList.remove(
                        "active"
                    );
                }
            );

        setTimeout(
            () => {

                map.invalidateSize();
            },
            100
        );
    }
);


// ============================================================
// LAYER REGISTRY
// ============================================================

const uploadedLayers = {};


/*
 * This represents the analysis whose legend is
 * currently displayed.
 *
 * Multiple analysis layers may exist simultaneously.
 */
let activeAnalysisLayerKey =
    null;


let activeFlowSummaryLayerKey =
    null;


// ============================================================
// DISPLAY COLOR PALETTE
// ============================================================

const displayLayerColors = [

    "#3a86ff",
    "#2ecc71",
    "#9b59b6",
    "#f39c12",
    "#1abc9c",
    "#e67e22",
    "#e74c3c",
    "#34495e"
];


let displayColorIndex =
    0;


// ============================================================
// UNIFIED LAYERS
// ============================================================

function getLayersContainer() {

    return getEl(
        "toc-layers-list"
    );
}


function refreshLayersEmptyMessage() {

    const empty =
        getEl(
            "toc-layers-empty"
        );

    if (!empty) {
        return;
    }

    const hasLayers =
        Object.keys(
            uploadedLayers
        ).length > 0;

    empty.style.display =
        hasLayers
            ? "none"
            : "block";
}


// ============================================================
// GENERIC POPUP
// ============================================================

function bindGenericPopup(
    feature,
    layer
) {

    const properties =
        feature?.properties ||
        {};

    const rows =
        Object.entries(
            properties
        )
        .filter(
            (
                [, value]
            ) =>
                value !== null &&
                value !== undefined &&
                value !== ""
        )
        .slice(
            0,
            50
        )
        .map(
            (
                [key, value]
            ) => `

                <div class="sensd-popup-row">

                    <strong>
                        ${escapeHtml(key)}
                    </strong>:

                    ${escapeHtml(value)}

                </div>
            `
        )
        .join("");

    if (rows) {

        layer.bindPopup(
            `
                <div class="sensd-popup">
                    ${rows}
                </div>
            `
        );
    }
}


// ============================================================
// DATA LAYER UPLOAD
// ============================================================

const referenceDropZone =
    getEl(
        "reference-drop-zone"
    );

const referenceFileInput =
    getEl(
        "reference-file-input"
    );

const referenceFileName =
    getEl(
        "reference-file-name"
    );

const referenceCoordinateConfig =
    getEl(
        "reference-coordinate-config"
    );

const referenceLatColumn =
    getEl(
        "reference-lat-column"
    );

const referenceLngColumn =
    getEl(
        "reference-lng-column"
    );

const referenceUploadBtn =
    getEl(
        "reference-upload-btn"
    );

const referenceStatus =
    getEl(
        "reference-upload-status"
    );


function setReferenceFile(
    file
) {

    if (!file) {
        return;
    }

    const extension =
        fileExtension(
            file.name
        );

    if (
        referenceFileName
    ) {

        referenceFileName
            .textContent =
            file.name;
    }

    setStatus(
        referenceStatus,
        ""
    );

    if (
        extension === "csv" ||
        extension === "xlsx" ||
        extension === "xls"
    ) {

        if (
            referenceCoordinateConfig
        ) {

            referenceCoordinateConfig
                .style
                .display =
                "block";
        }

        if (
            referenceUploadBtn
        ) {

            referenceUploadBtn
                .disabled =
                true;
        }

        inspectReferenceColumns(
            file
        );

    } else {

        if (
            referenceCoordinateConfig
        ) {

            referenceCoordinateConfig
                .style
                .display =
                "none";
        }

        if (
            referenceUploadBtn
        ) {

            referenceUploadBtn
                .disabled =
                false;
        }
    }
}


referenceDropZone
?.addEventListener(
    "dragover",
    event => {

        event.preventDefault();

        referenceDropZone
            .classList.add(
                "drag-over"
            );
    }
);


referenceDropZone
?.addEventListener(
    "dragleave",
    () => {

        referenceDropZone
            .classList.remove(
                "drag-over"
            );
    }
);


referenceDropZone
?.addEventListener(
    "drop",
    event => {

        event.preventDefault();

        referenceDropZone
            .classList.remove(
                "drag-over"
            );

        const file =
            event
                .dataTransfer
                ?.files?.[0];

        if (!file) {
            return;
        }

        try {

            const transfer =
                new DataTransfer();

            transfer.items.add(
                file
            );

            referenceFileInput
                .files =
                transfer.files;

        } catch (error) {

            console.warn(
                error
            );
        }

        setReferenceFile(
            file
        );
    }
);


referenceFileInput
?.addEventListener(
    "change",
    () => {

        setReferenceFile(
            referenceFileInput
                .files?.[0]
        );
    }
);


async function inspectReferenceColumns(
    file
) {

    const formData =
        new FormData();

    formData.append(
        "file",
        file
    );

    setStatus(
        referenceStatus,
        "Reading fields..."
    );

    try {

        const response =
            await fetch(
                SENSD_API
                    .inspectColumns,
                {
                    method:
                        "POST",

                    body:
                        formData
                }
            );

        const data =
            await readJsonResponse(
                response
            );

        const columns =
            data.columns ||
            [];

        populateSelect(
            referenceLatColumn,
            columns,
            {
                placeholder:
                    "— select latitude —"
            }
        );

        populateSelect(
            referenceLngColumn,
            columns,
            {
                placeholder:
                    "— select longitude —"
            }
        );

        autoSelectField(
            referenceLatColumn,
            columns,
            [
                "latitude",
                "lat",
                "y"
            ]
        );

        autoSelectField(
            referenceLngColumn,
            columns,
            [
                "longitude",
                "lon",
                "lng",
                "long",
                "x"
            ]
        );

        if (
            referenceUploadBtn
        ) {

            referenceUploadBtn
                .disabled =
                false;
        }

        setStatus(
            referenceStatus,
            ""
        );

    } catch (error) {

        setStatus(
            referenceStatus,
            error.message,
            "error"
        );
    }
}


referenceUploadBtn
?.addEventListener(
    "click",
    async () => {

        const file =
            referenceFileInput
                ?.files?.[0];

        if (!file) {
            return;
        }

        const extension =
            fileExtension(
                file.name
            );

        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        if (
            extension === "csv" ||
            extension === "xlsx" ||
            extension === "xls"
        ) {

            if (
                !referenceLatColumn
                    .value ||

                !referenceLngColumn
                    .value
            ) {

                setStatus(
                    referenceStatus,
                    "Select latitude and longitude fields.",
                    "error"
                );

                return;
            }

            formData.append(
                "lat_column",
                referenceLatColumn
                    .value
            );

            formData.append(
                "lng_column",
                referenceLngColumn
                    .value
            );
        }

        referenceUploadBtn
            .disabled =
            true;

        setStatus(
            referenceStatus,
            "Uploading..."
        );

        try {

            const response =
                await fetch(
                    SENSD_API
                        .uploadReference,
                    {
                        method:
                            "POST",

                        body:
                            formData
                    }
                );

            const data =
                await readJsonResponse(
                    response
                );

            renderDataLayer(
                data.geojson,
                data.filename,
                data.dataset_id
            );

            setStatus(
                referenceStatus,

                `Loaded ${formatNumber(
                    data.feature_count,
                    0
                )} features.`,

                "success"
            );

            referenceFileInput
                .value =
                "";

            if (
                referenceFileName
            ) {

                referenceFileName
                    .textContent =
                    "";
            }

            if (
                referenceCoordinateConfig
            ) {

                referenceCoordinateConfig
                    .style
                    .display =
                    "none";
            }

        } catch (error) {

            setStatus(
                referenceStatus,
                error.message,
                "error"
            );

        } finally {

            referenceUploadBtn
                .disabled =
                false;
        }
    }
);


// ============================================================
// RENDER DATA LAYER
// ============================================================

function renderDataLayer(
    geojson,
    filename,
    datasetId = null
) {

    if (
        !geojson
            ?.features
            ?.length
    ) {

        throw new Error(
            "Dataset contains no features."
        );
    }

    const layerKey =
        uniqueLayerKey(
            "data"
        );

    const color =
        displayLayerColors[
            displayColorIndex %
            displayLayerColors.length
        ];

    displayColorIndex +=
        1;

    const group =
        L.geoJSON(
            geojson,
            {
                style:
                    () => ({
                        color:
                            color,

                        weight:
                            1.5,

                        opacity:
                            0.9,

                        fillColor:
                            color,

                        fillOpacity:
                            0.25
                    }),

                pointToLayer:
                    (
                        feature,
                        latlng
                    ) => {

                        return L.circleMarker(
                            latlng,
                            {
                                radius:
                                    6,

                                fillColor:
                                    color,

                                color:
                                    "#ffffff",

                                weight:
                                    1.2,

                                opacity:
                                    1,

                                fillOpacity:
                                    0.85
                            }
                        );
                    },

                onEachFeature:
                    (
                        feature,
                        layer
                    ) => {

                        bindGenericPopup(
                            feature,
                            layer
                        );
                    }
            }
        )
        .addTo(map);

    uploadedLayers[
        layerKey
    ] = {

        layerType:
            "data",

        group,

        geojson,

        filename,

        datasetId,

        color,

        visible:
            true
    };

    addDataLayerToToc(
        layerKey
    );

    refreshLayersEmptyMessage();

    safeFitBounds(
        group
    );

    return layerKey;
}


// ============================================================
// DATA LAYER TOC
// ============================================================

function addDataLayerToToc(
    layerKey
) {

    const entry =
        uploadedLayers[
            layerKey
        ];

    const container =
        getLayersContainer();

    if (
        !entry ||
        !container
    ) {
        return;
    }

    const row =
        document.createElement(
            "div"
        );

    row.className =
        "toc-row";

    row.id =
        `toc-row-${layerKey}`;

    row.innerHTML = `

        <label class="toc-toggle-label">

            <input
                type="checkbox"
                checked
                id="toc-toggle-${layerKey}"
            >

            <span class="toc-toggle-slider"></span>

        </label>


        <span
            class="layer-dot"
            style="background:${entry.color};"
        ></span>


        <span
            class="toc-layer-name"
            title="${escapeHtml(
                entry.filename
            )}"
        >
            ${escapeHtml(
                entry.filename
            )}
        </span>


        <div class="toc-layer-actions">

            <button
                class="toc-action-btn"
                type="button"
                title="Remove layer"
            >
                <i class="fa fa-trash"></i>
            </button>

        </div>
    `;

    container.appendChild(
        row
    );

    getEl(
        `toc-toggle-${layerKey}`
    )
    ?.addEventListener(
        "change",
        event => {

            if (
                event.target.checked
            ) {

                entry.group
                    .addTo(map);

            } else {

                map.removeLayer(
                    entry.group
                );
            }

            entry.visible =
                event.target.checked;
        }
    );

    row
        .querySelector(
            ".toc-action-btn"
        )
        ?.addEventListener(
            "click",
            () => {

                removeLayer(
                    layerKey
                );
            }
        );
}


// ============================================================
// FLOW COLORS
// ============================================================

const predefinedFlowComboColors = {

    "Raw→Raw":
        "#c0392b",

    "Raw→Semicooked":
        "#e67e22",

    "Semicooked→Semicooked":
        "#f1c40f",

    "Semicooked→Cooked":
        "#2ecc71",

    "Raw→Cooked":
        "#16a085",

    "Cooked→Cooked":
        "#27ae60"
};


const dynamicFlowPalette = [

    "#4f8ef7",
    "#9b59b6",
    "#e84393",
    "#00a8a8",
    "#8e7d3b",
    "#d35400",
    "#2980b9",
    "#7f8c8d"
];


const dynamicFlowColors =
    new Map();


function flowComboKey(
    productFrom,
    productTo
) {

    const from =
        String(
            productFrom ||
            "Unknown"
        )
        .trim() ||
        "Unknown";

    const to =
        String(
            productTo ||
            "Unknown"
        )
        .trim() ||
        "Unknown";

    return (
        `${from}→${to}`
    );
}


function getFlowComboColor(
    productFrom,
    productTo
) {

    const key =
        flowComboKey(
            productFrom,
            productTo
        );

    if (
        predefinedFlowComboColors[
            key
        ]
    ) {

        return (
            predefinedFlowComboColors[
                key
            ]
        );
    }

    if (
        !dynamicFlowColors
            .has(key)
    ) {

        dynamicFlowColors.set(
            key,

            dynamicFlowPalette[
                dynamicFlowColors
                    .size %
                dynamicFlowPalette
                    .length
            ]
        );
    }

    return (
        dynamicFlowColors
            .get(key)
    );
}


// ============================================================
// FLOW FILTER STATE
// ============================================================

function ensureFlowFilterState(
    entry
) {

    if (
        !entry.activeCombos
    ) {

        entry.activeCombos =
            new Set(
                Object.keys(
                    entry.comboGroups ||
                    {}
                )
            );
    }

    if (
        !entry.filterControls
    ) {

        entry.filterControls = {

            toc:
                new Map(),

            summary:
                new Map()
        };
    }
}


function syncFlowFilterControls(
    entry,
    combo
) {

    ensureFlowFilterState(
        entry
    );

    const active =
        entry.activeCombos
            .has(combo);

    const tocCheckbox =
        entry.filterControls
            .toc
            .get(combo);

    const summaryCheckbox =
        entry.filterControls
            .summary
            .get(combo);

    if (
        tocCheckbox
    ) {

        tocCheckbox.checked =
            active;
    }

    if (
        summaryCheckbox
    ) {

        summaryCheckbox.checked =
            active;
    }
}


function setFlowComboActive(
    layerKey,
    combo,
    active
) {

    const entry =
        uploadedLayers[
            layerKey
        ];

    if (
        !entry ||
        entry.layerType !==
            "flow"
    ) {
        return;
    }

    ensureFlowFilterState(
        entry
    );

    if (active) {

        entry.activeCombos
            .add(combo);

    } else {

        entry.activeCombos
            .delete(combo);
    }

    const group =
        entry.comboGroups[
            combo
        ];

    if (group) {

        if (
            active &&
            entry.visible
        ) {

            group.addTo(
                map
            );

        } else if (
            map.hasLayer(
                group
            )
        ) {

            map.removeLayer(
                group
            );
        }
    }

    syncFlowFilterControls(
        entry,
        combo
    );

    if (
        activeFlowSummaryLayerKey ===
        layerKey
    ) {

        updateDynamicFlowSummary(
            entry
        );
    }
}


function getFilteredFlowFeatures(
    entry
) {

    if (
        !entry ||
        entry.layerType !==
            "flow"
    ) {
        return [];
    }

    ensureFlowFilterState(
        entry
    );

    return entry
        .geojson
        .features
        .filter(
            feature => {

                const p =
                    feature.properties ||
                    {};

                const combo =
                    flowComboKey(
                        p.product_type_i,
                        p.product_type_j
                    );

                return (
                    entry.activeCombos
                        .has(combo)
                );
            }
        );
}


// ============================================================
// FLOW UPLOAD
// ============================================================

const flowDropZone =
    getEl(
        "upload-drop-zone"
    );

const flowFileInput =
    getEl(
        "dash-file-input"
    );

const flowFileName =
    getEl(
        "upload-file-name"
    );

const flowColumnMapping =
    getEl(
        "flow-column-mapping"
    );

const flowUploadBtn =
    getEl(
        "dash-upload-btn"
    );

const flowUploadStatus =
    getEl(
        "dash-upload-status"
    );


const flowMappingElements = {

    from_id:
        getEl(
            "map-from-id"
        ),

    from_node:
        getEl(
            "map-from-node"
        ),

    from_city_area:
        getEl(
            "map-from-city-area"
        ),

    from_state:
        getEl(
            "map-from-state"
        ),

    from_latitude:
        getEl(
            "map-from-latitude"
        ),

    from_longitude:
        getEl(
            "map-from-longitude"
        ),

    to_id:
        getEl(
            "map-to-id"
        ),

    to_node:
        getEl(
            "map-to-node"
        ),

    to_city_area:
        getEl(
            "map-to-city-area"
        ),

    to_state:
        getEl(
            "map-to-state"
        ),

    to_latitude:
        getEl(
            "map-to-latitude"
        ),

    to_longitude:
        getEl(
            "map-to-longitude"
        ),

    quantity:
        getEl(
            "map-quantity"
        ),

    product_type_i:
        getEl(
            "map-product-type-i"
        ),

    product_type_j:
        getEl(
            "map-product-type-j"
        )
};


const flowRequiredMappings = [

    "from_id",
    "from_latitude",
    "from_longitude",

    "to_id",
    "to_latitude",
    "to_longitude",

    "quantity"
];


const flowMappingAliases = {

    from_id: [
        "fromid",
        "originid",
        "sourceid",
        "from_id"
    ],

    from_node: [
        "fromnode",
        "originname",
        "sourcename",
        "from_node"
    ],

    from_city_area: [
        "fromcityarea",
        "fromcity",
        "origincity",
        "sourcecity",
        "from_city_area"
    ],

    from_state: [
        "fromstate",
        "originstate",
        "sourcestate",
        "from_state"
    ],

    from_latitude: [
        "fromlatitude",
        "originlatitude",
        "sourcelatitude",
        "fromlat",
        "originlat",
        "from_latitude"
    ],

    from_longitude: [
        "fromlongitude",
        "originlongitude",
        "sourcelongitude",
        "fromlon",
        "fromlng",
        "originlon",
        "from_longitude"
    ],

    to_id: [
        "toid",
        "destinationid",
        "destid",
        "to_id"
    ],

    to_node: [
        "tonode",
        "destinationname",
        "destname",
        "to_node"
    ],

    to_city_area: [
        "tocityarea",
        "tocity",
        "destinationcity",
        "destcity",
        "to_city_area"
    ],

    to_state: [
        "tostate",
        "destinationstate",
        "deststate",
        "to_state"
    ],

    to_latitude: [
        "tolatitude",
        "destinationlatitude",
        "destlatitude",
        "tolat",
        "to_latitude"
    ],

    to_longitude: [
        "tolongitude",
        "destinationlongitude",
        "destlongitude",
        "tolon",
        "tolng",
        "to_longitude"
    ],

    quantity: [
        "quantity",
        "qty",
        "flow",
        "volume",
        "weight"
    ],

    product_type_i: [
        "producttypei",
        "productfrom",
        "fromproducttype",
        "product_type_i"
    ],

    product_type_j: [
        "producttypej",
        "productto",
        "toproducttype",
        "product_type_j"
    ]
};


function validateFlowMapping() {

    if (
        !flowUploadBtn
    ) {
        return;
    }

    const complete =
        flowRequiredMappings
            .every(
                key =>
                    Boolean(
                        flowMappingElements[
                            key
                        ]?.value
                    )
            );

    flowUploadBtn.disabled =
        !complete ||
        !flowFileInput
            ?.files?.length;
}


function setFlowFile(
    file
) {

    if (!file) {
        return;
    }

    if (
        flowFileName
    ) {

        flowFileName.textContent =
            file.name;
    }

    if (
        flowColumnMapping
    ) {

        flowColumnMapping
            .style
            .display =
            "none";
    }

    if (
        flowUploadBtn
    ) {

        flowUploadBtn
            .disabled =
            true;
    }

    inspectFlowColumns(
        file
    );
}


flowFileInput
?.addEventListener(
    "change",
    () => {

        setFlowFile(
            flowFileInput
                .files?.[0]
        );
    }
);


flowDropZone
?.addEventListener(
    "dragover",
    event => {

        event.preventDefault();

        flowDropZone
            .classList.add(
                "drag-over"
            );
    }
);


flowDropZone
?.addEventListener(
    "dragleave",
    () => {

        flowDropZone
            .classList.remove(
                "drag-over"
            );
    }
);


flowDropZone
?.addEventListener(
    "drop",
    event => {

        event.preventDefault();

        flowDropZone
            .classList.remove(
                "drag-over"
            );

        const file =
            event
                .dataTransfer
                ?.files?.[0];

        if (!file) {
            return;
        }

        try {

            const transfer =
                new DataTransfer();

            transfer.items.add(
                file
            );

            flowFileInput.files =
                transfer.files;

        } catch (error) {

            console.warn(
                error
            );
        }

        setFlowFile(
            file
        );
    }
);


async function inspectFlowColumns(
    file
) {

    const formData =
        new FormData();

    formData.append(
        "file",
        file
    );

    setStatus(
        flowUploadStatus,
        "Reading fields..."
    );

    try {

        const response =
            await fetch(
                SENSD_API
                    .inspectColumns,
                {
                    method:
                        "POST",

                    body:
                        formData
                }
            );

        const data =
            await readJsonResponse(
                response
            );

        const fields =
            data.columns ||
            [];

        Object.entries(
            flowMappingElements
        )
        .forEach(
            (
                [
                    mappingName,
                    select
                ]
            ) => {

                populateSelect(
                    select,
                    fields,
                    {
                        optional:
                            !flowRequiredMappings
                                .includes(
                                    mappingName
                                )
                    }
                );

                autoSelectField(
                    select,
                    fields,
                    flowMappingAliases[
                        mappingName
                    ] ||
                    []
                );
            }
        );

        if (
            flowColumnMapping
        ) {

            flowColumnMapping
                .style
                .display =
                "block";
        }

        validateFlowMapping();

        setStatus(
            flowUploadStatus,
            ""
        );

    } catch (error) {

        setStatus(
            flowUploadStatus,
            error.message,
            "error"
        );
    }
}


Object.values(
    flowMappingElements
)
.forEach(
    select => {

        select
            ?.addEventListener(
                "change",
                validateFlowMapping
            );
    }
);


flowUploadBtn
?.addEventListener(
    "click",
    async () => {

        const file =
            flowFileInput
                ?.files?.[0];

        if (!file) {
            return;
        }

        validateFlowMapping();

        if (
            flowUploadBtn.disabled
        ) {
            return;
        }

        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        Object.entries(
            flowMappingElements
        )
        .forEach(
            (
                [key, select]
            ) => {

                formData.append(
                    key,
                    select?.value ||
                    ""
                );
            }
        );

        flowUploadBtn.disabled =
            true;

        setStatus(
            flowUploadStatus,
            "Uploading and processing..."
        );

        try {

            const response =
                await fetch(
                    SENSD_API
                        .uploadFlow,
                    {
                        method:
                            "POST",

                        body:
                            formData
                    }
                );

            const data =
                await readJsonResponse(
                    response
                );

            renderFlowLayer(
                data.geojson,
                data.filename,
                data.dataset_id
            );

            setStatus(
                flowUploadStatus,

                `Loaded ${formatNumber(
                    data.rows_loaded,
                    0
                )} flow records.`,

                "success"
            );

            flowFileInput.value =
                "";

            if (
                flowFileName
            ) {

                flowFileName
                    .textContent =
                    "";
            }

            if (
                flowColumnMapping
            ) {

                flowColumnMapping
                    .style
                    .display =
                    "none";
            }

        } catch (error) {

            setStatus(
                flowUploadStatus,
                error.message,
                "error"
            );

        } finally {

            validateFlowMapping();
        }
    }
);


// ============================================================
// FLOW ARROW
// ============================================================

function addFlowArrow(
    fromLat,
    fromLon,
    toLat,
    toLon,
    color,
    group
) {

    const size =
        8;


    function buildChevron() {

        const fromPoint =
            map.latLngToLayerPoint(
                [
                    fromLat,
                    fromLon
                ]
            );

        const toPoint =
            map.latLngToLayerPoint(
                [
                    toLat,
                    toLon
                ]
            );

        const centerX =
            (
                fromPoint.x +
                toPoint.x
            ) / 2;

        const centerY =
            (
                fromPoint.y +
                toPoint.y
            ) / 2;

        const angle =
            Math.atan2(
                toPoint.y -
                fromPoint.y,

                toPoint.x -
                fromPoint.x
            );

        const armOneAngle =
            angle +
            Math.PI -
            0.5;

        const armTwoAngle =
            angle +
            Math.PI +
            0.5;

        const armOne = {

            x:
                centerX +
                size *
                Math.cos(
                    armOneAngle
                ),

            y:
                centerY +
                size *
                Math.sin(
                    armOneAngle
                )
        };

        const armTwo = {

            x:
                centerX +
                size *
                Math.cos(
                    armTwoAngle
                ),

            y:
                centerY +
                size *
                Math.sin(
                    armTwoAngle
                )
        };

        return [

            map.layerPointToLatLng(
                [
                    armOne.x,
                    armOne.y
                ]
            ),

            map.layerPointToLatLng(
                [
                    centerX,
                    centerY
                ]
            ),

            map.layerPointToLatLng(
                [
                    armTwo.x,
                    armTwo.y
                ]
            )
        ];
    }


    const arrow =
        L.polyline(
            buildChevron(),
            {
                color:
                    color,

                weight:
                    1.5,

                opacity:
                    0.9,

                interactive:
                    false
            }
        );


    const refresh =
        () => {

            if (
                map.hasLayer(
                    arrow
                )
            ) {

                arrow.setLatLngs(
                    buildChevron()
                );
            }
        };


    arrow.on(
        "add",
        () => {

            map.on(
                "zoomend moveend",
                refresh
            );
        }
    );


    arrow.on(
        "remove",
        () => {

            map.off(
                "zoomend moveend",
                refresh
            );
        }
    );


    group.addLayer(
        arrow
    );
}


// ============================================================
// FLOW RENDERING
// ============================================================

function renderFlowLayer(
    geojson,
    filename,
    datasetId = null
) {

    if (
        !geojson
            ?.features
            ?.length
    ) {

        throw new Error(
            "No valid flow records were returned."
        );
    }

    const layerKey =
        uniqueLayerKey(
            "flow"
        );

    const quantities =
        geojson
            .features
            .map(
                feature =>
                    Number(
                        feature
                            ?.properties
                            ?.quantity
                    ) ||
                    0
            );

    const minimumQuantity =
        Math.min(
            ...quantities
        );

    const maximumQuantity =
        Math.max(
            ...quantities
        );


    const pointsGroup =
        L.layerGroup()
            .addTo(map);


    const comboGroups = {};


    geojson
        .features
        .forEach(
            feature => {

                const properties =
                    feature.properties ||
                    {};

                const combo =
                    flowComboKey(
                        properties
                            .product_type_i,

                        properties
                            .product_type_j
                    );

                if (
                    !comboGroups[
                        combo
                    ]
                ) {

                    comboGroups[
                        combo
                    ] =
                        L.layerGroup()
                            .addTo(map);
                }
            }
        );


    uploadedLayers[
        layerKey
    ] = {

        layerType:
            "flow",

        pointsGroup,

        comboGroups,

        geojson,

        filename,

        datasetId,

        visible:
            true,

        minimumQuantity,

        maximumQuantity,

        activeCombos:
            new Set(
                Object.keys(
                    comboGroups
                )
            ),

        filterControls: {

            toc:
                new Map(),

            summary:
                new Map()
        },

        style: {

            lineColor:
                null,

            pointColor:
                "#3a86ff",

            weight:
                null,

            radius:
                6,

            opacity:
                0.75,

            colorMode:
                "combo",

            singleColor:
                "#4f8ef7",

            showArrows:
                true
        }
    };


    rebuildFlowLayer(
        layerKey
    );

    addFlowLayerToToc(
        layerKey
    );

    refreshLayersEmptyMessage();

    refreshFlowLayerSelects();


    const bounds =
        L.latLngBounds([]);


    geojson
        .features
        .forEach(
            feature => {

                const p =
                    feature.properties ||
                    {};

                const coordinates = [

                    [
                        Number(
                            p.from_latitude
                        ),

                        Number(
                            p.from_longitude
                        )
                    ],

                    [
                        Number(
                            p.to_latitude
                        ),

                        Number(
                            p.to_longitude
                        )
                    ]
                ];


                coordinates.forEach(
                    coordinate => {

                        if (
                            Number.isFinite(
                                coordinate[0]
                            ) &&

                            Number.isFinite(
                                coordinate[1]
                            )
                        ) {

                            bounds.extend(
                                coordinate
                            );
                        }
                    }
                );
            }
        );


    if (
        bounds.isValid()
    ) {

        map.fitBounds(
            bounds,
            {
                padding:
                    [40, 40],

                maxZoom:
                    13
            }
        );
    }
}


function calculateFlowWeight(
    entry,
    quantity
) {

    if (
        entry.style.weight !==
        null
    ) {

        return Number(
            entry.style.weight
        );
    }

    if (
        entry.maximumQuantity ===
        entry.minimumQuantity
    ) {

        return 3;
    }

    const normalized =
        (
            quantity -
            entry.minimumQuantity
        ) /
        (
            entry.maximumQuantity -
            entry.minimumQuantity
        );

    return (
        1.5 +
        normalized * 6
    );
}


function rebuildFlowLayer(
    layerKey
) {

    const entry =
        uploadedLayers[
            layerKey
        ];

    if (
        !entry ||
        entry.layerType !==
            "flow"
    ) {
        return;
    }

    ensureFlowFilterState(
        entry
    );

    Object.values(
        entry.comboGroups
    )
    .forEach(
        group => {

            group.clearLayers();

            if (
                map.hasLayer(
                    group
                )
            ) {

                map.removeLayer(
                    group
                );
            }
        }
    );

    entry.pointsGroup
        .clearLayers();

    if (
        map.hasLayer(
            entry.pointsGroup
        )
    ) {

        map.removeLayer(
            entry.pointsGroup
        );
    }


    const seenNodes =
        new Set();


    entry
        .geojson
        .features
        .forEach(
            feature => {

                const p =
                    feature.properties ||
                    {};

                const fromLat =
                    Number(
                        p.from_latitude
                    );

                const fromLon =
                    Number(
                        p.from_longitude
                    );

                const toLat =
                    Number(
                        p.to_latitude
                    );

                const toLon =
                    Number(
                        p.to_longitude
                    );

                const quantity =
                    Number(
                        p.quantity
                    ) ||
                    0;

                if (
                    !Number.isFinite(
                        fromLat
                    ) ||

                    !Number.isFinite(
                        fromLon
                    ) ||

                    !Number.isFinite(
                        toLat
                    ) ||

                    !Number.isFinite(
                        toLon
                    )
                ) {

                    return;
                }

                const combo =
                    flowComboKey(
                        p.product_type_i,
                        p.product_type_j
                    );

                if (
                    !entry
                        .comboGroups[
                            combo
                        ]
                ) {

                    entry.comboGroups[
                        combo
                    ] =
                        L.layerGroup();
                }

                const color =
                    entry.style
                        .colorMode ===
                    "single"

                        ? entry
                            .style
                            .singleColor

                        : (
                            entry
                                .style
                                .lineColor ||

                            getFlowComboColor(
                                p.product_type_i,
                                p.product_type_j
                            )
                        );

                const weight =
                    calculateFlowWeight(
                        entry,
                        quantity
                    );

                const line =
                    L.polyline(
                        [
                            [
                                fromLat,
                                fromLon
                            ],

                            [
                                toLat,
                                toLon
                            ]
                        ],
                        {
                            color:
                                color,

                            weight:
                                weight,

                            opacity:
                                entry
                                    .style
                                    .opacity
                        }
                    );

                line.bindPopup(
                    buildFlowPopup(
                        p,
                        entry.filename
                    )
                );

                entry
                    .comboGroups[
                        combo
                    ]
                    .addLayer(
                        line
                    );

                if (
                    entry
                        .style
                        .showArrows
                ) {

                    addFlowArrow(
                        fromLat,
                        fromLon,
                        toLat,
                        toLon,
                        color,

                        entry
                            .comboGroups[
                                combo
                            ]
                    );
                }


                const nodeCandidates = [

                    {
                        id:
                            p.from_id,

                        name:
                            p.from_node,

                        city:
                            p.from_city_area,

                        state:
                            p.from_state,

                        product:
                            p.product_type_i,

                        role:
                            "Origin",

                        lat:
                            fromLat,

                        lon:
                            fromLon
                    },

                    {
                        id:
                            p.to_id,

                        name:
                            p.to_node,

                        city:
                            p.to_city_area,

                        state:
                            p.to_state,

                        product:
                            p.product_type_j,

                        role:
                            "Destination",

                        lat:
                            toLat,

                        lon:
                            toLon
                    }
                ];


                nodeCandidates
                    .forEach(
                        node => {

                            const nodeKey =
                                `${node.id}|${node.lat}|${node.lon}`;

                            if (
                                seenNodes
                                    .has(
                                        nodeKey
                                    )
                            ) {

                                return;
                            }

                            seenNodes.add(
                                nodeKey
                            );

                            const marker =
                                L.circleMarker(
                                    [
                                        node.lat,
                                        node.lon
                                    ],
                                    {
                                        radius:
                                            Number(
                                                entry
                                                    .style
                                                    .radius
                                            ),

                                        fillColor:
                                            entry
                                                .style
                                                .pointColor,

                                        color:
                                            "#ffffff",

                                        weight:
                                            1.4,

                                        opacity:
                                            1,

                                        fillOpacity:
                                            0.9
                                    }
                                );

                            marker.bindPopup(
                                `
                                    <div class="sensd-popup">

                                        <strong>Node:</strong>
                                        ${escapeHtml(
                                            node.name ||
                                            node.id ||
                                            "—"
                                        )}
                                        <br>

                                        <strong>Role:</strong>
                                        ${escapeHtml(
                                            node.role
                                        )}
                                        <br>

                                        <strong>City / Area:</strong>
                                        ${escapeHtml(
                                            node.city ||
                                            "—"
                                        )}
                                        <br>

                                        <strong>State:</strong>
                                        ${escapeHtml(
                                            node.state ||
                                            "—"
                                        )}
                                        <br>

                                        <strong>Product:</strong>
                                        ${escapeHtml(
                                            node.product ||
                                            "—"
                                        )}

                                    </div>
                                `
                            );

                            entry
                                .pointsGroup
                                .addLayer(
                                    marker
                                );
                        }
                    );
            }
        );


    if (
        entry.visible
    ) {

        entry.pointsGroup
            .addTo(map);

        Object.entries(
            entry.comboGroups
        )
        .forEach(
            (
                [
                    combo,
                    group
                ]
            ) => {

                if (
                    entry
                        .activeCombos
                        .has(combo)
                ) {

                    group.addTo(
                        map
                    );
                }
            }
        );
    }
}


function buildFlowPopup(
    properties,
    filename
) {

    return `
        <div class="sensd-popup">

            <strong>Flow:</strong>
            ${escapeHtml(
                properties.from_id ||
                "—"
            )}
            →
            ${escapeHtml(
                properties.to_id ||
                "—"
            )}
            <br>

            <strong>From:</strong>
            ${escapeHtml(
                properties.from_node ||
                properties.from_id ||
                "—"
            )}
            <br>

            <strong>To:</strong>
            ${escapeHtml(
                properties.to_node ||
                properties.to_id ||
                "—"
            )}
            <br>

            <strong>Product:</strong>
            ${escapeHtml(
                properties.product_type_i ||
                "—"
            )}
            →
            ${escapeHtml(
                properties.product_type_j ||
                "—"
            )}
            <br>

            <strong>Quantity:</strong>
            ${formatNumber(
                properties.quantity,
                2
            )}
            <br>

            <strong>Dataset:</strong>
            ${escapeHtml(
                filename
            )}

        </div>
    `;
}


// ============================================================
// FLOW TOC
// ============================================================

function addFlowLayerToToc(
    layerKey
) {

    const entry =
        uploadedLayers[
            layerKey
        ];

    const container =
        getLayersContainer();

    if (
        !entry ||
        !container
    ) {
        return;
    }

    ensureFlowFilterState(
        entry
    );

    const parent =
        document.createElement(
            "div"
        );

    parent.className =
        "toc-tree-parent";

    parent.id =
        `toc-row-${layerKey}`;

    parent.innerHTML = `

        <div class="toc-tree-header">

            <button
                type="button"
                class="toc-tree-toggle-btn"
                id="toc-tree-btn-${layerKey}"
                title="Expand or collapse flow layer"
            >
                <i class="fa fa-chevron-down"></i>
            </button>

            <label class="toc-toggle-label">

                <input
                    type="checkbox"
                    checked
                    id="toc-toggle-${layerKey}"
                >

                <span class="toc-toggle-slider"></span>

            </label>

            <span
                class="toc-layer-name"
                title="${escapeHtml(
                    entry.filename
                )}"
            >
                ${escapeHtml(
                    entry.filename
                )}
            </span>

            <div class="toc-layer-actions">

                <button
                    type="button"
                    class="toc-action-btn"
                    title="Remove layer"
                >
                    <i class="fa fa-trash"></i>
                </button>

            </div>

        </div>


        <div
            class="toc-tree-children"
            id="toc-children-${layerKey}"
        ></div>
    `;

    container.appendChild(
        parent
    );

    const children =
        getEl(
            `toc-children-${layerKey}`
        );

    addFlowNodeSubRow(
        children,
        entry
    );


    Object.entries(
        entry.comboGroups
    )
    .forEach(
        (
            [
                combo,
                group
            ]
        ) => {

            const parts =
                combo.split(
                    "→"
                );

            addFlowComboSubRow(
                children,
                layerKey,
                combo,

                getFlowComboColor(
                    parts[0],
                    parts[1]
                ),

                group
            );
        }
    );


    getEl(
        `toc-tree-btn-${layerKey}`
    )
    ?.addEventListener(
        "click",
        () => {

            const open =
                children
                    .style
                    .display !==
                "none";

            children.style.display =
                open
                    ? "none"
                    : "block";

            const icon =
                getEl(
                    `toc-tree-btn-${layerKey}`
                )
                ?.querySelector(
                    "i"
                );

            if (icon) {

                icon.className =
                    open
                        ? "fa fa-chevron-right"
                        : "fa fa-chevron-down";
            }
        }
    );


    getEl(
        `toc-toggle-${layerKey}`
    )
    ?.addEventListener(
        "change",
        event => {

            const visible =
                event.target.checked;

            entry.visible =
                visible;

            if (visible) {

                entry
                    .pointsGroup
                    .addTo(map);

                Object.entries(
                    entry.comboGroups
                )
                .forEach(
                    (
                        [
                            combo,
                            group
                        ]
                    ) => {

                        if (
                            entry
                                .activeCombos
                                .has(combo)
                        ) {

                            group.addTo(
                                map
                            );
                        }
                    }
                );

            } else {

                if (
                    map.hasLayer(
                        entry.pointsGroup
                    )
                ) {

                    map.removeLayer(
                        entry.pointsGroup
                    );
                }

                Object.values(
                    entry.comboGroups
                )
                .forEach(
                    group => {

                        if (
                            map.hasLayer(
                                group
                            )
                        ) {

                            map.removeLayer(
                                group
                            );
                        }
                    }
                );
            }
        }
    );


    parent
        .querySelector(
            ".toc-action-btn"
        )
        ?.addEventListener(
            "click",
            () => {

                removeLayer(
                    layerKey
                );
            }
        );
}


function addFlowNodeSubRow(
    container,
    entry
) {

    if (!container) {
        return;
    }

    const row =
        document.createElement(
            "div"
        );

    row.className =
        "toc-row toc-sub-row";

    row.innerHTML = `

        <label class="toc-toggle-label">

            <input
                type="checkbox"
                checked
            >

            <span class="toc-toggle-slider"></span>

        </label>

        <span
            class="layer-dot"
            style="background:${entry.style.pointColor};"
        ></span>

        <span
            class="toc-layer-name"
            title="Nodes"
        >
            Nodes
        </span>
    `;

    container.appendChild(
        row
    );

    row
        .querySelector(
            'input[type="checkbox"]'
        )
        ?.addEventListener(
            "change",
            event => {

                if (
                    event
                        .target
                        .checked &&

                    entry.visible
                ) {

                    entry
                        .pointsGroup
                        .addTo(map);

                } else {

                    if (
                        map.hasLayer(
                            entry
                                .pointsGroup
                        )
                    ) {

                        map.removeLayer(
                            entry
                                .pointsGroup
                        );
                    }
                }
            }
        );
}


function addFlowComboSubRow(
    container,
    layerKey,
    combo,
    color,
    layerGroup
) {

    if (!container) {
        return;
    }

    const entry =
        uploadedLayers[
            layerKey
        ];

    if (!entry) {
        return;
    }

    ensureFlowFilterState(
        entry
    );

    const row =
        document.createElement(
            "div"
        );

    row.className =
        "toc-row toc-sub-row";

    row.innerHTML = `

        <label class="toc-toggle-label">

            <input
                type="checkbox"
                ${
                    entry
                        .activeCombos
                        .has(combo)
                        ? "checked"
                        : ""
                }
            >

            <span class="toc-toggle-slider"></span>

        </label>

        <span
            class="layer-dot"
            style="background:${color};"
        ></span>

        <span
            class="toc-layer-name"
            title="${escapeHtml(combo)}"
        >
            ${escapeHtml(combo)}
        </span>
    `;

    container.appendChild(
        row
    );

    const checkbox =
        row.querySelector(
            'input[type="checkbox"]'
        );

    if (checkbox) {

        entry
            .filterControls
            .toc
            .set(
                combo,
                checkbox
            );

        checkbox.addEventListener(
            "change",
            () => {

                setFlowComboActive(
                    layerKey,
                    combo,
                    checkbox.checked
                );
            }
        );
    }
}


// ============================================================
// ANALYSIS LEGEND HELPERS
// ============================================================

function showStoredAnalysisLegend(
    entry
) {

    if (
        !entry ||
        !entry.legend
    ) {

        hideAnalysisLegend();

        return;
    }

    if (
        entry.legend.type ===
        "bivariate-matrix"
    ) {

        showBivariateLegend(
            entry.legend.xLabel,
            entry.legend.yLabel,
            entry.legend.colors
        );

    } else {

        showAnalysisLegend(
            entry.legend.title,
            entry.legend.rows
        );
    }
}


function findMostRecentVisibleAnalysis(
    excludedLayerKey =
        null
) {

    const entries =
        Object.entries(
            uploadedLayers
        );

    for (
        let index =
            entries.length - 1;

        index >= 0;

        index -= 1
    ) {

        const [
            key,
            entry
        ] =
            entries[index];

        if (
            key ===
            excludedLayerKey
        ) {
            continue;
        }

        if (
            entry.layerType ===
                "analysis" &&

            entry.visible
        ) {

            return [
                key,
                entry
            ];
        }
    }

    return null;
}


function restoreAnotherAnalysisLegend(
    excludedLayerKey =
        null
) {

    const result =
        findMostRecentVisibleAnalysis(
            excludedLayerKey
        );

    if (!result) {

        activeAnalysisLayerKey =
            null;

        hideAnalysisLegend();

        return;
    }

    const [
        layerKey,
        entry
    ] =
        result;

    activeAnalysisLayerKey =
        layerKey;

    showStoredAnalysisLegend(
        entry
    );
}


// ============================================================
// REMOVE LAYER
// ============================================================

function removeLayer(
    layerKey
) {

    const entry =
        uploadedLayers[
            layerKey
        ];

    if (!entry) {
        return;
    }

    const removingDisplayedAnalysis =
        (
            entry.layerType ===
                "analysis" &&

            activeAnalysisLayerKey ===
                layerKey
        );


    if (
        entry.layerType ===
        "flow"
    ) {

        if (
            map.hasLayer(
                entry.pointsGroup
            )
        ) {

            map.removeLayer(
                entry.pointsGroup
            );
        }

        Object.values(
            entry.comboGroups
        )
        .forEach(
            group => {

                if (
                    map.hasLayer(
                        group
                    )
                ) {

                    map.removeLayer(
                        group
                    );
                }
            }
        );

        if (
            activeFlowSummaryLayerKey ===
            layerKey
        ) {

            activeFlowSummaryLayerKey =
                null;
        }

    } else if (
        entry.group &&
        map.hasLayer(
            entry.group
        )
    ) {

        map.removeLayer(
            entry.group
        );
    }


    delete uploadedLayers[
        layerKey
    ];


    getEl(
        `toc-row-${layerKey}`
    )
    ?.remove();


    if (
        removingDisplayedAnalysis
    ) {

        restoreAnotherAnalysisLegend(
            layerKey
        );
    }


    refreshLayersEmptyMessage();

    refreshFlowLayerSelects();

    clearFlowSummaryIfNeeded();
}


window.removeLayer =
    removeLayer;


// ============================================================
// FLOW LAYER SELECTS
// ============================================================

function refreshFlowLayerSelects() {

    const flowEntries =
        Object.entries(
            uploadedLayers
        )
        .filter(
            (
                [, entry]
            ) =>
                entry.layerType ===
                "flow"
        );


    [
        getEl(
            "sym-layer-select"
        ),

        getEl(
            "analysis-layer-select"
        )
    ]
    .forEach(
        select => {

            if (!select) {
                return;
            }

            const previousValue =
                select.value;

            select.innerHTML =
                `<option value="">— select a flow layer —</option>`;

            flowEntries
                .forEach(
                    (
                        [
                            key,
                            entry
                        ]
                    ) => {

                        const option =
                            document.createElement(
                                "option"
                            );

                        option.value =
                            key;

                        option.textContent =
                            entry.filename;

                        select.appendChild(
                            option
                        );
                    }
                );

            if (
                previousValue &&
                uploadedLayers[
                    previousValue
                ]?.layerType ===
                    "flow"
            ) {

                select.value =
                    previousValue;
            }
        }
    );


    const symEmpty =
        getEl(
            "sym-empty-msg"
        );

    if (
        symEmpty
    ) {

        symEmpty.style.display =
            flowEntries.length
                ? "none"
                : "block";
    }


    const analysisEmpty =
        getEl(
            "analysis-empty-msg"
        );

    if (
        analysisEmpty
    ) {

        analysisEmpty.style.display =
            flowEntries.length
                ? "none"
                : "block";
    }
}


// ============================================================
// SYMBOLOGY
// ============================================================

const symLayerSelect =
    getEl(
        "sym-layer-select"
    );


symLayerSelect
?.addEventListener(
    "change",
    () => {

        const entry =
            uploadedLayers[
                symLayerSelect
                    .value
            ];

        const controls =
            getEl(
                "sym-controls"
            );

        if (!entry) {

            if (
                controls
            ) {

                controls.style.display =
                    "none";
            }

            return;
        }

        if (
            controls
        ) {

            controls.style.display =
                "block";
        }

        getEl(
            "sym-line-color"
        ).value =
            entry
                .style
                .singleColor ||
            "#4f8ef7";

        getEl(
            "sym-point-color"
        ).value =
            entry
                .style
                .pointColor ||
            "#3a86ff";

        getEl(
            "sym-weight"
        ).value =
            entry
                .style
                .weight ||
            3;

        getEl(
            "sym-radius"
        ).value =
            entry
                .style
                .radius ||
            6;

        getEl(
            "sym-opacity"
        ).value =
            Math.round(
                (
                    entry
                        .style
                        .opacity ||
                    0.75
                ) *
                100
            );

        updateSymbologyLabels();
    }
);


function updateSymbologyLabels() {

    const weight =
        getEl(
            "sym-weight-val"
        );

    const radius =
        getEl(
            "sym-radius-val"
        );

    const opacity =
        getEl(
            "sym-opacity-val"
        );

    if (weight) {

        weight.textContent =
            getEl(
                "sym-weight"
            )?.value ||
            "3";
    }

    if (radius) {

        radius.textContent =
            getEl(
                "sym-radius"
            )?.value ||
            "6";
    }

    if (opacity) {

        opacity.textContent =
            getEl(
                "sym-opacity"
            )?.value ||
            "75";
    }
}


[
    "sym-weight",
    "sym-radius",
    "sym-opacity"
]
.forEach(
    id => {

        getEl(id)
            ?.addEventListener(
                "input",
                updateSymbologyLabels
            );
    }
);


getEl(
    "sym-apply-btn"
)
?.addEventListener(
    "click",
    () => {

        const layerKey =
            symLayerSelect
                .value;

        const entry =
            uploadedLayers[
                layerKey
            ];

        if (!entry) {
            return;
        }

        entry.style.colorMode =
            "single";

        entry.style.singleColor =
            getEl(
                "sym-line-color"
            ).value;

        entry.style.pointColor =
            getEl(
                "sym-point-color"
            ).value;

        entry.style.weight =
            Number(
                getEl(
                    "sym-weight"
                ).value
            );

        entry.style.radius =
            Number(
                getEl(
                    "sym-radius"
                ).value
            );

        entry.style.opacity =
            Number(
                getEl(
                    "sym-opacity"
                ).value
            ) /
            100;

        rebuildFlowLayer(
            layerKey
        );
    }
);


getEl(
    "sym-reset-btn"
)
?.addEventListener(
    "click",
    () => {

        const layerKey =
            symLayerSelect
                .value;

        const entry =
            uploadedLayers[
                layerKey
            ];

        if (!entry) {
            return;
        }

        entry.style.lineColor =
            null;

        entry.style.pointColor =
            "#3a86ff";

        entry.style.weight =
            null;

        entry.style.radius =
            6;

        entry.style.opacity =
            0.75;

        entry.style.colorMode =
            "combo";

        entry.style.singleColor =
            "#4f8ef7";

        entry.style.showArrows =
            true;

        rebuildFlowLayer(
            layerKey
        );

        symLayerSelect
            .dispatchEvent(
                new Event(
                    "change"
                )
            );
    }
);


// ============================================================
// FLOW SUMMARY
// ============================================================

function updateDynamicFlowSummary(
    entry
) {

    if (
        !entry ||
        entry.layerType !==
            "flow"
    ) {
        return;
    }

    const features =
        getFilteredFlowFeatures(
            entry
        );

    const quantities =
        features.map(
            feature =>
                Number(
                    feature
                        ?.properties
                        ?.quantity
                ) ||
                0
        );

    const totalFlows =
        features.length;

    const totalQuantity =
        quantities.reduce(
            (
                total,
                value
            ) =>
                total +
                value,
            0
        );

    const averageQuantity =
        totalFlows > 0

            ? (
                totalQuantity /
                totalFlows
            )

            : null;

    const maximumQuantity =
        totalFlows > 0

            ? Math.max(
                ...quantities
            )

            : null;


    const totalFlowsEl =
        getEl(
            "stat-total-flows"
        );

    const totalQuantityEl =
        getEl(
            "stat-total-qty"
        );

    const averageQuantityEl =
        getEl(
            "stat-avg-qty"
        );

    const maximumQuantityEl =
        getEl(
            "stat-max-qty"
        );


    if (
        totalFlowsEl
    ) {

        totalFlowsEl.textContent =
            formatNumber(
                totalFlows,
                0
            );
    }

    if (
        totalQuantityEl
    ) {

        totalQuantityEl.textContent =
            formatNumber(
                totalQuantity,
                1
            );
    }

    if (
        averageQuantityEl
    ) {

        averageQuantityEl.textContent =
            averageQuantity ===
            null

                ? "—"

                : formatNumber(
                    averageQuantity,
                    1
                );
    }

    if (
        maximumQuantityEl
    ) {

        maximumQuantityEl.textContent =
            maximumQuantity ===
            null

                ? "—"

                : formatNumber(
                    maximumQuantity,
                    1
                );
    }


    renderProductMix(
        entry,
        features
    );

    renderTopFlows(
        entry,
        features
    );


    const results =
        getEl(
            "analysis-results"
        );

    if (
        results
    ) {

        results.style.display =
            "block";
    }
}


getEl(
    "run-analysis-btn"
)
?.addEventListener(
    "click",
    () => {

        const layerKey =
            getEl(
                "analysis-layer-select"
            )?.value;

        const entry =
            uploadedLayers[
                layerKey
            ];

        if (
            !entry ||
            entry.layerType !==
                "flow"
        ) {
            return;
        }

        activeFlowSummaryLayerKey =
            layerKey;

        renderProductFilters(
            entry,
            layerKey
        );

        updateDynamicFlowSummary(
            entry
        );
    }
);


function renderProductMix(
    entry,
    features = null
) {

    const activeFeatures =
        features ||
        getFilteredFlowFeatures(
            entry
        );

    const totals = {};


    activeFeatures
        .forEach(
            feature => {

                const p =
                    feature.properties ||
                    {};

                const combo =
                    flowComboKey(
                        p.product_type_i,
                        p.product_type_j
                    );

                totals[
                    combo
                ] =
                    (
                        totals[
                            combo
                        ] ||
                        0
                    ) +
                    (
                        Number(
                            p.quantity
                        ) ||
                        0
                    );
            }
        );


    const chart =
        getEl(
            "product-mix-chart"
        );

    if (!chart) {
        return;
    }


    const entries =
        Object.entries(
            totals
        )
        .sort(
            (
                first,
                second
            ) =>
                second[1] -
                first[1]
        );


    if (
        !entries.length
    ) {

        chart.innerHTML = `

            <div class="toc-empty-msg">
                No selected flows.
            </div>
        `;

        return;
    }


    chart.innerHTML =
        entries
            .map(
                (
                    [
                        combo,
                        value
                    ]
                ) => `

                    <div class="analysis-bar-row">

                        <span>
                            ${escapeHtml(
                                combo
                            )}
                        </span>

                        <strong>
                            ${formatNumber(
                                value,
                                1
                            )}
                        </strong>

                    </div>
                `
            )
            .join("");
}


function renderTopFlows(
    entry,
    features = null
) {

    const activeFeatures =
        features ||
        getFilteredFlowFeatures(
            entry
        );

    const routes =
        activeFeatures
            .map(
                feature => {

                    const p =
                        feature.properties ||
                        {};

                    return {

                        from:
                            p.from_node ||
                            p.from_id ||
                            "—",

                        to:
                            p.to_node ||
                            p.to_id ||
                            "—",

                        quantity:
                            Number(
                                p.quantity
                            ) ||
                            0
                    };
                }
            )
            .sort(
                (
                    first,
                    second
                ) =>
                    second.quantity -
                    first.quantity
            )
            .slice(
                0,
                5
            );


    const chart =
        getEl(
            "top-flows-chart"
        );

    if (!chart) {
        return;
    }


    if (
        !routes.length
    ) {

        chart.innerHTML = `

            <div class="toc-empty-msg">
                No selected flows.
            </div>
        `;

        return;
    }


    chart.innerHTML =
        routes
            .map(
                route => `

                    <div class="analysis-bar-row">

                        <span>
                            ${escapeHtml(
                                route.from
                            )}
                            →
                            ${escapeHtml(
                                route.to
                            )}
                        </span>

                        <strong>
                            ${formatNumber(
                                route.quantity,
                                1
                            )}
                        </strong>

                    </div>
                `
            )
            .join("");
}


function renderProductFilters(
    entry,
    layerKey
) {

    const container =
        getEl(
            "product-filter-row"
        );

    if (!container) {
        return;
    }

    ensureFlowFilterState(
        entry
    );

    entry
        .filterControls
        .summary
        .clear();

    container.innerHTML =
        "";


    Object.keys(
        entry.comboGroups
    )
    .forEach(
        combo => {

            const label =
                document.createElement(
                    "label"
                );

            label.className =
                "product-filter-item";


            const checkbox =
                document.createElement(
                    "input"
                );

            checkbox.type =
                "checkbox";

            checkbox.checked =
                entry
                    .activeCombos
                    .has(combo);


            entry
                .filterControls
                .summary
                .set(
                    combo,
                    checkbox
                );


            checkbox.addEventListener(
                "change",
                () => {

                    setFlowComboActive(
                        layerKey,
                        combo,
                        checkbox.checked
                    );
                }
            );


            label.appendChild(
                checkbox
            );

            label.appendChild(
                document.createTextNode(
                    ` ${combo}`
                )
            );

            container.appendChild(
                label
            );
        }
    );
}


function clearFlowSummaryIfNeeded() {

    if (
        activeFlowSummaryLayerKey &&
        uploadedLayers[
            activeFlowSummaryLayerKey
        ]
    ) {
        return;
    }

    activeFlowSummaryLayerKey =
        null;

    const results =
        getEl(
            "analysis-results"
        );

    if (
        results
    ) {

        results.style.display =
            "none";
    }

    const productFilters =
        getEl(
            "product-filter-row"
        );

    if (
        productFilters
    ) {

        productFilters.innerHTML =
            "";
    }
}


// ============================================================
// ANALYSIS FILE INSPECTION
// ============================================================

async function inspectAnalysisFile(
    file,
    {
        status,

        selects,

        geographySelect,

        geographyAliases = [
            "geoid",
            "geography",
            "id",
            "fid",
            "name",
            "region",
            "area"
        ],

        autoSelections = {}
    }
) {

    const formData =
        new FormData();

    formData.append(
        "file",
        file
    );

    setStatus(
        status,
        "Reading fields..."
    );

    try {

        const response =
            await fetch(
                SENSD_API
                    .inspectColumns,
                {
                    method:
                        "POST",

                    body:
                        formData
                }
            );

        const data =
            await readJsonResponse(
                response
            );

        const fields =
            data.columns ||
            [];


        selects
            .forEach(
                item => {

                    populateSelect(
                        item.select,
                        fields,
                        {
                            optional:
                                Boolean(
                                    item.optional
                                ),

                            placeholder:
                                item.placeholder ||
                                "— select field —"
                        }
                    );
                }
            );


        if (
            geographySelect
        ) {

            autoSelectField(
                geographySelect,
                fields,
                geographyAliases
            );
        }


        Object.entries(
            autoSelections
        )
        .forEach(
            (
                [
                    elementId,
                    aliases
                ]
            ) => {

                autoSelectField(
                    getEl(
                        elementId
                    ),
                    fields,
                    aliases
                );
            }
        );


        setStatus(
            status,
            ""
        );

        return fields;

    } catch (error) {

        setStatus(
            status,
            error.message,
            "error"
        );

        throw error;
    }
}


// ============================================================
// RISK MAP
// ============================================================

const salmonellaFile =
    getEl(
        "spatial-salmonella-file"
    );

const salmonellaGeo =
    getEl(
        "spatial-salmonella-geography-column"
    );

const salmonellaCases =
    getEl(
        "spatial-salmonella-cases-column"
    );

const salmonellaPopulation =
    getEl(
        "spatial-salmonella-population-column"
    );

const salmonellaButton =
    getEl(
        "spatial-salmonella-generate-btn"
    );

const salmonellaStatus =
    getEl(
        "spatial-salmonella-status"
    );


function validateSalmonellaForm() {

    if (
        !salmonellaButton
    ) {
        return;
    }

    salmonellaButton.disabled =
        !(
            salmonellaFile
                ?.files?.length &&

            salmonellaGeo
                ?.value &&

            salmonellaCases
                ?.value &&

            salmonellaPopulation
                ?.value
        );
}


salmonellaFile
?.addEventListener(
    "change",
    async () => {

        const file =
            salmonellaFile
                .files?.[0];

        if (!file) {
            return;
        }

        const fileName =
            getEl(
                "spatial-salmonella-file-name"
            );

        if (
            fileName
        ) {

            fileName.textContent =
                file.name;
        }


        try {

            await inspectAnalysisFile(
                file,
                {
                    status:
                        salmonellaStatus,

                    geographySelect:
                        salmonellaGeo,

                    selects: [

                        {
                            select:
                                salmonellaGeo
                        },

                        {
                            select:
                                salmonellaCases
                        },

                        {
                            select:
                                salmonellaPopulation
                        }
                    ],

                    autoSelections: {

                        "spatial-salmonella-cases-column": [
                            "cases",
                            "salmonellacases",
                            "casecount"
                        ],

                        "spatial-salmonella-population-column": [
                            "population",
                            "pop",
                            "totalpopulation"
                        ]
                    }
                }
            );

        } finally {

            validateSalmonellaForm();
        }
    }
);


[
    salmonellaGeo,
    salmonellaCases,
    salmonellaPopulation
]
.forEach(
    element => {

        element
            ?.addEventListener(
                "change",
                validateSalmonellaForm
            );
    }
);


salmonellaButton
?.addEventListener(
    "click",
    async () => {

        const file =
            salmonellaFile
                ?.files?.[0];

        if (!file) {
            return;
        }

        salmonellaButton
            .disabled =
            true;

        setStatus(
            salmonellaStatus,
            "Calculating risk..."
        );


        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        formData.append(
            "geography_column",
            salmonellaGeo.value
        );

        formData.append(
            "cases_column",
            salmonellaCases.value
        );

        formData.append(
            "population_column",
            salmonellaPopulation
                .value
        );


        try {

            const response =
                await fetch(
                    SENSD_API
                        .salmonellaRisk,
                    {
                        method:
                            "POST",

                        body:
                            formData
                    }
                );

            const data =
                await readJsonResponse(
                    response
                );

            renderSalmonellaRiskLayer(
                data.geojson,
                file.name,
                data.dataset_id
            );

            setStatus(
                salmonellaStatus,
                "Risk Map created.",
                "success"
            );

        } catch (error) {

            setStatus(
                salmonellaStatus,
                error.message,
                "error"
            );

        } finally {

            validateSalmonellaForm();
        }
    }
);


// ============================================================
// RISK COLORS
// ============================================================

const salmonellaRiskColors = {

    "Very Low":
        "#d9f0a3",

    "Low":
        "#addd8e",

    "Moderate":
        "#78c679",

    "High":
        "#fdae61",

    "Very High":
        "#d73027",

    "No Data":
        "#bdbdbd"
};


// ============================================================
// RENDER RISK MAP
// ============================================================

function renderSalmonellaRiskLayer(
    geojson,
    filename,
    datasetId
) {

    const layerKey =
        uniqueLayerKey(
            "analysis_risk"
        );


    const legendRows = [

        [
            "Very High",
            salmonellaRiskColors[
                "Very High"
            ]
        ],

        [
            "High",
            salmonellaRiskColors[
                "High"
            ]
        ],

        [
            "Moderate",
            salmonellaRiskColors[
                "Moderate"
            ]
        ],

        [
            "Low",
            salmonellaRiskColors[
                "Low"
            ]
        ],

        [
            "Very Low",
            salmonellaRiskColors[
                "Very Low"
            ]
        ],

        [
            "No Data",
            salmonellaRiskColors[
                "No Data"
            ]
        ]
    ];


    const group =
        L.geoJSON(
            geojson,
            {
                style:
                    feature => {

                        const level =
                            feature
                                ?.properties
                                ?.sensd_risk_level ||
                            "No Data";

                        return {

                            color:
                                "#ffffff",

                            weight:
                                0.6,

                            opacity:
                                1,

                            fillColor:
                                salmonellaRiskColors[
                                    level
                                ] ||
                                salmonellaRiskColors[
                                    "No Data"
                                ],

                            fillOpacity:
                                0.82
                        };
                    },

                onEachFeature:
                    (
                        feature,
                        layer
                    ) => {

                        const p =
                            feature.properties ||
                            {};

                        layer.bindPopup(
                            `
                                <div class="sensd-popup">

                                    <strong>Risk Level:</strong>
                                    ${escapeHtml(
                                        p.sensd_risk_level ||
                                        "No Data"
                                    )}
                                    <br>

                                    <strong>Cases:</strong>
                                    ${formatNumber(
                                        p.sensd_salmonella_cases,
                                        0
                                    )}
                                    <br>

                                    <strong>Population:</strong>
                                    ${formatNumber(
                                        p.sensd_population,
                                        0
                                    )}
                                    <br>

                                    <strong>Rate per 100,000:</strong>
                                    ${formatNumber(
                                        p.sensd_salmonella_rate,
                                        2
                                    )}
                                    <br>

                                    <strong>Percentile:</strong>
                                    ${formatNumber(
                                        p.sensd_percentile,
                                        1
                                    )}

                                </div>
                            `
                        );
                    }
            }
        )
        .addTo(map);


    registerAnalysisLayer(
        layerKey,
        group,
        geojson,
        filename,
        datasetId,
        {
            type:
                "standard",

            title:
                "Risk Map",

            rows:
                legendRows
        }
    );


    showAnalysisLegend(
        "Risk Map",
        legendRows
    );


    safeFitBounds(
        group
    );
}


// ============================================================
// BIVARIATE ANALYSIS
// ============================================================

const bivariateFile =
    getEl(
        "spatial-bivariate-file"
    );

const bivariateGeo =
    getEl(
        "spatial-bivariate-geography-column"
    );

const bivariateState =
    getEl(
        "spatial-bivariate-state-column"
    );

const bivariateCounty =
    getEl(
        "spatial-bivariate-county-column"
    );

const bivariateX =
    getEl(
        "spatial-bivariate-x-column"
    );

const bivariateY =
    getEl(
        "spatial-bivariate-y-column"
    );

const bivariateButton =
    getEl(
        "spatial-bivariate-generate-btn"
    );

const bivariateStatus =
    getEl(
        "spatial-bivariate-status"
    );


function validateBivariateForm() {

    if (
        !bivariateButton
    ) {
        return;
    }

    bivariateButton.disabled =
        !(
            bivariateFile
                ?.files?.length &&

            bivariateGeo
                ?.value &&

            bivariateX
                ?.value &&

            bivariateY
                ?.value &&

            bivariateX.value !==
                bivariateY.value
        );
}


bivariateFile
?.addEventListener(
    "change",
    async () => {

        const file =
            bivariateFile
                .files?.[0];

        if (!file) {
            return;
        }

        const fileName =
            getEl(
                "spatial-bivariate-file-name"
            );

        if (
            fileName
        ) {

            fileName.textContent =
                file.name;
        }


        try {

            await inspectAnalysisFile(
                file,
                {
                    status:
                        bivariateStatus,

                    geographySelect:
                        bivariateGeo,

                    selects: [

                        {
                            select:
                                bivariateGeo
                        },

                        {
                            select:
                                bivariateState,

                            optional:
                                true
                        },

                        {
                            select:
                                bivariateCounty,

                            optional:
                                true
                        },

                        {
                            select:
                                bivariateX
                        },

                        {
                            select:
                                bivariateY
                        }
                    ]
                }
            );

        } finally {

            validateBivariateForm();
        }
    }
);


[
    bivariateGeo,
    bivariateState,
    bivariateCounty,
    bivariateX,
    bivariateY
]
.forEach(
    element => {

        element
            ?.addEventListener(
                "change",
                validateBivariateForm
            );
    }
);


bivariateButton
?.addEventListener(
    "click",
    async () => {

        const file =
            bivariateFile
                ?.files?.[0];

        if (!file) {
            return;
        }

        if (
            bivariateX.value ===
            bivariateY.value
        ) {

            setStatus(
                bivariateStatus,
                "Variable 1 and Variable 2 must be different.",
                "error"
            );

            return;
        }

        bivariateButton.disabled =
            true;

        setStatus(
            bivariateStatus,
            "Running Bivariate Analysis..."
        );


        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        formData.append(
            "geography_column",
            bivariateGeo.value
        );

        formData.append(
            "state_column",
            bivariateState.value
        );

        formData.append(
            "county_column",
            bivariateCounty.value
        );

        formData.append(
            "x_column",
            bivariateX.value
        );

        formData.append(
            "y_column",
            bivariateY.value
        );


        try {

            const response =
                await fetch(
                    SENSD_API
                        .bivariate,
                    {
                        method:
                            "POST",

                        body:
                            formData
                    }
                );

            const data =
                await readJsonResponse(
                    response
                );

            renderBivariateLayer(
                data.geojson,
                file.name,
                data.dataset_id,

                data.x_column ||
                bivariateX.value,

                data.y_column ||
                bivariateY.value
            );

            setStatus(
                bivariateStatus,
                "Bivariate Analysis completed.",
                "success"
            );

        } catch (error) {

            setStatus(
                bivariateStatus,
                error.message,
                "error"
            );

        } finally {

            validateBivariateForm();
        }
    }
);


// ============================================================
// BIVARIATE COLORS
// ============================================================

const bivariateColors = {

    x1y1:
        "#e8e8e8",

    x2y1:
        "#b5c0da",

    x3y1:
        "#6c83b5",

    x1y2:
        "#b8d6be",

    x2y2:
        "#90b2b3",

    x3y2:
        "#567994",

    x1y3:
        "#73ae80",

    x2y3:
        "#5a9178",

    x3y3:
        "#2a5a5b",

    no_data:
        "#bdbdbd"
};


// ============================================================
// RENDER BIVARIATE
// ============================================================

function renderBivariateLayer(
    geojson,
    filename,
    datasetId,
    xColumn,
    yColumn
) {

    const layerKey =
        uniqueLayerKey(
            "analysis_bivariate"
        );


    const bivariateLegend = {

        type:
            "bivariate-matrix",

        title:
            `${xColumn} × ${yColumn}`,

        xLabel:
            xColumn,

        yLabel:
            yColumn,

        colors: {

            x1y1:
                bivariateColors
                    .x1y1,

            x2y1:
                bivariateColors
                    .x2y1,

            x3y1:
                bivariateColors
                    .x3y1,

            x1y2:
                bivariateColors
                    .x1y2,

            x2y2:
                bivariateColors
                    .x2y2,

            x3y2:
                bivariateColors
                    .x3y2,

            x1y3:
                bivariateColors
                    .x1y3,

            x2y3:
                bivariateColors
                    .x2y3,

            x3y3:
                bivariateColors
                    .x3y3,

            no_data:
                bivariateColors
                    .no_data
        }
    };


    const group =
        L.geoJSON(
            geojson,
            {
                style:
                    feature => {

                        const category =
                            feature
                                ?.properties
                                ?.sensd_bivariate_class ||
                            "no_data";

                        return {

                            color:
                                "#ffffff",

                            weight:
                                0.6,

                            opacity:
                                1,

                            fillColor:
                                bivariateColors[
                                    category
                                ] ||
                                bivariateColors
                                    .no_data,

                            fillOpacity:
                                0.86
                        };
                    },

                onEachFeature:
                    (
                        feature,
                        layer
                    ) => {

                        const p =
                            feature.properties ||
                            {};

                        layer.bindPopup(
                            `
                                <div class="sensd-popup">

                                    <strong>State:</strong>
                                    ${escapeHtml(
                                        p.sensd_state_name ||
                                        "—"
                                    )}
                                    <br>

                                    <strong>County:</strong>
                                    ${escapeHtml(
                                        p.sensd_county_name ||
                                        "—"
                                    )}
                                    <br>

                                    <strong>${escapeHtml(
                                        xColumn
                                    )}:</strong>
                                    ${formatNumber(
                                        p.sensd_bivariate_x_value,
                                        3
                                    )}
                                    <br>

                                    <strong>${escapeHtml(
                                        yColumn
                                    )}:</strong>
                                    ${formatNumber(
                                        p.sensd_bivariate_y_value,
                                        3
                                    )}
                                    <br>

                                    <strong>Class:</strong>
                                    ${escapeHtml(
                                        p.sensd_bivariate_label ||
                                        "No Data"
                                    )}

                                </div>
                            `
                        );
                    }
            }
        )
        .addTo(map);


    registerAnalysisLayer(
        layerKey,
        group,
        geojson,
        filename,
        datasetId,
        bivariateLegend
    );


    showBivariateLegend(
        xColumn,
        yColumn,
        bivariateColors
    );


    safeFitBounds(
        group
    );
}


// ============================================================
// LOCAL MORAN
// ============================================================

const localMoranFile =
    getEl(
        "spatial-local-moran-file"
    );

const localMoranGeo =
    getEl(
        "spatial-local-moran-geography-column"
    );

const localMoranState =
    getEl(
        "spatial-local-moran-state-column"
    );

const localMoranCounty =
    getEl(
        "spatial-local-moran-county-column"
    );

const localMoranValue =
    getEl(
        "spatial-local-moran-value-column"
    );

const localMoranPermutations =
    getEl(
        "spatial-local-moran-permutations"
    );

const localMoranSignificance =
    getEl(
        "spatial-local-moran-significance"
    );

const localMoranSeed =
    getEl(
        "spatial-local-moran-seed"
    );

const localMoranButton =
    getEl(
        "spatial-local-moran-generate-btn"
    );

const localMoranStatus =
    getEl(
        "spatial-local-moran-status"
    );


function validateLocalMoranForm() {

    if (
        !localMoranButton
    ) {
        return;
    }

    const permutations =
        Number(
            localMoranPermutations
                ?.value
        );

    const significance =
        Number(
            localMoranSignificance
                ?.value
        );

    const seed =
        Number(
            localMoranSeed
                ?.value
        );

    localMoranButton.disabled =
        !(
            localMoranFile
                ?.files?.length &&

            localMoranGeo
                ?.value &&

            localMoranValue
                ?.value &&

            Number.isInteger(
                permutations
            ) &&

            permutations >=
                1 &&

            Number.isFinite(
                significance
            ) &&

            significance >
                0 &&

            significance <=
                1 &&

            Number.isInteger(
                seed
            )
        );
}


localMoranFile
?.addEventListener(
    "change",
    async () => {

        const file =
            localMoranFile
                .files?.[0];

        if (!file) {
            return;
        }

        const fileName =
            getEl(
                "spatial-local-moran-file-name"
            );

        if (
            fileName
        ) {

            fileName.textContent =
                file.name;
        }

        hideLocalMoranSummary();


        try {

            await inspectAnalysisFile(
                file,
                {
                    status:
                        localMoranStatus,

                    geographySelect:
                        localMoranGeo,

                    selects: [

                        {
                            select:
                                localMoranGeo
                        },

                        {
                            select:
                                localMoranState,

                            optional:
                                true
                        },

                        {
                            select:
                                localMoranCounty,

                            optional:
                                true
                        },

                        {
                            select:
                                localMoranValue
                        }
                    ]
                }
            );

        } finally {

            validateLocalMoranForm();
        }
    }
);


[
    localMoranGeo,
    localMoranState,
    localMoranCounty,
    localMoranValue,
    localMoranPermutations,
    localMoranSignificance,
    localMoranSeed
]
.forEach(
    element => {

        element
            ?.addEventListener(
                "change",
                validateLocalMoranForm
            );

        element
            ?.addEventListener(
                "input",
                validateLocalMoranForm
            );
    }
);


localMoranButton
?.addEventListener(
    "click",
    async () => {

        const file =
            localMoranFile
                ?.files?.[0];

        if (!file) {

            setStatus(
                localMoranStatus,
                "Select a polygon GeoJSON dataset.",
                "error"
            );

            return;
        }

        validateLocalMoranForm();

        if (
            localMoranButton
                .disabled
        ) {

            setStatus(
                localMoranStatus,
                "Complete the required analysis settings.",
                "error"
            );

            return;
        }

        localMoranButton.disabled =
            true;

        hideLocalMoranSummary();

        setStatus(
            localMoranStatus,
            "Running Local Moran's I..."
        );


        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        formData.append(
            "geography_column",
            localMoranGeo.value
        );

        formData.append(
            "value_column",
            localMoranValue.value
        );

        formData.append(
            "state_column",
            localMoranState.value
        );

        formData.append(
            "county_column",
            localMoranCounty.value
        );

        formData.append(
            "permutations",
            localMoranPermutations
                .value
        );

        formData.append(
            "significance_level",
            localMoranSignificance
                .value
        );

        formData.append(
            "seed",
            localMoranSeed.value
        );


        try {

            const response =
                await fetch(
                    SENSD_API
                        .localMoran,
                    {
                        method:
                            "POST",

                        body:
                            formData
                    }
                );

            const data =
                await readJsonResponse(
                    response
                );

            renderLocalMoranLayer(
                data.geojson,

                data.filename ||
                file.name,

                data.dataset_id,

                data.value_column ||
                localMoranValue.value
            );

            updateLocalMoranSummary(
                data.summary ||
                {}
            );

            setStatus(
                localMoranStatus,
                "Hotspot Analysis completed.",
                "success"
            );

        } catch (error) {

            console.error(
                "Local Moran error:",
                error
            );

            setStatus(
                localMoranStatus,
                error.message,
                "error"
            );

        } finally {

            validateLocalMoranForm();
        }
    }
);


const localMoranColors = {

    HH:
        "#e31a1c",

    LL:
        "#1f78b4",

    HL:
        "#fb9a99",

    LH:
        "#a6cee3",

    NS:
        "#d9d9d9",

    ISLAND:
        "#969696",

    NO_DATA:
        "#f7f7f7"
};


function localMoranColor(
    code
) {

    return (
        localMoranColors[
            code
        ] ||
        localMoranColors
            .NO_DATA
    );
}


function renderLocalMoranLayer(
    geojson,
    filename,
    datasetId,
    valueColumn
) {

    const layerKey =
        uniqueLayerKey(
            "analysis_local_moran"
        );


    const legendRows = [

        [
            "Hot Spot — High-High",
            localMoranColors.HH
        ],

        [
            "Cold Spot — Low-Low",
            localMoranColors.LL
        ],

        [
            "High-Low Spatial Outlier",
            localMoranColors.HL
        ],

        [
            "Low-High Spatial Outlier",
            localMoranColors.LH
        ],

        [
            "Not Significant",
            localMoranColors.NS
        ],

        [
            "No Neighbors",
            localMoranColors.ISLAND
        ],

        [
            "No Data",
            localMoranColors.NO_DATA
        ]
    ];


    let group;


    group =
        L.geoJSON(
            geojson,
            {
                style:
                    feature => {

                        const p =
                            feature.properties ||
                            {};

                        const code =
                            p.sensd_local_moran_cluster_code ||
                            "NO_DATA";

                        return {

                            color:
                                "#ffffff",

                            weight:
                                0.7,

                            opacity:
                                1,

                            fillColor:
                                localMoranColor(
                                    code
                                ),

                            fillOpacity:
                                code === "NS"
                                    ? 0.55
                                    : 0.88
                        };
                    },

                onEachFeature:
                    (
                        feature,
                        layer
                    ) => {

                        const p =
                            feature.properties ||
                            {};

                        layer.bindPopup(
                            buildLocalMoranPopup(
                                p,
                                valueColumn
                            )
                        );

                        layer.on(
                            "mouseover",
                            function () {

                                this.setStyle(
                                    {
                                        weight:
                                            2,

                                        color:
                                            "#333333"
                                    }
                                );
                            }
                        );

                        layer.on(
                            "mouseout",
                            function () {

                                group.resetStyle(
                                    this
                                );
                            }
                        );
                    }
            }
        )
        .addTo(map);


    registerAnalysisLayer(
        layerKey,
        group,
        geojson,
        filename,
        datasetId,
        {
            type:
                "standard",

            title:
                "Hotspot Analysis — Local Moran's I",

            rows:
                legendRows
        }
    );


    showAnalysisLegend(
        "Hotspot Analysis — Local Moran's I",
        legendRows
    );


    safeFitBounds(
        group
    );
}


function buildLocalMoranPopup(
    properties,
    valueColumn
) {

    return `
        <div class="sensd-popup">

            <div
                style="
                    font-weight:700;
                    margin-bottom:6px;
                "
            >
                Hotspot Analysis
            </div>

            <strong>State:</strong>
            ${escapeHtml(
                properties
                    .sensd_state_name ||
                "—"
            )}
            <br>

            <strong>County:</strong>
            ${escapeHtml(
                properties
                    .sensd_county_name ||
                "—"
            )}
            <br>

            <strong>${escapeHtml(
                valueColumn ||
                "Analysis Variable"
            )}:</strong>
            ${formatNumber(
                properties
                    .sensd_local_moran_value,
                4
            )}
            <br>

            <strong>Local Moran's I:</strong>
            ${formatNumber(
                properties
                    .sensd_local_moran_i,
                5
            )}
            <br>

            <strong>Pseudo p-value:</strong>
            ${formatNumber(
                properties
                    .sensd_local_moran_p,
                4
            )}
            <br>

            <strong>Neighbors:</strong>
            ${formatNumber(
                properties
                    .sensd_local_moran_neighbor_count,
                0
            )}
            <br>

            <strong>Cluster:</strong>
            ${escapeHtml(
                properties
                    .sensd_local_moran_cluster_label ||
                "No Data"
            )}
            <br>

            <strong>Interpretation:</strong>
            ${escapeHtml(
                properties
                    .sensd_local_moran_interpretation ||
                "No Data"
            )}
            <br>

            <strong>Significant:</strong>
            ${
                properties
                    .sensd_local_moran_significant
                    ? "Yes"
                    : "No"
            }

        </div>
    `;
}


function updateLocalMoranSummary(
    summary
) {

    const values = {

        "spatial-local-moran-hotspot-count":
            summary.hot_spot_count ??
            summary.high_high_count,

        "spatial-local-moran-coldspot-count":
            summary.cold_spot_count ??
            summary.low_low_count,

        "spatial-local-moran-hl-count":
            summary.high_value_outlier_count ??
            summary.high_low_count,

        "spatial-local-moran-lh-count":
            summary.low_value_outlier_count ??
            summary.low_high_count,

        "spatial-local-moran-significant-count":
            summary.significant_count,

        "spatial-local-moran-ns-count":
            summary.not_significant_count,

        "spatial-local-moran-island-count":
            summary.island_count
    };


    Object.entries(
        values
    )
    .forEach(
        (
            [
                id,
                value
            ]
        ) => {

            const element =
                getEl(id);

            if (
                element
            ) {

                element.textContent =
                    formatNumber(
                        value,
                        0
                    );
            }
        }
    );


    const meanNeighbors =
        getEl(
            "spatial-local-moran-mean-neighbors"
        );

    if (
        meanNeighbors
    ) {

        meanNeighbors.textContent =
            formatNumber(
                summary.mean_neighbors,
                2
            );
    }


    const summaryPanel =
        getEl(
            "spatial-local-moran-summary"
        );

    if (
        summaryPanel
    ) {

        summaryPanel.style.display =
            "block";
    }
}


function hideLocalMoranSummary() {

    const panel =
        getEl(
            "spatial-local-moran-summary"
        );

    if (
        panel
    ) {

        panel.style.display =
            "none";
    }
}


// ============================================================
// SPATIAL ASSOCIATION
// ============================================================

const spatialAssociationFile =
    getEl(
        "spatial-association-file"
    );

const spatialAssociationGeo =
    getEl(
        "spatial-association-geography-column"
    );

const spatialAssociationState =
    getEl(
        "spatial-association-state-column"
    );

const spatialAssociationCounty =
    getEl(
        "spatial-association-county-column"
    );

const spatialAssociationX =
    getEl(
        "spatial-association-x-column"
    );

const spatialAssociationY =
    getEl(
        "spatial-association-y-column"
    );

const spatialAssociationPermutations =
    getEl(
        "spatial-association-permutations"
    );

const spatialAssociationSignificance =
    getEl(
        "spatial-association-significance"
    );

const spatialAssociationSeed =
    getEl(
        "spatial-association-seed"
    );

const spatialAssociationButton =
    getEl(
        "spatial-association-generate-btn"
    );

const spatialAssociationStatus =
    getEl(
        "spatial-association-status"
    );


function validateSpatialAssociationForm() {

    if (
        !spatialAssociationButton
    ) {
        return;
    }

    const permutations =
        Number(
            spatialAssociationPermutations
                ?.value
        );

    const significance =
        Number(
            spatialAssociationSignificance
                ?.value
        );

    const seed =
        Number(
            spatialAssociationSeed
                ?.value
        );

    spatialAssociationButton
        .disabled =
        !(
            spatialAssociationFile
                ?.files?.length &&

            spatialAssociationGeo
                ?.value &&

            spatialAssociationX
                ?.value &&

            spatialAssociationY
                ?.value &&

            spatialAssociationX
                .value !==
            spatialAssociationY
                .value &&

            Number.isInteger(
                permutations
            ) &&

            permutations >=
                1 &&

            Number.isFinite(
                significance
            ) &&

            significance >
                0 &&

            significance <=
                1 &&

            Number.isInteger(
                seed
            )
        );
}


spatialAssociationFile
?.addEventListener(
    "change",
    async () => {

        const file =
            spatialAssociationFile
                .files?.[0];

        if (!file) {
            return;
        }

        const fileName =
            getEl(
                "spatial-association-file-name"
            );

        if (
            fileName
        ) {

            fileName.textContent =
                file.name;
        }

        hideSpatialAssociationSummary();


        try {

            await inspectAnalysisFile(
                file,
                {
                    status:
                        spatialAssociationStatus,

                    geographySelect:
                        spatialAssociationGeo,

                    selects: [

                        {
                            select:
                                spatialAssociationGeo
                        },

                        {
                            select:
                                spatialAssociationState,

                            optional:
                                true
                        },

                        {
                            select:
                                spatialAssociationCounty,

                            optional:
                                true
                        },

                        {
                            select:
                                spatialAssociationX
                        },

                        {
                            select:
                                spatialAssociationY
                        }
                    ]
                }
            );

        } finally {

            validateSpatialAssociationForm();
        }
    }
);


[
    spatialAssociationGeo,
    spatialAssociationState,
    spatialAssociationCounty,
    spatialAssociationX,
    spatialAssociationY,
    spatialAssociationPermutations,
    spatialAssociationSignificance,
    spatialAssociationSeed
]
.forEach(
    element => {

        element
            ?.addEventListener(
                "change",
                validateSpatialAssociationForm
            );

        element
            ?.addEventListener(
                "input",
                validateSpatialAssociationForm
            );
    }
);


spatialAssociationButton
?.addEventListener(
    "click",
    async () => {

        const file =
            spatialAssociationFile
                ?.files?.[0];

        if (!file) {

            setStatus(
                spatialAssociationStatus,
                "Select a polygon GeoJSON dataset.",
                "error"
            );

            return;
        }

        if (
            spatialAssociationX
                .value ===
            spatialAssociationY
                .value
        ) {

            setStatus(
                spatialAssociationStatus,
                "Variable X and Variable Y must be different.",
                "error"
            );

            return;
        }

        validateSpatialAssociationForm();

        if (
            spatialAssociationButton
                .disabled
        ) {

            setStatus(
                spatialAssociationStatus,
                "Complete the required analysis settings.",
                "error"
            );

            return;
        }

        hideSpatialAssociationSummary();

        spatialAssociationButton
            .disabled =
            true;

        setStatus(
            spatialAssociationStatus,
            "Running Global and Local Bivariate Moran's I..."
        );


        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        formData.append(
            "geography_column",
            spatialAssociationGeo
                .value
        );

        formData.append(
            "state_column",
            spatialAssociationState
                .value
        );

        formData.append(
            "county_column",
            spatialAssociationCounty
                .value
        );

        formData.append(
            "x_column",
            spatialAssociationX
                .value
        );

        formData.append(
            "y_column",
            spatialAssociationY
                .value
        );

        formData.append(
            "permutations",
            spatialAssociationPermutations
                .value
        );

        formData.append(
            "significance_level",
            spatialAssociationSignificance
                .value
        );

        formData.append(
            "seed",
            spatialAssociationSeed
                .value
        );


        try {

            const response =
                await fetch(
                    SENSD_API
                        .spatialAssociation,
                    {
                        method:
                            "POST",

                        body:
                            formData
                    }
                );

            const data =
                await readJsonResponse(
                    response
                );

            renderSpatialAssociationLayer(
                data.geojson,

                data.filename ||
                file.name,

                data.dataset_id,

                data.x_column ||
                spatialAssociationX
                    .value,

                data.y_column ||
                spatialAssociationY
                    .value
            );

            updateSpatialAssociationSummary(
                data.summary ||
                {}
            );

            setStatus(
                spatialAssociationStatus,
                "Spatial Association Analysis completed.",
                "success"
            );

        } catch (error) {

            console.error(
                "Spatial Association error:",
                error
            );

            setStatus(
                spatialAssociationStatus,
                error.message,
                "error"
            );

        } finally {

            validateSpatialAssociationForm();
        }
    }
);


const spatialAssociationColors = {

    HH:
        "#d7191c",

    LL:
        "#2c7bb6",

    HL:
        "#fdae61",

    LH:
        "#abd9e9",

    NS:
        "#d9d9d9",

    ISLAND:
        "#969696",

    NO_DATA:
        "#f7f7f7"
};


function spatialAssociationColor(
    code
) {

    return (
        spatialAssociationColors[
            code
        ] ||
        spatialAssociationColors
            .NO_DATA
    );
}


function renderSpatialAssociationLayer(
    geojson,
    filename,
    datasetId,
    xColumn,
    yColumn
) {

    const layerKey =
        uniqueLayerKey(
            "analysis_spatial_association"
        );


    const legendRows = [

        [
            "High X / High Neighboring Y",
            spatialAssociationColors.HH
        ],

        [
            "Low X / Low Neighboring Y",
            spatialAssociationColors.LL
        ],

        [
            "High X / Low Neighboring Y",
            spatialAssociationColors.HL
        ],

        [
            "Low X / High Neighboring Y",
            spatialAssociationColors.LH
        ],

        [
            "Not Significant",
            spatialAssociationColors.NS
        ],

        [
            "No Neighbors",
            spatialAssociationColors.ISLAND
        ],

        [
            "No Data",
            spatialAssociationColors.NO_DATA
        ]
    ];


    let group;


    group =
        L.geoJSON(
            geojson,
            {
                style:
                    feature => {

                        const p =
                            feature.properties ||
                            {};

                        const code =
                            p.sensd_spatial_assoc_cluster_code ||
                            "NO_DATA";

                        return {

                            color:
                                "#ffffff",

                            weight:
                                0.7,

                            opacity:
                                1,

                            fillColor:
                                spatialAssociationColor(
                                    code
                                ),

                            fillOpacity:
                                code ===
                                "NS"
                                    ? 0.55
                                    : 0.88
                        };
                    },

                onEachFeature:
                    (
                        feature,
                        layer
                    ) => {

                        const p =
                            feature.properties ||
                            {};

                        layer.bindPopup(
                            buildSpatialAssociationPopup(
                                p,
                                xColumn,
                                yColumn
                            )
                        );

                        layer.on(
                            "mouseover",
                            function () {

                                this.setStyle(
                                    {
                                        weight:
                                            2,

                                        color:
                                            "#333333"
                                    }
                                );
                            }
                        );

                        layer.on(
                            "mouseout",
                            function () {

                                group.resetStyle(
                                    this
                                );
                            }
                        );
                    }
            }
        )
        .addTo(map);


    registerAnalysisLayer(
        layerKey,
        group,
        geojson,
        filename,
        datasetId,
        {
            type:
                "standard",

            title:
                `Spatial Association: ${xColumn} → neighboring ${yColumn}`,

            rows:
                legendRows
        }
    );


    showAnalysisLegend(
        `Spatial Association: ${xColumn} → neighboring ${yColumn}`,
        legendRows
    );


    safeFitBounds(
        group
    );
}


function buildSpatialAssociationPopup(
    properties,
    xColumn,
    yColumn
) {

    return `
        <div class="sensd-popup">

            <div
                style="
                    font-weight:700;
                    margin-bottom:6px;
                "
            >
                Spatial Association Analysis
            </div>

            <strong>State:</strong>
            ${escapeHtml(
                properties
                    .sensd_state_name ||
                "—"
            )}
            <br>

            <strong>County:</strong>
            ${escapeHtml(
                properties
                    .sensd_county_name ||
                "—"
            )}
            <br>

            <strong>${escapeHtml(
                xColumn
            )}:</strong>
            ${formatNumber(
                properties
                    .sensd_spatial_assoc_x_value,
                4
            )}
            <br>

            <strong>${escapeHtml(
                yColumn
            )}:</strong>
            ${formatNumber(
                properties
                    .sensd_spatial_assoc_y_value,
                4
            )}
            <br>

            <strong>Spatial lag of ${escapeHtml(
                yColumn
            )}:</strong>
            ${formatNumber(
                properties
                    .sensd_spatial_assoc_lag_y,
                4
            )}
            <br>

            <strong>Local Bivariate Moran's I:</strong>
            ${formatNumber(
                properties
                    .sensd_spatial_assoc_local_i,
                5
            )}
            <br>

            <strong>Pseudo p-value:</strong>
            ${formatNumber(
                properties
                    .sensd_spatial_assoc_p,
                4
            )}
            <br>

            <strong>Neighbors:</strong>
            ${formatNumber(
                properties
                    .sensd_spatial_assoc_neighbor_count,
                0
            )}
            <br>

            <strong>Local Association:</strong>
            ${escapeHtml(
                properties
                    .sensd_spatial_assoc_cluster_label ||
                "No Data"
            )}
            <br>

            <strong>Interpretation:</strong>
            ${escapeHtml(
                properties
                    .sensd_spatial_assoc_interpretation ||
                "No Data"
            )}
            <br>

            <strong>Significant:</strong>
            ${
                properties
                    .sensd_spatial_assoc_significant
                    ? "Yes"
                    : "No"
            }

        </div>
    `;
}


function updateSpatialAssociationSummary(
    summary
) {

    const mappings = {

        "spatial-association-global-i":
            [
                summary.global_bivariate_moran_i,
                5
            ],

        "spatial-association-global-p":
            [
                summary.global_pseudo_p_value,
                4
            ],

        "spatial-association-global-z":
            [
                summary.global_permutation_z_score,
                4
            ],

        "spatial-association-pearson":
            [
                summary.same_location_pearson_correlation,
                4
            ],

        "spatial-association-hh-count":
            [
                summary.high_high_count,
                0
            ],

        "spatial-association-ll-count":
            [
                summary.low_low_count,
                0
            ],

        "spatial-association-hl-count":
            [
                summary.high_low_count,
                0
            ],

        "spatial-association-lh-count":
            [
                summary.low_high_count,
                0
            ],

        "spatial-association-significant-count":
            [
                summary.significant_count,
                0
            ],

        "spatial-association-ns-count":
            [
                summary.not_significant_count,
                0
            ],

        "spatial-association-island-count":
            [
                summary.island_count,
                0
            ],

        "spatial-association-mean-neighbors":
            [
                summary.mean_neighbors,
                2
            ]
    };


    Object.entries(
        mappings
    )
    .forEach(
        (
            [
                id,
                [
                    value,
                    decimals
                ]
            ]
        ) => {

            const element =
                getEl(
                    id
                );

            if (
                element
            ) {

                element.textContent =
                    formatNumber(
                        value,
                        decimals
                    );
            }
        }
    );


    const direction =
        getEl(
            "spatial-association-global-direction"
        );

    if (
        direction
    ) {

        direction.textContent =
            summary.global_direction ||
            "—";
    }


    const significant =
        getEl(
            "spatial-association-global-significant"
        );

    if (
        significant
    ) {

        significant.textContent =
            summary
                .global_significant ===
            true

                ? "Yes"

                : (
                    summary
                        .global_significant ===
                    false

                        ? "No"
                        : "—"
                );
    }


    const interpretation =
        getEl(
            "spatial-association-global-interpretation"
        );

    if (
        interpretation
    ) {

        interpretation.textContent =
            summary
                .global_interpretation ||
            "";
    }


    const panel =
        getEl(
            "spatial-association-summary"
        );

    if (
        panel
    ) {

        panel.style.display =
            "block";
    }
}


function hideSpatialAssociationSummary() {

    const panel =
        getEl(
            "spatial-association-summary"
        );

    if (
        panel
    ) {

        panel.style.display =
            "none";
    }
}


// ============================================================
// SPATIAL REGRESSION
// ============================================================

const spatialRegressionFile =
    getEl(
        "spatial-regression-file"
    );

const spatialRegressionGeo =
    getEl(
        "spatial-regression-geography-column"
    );

const spatialRegressionState =
    getEl(
        "spatial-regression-state-column"
    );

const spatialRegressionCounty =
    getEl(
        "spatial-regression-county-column"
    );

const spatialRegressionDependent =
    getEl(
        "spatial-regression-dependent-column"
    );

const spatialRegressionIndependent =
    getEl(
        "spatial-regression-independent-columns"
    );

const spatialRegressionSignificance =
    getEl(
        "spatial-regression-significance"
    );

const spatialRegressionButton =
    getEl(
        "spatial-regression-generate-btn"
    );

const spatialRegressionStatus =
    getEl(
        "spatial-regression-status"
    );


function updateSpatialRegressionSelectedVariables() {

    const selected =
        getSelectedOptions(
            spatialRegressionIndependent
        );

    const display =
        getEl(
            "spatial-regression-selected-x"
        );

    if (!display) {
        return;
    }

    if (
        !selected.length
    ) {

        display.textContent =
            "No independent variables selected.";

        return;
    }

    display.textContent =
        `Selected: ${selected.join(", ")}`;
}


function validateSpatialRegressionForm() {

    if (
        !spatialRegressionButton
    ) {
        return;
    }

    const selectedIndependent =
        getSelectedOptions(
            spatialRegressionIndependent
        );

    const dependent =
        spatialRegressionDependent
            ?.value ||
        "";

    const significance =
        Number(
            spatialRegressionSignificance
                ?.value
        );

    const containsDependent =
        selectedIndependent
            .includes(
                dependent
            );

    spatialRegressionButton
        .disabled =
        !(
            spatialRegressionFile
                ?.files?.length &&

            spatialRegressionGeo
                ?.value &&

            dependent &&

            selectedIndependent
                .length >=
                1 &&

            !containsDependent &&

            Number.isFinite(
                significance
            ) &&

            significance >
                0 &&

            significance <=
                1
        );
}


spatialRegressionFile
?.addEventListener(
    "change",
    async () => {

        const file =
            spatialRegressionFile
                .files?.[0];

        if (!file) {
            return;
        }

        const fileName =
            getEl(
                "spatial-regression-file-name"
            );

        if (
            fileName
        ) {

            fileName.textContent =
                file.name;
        }

        hideSpatialRegressionSummary();

        setStatus(
            spatialRegressionStatus,
            "Reading fields..."
        );


        try {

            const formData =
                new FormData();

            formData.append(
                "file",
                file
            );

            const response =
                await fetch(
                    SENSD_API
                        .inspectColumns,
                    {
                        method:
                            "POST",

                        body:
                            formData
                    }
                );

            const data =
                await readJsonResponse(
                    response
                );

            const fields =
                data.columns ||
                [];

            populateSelect(
                spatialRegressionGeo,
                fields,
                {
                    placeholder:
                        "— select unique geography field —"
                }
            );

            populateSelect(
                spatialRegressionState,
                fields,
                {
                    optional:
                        true
                }
            );

            populateSelect(
                spatialRegressionCounty,
                fields,
                {
                    optional:
                        true
                }
            );

            populateSelect(
                spatialRegressionDependent,
                fields,
                {
                    placeholder:
                        "— select numeric field —"
                }
            );

            populateMultiSelect(
                spatialRegressionIndependent,
                fields
            );

            autoSelectField(
                spatialRegressionGeo,
                fields,
                [
                    "geoid",
                    "geography",
                    "id",
                    "fid",
                    "name",
                    "region",
                    "area"
                ]
            );

            setStatus(
                spatialRegressionStatus,
                ""
            );

            updateSpatialRegressionSelectedVariables();

            validateSpatialRegressionForm();

        } catch (error) {

            setStatus(
                spatialRegressionStatus,
                error.message,
                "error"
            );
        }
    }
);


[
    spatialRegressionGeo,
    spatialRegressionState,
    spatialRegressionCounty,
    spatialRegressionDependent,
    spatialRegressionSignificance
]
.forEach(
    element => {

        element
            ?.addEventListener(
                "change",
                validateSpatialRegressionForm
            );
    }
);


spatialRegressionIndependent
?.addEventListener(
    "change",
    () => {

        updateSpatialRegressionSelectedVariables();

        validateSpatialRegressionForm();
    }
);


spatialRegressionDependent
?.addEventListener(
    "change",
    () => {

        const dependent =
            spatialRegressionDependent
                .value;

        Array.from(
            spatialRegressionIndependent
                ?.options ||
            []
        )
        .forEach(
            option => {

                if (
                    option.value ===
                    dependent
                ) {

                    option.selected =
                        false;
                }
            }
        );

        updateSpatialRegressionSelectedVariables();

        validateSpatialRegressionForm();
    }
);


spatialRegressionButton
?.addEventListener(
    "click",
    async () => {

        const file =
            spatialRegressionFile
                ?.files?.[0];

        if (!file) {

            setStatus(
                spatialRegressionStatus,
                "Select a polygon GeoJSON dataset.",
                "error"
            );

            return;
        }


        const independentVariables =
            getSelectedOptions(
                spatialRegressionIndependent
            );


        if (
            !independentVariables
                .length
        ) {

            setStatus(
                spatialRegressionStatus,
                "Select at least one independent variable.",
                "error"
            );

            return;
        }


        if (
            independentVariables
                .includes(
                    spatialRegressionDependent
                        .value
                )
        ) {

            setStatus(
                spatialRegressionStatus,
                "The dependent variable cannot also be an independent variable.",
                "error"
            );

            return;
        }


        validateSpatialRegressionForm();


        if (
            spatialRegressionButton
                .disabled
        ) {

            setStatus(
                spatialRegressionStatus,
                "Complete the required regression settings.",
                "error"
            );

            return;
        }


        hideSpatialRegressionSummary();

        spatialRegressionButton
            .disabled =
            true;

        setStatus(
            spatialRegressionStatus,
            "Running OLS regression and spatial diagnostics..."
        );


        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        formData.append(
            "geography_column",
            spatialRegressionGeo
                .value
        );

        formData.append(
            "state_column",
            spatialRegressionState
                .value
        );

        formData.append(
            "county_column",
            spatialRegressionCounty
                .value
        );

        formData.append(
            "dependent_column",
            spatialRegressionDependent
                .value
        );


        independentVariables
            .forEach(
                variable => {

                    formData.append(
                        "independent_columns",
                        variable
                    );
                }
            );


        formData.append(
            "significance_level",
            spatialRegressionSignificance
                .value
        );


        try {

            const response =
                await fetch(
                    SENSD_API
                        .spatialRegression,
                    {
                        method:
                            "POST",

                        body:
                            formData
                    }
                );

            const data =
                await readJsonResponse(
                    response
                );

            renderSpatialRegressionLayer(
                data.geojson,

                data.filename ||
                file.name,

                data.dataset_id,

                data.dependent_column ||
                spatialRegressionDependent
                    .value
            );

            updateSpatialRegressionSummary(
                data.summary ||
                {},

                data.coefficients ||
                []
            );

            setStatus(
                spatialRegressionStatus,
                "Spatial Regression Analysis completed.",
                "success"
            );

        } catch (error) {

            console.error(
                "Spatial Regression error:",
                error
            );

            setStatus(
                spatialRegressionStatus,
                error.message,
                "error"
            );

        } finally {

            validateSpatialRegressionForm();
        }
    }
);


const spatialRegressionResidualColors = {

    strongPositive:
        "#b2182b",

    moderatePositive:
        "#ef8a62",

    slightPositive:
        "#fddbc7",

    nearZero:
        "#f7f7f7",

    slightNegative:
        "#d1e5f0",

    moderateNegative:
        "#67a9cf",

    strongNegative:
        "#2166ac",

    noData:
        "#bdbdbd"
};


function classifyStandardizedResidual(
    value
) {

    const residual =
        Number(
            value
        );

    if (
        !Number.isFinite(
            residual
        )
    ) {

        return {

            label:
                "No Data",

            color:
                spatialRegressionResidualColors
                    .noData
        };
    }

    if (
        residual >=
        2
    ) {

        return {

            label:
                "≥ +2.0",

            color:
                spatialRegressionResidualColors
                    .strongPositive
        };
    }

    if (
        residual >=
        1
    ) {

        return {

            label:
                "+1.0 to < +2.0",

            color:
                spatialRegressionResidualColors
                    .moderatePositive
        };
    }

    if (
        residual >=
        0.25
    ) {

        return {

            label:
                "+0.25 to < +1.0",

            color:
                spatialRegressionResidualColors
                    .slightPositive
        };
    }

    if (
        residual >
        -0.25
    ) {

        return {

            label:
                "-0.25 to +0.25",

            color:
                spatialRegressionResidualColors
                    .nearZero
        };
    }

    if (
        residual >
        -1
    ) {

        return {

            label:
                "> -1.0 to -0.25",

            color:
                spatialRegressionResidualColors
                    .slightNegative
        };
    }

    if (
        residual >
        -2
    ) {

        return {

            label:
                "> -2.0 to -1.0",

            color:
                spatialRegressionResidualColors
                    .moderateNegative
        };
    }

    return {

        label:
            "≤ -2.0",

        color:
            spatialRegressionResidualColors
                .strongNegative
    };
}


function renderSpatialRegressionLayer(
    geojson,
    filename,
    datasetId,
    dependentColumn
) {

    const layerKey =
        uniqueLayerKey(
            "analysis_spatial_regression"
        );


    const legendRows = [

        [
            "≥ +2.0",
            spatialRegressionResidualColors
                .strongPositive
        ],

        [
            "+1.0 to < +2.0",
            spatialRegressionResidualColors
                .moderatePositive
        ],

        [
            "+0.25 to < +1.0",
            spatialRegressionResidualColors
                .slightPositive
        ],

        [
            "-0.25 to +0.25",
            spatialRegressionResidualColors
                .nearZero
        ],

        [
            "> -1.0 to -0.25",
            spatialRegressionResidualColors
                .slightNegative
        ],

        [
            "> -2.0 to -1.0",
            spatialRegressionResidualColors
                .moderateNegative
        ],

        [
            "≤ -2.0",
            spatialRegressionResidualColors
                .strongNegative
        ],

        [
            "No Data",
            spatialRegressionResidualColors
                .noData
        ]
    ];


    let group;


    group =
        L.geoJSON(
            geojson,
            {
                style:
                    feature => {

                        const p =
                            feature.properties ||
                            {};

                        const classification =
                            classifyStandardizedResidual(
                                p.sensd_regression_standardized_residual
                            );

                        return {

                            color:
                                "#ffffff",

                            weight:
                                0.7,

                            opacity:
                                1,

                            fillColor:
                                classification
                                    .color,

                            fillOpacity:
                                p.sensd_regression_included ===
                                false
                                    ? 0.45
                                    : 0.86
                        };
                    },

                onEachFeature:
                    (
                        feature,
                        layer
                    ) => {

                        const p =
                            feature.properties ||
                            {};

                        layer.bindPopup(
                            buildSpatialRegressionPopup(
                                p,
                                dependentColumn
                            )
                        );

                        layer.on(
                            "mouseover",
                            function () {

                                this.setStyle(
                                    {
                                        weight:
                                            2,

                                        color:
                                            "#333333"
                                    }
                                );
                            }
                        );

                        layer.on(
                            "mouseout",
                            function () {

                                group.resetStyle(
                                    this
                                );
                            }
                        );
                    }
            }
        )
        .addTo(map);


    registerAnalysisLayer(
        layerKey,
        group,
        geojson,
        filename,
        datasetId,
        {
            type:
                "standard",

            title:
                "Spatial Regression — Standardized Residuals",

            rows:
                legendRows
        }
    );


    showAnalysisLegend(
        "Spatial Regression — Standardized Residuals",
        legendRows
    );


    safeFitBounds(
        group
    );
}


function buildSpatialRegressionPopup(
    properties,
    dependentColumn
) {

    const standardizedResidual =
        properties
            .sensd_regression_standardized_residual;

    const classification =
        classifyStandardizedResidual(
            standardizedResidual
        );

    return `
        <div class="sensd-popup">

            <div
                style="
                    font-weight:700;
                    margin-bottom:6px;
                "
            >
                Spatial Regression
            </div>

            <strong>State:</strong>
            ${escapeHtml(
                properties
                    .sensd_state_name ||
                "—"
            )}
            <br>

            <strong>County:</strong>
            ${escapeHtml(
                properties
                    .sensd_county_name ||
                "—"
            )}
            <br>

            <strong>Dependent Variable:</strong>
            ${escapeHtml(
                dependentColumn ||
                "—"
            )}
            <br>

            <strong>Observed:</strong>
            ${formatNumber(
                properties
                    .sensd_regression_observed,
                4
            )}
            <br>

            <strong>Predicted:</strong>
            ${formatNumber(
                properties
                    .sensd_regression_predicted,
                4
            )}
            <br>

            <strong>Residual:</strong>
            ${formatNumber(
                properties
                    .sensd_regression_residual,
                4
            )}
            <br>

            <strong>Standardized Residual:</strong>
            ${formatNumber(
                standardizedResidual,
                4
            )}
            <br>

            <strong>Residual Class:</strong>
            ${escapeHtml(
                classification.label
            )}
            <br>

            <strong>Neighbors:</strong>
            ${formatNumber(
                properties
                    .sensd_regression_neighbor_count,
                0
            )}
            <br>

            <strong>Included in Model:</strong>
            ${
                properties
                    .sensd_regression_included
                    ? "Yes"
                    : "No"
            }

        </div>
    `;
}


function updateSpatialRegressionSummary(
    summary,
    coefficients
) {

    const modelValues = {

        "spatial-regression-r2":
            [
                summary.r_squared,
                4
            ],

        "spatial-regression-adjusted-r2":
            [
                summary.adjusted_r_squared,
                4
            ],

        "spatial-regression-aic":
            [
                summary.aic,
                3
            ],

        "spatial-regression-bic":
            [
                summary.schwarz_bic,
                3
            ],

        "spatial-regression-observations":
            [
                summary.observations,
                0
            ],

        "spatial-regression-predictor-count":
            [
                summary.predictor_count,
                0
            ],

        "spatial-regression-log-likelihood":
            [
                summary.log_likelihood,
                3
            ],

        "spatial-regression-rss":
            [
                summary.residual_sum_squares,
                3
            ],

        "spatial-regression-moran-i":
            [
                summary.residual_moran_i,
                5
            ],

        "spatial-regression-moran-expected":
            [
                summary.residual_moran_expected,
                5
            ],

        "spatial-regression-moran-z":
            [
                summary.residual_moran_z_score,
                4
            ],

        "spatial-regression-moran-p":
            [
                summary.residual_moran_p_value,
                4
            ],

        "spatial-regression-lm-error":
            [
                summary
                    .lm_error
                    ?.statistic,
                4
            ],

        "spatial-regression-lm-error-p":
            [
                summary
                    .lm_error
                    ?.p_value,
                4
            ],

        "spatial-regression-rlm-error":
            [
                summary
                    .robust_lm_error
                    ?.statistic,
                4
            ],

        "spatial-regression-rlm-error-p":
            [
                summary
                    .robust_lm_error
                    ?.p_value,
                4
            ],

        "spatial-regression-lm-lag":
            [
                summary
                    .lm_lag
                    ?.statistic,
                4
            ],

        "spatial-regression-lm-lag-p":
            [
                summary
                    .lm_lag
                    ?.p_value,
                4
            ],

        "spatial-regression-rlm-lag":
            [
                summary
                    .robust_lm_lag
                    ?.statistic,
                4
            ],

        "spatial-regression-rlm-lag-p":
            [
                summary
                    .robust_lm_lag
                    ?.p_value,
                4
            ]
    };


    Object.entries(
        modelValues
    )
    .forEach(
        (
            [
                id,
                [
                    value,
                    decimals
                ]
            ]
        ) => {

            const element =
                getEl(id);

            if (
                element
            ) {

                element.textContent =
                    formatNumber(
                        value,
                        decimals
                    );
            }
        }
    );


    const moranSignificant =
        getEl(
            "spatial-regression-moran-significant"
        );

    if (
        moranSignificant
    ) {

        moranSignificant.textContent =
            summary
                .residual_moran_significant ===
            true

                ? "Yes"

                : (
                    summary
                        .residual_moran_significant ===
                    false

                        ? "No"
                        : "—"
                );
    }


    const modelIndication =
        getEl(
            "spatial-regression-model-indication"
        );

    if (
        modelIndication
    ) {

        modelIndication.textContent =
            summary.model_indication ||
            "—";
    }


    const residualDependence =
        getEl(
            "spatial-regression-residual-dependence"
        );

    if (
        residualDependence
    ) {

        residualDependence.textContent =
            summary
                .residual_spatial_dependence ===
            true

                ? "Detected"

                : (
                    summary
                        .residual_spatial_dependence ===
                    false

                        ? "Not Detected"
                        : "—"
                );
    }


    const interpretation =
        getEl(
            "spatial-regression-diagnostic-interpretation"
        );

    if (
        interpretation
    ) {

        interpretation.textContent =
            summary
                .diagnostic_interpretation ||
            "";
    }


    renderSpatialRegressionCoefficients(
        coefficients
    );


    const summaryPanel =
        getEl(
            "spatial-regression-summary"
        );

    if (
        summaryPanel
    ) {

        summaryPanel.style.display =
            "block";
    }
}


function renderSpatialRegressionCoefficients(
    coefficients
) {

    const body =
        getEl(
            "spatial-regression-coefficient-body"
        );

    if (!body) {
        return;
    }

    body.innerHTML =
        "";


    if (
        !Array.isArray(
            coefficients
        ) ||

        !coefficients.length
    ) {

        body.innerHTML = `

            <tr>

                <td colspan="5">
                    No coefficient results available.
                </td>

            </tr>
        `;

        return;
    }


    coefficients
        .forEach(
            coefficient => {

                const row =
                    document.createElement(
                        "tr"
                    );

                const significant =
                    coefficient
                        .significant ===
                    true;


                row.innerHTML = `

                    <td>
                        ${escapeHtml(
                            coefficient.variable ||
                            "—"
                        )}
                    </td>

                    <td>
                        ${formatNumber(
                            coefficient.coefficient,
                            6
                        )}
                    </td>

                    <td>
                        ${formatNumber(
                            coefficient.standard_error,
                            6
                        )}
                    </td>

                    <td>
                        ${formatNumber(
                            coefficient.t_statistic,
                            4
                        )}
                    </td>

                    <td
                        title="${
                            significant
                                ? "Statistically significant"
                                : "Not statistically significant"
                        }"
                    >
                        ${formatNumber(
                            coefficient.p_value,
                            4
                        )}

                        ${
                            significant
                                ? " *"
                                : ""
                        }
                    </td>
                `;

                body.appendChild(
                    row
                );
            }
        );
}


function hideSpatialRegressionSummary() {

    const panel =
        getEl(
            "spatial-regression-summary"
        );

    if (
        panel
    ) {

        panel.style.display =
            "none";
    }

    const body =
        getEl(
            "spatial-regression-coefficient-body"
        );

    if (
        body
    ) {

        body.innerHTML =
            "";
    }
}


// ============================================================
// ANALYSIS LAYER MANAGEMENT
// ============================================================

function registerAnalysisLayer(
    layerKey,
    group,
    geojson,
    filename,
    datasetId,
    legend
) {

    uploadedLayers[
        layerKey
    ] = {

        layerType:
            "analysis",

        group,

        geojson,

        filename:
            filename ||
            "Analysis Result",

        datasetId,

        legend,

        visible:
            true
    };


    /*
     * New analysis becomes the currently displayed legend.
     *
     * Existing analysis layers are NOT removed.
     */
    activeAnalysisLayerKey =
        layerKey;


    addAnalysisLayerToToc(
        layerKey
    );


    refreshLayersEmptyMessage();
}


// ============================================================
// ANALYSIS LAYER TOC
// ============================================================

function addAnalysisLayerToToc(
    layerKey
) {

    const entry =
        uploadedLayers[
            layerKey
        ];

    const container =
        getLayersContainer();

    if (
        !entry ||
        !container
    ) {
        return;
    }


    const row =
        document.createElement(
            "div"
        );

    row.className =
        "toc-row";

    row.id =
        `toc-row-${layerKey}`;


    const displayName =
        entry.legend?.title ||
        entry.filename ||
        "Analysis Result";


    row.innerHTML = `

        <label class="toc-toggle-label">

            <input
                type="checkbox"
                checked
            >

            <span class="toc-toggle-slider"></span>

        </label>

        <span
            class="layer-dot"
            style="background:#6c757d;"
        ></span>

        <span
            class="toc-layer-name"
            title="${escapeHtml(
                displayName
            )}"
        >
            ${escapeHtml(
                displayName
            )}
        </span>

        <div class="toc-layer-actions">

            <button
                type="button"
                class="toc-action-btn"
                title="Remove layer"
            >
                <i class="fa fa-trash"></i>
            </button>

        </div>
    `;


    container.appendChild(
        row
    );


    const checkbox =
        row.querySelector(
            'input[type="checkbox"]'
        );


    checkbox
        ?.addEventListener(
            "change",
            () => {

                entry.visible =
                    checkbox.checked;


                if (
                    checkbox.checked
                ) {

                    entry.group
                        .addTo(map);

                    activeAnalysisLayerKey =
                        layerKey;

                    showStoredAnalysisLegend(
                        entry
                    );

                } else {

                    if (
                        map.hasLayer(
                            entry.group
                        )
                    ) {

                        map.removeLayer(
                            entry.group
                        );
                    }

                    if (
                        activeAnalysisLayerKey ===
                        layerKey
                    ) {

                        restoreAnotherAnalysisLegend(
                            layerKey
                        );
                    }
                }
            }
        );


    row
        .querySelector(
            ".toc-action-btn"
        )
        ?.addEventListener(
            "click",
            () => {

                removeLayer(
                    layerKey
                );
            }
        );
}


// ============================================================
// STANDARD ANALYSIS LEGEND
// ============================================================

function showAnalysisLegend(
    title,
    rows
) {

    const legend =
        getEl(
            "analysis-map-legend"
        );

    if (!legend) {
        return;
    }

    legend.innerHTML = `

        <div class="analysis-legend-title">
            ${escapeHtml(title)}
        </div>

        ${
            rows
                .map(
                    (
                        [
                            label,
                            color
                        ]
                    ) => `

                        <div class="analysis-legend-row">

                            <span
                                class="analysis-legend-swatch"
                                style="background-color:${color};"
                            ></span>

                            <span>
                                ${escapeHtml(
                                    label
                                )}
                            </span>

                        </div>
                    `
                )
                .join("")
        }
    `;

    legend.style.display =
        "block";
}


// ============================================================
// COMPACT BIVARIATE 3 x 3 MATRIX LEGEND
// ============================================================

function showBivariateLegend(
    xLabel,
    yLabel,
    colors
) {

    const legend =
        getEl(
            "analysis-map-legend"
        );

    if (!legend) {
        return;
    }


    legend.innerHTML = `

        <div class="analysis-legend-title bivariate-main-title">

            <div>
                ${escapeHtml(xLabel)}
            </div>

            <div class="bivariate-title-divider">
                ×
            </div>

            <div>
                ${escapeHtml(yLabel)}
            </div>

        </div>


        <div class="bivariate-matrix-legend">

            <div class="bivariate-axis-y">

                <span>Y</span>

                <span class="bivariate-axis-arrow">
                    ↑
                </span>

            </div>


            <div class="bivariate-matrix-content">

                <div class="bivariate-column-labels">

                    <span>Low</span>
                    <span>Med</span>
                    <span>High</span>

                </div>


                <div class="bivariate-grid-layout">

                    <div class="bivariate-row-labels">

                        <span>High</span>
                        <span>Med</span>
                        <span>Low</span>

                    </div>


                    <div class="bivariate-color-grid">

                        <div
                            class="bivariate-color-cell"
                            style="background:${colors.x1y3};"
                            title="Low X / High Y"
                        ></div>

                        <div
                            class="bivariate-color-cell"
                            style="background:${colors.x2y3};"
                            title="Medium X / High Y"
                        ></div>

                        <div
                            class="bivariate-color-cell"
                            style="background:${colors.x3y3};"
                            title="High X / High Y"
                        ></div>


                        <div
                            class="bivariate-color-cell"
                            style="background:${colors.x1y2};"
                            title="Low X / Medium Y"
                        ></div>

                        <div
                            class="bivariate-color-cell"
                            style="background:${colors.x2y2};"
                            title="Medium X / Medium Y"
                        ></div>

                        <div
                            class="bivariate-color-cell"
                            style="background:${colors.x3y2};"
                            title="High X / Medium Y"
                        ></div>


                        <div
                            class="bivariate-color-cell"
                            style="background:${colors.x1y1};"
                            title="Low X / Low Y"
                        ></div>

                        <div
                            class="bivariate-color-cell"
                            style="background:${colors.x2y1};"
                            title="Medium X / Low Y"
                        ></div>

                        <div
                            class="bivariate-color-cell"
                            style="background:${colors.x3y1};"
                            title="High X / Low Y"
                        ></div>

                    </div>

                </div>


                <div class="bivariate-axis-x">
                    X →
                </div>

            </div>

        </div>


        <div class="bivariate-variable-key">

            <div>
                <strong>X:</strong>
                ${escapeHtml(xLabel)}
            </div>

            <div>
                <strong>Y:</strong>
                ${escapeHtml(yLabel)}
            </div>

        </div>


        <div class="bivariate-no-data-row">

            <span
                class="analysis-legend-swatch"
                style="background:${colors.no_data};"
            ></span>

            <span>
                No Data
            </span>

        </div>
    `;


    legend.style.display =
        "block";
}


// ============================================================
// HIDE ANALYSIS LEGEND
// ============================================================

function hideAnalysisLegend() {

    const legend =
        getEl(
            "analysis-map-legend"
        );

    if (!legend) {
        return;
    }

    legend.style.display =
        "none";

    legend.innerHTML =
        "";
}


// ============================================================
// EXPORT LAYOUT
// ============================================================

let currentLayoutTemplate =
    "a4_portrait";


document
    .querySelectorAll(
        "#export-layout-gallery .gallery-tile"
    )
    .forEach(
        tile => {

            tile.addEventListener(
                "click",
                () => {

                    document
                        .querySelectorAll(
                            "#export-layout-gallery .gallery-tile"
                        )
                        .forEach(
                            item => {

                                item.classList.remove(
                                    "active"
                                );
                            }
                        );

                    tile.classList.add(
                        "active"
                    );

                    currentLayoutTemplate =
                        tile.dataset
                            .layout;
                }
            );
        }
    );


// ============================================================
// MAP EXPORT
// ============================================================

getEl(
    "export-map-btn"
)
?.addEventListener(
    "click",
    async () => {

        const button =
            getEl(
                "export-map-btn"
            );

        const status =
            getEl(
                "export-status"
            );

        if (
            typeof html2canvas ===
            "undefined"
        ) {

            if (
                status
            ) {

                status.textContent =
                    "Map export library is unavailable.";
            }

            return;
        }

        if (
            button
        ) {

            button.disabled =
                true;
        }

        if (
            status
        ) {

            status.textContent =
                "Rendering map...";
        }


        try {

            const mapWrapper =
                getEl(
                    "dashboard-map-wrapper"
                );

            const canvas =
                await html2canvas(
                    mapWrapper,
                    {
                        useCORS:
                            true,

                        logging:
                            false,

                        backgroundColor:
                            null
                    }
                );


            const dimensionsByLayout = {

                a4_portrait: {

                    width:
                        1240,

                    height:
                        1754
                },

                a4_landscape: {

                    width:
                        1754,

                    height:
                        1240
                },

                presentation: {

                    width:
                        1920,

                    height:
                        1080
                },

                social: {

                    width:
                        1080,

                    height:
                        1080
                }
            };


            const dimensions =
                dimensionsByLayout[
                    currentLayoutTemplate
                ] ||
                dimensionsByLayout
                    .a4_portrait;


            const outputCanvas =
                document.createElement(
                    "canvas"
                );

            outputCanvas.width =
                dimensions.width;

            outputCanvas.height =
                dimensions.height;


            const context =
                outputCanvas
                    .getContext(
                        "2d"
                    );


            context.fillStyle =
                "#ffffff";

            context.fillRect(
                0,
                0,
                dimensions.width,
                dimensions.height
            );


            const title =
                getEl(
                    "export-title"
                )?.value ||
                "SENSD Map";


            const subtitle =
                getEl(
                    "export-subtitle"
                )?.value ||
                "";


            context.fillStyle =
                "#111111";

            context.font =
                "bold 34px sans-serif";

            context.fillText(
                title,
                40,
                55
            );


            if (
                subtitle
            ) {

                context.fillStyle =
                    "#666666";

                context.font =
                    "18px sans-serif";

                context.fillText(
                    subtitle,
                    40,
                    85
                );
            }


            const topMargin =
                120;

            const sideMargin =
                40;

            const availableWidth =
                dimensions.width -
                sideMargin * 2;

            const availableHeight =
                dimensions.height -
                topMargin -
                60;


            const scale =
                Math.min(
                    availableWidth /
                    canvas.width,

                    availableHeight /
                    canvas.height
                );


            const drawWidth =
                canvas.width *
                scale;

            const drawHeight =
                canvas.height *
                scale;


            context.drawImage(
                canvas,

                (
                    dimensions.width -
                    drawWidth
                ) /
                2,

                topMargin +
                (
                    availableHeight -
                    drawHeight
                ) /
                2,

                drawWidth,
                drawHeight
            );


            outputCanvas.toBlob(
                blob => {

                    if (!blob) {
                        return;
                    }

                    const url =
                        URL.createObjectURL(
                            blob
                        );

                    const anchor =
                        document.createElement(
                            "a"
                        );

                    anchor.href =
                        url;

                    anchor.download =
                        `sensd-${currentLayoutTemplate}-map.png`;

                    anchor.click();

                    URL.revokeObjectURL(
                        url
                    );

                    if (
                        status
                    ) {

                        status.textContent =
                            "Map exported.";
                    }
                },

                "image/png"
            );

        } catch (error) {

            console.error(
                error
            );

            if (
                status
            ) {

                status.textContent =
                    "Map export failed.";
            }

        } finally {

            if (
                button
            ) {

                button.disabled =
                    false;
            }
        }
    }
);


// ============================================================
// INITIALIZE TOOLBOX TREE
// ============================================================

function initializeToolboxTree() {

    document
        .querySelectorAll(
            ".toolbox-tree-children"
        )
        .forEach(
            children => {

                children.style.display =
                    "block";
            }
        );


    document
        .querySelectorAll(
            ".toolbox-tree-parent"
        )
        .forEach(
            parent => {

                parent.classList.add(
                    "open"
                );

                const chevron =
                    parent.querySelector(
                        ".toolbox-tree-chevron"
                    );

                if (
                    chevron
                ) {

                    chevron.className =
                        "fa fa-chevron-down toolbox-tree-chevron";
                }
            }
        );
}


// ============================================================
// INITIALIZE SIDEBAR STATE
// ============================================================

function initializeSidebarState() {

    if (
        tocRestoreBtn
    ) {

        tocRestoreBtn
            .style
            .display =

            tocPanel
                ?.classList.contains(
                    "collapsed"
                )

                ? "flex"
                : "none";
    }


    if (
        toolboxRestoreBtn
    ) {

        toolboxRestoreBtn
            .style
            .display =

            toolboxPanel
                ?.classList.contains(
                    "collapsed"
                )

                ? "flex"
                : "none";
    }


    if (
        tocResizeHandle
    ) {

        tocResizeHandle
            .classList.toggle(
                "hidden",

                Boolean(
                    tocPanel
                        ?.classList.contains(
                            "collapsed"
                        )
                )
            );
    }


    if (
        toolboxResizeHandle
    ) {

        toolboxResizeHandle
            .classList.toggle(
                "hidden",

                Boolean(
                    toolboxPanel
                        ?.classList.contains(
                            "collapsed"
                        )
                )
            );
    }
}


// ============================================================
// WINDOW RESIZE
// ============================================================

window.addEventListener(
    "resize",
    () => {

        map.invalidateSize(
            false
        );
    }
);


// ============================================================
// INITIAL STATE
// ============================================================

initializeToolboxTree();

initializeSidebarState();

refreshLayersEmptyMessage();

refreshFlowLayerSelects();

validateFlowMapping();

validateSalmonellaForm();

validateBivariateForm();

validateLocalMoranForm();

validateSpatialAssociationForm();

validateSpatialRegressionForm();

updateSpatialRegressionSelectedVariables();

updateSymbologyLabels();


setTimeout(
    () => {

        map.invalidateSize(
            true
        );
    },
    200
);


// ============================================================
// END OF FILE
// ============================================================
