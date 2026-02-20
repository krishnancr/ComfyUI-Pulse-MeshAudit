import { app } from "../../../scripts/app.js";

// Load CSS stylesheet
const link = document.createElement('link');
link.rel = 'stylesheet';
link.href = import.meta.url.replace('/js/mesh_audit_carousel.js', '/css/mesh_audit_carousel.css');
if (!document.querySelector(`link[href="${link.href}"]`)) {
    document.head.appendChild(link);
}

// Data order from Python: outer=cameras, inner=modes → images[camIdx * 4 + modeIdx]
const CAMERAS = ["Perspective", "Front", "Right", "Left"];
const MODES   = ["Path Trace", "Wireframe", "Geo Analysis", "Sliver Tri"];

function imgUrl(img) {
    return `/view?filename=${img.filename}&subfolder=${img.subfolder}&type=${img.type}`;
}

/**
 * Escape HTML special characters for safe display
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Build the Asset Stats accordion panel
 * @param {Object} stats - asset_stats object from node response
 * @returns {HTMLElement} - Root div containing accordion
 */
function buildAssetStatsAccordion(stats) {
    const container = document.createElement('div');
    container.className = 'asset-stats-panel';

    // Header (clickable to toggle)
    const header = document.createElement('div');
    header.className = 'asset-stats-header';
    header.innerHTML = '▼ Asset Stats';

    // Content container (will be hidden when collapsed)
    const content = document.createElement('div');
    content.className = 'asset-stats-content';

    // Scene Metadata section
    const sceneSection = document.createElement('div');
    sceneSection.className = 'asset-stats-section';
    sceneSection.innerHTML = `
        <div class="asset-stats-section-title">Scene Metadata</div>
        <div class="asset-stats-item">
            <span class="label">Asset Name:</span>
            <span class="value">${escapeHtml(stats.scene.name)}</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Timestamp:</span>
            <span class="value">${escapeHtml(stats.scene.timestamp)}</span>
        </div>
    `;

    // Geometry Stats section
    const geoSection = document.createElement('div');
    geoSection.className = 'asset-stats-section';
    geoSection.innerHTML = `
        <div class="asset-stats-section-title">Geometry Stats</div>
        <div class="asset-stats-item">
            <span class="label">Edge Count:</span>
            <span class="value">${stats.geometry.edge_count.toLocaleString()}</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Face Count:</span>
            <span class="value">${stats.geometry.face_count.toLocaleString()}</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Vertex Count:</span>
            <span class="value">${stats.geometry.vertex_count.toLocaleString()}</span>
        </div>
    `;

    // Quality Metrics section
    const qualitySection = document.createElement('div');
    qualitySection.className = 'asset-stats-section';
    qualitySection.innerHTML = `
        <div class="asset-stats-section-title">Quality Metrics</div>
        <div class="asset-stats-item">
            <span class="label">Degenerate Triangles:</span>
            <span class="value">${stats.quality_metrics.degenerate_triangles_pct.toFixed(2)}%</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Sliver Triangles:</span>
            <span class="value">${stats.quality_metrics.sliver_triangles_pct.toFixed(2)}%</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Inverted Triangles:</span>
            <span class="value">${stats.quality_metrics.inverted_triangles_pct.toFixed(2)}%</span>
        </div>
    `;

    // Assemble content
    content.appendChild(sceneSection);
    content.appendChild(geoSection);
    content.appendChild(qualitySection);

    // Assemble container
    container.appendChild(header);
    container.appendChild(content);

    // Add expand/collapse handler
    let expanded = true;
    header.addEventListener('click', () => {
        expanded = !expanded;
        if (expanded) {
            content.classList.remove('collapsed');
            header.innerHTML = '▼ Asset Stats';
        } else {
            content.classList.add('collapsed');
            header.innerHTML = '▶ Asset Stats';
        }
    });

    return container;
}

app.registerExtension({
    name: "Pulse.MeshAuditCarousel",

    nodeCreated(node) {
        if (node.comfyClass !== "PulseMeshAudit") return;

        node.onExecuted = function (msg) {
            const labels = msg.mesh_audit_carousel[0].labels;
            const images = msg.images;

            // Suppress ComfyUI default image preview
            Object.defineProperty(this, "imgs", {
                get: () => [],
                set: () => {},
                configurable: true,
            });

            // Tear down any existing carousel widget
            const existingIndex = this.widgets
                ? this.widgets.findIndex((w) => w.name === "mesh_audit_carousel")
                : -1;
            if (existingIndex !== -1) {
                const existing = this.widgets[existingIndex];
                if (existing.element?.parentNode) {
                    existing.element.parentNode.removeChild(existing.element);
                }
                this.widgets.splice(existingIndex, 1);
            }

            // ── Outer container ──────────────────────────────────────────────
            const container = document.createElement("div");
            container.style.cssText = "width:100%; background:#111; border-radius:8px; overflow:hidden; font-family:monospace; box-sizing:border-box;";

            // Camera column headers (pure 4-col, no label col)
            const camHeader = document.createElement("div");
            camHeader.style.cssText = "display:grid; grid-template-columns:repeat(4,1fr); gap:2px; padding:2px 2px 0;";
            CAMERAS.forEach((cam) => {
                const h = document.createElement("div");
                h.style.cssText = "background:#2a2a2a; color:#aaa; font-size:10px; text-align:center; padding:3px 0; border-radius:2px;";
                h.textContent = cam;
                camHeader.appendChild(h);
            });
            container.appendChild(camHeader);

            // ── One section per shading mode ─────────────────────────────────
            MODES.forEach((mode, modeIdx) => {
                // Full-width mode label banner
                const banner = document.createElement("div");
                banner.style.cssText = "background:#1e1e1e; color:#888; font-size:10px; padding:3px 6px; margin-top:4px; letter-spacing:0.05em; text-transform:uppercase;";
                banner.textContent = mode;
                container.appendChild(banner);

                // 4-column image row — no label col, full width
                const row = document.createElement("div");
                row.style.cssText = "display:grid; grid-template-columns:repeat(4,1fr); gap:2px; padding:0 2px 2px;";

                CAMERAS.forEach((cam, camIdx) => {
                    const idx = camIdx * 4 + modeIdx;
                    const imgData = images[idx];

                    const cell = document.createElement("div");
                    cell.style.cssText = "background:#000; cursor:pointer; overflow:hidden; position:relative;";

                    const thumb = document.createElement("img");
                    thumb.style.cssText = "width:100%; height:auto; display:block;";
                    thumb.src = imgUrl(imgData);
                    thumb.title = `${mode} — ${cam}`;

                    cell.addEventListener("mouseenter", () => { cell.style.outline = "1px solid #555"; });
                    cell.addEventListener("mouseleave", () => { cell.style.outline = "none"; });

                    // Click to view fullscreen with navigation
                    cell.addEventListener("click", () => {
                        let currentIdx = camIdx * 4 + modeIdx;

                        const viewer = document.createElement("div");
                        viewer.style.cssText = `
                            position: fixed;
                            top: 50%;
                            left: 50%;
                            transform: translate(-50%, -50%);
                            background: #000;
                            border: 2px solid #555;
                            border-radius: 8px;
                            padding: 20px;
                            max-width: 90vw;
                            max-height: 90vh;
                            z-index: 10000;
                            box-shadow: 0 0 20px rgba(0,0,0,0.9);
                            display: flex;
                            flex-direction: column;
                            gap: 10px;
                        `;

                        // Header with title and close button
                        const header = document.createElement("div");
                        header.style.cssText = `
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            color: #aaa;
                            font-size: 12px;
                            font-family: monospace;
                        `;
                        header.innerHTML = `
                            <span id="img-title"></span>
                            <button id="close-btn" style="background: #444; color: #fff; border: none; padding: 4px 8px; cursor: pointer; border-radius: 4px; font-weight: bold;">✕</button>
                        `;
                        viewer.appendChild(header);

                        // Image container
                        const imgContainer = document.createElement("div");
                        imgContainer.style.cssText = `
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            overflow: auto;
                            flex: 1;
                        `;
                        const fullImg = document.createElement("img");
                        fullImg.style.cssText = `
                            max-width: 100%;
                            max-height: 100%;
                            object-fit: contain;
                        `;
                        imgContainer.appendChild(fullImg);
                        viewer.appendChild(imgContainer);

                        // Navigation footer
                        const footer = document.createElement("div");
                        footer.style.cssText = `
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            color: #aaa;
                            font-size: 11px;
                            font-family: monospace;
                        `;
                        footer.innerHTML = `
                            <span id="nav-info"></span>
                            <span id="shortcuts">← → to navigate · ESC to close</span>
                        `;
                        viewer.appendChild(footer);

                        document.body.appendChild(viewer);

                        const updateImage = () => {
                            const imgData = images[currentIdx];
                            fullImg.src = imgUrl(imgData);
                            const cam = CAMERAS[Math.floor(currentIdx / 4)];
                            const mode = MODES[currentIdx % 4];
                            document.getElementById("img-title").textContent = `${mode} — ${cam}`;
                            document.getElementById("nav-info").textContent = `Image ${currentIdx + 1} / ${images.length}`;
                        };

                        const closeViewer = () => {
                            viewer.remove();
                            document.removeEventListener("keydown", handleKeydown);
                        };

                        const handleKeydown = (e) => {
                            if (e.key === "Escape") {
                                closeViewer();
                            } else if (e.key === "ArrowLeft") {
                                currentIdx = (currentIdx - 1 + images.length) % images.length;
                                updateImage();
                            } else if (e.key === "ArrowRight") {
                                currentIdx = (currentIdx + 1) % images.length;
                                updateImage();
                            }
                        };

                        document.getElementById("close-btn").addEventListener("click", closeViewer);
                        document.addEventListener("keydown", handleKeydown);

                        updateImage();
                    });

                    cell.appendChild(thumb);
                    row.appendChild(cell);
                });

                container.appendChild(row);
            });

            // Build final widget: carousel + accordion (if stats available)
            let widgetElement = container;

            // If stats available, create flex layout with accordion
            if (msg.asset_stats && msg.asset_stats.scene && msg.asset_stats.geometry && msg.asset_stats.quality_metrics) {
                const mainContainer = document.createElement("div");
                mainContainer.style.cssText = "display:flex; gap:15px; width:100%; box-sizing:border-box; align-items:flex-start;";

                const carouselWrapper = document.createElement("div");
                carouselWrapper.style.cssText = "flex:1; min-width:0;";
                carouselWrapper.appendChild(container);

                const statsWrapper = document.createElement("div");
                statsWrapper.style.cssText = "flex:0 0 320px;";
                try {
                    const accordion = buildAssetStatsAccordion(msg.asset_stats);
                    statsWrapper.appendChild(accordion);
                } catch (e) {
                    console.error("[MeshAudit] Error building accordion:", e);
                }

                mainContainer.appendChild(carouselWrapper);
                mainContainer.appendChild(statsWrapper);
                widgetElement = mainContainer;
            }

            this.addDOMWidget("mesh_audit_carousel", "div", widgetElement, { serialize: false });
            this.setSize([this.size[0], this.computeSize()[1]]);
        };

        node.onRemoved = function () {
            if (!this.widgets) return;
            const idx = this.widgets.findIndex((w) => w.name === "mesh_audit_carousel");
            if (idx !== -1) {
                const widget = this.widgets[idx];
                if (widget.element?.parentNode) {
                    widget.element.parentNode.removeChild(widget.element);
                }
                this.widgets.splice(idx, 1);
            }
        };
    },
});
