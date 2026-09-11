(function () {
    "use strict";

    // Deliberately snake_case throughout (unlike land-map.js's pre-existing camelCase, which is
    // left untouched since it isn't being modified here). All coordinate math is in inches,
    // matching the inch-based viewBox on #bed-detail-svg -- no feet<->inches conversion anywhere.

    var data_el = document.getElementById("bed-detail-data");
    var svg = document.getElementById("bed-detail-svg");
    if (!data_el || !svg) return;

    var data = JSON.parse(data_el.textContent);

    var planted_layer = document.getElementById("planted-layer");
    var lattice_layer = document.getElementById("lattice-layer");
    var staged_layer = document.getElementById("staged-layer");
    var shade_layer = document.getElementById("shade-layer");
    var shade_date_input = document.getElementById("shade-date");
    var palette_seed = document.getElementById("palette-seed");
    var palette_transplant = document.getElementById("palette-transplant");
    var mode_seed_radio = document.getElementById("mode-seed");
    var mode_transplant_radio = document.getElementById("mode-transplant");
    var batch_form = document.getElementById("batch-plant-form");
    var batch_variety_id_input = document.getElementById("batch-variety-id");
    var batch_source_type_input = document.getElementById("batch-source-type");
    var batch_points_input = document.getElementById("batch-points");
    var batch_planted_date_input = document.getElementById("batch-planted-date");
    var batch_staged_count = document.getElementById("batch-staged-count");
    var lot_select = document.getElementById("batch-transplant-lot-select");
    var lot_quantity_wrap = document.getElementById("armed-lot-quantity-wrap");
    var lot_quantity_input = document.getElementById("armed-lot-quantity-input");
    var quantity_per_point_wrap = document.getElementById("batch-quantity-per-point-wrap");
    var grid_offset_controls = document.getElementById("grid-offset-controls");
    var zoom_controls = document.getElementById("zoom-controls");
    var zoom_display = document.getElementById("zoom-level-display");

    var SVG_NS = "http://www.w3.org/2000/svg";
    var DEFAULT_SPACING_IN = 12; // fallback lattice spacing for a variety with no spacing_in set

    var state = {
        mode: "seed",
        armed_variety: null, // {id, common_name, name, spacing_in, color_hex}
        armed_lot_id: null,
        staged_points: [], // [{x_in, y_in}]
    };

    // "variety_id|planted_date|x_in,y_in" -> bool. render_lattice() rebuilds every lattice/staged circle from
    // scratch on every staging click, so without this a warning already known from a prior fetch would flash
    // away and only reappear once the new fetch (re-issued on every render) round-trips -- most noticeable on
    // a slow connection, where it can read as the warning having vanished for good rather than just refreshing.
    var shade_warning_cache = {};

    function shade_cache_key(variety_id, planted_date, x_in, y_in) {
        return variety_id + "|" + planted_date + "|" + x_in + "," + y_in;
    }

    function post(path, body) {
        return fetch(path, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams(body),
        });
    }

    function clear_children(el) {
        while (el.firstChild) el.removeChild(el.firstChild);
    }

    function varieties_for_mode(mode) {
        return mode === "seed" ? data.seed_varieties : data.transplant_varieties;
    }

    function lots_for_variety(variety_id) {
        return data.transplant_lots_by_variety[String(variety_id)] || [];
    }

    function armed_lot() {
        if (state.mode !== "transplant" || !state.armed_variety || state.armed_lot_id == null) return null;
        var lots = lots_for_variety(state.armed_variety.id);
        for (var i = 0; i < lots.length; i++) {
            if (lots[i].id === state.armed_lot_id) return lots[i];
        }
        return null;
    }

    function can_stage_more() {
        if (state.mode !== "transplant") return true;
        var lot = armed_lot();
        if (!lot) return false;
        return state.staged_points.length < lot.quantity_on_hand;
    }

    function distance_in(a, b) {
        var dx = a.x_in - b.x_in;
        var dy = a.y_in - b.y_in;
        return Math.sqrt(dx * dx + dy * dy);
    }

    function same_variety_points(variety_id) {
        var persisted = data.plantings.filter(function (p) {
            return p.variety_id === variety_id;
        });
        var staged = state.armed_variety && state.armed_variety.id === variety_id ? state.staged_points : [];
        return persisted.concat(staged);
    }

    function is_blocked(point, variety_id, spacing_in) {
        var occupied = same_variety_points(variety_id);
        for (var i = 0; i < occupied.length; i++) {
            if (distance_in(point, occupied[i]) < spacing_in) return true;
        }
        return false;
    }

    function lattice_start(offset_in, spacing_in) {
        // Normalizes the stored offset (which can be any accumulated inch value, positive or negative)
        // into [0, spacing_in) so the lattice shifts visually without ever starting outside the bed.
        return ((offset_in % spacing_in) + spacing_in) % spacing_in;
    }

    function lattice_points(spacing_in, offset_x_in, offset_y_in) {
        var points = [];
        if (!spacing_in || spacing_in <= 0) return points;
        var start_x = lattice_start(offset_x_in || 0, spacing_in);
        var start_y = lattice_start(offset_y_in || 0, spacing_in);
        for (var x = start_x; x <= data.width_in + 1e-6; x += spacing_in) {
            for (var y = start_y; y <= data.length_in + 1e-6; y += spacing_in) {
                points.push({ x_in: Math.min(x, data.width_in), y_in: Math.min(y, data.length_in) });
            }
        }
        return points;
    }

    function companion_relation(common_name_a, common_name_b) {
        for (var i = 0; i < data.companion_rules.length; i++) {
            var rule = data.companion_rules[i];
            if (
                (rule.a === common_name_a && rule.b === common_name_b) ||
                (rule.a === common_name_b && rule.b === common_name_a)
            ) {
                return rule.relation;
            }
        }
        return null;
    }

    function make_circle(x_in, y_in, r, cls, fill) {
        var circle = document.createElementNS(SVG_NS, "circle");
        circle.setAttribute("cx", x_in);
        circle.setAttribute("cy", y_in);
        circle.setAttribute("r", r);
        if (fill) circle.setAttribute("fill", fill);
        circle.setAttribute("class", cls);
        return circle;
    }

    function toggle_point(point) {
        var index = -1;
        for (var i = 0; i < state.staged_points.length; i++) {
            if (state.staged_points[i].x_in === point.x_in && state.staged_points[i].y_in === point.y_in) {
                index = i;
                break;
            }
        }
        if (index >= 0) {
            state.staged_points.splice(index, 1);
        } else {
            if (!can_stage_more()) return;
            state.staged_points.push(point);
        }
        render_lattice();
    }

    function update_companion_tints() {
        var armed_name = state.armed_variety ? state.armed_variety.common_name : null;
        [planted_layer, staged_layer].forEach(function (layer) {
            var dots = layer.querySelectorAll(".planting-dot");
            for (var i = 0; i < dots.length; i++) {
                var dot = dots[i];
                dot.classList.remove("companion", "antagonist");
                if (!armed_name) continue;
                var other_name = dot.getAttribute("data-common-name") || armed_name;
                var relation = companion_relation(armed_name, other_name);
                if (relation) dot.classList.add(relation);
            }
        });
    }

    function populate_lot_select() {
        clear_children(lot_select);
        var placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Choose a transplant lot";
        lot_select.appendChild(placeholder);
        lots_for_variety(state.armed_variety.id).forEach(function (lot) {
            var option = document.createElement("option");
            option.value = String(lot.id);
            option.textContent = "Lot #" + lot.id + " (" + lot.quantity_on_hand + " on hand)";
            if (lot.id === state.armed_lot_id) option.selected = true;
            lot_select.appendChild(option);
        });
    }

    function sync_lot_quantity_input() {
        var lot = armed_lot();
        lot_quantity_wrap.hidden = !lot;
        if (lot) lot_quantity_input.value = lot.quantity_on_hand;
    }

    function update_batch_form() {
        if (!state.armed_variety) {
            batch_form.hidden = true;
            return;
        }
        batch_form.hidden = false;
        batch_variety_id_input.value = String(state.armed_variety.id);
        batch_source_type_input.value = state.mode;
        batch_points_input.value = JSON.stringify(state.staged_points);
        batch_staged_count.textContent = state.staged_points.length + " point(s) staged";
        lot_select.hidden = state.mode !== "transplant";
        if (state.mode === "transplant") populate_lot_select();
        quantity_per_point_wrap.hidden = state.mode !== "seed";
        sync_lot_quantity_input();
    }

    function render_shade_grid(grid) {
        clear_children(shade_layer);
        if (!grid) return;
        for (var row = 0; row < grid.rows; row++) {
            for (var col = 0; col < grid.cols; col++) {
                var shade = grid.cells[row][col];
                if (shade === "full_sun") continue;
                var rect = document.createElementNS(SVG_NS, "rect");
                rect.setAttribute("x", col * 12);
                rect.setAttribute("y", row * 12);
                rect.setAttribute("width", 12);
                rect.setAttribute("height", 12);
                rect.setAttribute("class", "shade-cell " + shade);
                shade_layer.appendChild(rect);
            }
        }
    }

    function fetch_shade_grid() {
        if (!shade_layer) return;
        var on_date = shade_date_input ? shade_date_input.value : "";
        fetch("/beds/" + data.bed_id + "/shade-grid?on_date=" + encodeURIComponent(on_date))
            .then(function (response) {
                return response.ok ? response.json() : null;
            })
            .then(function (grid) {
                if (grid) render_shade_grid(grid);
            });
    }

    function collect_shade_check_points() {
        var points = [];
        var els = [];
        [lattice_layer, staged_layer].forEach(function (layer) {
            var circles = layer.querySelectorAll("circle");
            for (var i = 0; i < circles.length; i++) {
                var circle = circles[i];
                points.push({ x_in: parseFloat(circle.getAttribute("cx")), y_in: parseFloat(circle.getAttribute("cy")) });
                els.push(circle);
            }
        });
        return { points: points, els: els };
    }

    function fetch_shade_warnings() {
        if (!state.armed_variety || !batch_planted_date_input || !batch_planted_date_input.value) return;
        var collected = collect_shade_check_points();
        if (!collected.points.length) return;
        var variety_id = state.armed_variety.id;
        var planted_date = batch_planted_date_input.value;
        post("/beds/" + data.bed_id + "/shade-warnings", {
            variety_id: String(variety_id),
            planted_date: planted_date,
            points: JSON.stringify(collected.points),
        })
            .then(function (response) {
                return response.ok ? response.json() : null;
            })
            .then(function (result) {
                if (!result) return;
                collected.els.forEach(function (el, i) {
                    el.classList.toggle("shade-warning", !!result.warnings[i]);
                });
                collected.points.forEach(function (point, i) {
                    shade_warning_cache[shade_cache_key(variety_id, planted_date, point.x_in, point.y_in)] =
                        !!result.warnings[i];
                });
            });
    }

    function render_lattice() {
        clear_children(lattice_layer);
        clear_children(staged_layer);
        if (state.armed_variety) {
            var spacing_in = state.armed_variety.spacing_in || DEFAULT_SPACING_IN;
            var radius_in = spacing_in / 2; // adjacent same-variety circles just touch, never overlap
            var planted_date = batch_planted_date_input ? batch_planted_date_input.value : "";
            var cached_warning = function (point) {
                return !!shade_warning_cache[shade_cache_key(state.armed_variety.id, planted_date, point.x_in, point.y_in)];
            };
            lattice_points(spacing_in, data.grid_offset_x_in, data.grid_offset_y_in).forEach(function (point) {
                var blocked = is_blocked(point, state.armed_variety.id, spacing_in);
                var circle = make_circle(point.x_in, point.y_in, radius_in, "lattice-point" + (blocked ? " blocked" : ""));
                if (cached_warning(point)) circle.classList.add("shade-warning");
                if (!blocked) {
                    circle.addEventListener("click", function () {
                        toggle_point(point);
                    });
                }
                lattice_layer.appendChild(circle);
            });
            state.staged_points.forEach(function (point) {
                var dot = make_circle(point.x_in, point.y_in, radius_in, "planting-dot staged", state.armed_variety.color_hex);
                if (cached_warning(point)) dot.classList.add("shade-warning");
                dot.setAttribute("data-common-name", state.armed_variety.common_name);
                // The staged dot sits on top of (and, once staged, always outranks -- see is_blocked)
                // its own lattice point, so unstaging has to be wired here rather than on the lattice
                // circle underneath.
                dot.addEventListener("click", function () {
                    toggle_point(point);
                });
                staged_layer.appendChild(dot);
            });
        }
        update_companion_tints();
        update_batch_form();
        fetch_shade_warnings();
    }

    function highlight_armed_button(variety_id, mode) {
        [palette_seed, palette_transplant].forEach(function (container) {
            if (!container) return;
            var buttons = container.querySelectorAll(".variety-palette-item");
            for (var i = 0; i < buttons.length; i++) {
                var button = buttons[i];
                var matches =
                    button.getAttribute("data-variety-id") === String(variety_id) && button.getAttribute("data-mode") === mode;
                button.classList.toggle("armed", matches);
            }
        });
    }

    function arm_variety(variety_id, mode) {
        var variety = varieties_for_mode(mode).filter(function (v) {
            return v.id === variety_id;
        })[0];
        if (!variety) return;
        state.mode = mode;
        state.armed_variety = variety;
        state.staged_points = [];
        state.armed_lot_id = null;
        if (mode === "transplant") {
            var lots = lots_for_variety(variety_id);
            if (lots.length === 1) state.armed_lot_id = lots[0].id;
        }
        highlight_armed_button(variety_id, mode);
        render_lattice();
    }

    function set_mode(mode) {
        state.mode = mode;
        state.armed_variety = null;
        state.armed_lot_id = null;
        state.staged_points = [];
        if (palette_seed) palette_seed.hidden = mode !== "seed";
        if (palette_transplant) palette_transplant.hidden = mode !== "transplant";
        highlight_armed_button(null, mode);
        render_lattice();
    }

    [palette_seed, palette_transplant].forEach(function (container) {
        if (!container) return;
        container.addEventListener("click", function (e) {
            var button = e.target.closest(".variety-palette-item");
            if (!button) return;
            arm_variety(parseInt(button.getAttribute("data-variety-id"), 10), button.getAttribute("data-mode"));
        });
    });

    if (mode_seed_radio) {
        mode_seed_radio.addEventListener("change", function () {
            if (mode_seed_radio.checked) set_mode("seed");
        });
    }
    if (mode_transplant_radio) {
        mode_transplant_radio.addEventListener("change", function () {
            if (mode_transplant_radio.checked) set_mode("transplant");
        });
    }

    if (lot_select) {
        lot_select.addEventListener("change", function () {
            state.armed_lot_id = lot_select.value ? parseInt(lot_select.value, 10) : null;
            render_lattice();
        });
    }

    if (lot_quantity_input) {
        lot_quantity_input.addEventListener("change", function () {
            var lot = armed_lot();
            if (!lot) return;
            var new_quantity = parseInt(lot_quantity_input.value, 10);
            if (isNaN(new_quantity) || new_quantity < 0) {
                lot_quantity_input.value = lot.quantity_on_hand;
                return;
            }
            post("/transplant-lots/" + lot.id + "/quantity", { quantity_on_hand: new_quantity }).then(function (response) {
                if (!response.ok) {
                    lot_quantity_input.value = lot.quantity_on_hand;
                    return;
                }
                lot.quantity_on_hand = new_quantity;
                if (state.staged_points.length > new_quantity) {
                    state.staged_points = state.staged_points.slice(0, new_quantity);
                }
                render_lattice();
            });
        });
    }

    if (batch_form) {
        batch_form.addEventListener("submit", function (e) {
            var lot = armed_lot();
            if (lot && state.staged_points.length < lot.quantity_on_hand) {
                var confirmed = window.confirm(
                    lot.quantity_on_hand + " left in this lot -- plant them too, or is the count off? " +
                        "(Cancel to go back and correct the on-hand quantity.)"
                );
                if (!confirmed) {
                    e.preventDefault();
                    return;
                }
            }
            batch_points_input.value = JSON.stringify(state.staged_points);
        });
    }

    if (grid_offset_controls) {
        grid_offset_controls.addEventListener("click", function (e) {
            var button = e.target.closest("button");
            if (!button) return;
            post("/beds/" + data.bed_id + "/grid-offset", {
                dx_in: button.getAttribute("data-dx-in"),
                dy_in: button.getAttribute("data-dy-in"),
            })
                .then(function (response) {
                    return response.ok ? response.json() : null;
                })
                .then(function (result) {
                    if (!result) return;
                    data.grid_offset_x_in = result.grid_offset_x_in;
                    data.grid_offset_y_in = result.grid_offset_y_in;
                    render_lattice();
                });
        });
    }

    var ZOOM_MIN_PCT = 50, ZOOM_MAX_PCT = 400, ZOOM_STEP_PCT = 25;
    var zoom_pct = 100;
    var base_px_per_in = null; // the SVG's natural "fit" scale, captured lazily on first zoom

    function apply_zoom() {
        if (zoom_pct === 100) {
            svg.style.width = "";
            svg.style.height = "";
        } else {
            if (base_px_per_in === null) base_px_per_in = svg.getBoundingClientRect().width / data.width_in;
            var px_per_in = base_px_per_in * (zoom_pct / 100);
            svg.style.width = (data.width_in * px_per_in) + "px";
            svg.style.height = (data.length_in * px_per_in) + "px";
        }
        if (zoom_display) zoom_display.textContent = zoom_pct + "%";
    }

    if (zoom_controls) {
        zoom_controls.addEventListener("click", function (e) {
            var button = e.target.closest("button");
            if (!button) return;
            var action = button.getAttribute("data-zoom");
            if (action === "in") zoom_pct = Math.min(ZOOM_MAX_PCT, zoom_pct + ZOOM_STEP_PCT);
            else if (action === "out") zoom_pct = Math.max(ZOOM_MIN_PCT, zoom_pct - ZOOM_STEP_PCT);
            else zoom_pct = 100;
            apply_zoom();
        });
    }

    if (shade_date_input) {
        shade_date_input.addEventListener("change", fetch_shade_grid);
    }
    if (batch_planted_date_input) {
        batch_planted_date_input.addEventListener("change", fetch_shade_warnings);
    }
    fetch_shade_grid();
})();
