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

    function currentRotateDeg(group) {
        var match = /rotate\(([-\d.]+),/.exec(group.getAttribute("transform") || "");
        return match ? parseFloat(match[1]) : 0;
    }

    function startDrag(group, downEvent) {
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
            newX = Math.round(origin.x + (point.x - startFeet.x));
            newY = Math.round(origin.y + (point.y - startFeet.y));
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
            newWidth = Math.max(1, Math.round(startWidth + (point.x - startFeet.x)));
            newLength = Math.max(1, Math.round(startLength + (point.y - startFeet.y)));
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
