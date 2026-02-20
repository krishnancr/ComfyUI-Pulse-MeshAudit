import { app } from "../../scripts/app.js";

// Data order from Python: outer=cameras, inner=modes → images[camIdx * 4 + modeIdx]
const CAMERAS = ["Perspective", "Front", "Right", "Left"];
const MODES   = ["Path Trace", "Wireframe", "Geo Analysis", "Sliver Tri"];

function imgUrl(img) {
    return `/view?filename=${img.filename}&subfolder=${img.subfolder}&type=${img.type}`;
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

                    cell.appendChild(thumb);
                    row.appendChild(cell);
                });

                container.appendChild(row);
            });

            this.addDOMWidget("mesh_audit_carousel", "div", container, { serialize: false });
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
