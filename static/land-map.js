(function () {
    "use strict";

    var svg = document.getElementById("land-map-svg");
    if (!svg) return;

    var DRAG_THRESHOLD_PX = 4;
    var suppressNextClick = false;

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

    function startDrag(group, downEvent) {
        var origin = currentTranslate(group);
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
            newX = Math.round(origin.x + (point.x - startFeet.x));
            newY = Math.round(origin.y + (point.y - startFeet.y));
            group.setAttribute("transform", "translate(" + newX + "," + newY + ")" + currentRotatePart(group));
        }

        function onUp(e) {
            group.releasePointerCapture(e.pointerId);
            group.removeEventListener("pointermove", onMove);
            group.removeEventListener("pointerup", onUp);
            if (moved) {
                suppressNextClick = true;
                post("/beds/" + bedIdFor(group) + "/position", { x: newX, y: newY });
            }
        }

        group.addEventListener("pointermove", onMove);
        group.addEventListener("pointerup", onUp);
    }

    function startResize(group, handle, downEvent) {
        var rect = group.querySelector(".bed-rect");
        var label = group.querySelector(".bed-label");
        var startWidth = parseFloat(rect.getAttribute("width"));
        var startHeight = parseFloat(rect.getAttribute("height"));
        var startFeet = toFeet(downEvent.clientX, downEvent.clientY);
        var moved = false;
        var newWidth = startWidth;
        var newHeight = startHeight;
        handle.setPointerCapture(downEvent.pointerId);

        function onMove(e) {
            if (
                Math.abs(e.clientX - downEvent.clientX) > DRAG_THRESHOLD_PX ||
                Math.abs(e.clientY - downEvent.clientY) > DRAG_THRESHOLD_PX
            ) {
                moved = true;
            }
            var point = toFeet(e.clientX, e.clientY);
            newWidth = Math.max(1, Math.round(startWidth + (point.x - startFeet.x)));
            newHeight = Math.max(1, Math.round(startHeight + (point.y - startFeet.y)));
            rect.setAttribute("width", newWidth);
            rect.setAttribute("height", newHeight);
            handle.setAttribute("x", newWidth - 1);
            handle.setAttribute("y", newHeight - 1);
            if (label) {
                label.setAttribute("x", newWidth / 2);
                label.setAttribute("y", newHeight / 2);
            }
        }

        function onUp(e) {
            handle.releasePointerCapture(e.pointerId);
            handle.removeEventListener("pointermove", onMove);
            handle.removeEventListener("pointerup", onUp);
            if (moved) {
                suppressNextClick = true;
                post("/beds/" + bedIdFor(group) + "/size", { width_ft: newWidth, height_ft: newHeight });
            }
        }

        handle.addEventListener("pointermove", onMove);
        handle.addEventListener("pointerup", onUp);
    }

    svg.addEventListener("pointerdown", function (e) {
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
})();
