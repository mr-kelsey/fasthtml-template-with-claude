(function () {
    "use strict";

    var svg = document.getElementById("land-map-svg");
    if (!svg) return;

    var DRAG_THRESHOLD_PX = 4;
    var suppressNextClick = false;
    var plotWidth = parseFloat(svg.dataset.plotWidth);
    var plotLength = parseFloat(svg.dataset.plotLength);

    // Kept in sync with the matching constants/logic in pages/land_plots.py (initial render).
    var LABEL_FONT_RATIO = 0.3;
    var LABEL_FONT_MIN = 0.2;
    var LABEL_FONT_MAX = 0.5;
    var LABEL_CHAR_WIDTH_RATIO = 0.6;
    var MIN_BED_DIM_FOR_LABEL = 1;

    function labelFontSize(width, length, label) {
        if (Math.min(width, length) < MIN_BED_DIM_FOR_LABEL) return null;
        var byDim = Math.min(width, length) * LABEL_FONT_RATIO;
        var byWidth = (width * 0.9) / (Math.max(label.length, 1) * LABEL_CHAR_WIDTH_RATIO);
        var fontSize = Math.min(LABEL_FONT_MAX, byDim, byWidth);
        return fontSize >= LABEL_FONT_MIN ? fontSize : null;
    }

    function clamp(value, low, high) {
        return Math.max(low, Math.min(value, high));
    }

    function toFeet(clientX, clientY) {
        var rect = svg.getBoundingClientRect();
        var viewBox = svg.viewBox.baseVal;
        return {
            x: ((clientX - rect.left) / rect.width) * viewBox.width,
            y: ((clientY - rect.top) / rect.height) * viewBox.height,
        };
    }

    function post(path, params) {
        return fetch(path, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams(params),
        });
    }

    function bedIdFor(group) {
        return group.id.replace("bed-", "");
    }

    function currentTranslate(group) {
        var match = /translate\(([-\d.]+),([-\d.]+)\)/.exec(group.getAttribute("transform") || "");
        return match ? { x: parseFloat(match[1]), y: parseFloat(match[2]) } : { x: 0, y: 0 };
    }

    function currentRotatePart(group) {
        var match = /rotate\([^)]+\)/.exec(group.getAttribute("transform") || "");
        return match ? " " + match[0] : "";
    }

    function currentRotateDeg(group) {
        var match = /rotate\(([-\d.]+),/.exec(group.getAttribute("transform") || "");
        return match ? parseFloat(match[1]) : 0;
    }

    function startDrag(group, downEvent) {
        var rect = group.querySelector(".bed-rect");
        var bedWidth = parseFloat(rect.getAttribute("width"));
        var bedLength = parseFloat(rect.getAttribute("height"));
        var maxX = Math.max(0, plotWidth - bedWidth);
        var maxY = Math.max(0, plotLength - bedLength);
        var origin = currentTranslate(group);
        var originalTransform = group.getAttribute("transform");
        var startFeet = toFeet(downEvent.clientX, downEvent.clientY);
        var moved = false;
        var newX = origin.x;
        var newY = origin.y;
        group.setPointerCapture(downEvent.pointerId);

        function onMove(e) {
            if (
                Math.abs(e.clientX - downEvent.clientX) > DRAG_THRESHOLD_PX ||
                Math.abs(e.clientY - downEvent.clientY) > DRAG_THRESHOLD_PX
            ) {
                moved = true;
            }
            var point = toFeet(e.clientX, e.clientY);
            newX = clamp(Math.round(origin.x + (point.x - startFeet.x)), 0, maxX);
            newY = clamp(Math.round(origin.y + (point.y - startFeet.y)), 0, maxY);
            group.setAttribute("transform", "translate(" + newX + "," + newY + ")" + currentRotatePart(group));
        }

        function cleanup(e) {
            group.releasePointerCapture(e.pointerId);
            group.removeEventListener("pointermove", onMove);
            group.removeEventListener("pointerup", onUp);
            group.removeEventListener("pointercancel", onCancel);
        }

        function onUp(e) {
            cleanup(e);
            if (moved) {
                suppressNextClick = true;
                post("/beds/" + bedIdFor(group) + "/position", { x: newX, y: newY })
                    .then(function (response) {
                        if (!response.ok) group.setAttribute("transform", originalTransform);
                    })
                    .catch(function () {
                        group.setAttribute("transform", originalTransform);
                    });
            }
        }

        function onCancel(e) {
            cleanup(e);
            group.setAttribute("transform", originalTransform);
        }

        group.addEventListener("pointermove", onMove);
        group.addEventListener("pointerup", onUp);
        group.addEventListener("pointercancel", onCancel);
    }

    function startResize(group, handle, downEvent) {
        var rect = group.querySelector(".bed-rect");
        var label = group.querySelector(".bed-label");
        var startWidth = parseFloat(rect.getAttribute("width"));
        var startLength = parseFloat(rect.getAttribute("height"));
        var translate = currentTranslate(group);
        var rotateDeg = currentRotateDeg(group);
        var maxWidth = Math.max(1, plotWidth - translate.x);
        var maxLength = Math.max(1, plotLength - translate.y);
        var startFeet = toFeet(downEvent.clientX, downEvent.clientY);
        var moved = false;
        var newWidth = startWidth;
        var newLength = startLength;
        handle.setPointerCapture(downEvent.pointerId);

        function applyDimensions(width, length) {
            rect.setAttribute("width", width);
            rect.setAttribute("height", length);
            handle.setAttribute("x", width - 1);
            handle.setAttribute("y", length - 1);
            if (label) {
                label.setAttribute("x", width / 2);
                label.setAttribute("y", length / 2);
                var fontSize = labelFontSize(width, length, label.textContent);
                if (fontSize) {
                    label.style.display = "";
                    label.setAttribute("font-size", fontSize);
                } else {
                    label.style.display = "none";
                }
            }
            group.setAttribute(
                "transform",
                "translate(" + translate.x + "," + translate.y + ") rotate(" + rotateDeg + "," + width / 2 + "," + length / 2 + ")"
            );
        }

        function onMove(e) {
            if (
                Math.abs(e.clientX - downEvent.clientX) > DRAG_THRESHOLD_PX ||
                Math.abs(e.clientY - downEvent.clientY) > DRAG_THRESHOLD_PX
            ) {
                moved = true;
            }
            var point = toFeet(e.clientX, e.clientY);
            newWidth = clamp(Math.round(startWidth + (point.x - startFeet.x)), 1, maxWidth);
            newLength = clamp(Math.round(startLength + (point.y - startFeet.y)), 1, maxLength);
            applyDimensions(newWidth, newLength);
        }

        function cleanup(e) {
            handle.releasePointerCapture(e.pointerId);
            handle.removeEventListener("pointermove", onMove);
            handle.removeEventListener("pointerup", onUp);
            handle.removeEventListener("pointercancel", onCancel);
        }

        function onUp(e) {
            cleanup(e);
            if (moved) {
                suppressNextClick = true;
                post("/beds/" + bedIdFor(group) + "/size", { width_ft: newWidth, length_ft: newLength })
                    .then(function (response) {
                        if (!response.ok) applyDimensions(startWidth, startLength);
                    })
                    .catch(function () {
                        applyDimensions(startWidth, startLength);
                    });
            }
        }

        function onCancel(e) {
            cleanup(e);
            applyDimensions(startWidth, startLength);
        }

        handle.addEventListener("pointermove", onMove);
        handle.addEventListener("pointerup", onUp);
        handle.addEventListener("pointercancel", onCancel);
    }

    svg.addEventListener("pointerdown", function (e) {
        if (drawState.active) return; // bed drag/resize is disabled while drawing/editing a shade polygon
        var group = e.target.closest(".bed-group");
        if (!group) return;
        var handle = e.target.closest(".resize-handle");
        if (handle) {
            e.stopPropagation();
            startResize(group, handle, e);
        } else {
            startDrag(group, e);
        }
    });

    // A drag/resize ends with a pointerup, which the browser follows with a synthetic click on
    // the same target. htmx's hx-trigger="click" on .bed-group would otherwise open the edit
    // dialog right after every drag. Swallow exactly that one click, in the capture phase so it
    // runs before htmx's own (bubble-phase) listener ever sees it.
    svg.addEventListener(
        "click",
        function (e) {
            if (suppressNextClick) {
                suppressNextClick = false;
                e.stopImmediatePropagation();
                e.preventDefault();
            }
        },
        true
    );

    // -- Phase 9: shade-source polygon drawing/editing -------------------------------------
    // Deliberately additive to the drag/resize code above rather than reworked into it -- this
    // is a distinct gesture (click-to-add-vertex / drag-a-vertex) over the same SVG canvas and
    // the same toFeet() helper, not another instance of the bed drag pattern.

    var shadeDataEl = document.getElementById("shade-map-data");
    var shadeDrawLayer = document.getElementById("shade-draw-layer");
    var shadeDrawStatus = document.getElementById("shade-draw-status");
    var shadeData = shadeDataEl ? JSON.parse(shadeDataEl.textContent) : null;

    var CLOSE_THRESHOLD_FT = 0.75;
    var VERTEX_RADIUS_FT = 0.35;
    var SVG_NS = "http://www.w3.org/2000/svg";

    // Kept in sync with SEASON_LABELS/SHADE_TYPE_LABELS in farm/pages/land_plots.py, same
    // duplication pattern as LABEL_FONT_RATIO etc. above.
    var SEASON_LABELS = { summer_solstice: "Summer solstice", winter_solstice: "Winter solstice" };
    var SHADE_TYPE_LABELS = { full: "Full shade", partial: "Partial shade" };

    var drawState = {
        active: false,
        sourceId: null,
        season: null,
        shadeType: null,
        points: [], // [{x, y}]
        editingExisting: false,
    };

    function shadeComboKey(season, shadeType) {
        return season + ":" + shadeType;
    }

    function shadeSourceLabel(sourceId) {
        var source = shadeData.shade_sources.filter(function (s) { return s.id === sourceId; })[0];
        return source ? source.label : "";
    }

    function highlightDrawButtons() {
        document.querySelectorAll(".shade-draw-button").forEach(function (button) {
            var matches =
                drawState.active &&
                parseInt(button.getAttribute("data-source-id"), 10) === drawState.sourceId &&
                button.getAttribute("data-season") === drawState.season &&
                button.getAttribute("data-shade-type") === drawState.shadeType;
            button.classList.toggle("armed", matches);
        });
    }

    function updateDrawStatus() {
        if (!shadeDrawStatus) return;
        while (shadeDrawStatus.firstChild) shadeDrawStatus.removeChild(shadeDrawStatus.firstChild);
        if (!drawState.active) {
            shadeDrawStatus.hidden = true;
            return;
        }
        shadeDrawStatus.hidden = false;
        var comboLabel =
            shadeSourceLabel(drawState.sourceId) + " — " +
            SEASON_LABELS[drawState.season] + " / " + SHADE_TYPE_LABELS[drawState.shadeType];
        var text = document.createElement("span");
        text.textContent = drawState.editingExisting
            ? "Editing " + comboLabel + ". Drag a point on the map to move it, or click Done to go back " +
                "to clicking beds."
            : "Drawing " + comboLabel + ". Click the map to place points (at least 3), " +
                "then click near the first point to close the shape.";
        // "Cancel" only while a fresh (unsaved) shape is still being placed -- there's nothing
        // to lose yet. Once it's closed (editingExisting), every change is already saved on
        // each vertex drop, so exiting is a plain "Done", not a discard.
        var exitButton = document.createElement("button");
        exitButton.type = "button";
        exitButton.textContent = drawState.editingExisting ? "Done" : "Cancel";
        exitButton.addEventListener("click", endDraw);
        shadeDrawStatus.appendChild(text);
        shadeDrawStatus.appendChild(exitButton);
    }

    // toFeet() above is a per-axis pixel stretch, not the true (letterboxed, aspect-preserving)
    // render scale -- see _js_naive_scale's comment in tests/farm/test_land_map_js.py. That's
    // invisible for bed drag/resize, which only ever consume toFeet() *deltas* (the distortion
    // cancels out of a subtraction). Freehand polygon points are placed absolutely, though, so
    // they need the real inverse of the browser's own rendering transform or they'd land
    // visibly off from the click on any plot whose aspect ratio isn't 1:1.
    function toFeetTrue(clientX, clientY) {
        var rect = svg.getBoundingClientRect();
        var viewBox = svg.viewBox.baseVal;
        var scale = Math.min(rect.width / viewBox.width, rect.height / viewBox.height);
        var offsetX = rect.left + (rect.width - viewBox.width * scale) / 2;
        var offsetY = rect.top + (rect.height - viewBox.height * scale) / 2;
        return { x: (clientX - offsetX) / scale, y: (clientY - offsetY) / scale };
    }

    function makeSvgEl(tag, attrs) {
        var el = document.createElementNS(SVG_NS, tag);
        for (var key in attrs) el.setAttribute(key, attrs[key]);
        return el;
    }

    function clearShadeDrawLayer() {
        while (shadeDrawLayer.firstChild) shadeDrawLayer.removeChild(shadeDrawLayer.firstChild);
    }

    function draftPathD() {
        var pts = drawState.points;
        var d = "M " + pts.map(function (p) { return p.x + "," + p.y; }).join(" L ");
        if (drawState.editingExisting && pts.length > 2) d += " Z";
        return d;
    }

    function startVertexDrag(index, handle, downEvent) {
        var pathEl = shadeDrawLayer.querySelector(".shade-draft-path");
        var origin = drawState.points[index];
        var startFeet = toFeetTrue(downEvent.clientX, downEvent.clientY);
        handle.setPointerCapture(downEvent.pointerId);

        function onMove(e) {
            var nowFeet = toFeetTrue(e.clientX, e.clientY);
            var pt = {
                x: clamp(origin.x + (nowFeet.x - startFeet.x), 0, plotWidth),
                y: clamp(origin.y + (nowFeet.y - startFeet.y), 0, plotLength),
            };
            drawState.points[index] = pt;
            handle.setAttribute("cx", pt.x);
            handle.setAttribute("cy", pt.y);
            if (pathEl) pathEl.setAttribute("d", draftPathD());
        }

        function cleanup(e) {
            handle.releasePointerCapture(e.pointerId);
            handle.removeEventListener("pointermove", onMove);
            handle.removeEventListener("pointerup", onUp);
            handle.removeEventListener("pointercancel", cleanup);
        }

        function onUp(e) {
            cleanup(e);
            saveDraft();
        }

        handle.addEventListener("pointermove", onMove);
        handle.addEventListener("pointerup", onUp);
        handle.addEventListener("pointercancel", cleanup);
    }

    function ensureArmedTypeGroupExpanded() {
        if (!drawState.active) return;
        var item = document.querySelector('.shade-source-item[data-source-id="' + drawState.sourceId + '"]');
        var group = item ? item.querySelector('.shade-type-group[data-shade-type="' + drawState.shadeType + '"]') : null;
        var rows = group ? group.querySelector(".shade-season-rows") : null;
        if (rows) rows.hidden = false;
    }

    function renderDraft() {
        if (!shadeDrawLayer) return;
        // A bed group's onclick navigates to its detail page (pages/land_plots.py's _bed_group) --
        // guarded on this flag so clicking a bed to place/drag a shade-polygon vertex over it
        // doesn't navigate away instead. pointerdown-based bed drag/resize is separately disabled
        // by the `if (drawState.active) return;` guard in the pointerdown listener below.
        window.__shadeDrawActive = drawState.active;
        ensureArmedTypeGroupExpanded();
        updateDrawStatus();
        highlightDrawButtons();
        clearShadeDrawLayer();
        if (!drawState.active) return;
        var pts = drawState.points;
        if (pts.length > 1) {
            shadeDrawLayer.appendChild(makeSvgEl("path", { d: draftPathD(), class: "shade-draft-path" }));
        }
        pts.forEach(function (point, index) {
            var handle = makeSvgEl("circle", { cx: point.x, cy: point.y, r: VERTEX_RADIUS_FT, class: "shade-vertex" });
            if (drawState.editingExisting) {
                handle.addEventListener("pointerdown", function (e) {
                    e.stopPropagation();
                    startVertexDrag(index, handle, e);
                });
            }
            shadeDrawLayer.appendChild(handle);
        });
    }

    function updateShadeSourceRow(sourceId, season, shadeType, polygonId) {
        var item = document.querySelector('.shade-source-item[data-source-id="' + sourceId + '"]');
        if (!item) return;
        var row = item.querySelector(
            '.shade-combo-row[data-season="' + season + '"][data-shade-type="' + shadeType + '"]'
        );
        if (!row) return;
        row.querySelector(".shade-draw-button").textContent = "Edit";
        var deleteButton = row.querySelector(".shade-delete-polygon-button");
        deleteButton.hidden = false;
        deleteButton.setAttribute("data-polygon-id", polygonId);
        var source = shadeData.shade_sources.filter(function (s) { return s.id === sourceId; })[0];
        if (source) source.polygons[shadeComboKey(season, shadeType)] = { id: polygonId, points: drawState.points.map(function (p) { return [p.x, p.y]; }) };
    }

    function resetShadeSourceRow(sourceId, season, shadeType) {
        var item = document.querySelector('.shade-source-item[data-source-id="' + sourceId + '"]');
        if (!item) return;
        var row = item.querySelector(
            '.shade-combo-row[data-season="' + season + '"][data-shade-type="' + shadeType + '"]'
        );
        if (!row) return;
        row.querySelector(".shade-draw-button").textContent = "Draw";
        var deleteButton = row.querySelector(".shade-delete-polygon-button");
        deleteButton.hidden = true;
        deleteButton.removeAttribute("data-polygon-id");
        var source = shadeData.shade_sources.filter(function (s) { return s.id === sourceId; })[0];
        if (source) source.polygons[shadeComboKey(season, shadeType)] = null;
    }

    function saveDraft() {
        if (drawState.points.length < 3) return;
        post("/shade-sources/" + drawState.sourceId + "/polygons", {
            season: drawState.season,
            shade_type: drawState.shadeType,
            points: JSON.stringify(drawState.points.map(function (p) { return [p.x, p.y]; })),
        })
            .then(function (response) {
                return response.ok ? response.json() : null;
            })
            .then(function (result) {
                if (!result) return;
                updateShadeSourceRow(drawState.sourceId, drawState.season, drawState.shadeType, result.id);
            });
    }

    function closeDraft() {
        drawState.editingExisting = true;
        renderDraft();
        saveDraft();
    }

    function endDraw() {
        drawState.active = false;
        drawState.sourceId = null;
        drawState.season = null;
        drawState.shadeType = null;
        drawState.points = [];
        drawState.editingExisting = false;
        renderDraft();
    }

    if (shadeDrawLayer && shadeData) {
        document.addEventListener("click", function (e) {
            var typeToggle = e.target.closest(".shade-type-toggle");
            if (typeToggle) {
                var group = typeToggle.closest(".shade-type-group");
                var rows = group ? group.querySelector(".shade-season-rows") : null;
                if (rows) rows.hidden = !rows.hidden;
                return;
            }
            var drawButton = e.target.closest(".shade-draw-button");
            if (drawButton) {
                var sourceId = parseInt(drawButton.getAttribute("data-source-id"), 10);
                var season = drawButton.getAttribute("data-season");
                var shadeType = drawButton.getAttribute("data-shade-type");
                var source = shadeData.shade_sources.filter(function (s) { return s.id === sourceId; })[0];
                var existing = source ? source.polygons[shadeComboKey(season, shadeType)] : null;
                drawState.active = true;
                drawState.sourceId = sourceId;
                drawState.season = season;
                drawState.shadeType = shadeType;
                drawState.editingExisting = !!existing;
                drawState.points = existing ? existing.points.map(function (p) { return { x: p[0], y: p[1] }; }) : [];
                renderDraft();
                return;
            }
            var deleteButton = e.target.closest(".shade-delete-polygon-button");
            if (deleteButton) {
                var polygonId = deleteButton.getAttribute("data-polygon-id");
                if (!polygonId) return;
                var row = deleteButton.closest(".shade-combo-row");
                var item = deleteButton.closest(".shade-source-item");
                post("/shade-polygons/" + polygonId + "/delete", {}).then(function (response) {
                    if (!response.ok) return;
                    resetShadeSourceRow(parseInt(item.getAttribute("data-source-id"), 10), row.getAttribute("data-season"), row.getAttribute("data-shade-type"));
                    if (drawState.sourceId === parseInt(item.getAttribute("data-source-id"), 10) && drawState.season === row.getAttribute("data-season") && drawState.shadeType === row.getAttribute("data-shade-type")) {
                        endDraw();
                    }
                });
            }
        });

        svg.addEventListener("click", function (e) {
            if (!drawState.active || drawState.editingExisting) return;
            var rawPoint = toFeetTrue(e.clientX, e.clientY);
            var point = { x: clamp(rawPoint.x, 0, plotWidth), y: clamp(rawPoint.y, 0, plotLength) };
            if (drawState.points.length >= 3) {
                var first = drawState.points[0];
                var dx = point.x - first.x;
                var dy = point.y - first.y;
                if (Math.sqrt(dx * dx + dy * dy) < CLOSE_THRESHOLD_FT) {
                    closeDraft();
                    return;
                }
            }
            drawState.points.push(point);
            renderDraft();
        });
    }
})();
