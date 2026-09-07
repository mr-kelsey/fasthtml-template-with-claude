from sqlalchemy import text

from farm.helpers import compute_window

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS seed_varieties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        common_name TEXT NOT NULL,
        name TEXT NOT NULL,
        plant_family TEXT NOT NULL,
        genus TEXT,
        species TEXT,
        germination_days_min INTEGER,
        germination_days_max INTEGER,
        days_to_maturity_min INTEGER,
        days_to_maturity_max INTEGER,
        spacing_in INTEGER,
        sun_needs TEXT,
        water_needs TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plantings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        variety_id INTEGER NOT NULL,
        bed_id INTEGER,
        location TEXT,
        planted_date TEXT NOT NULL,
        quantity INTEGER,
        quantity_germinated INTEGER,
        notes TEXT,
        cell_x INTEGER,
        cell_y INTEGER,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS land_plots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        width_ft INTEGER NOT NULL,
        length_ft INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS beds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        x INTEGER,
        y INTEGER,
        width_ft INTEGER NOT NULL,
        length_ft INTEGER NOT NULL,
        rotation_deg INTEGER NOT NULL DEFAULT 0,
        sun_exposure TEXT,
        irrigation_zone TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS farm_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        title TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        notes TEXT,
        linked_planting_id INTEGER,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

_AGRONOMIC_COLUMNS = (
    "germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, "
    "spacing_in, sun_needs, water_needs"
)

_SEED_VARIETY_COLUMNS = f"id, common_name, name, plant_family, genus, species, {_AGRONOMIC_COLUMNS}, created_at"

_PLANTING_COLUMNS = (
    "id, variety_id, bed_id, location, planted_date, quantity, quantity_germinated, notes, "
    "cell_x, cell_y, created_at"
)

_LAND_PLOT_COLUMNS = "id, name, width_ft, length_ft, created_at"

_BED_COLUMNS = (
    "id, plot_id, label, x, y, width_ft, length_ft, rotation_deg, sun_exposure, irrigation_zone, created_at"
)

_FARM_EVENT_COLUMNS = "fe.id, fe.event_type, fe.title, fe.start_date, fe.end_date, fe.notes, fe.linked_planting_id, fe.created_at"


def _connected_components(rows):
    "Groups rows sharing a (variety, planted_date) key into clusters of 4-directionally adjacent (cell_x, cell_y)."
    by_coord = {(row["cell_x"], row["cell_y"]): row for row in rows}
    visited = set()
    clusters = []
    for coord in by_coord:
        if coord in visited:
            continue
        cluster = []
        queue = [coord]
        visited.add(coord)
        while queue:
            current = queue.pop()
            cluster.append(by_coord[current])
            x, y = current
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor in by_coord and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        clusters.append(cluster)
    return clusters


def _agronomic_fields(
    germination_days_min: int,
    germination_days_max: int,
    days_to_maturity_min: int,
    days_to_maturity_max: int,
    spacing_in: int,
    sun_needs: str,
    water_needs: str,
):
    "Builds the dict of the 5 numeric + 2 text agronomic columns shared by every seed_varieties row."
    return {
        "germination_days_min": germination_days_min,
        "germination_days_max": germination_days_max,
        "days_to_maturity_min": days_to_maturity_min,
        "days_to_maturity_max": days_to_maturity_max,
        "spacing_in": spacing_in,
        "sun_needs": sun_needs or None,
        "water_needs": water_needs or None,
    }


class FarmDatabaseMixin:
    "Farm-planning schema (seed_varieties/plantings/land_plots/beds/farm_events) and queries. Relies on self.engine from the core Database."

    SCHEMA_STATEMENTS = SCHEMA_STATEMENTS

    def list_seed_varieties(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_SEED_VARIETY_COLUMNS} FROM seed_varieties ORDER BY common_name, name")
            ).mappings().all()

    def get_seed_variety(self, variety_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_SEED_VARIETY_COLUMNS} FROM seed_varieties WHERE id = :id"),
                {"id": variety_id},
            ).mappings().first()

    def add_seed_variety(
        self,
        common_name: str,
        name: str,
        plant_family: str,
        genus: str = None,
        species: str = None,
        germination_days_min: int = None,
        germination_days_max: int = None,
        days_to_maturity_min: int = None,
        days_to_maturity_max: int = None,
        spacing_in: int = None,
        sun_needs: str = None,
        water_needs: str = None,
    ):
        fields = _agronomic_fields(
            germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max,
            spacing_in, sun_needs, water_needs,
        )
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO seed_varieties (common_name, name, plant_family, genus, species, "
                    "germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, "
                    "spacing_in, sun_needs, water_needs) "
                    "VALUES (:common_name, :name, :plant_family, :genus, :species, "
                    ":germination_days_min, :germination_days_max, :days_to_maturity_min, :days_to_maturity_max, "
                    ":spacing_in, :sun_needs, :water_needs)"
                ),
                {
                    "common_name": common_name, "name": name, "plant_family": plant_family,
                    "genus": genus or None, "species": species or None, **fields,
                },
            )

    def update_seed_variety(
        self,
        variety_id: int,
        common_name: str,
        name: str,
        plant_family: str,
        genus: str = None,
        species: str = None,
        germination_days_min: int = None,
        germination_days_max: int = None,
        days_to_maturity_min: int = None,
        days_to_maturity_max: int = None,
        spacing_in: int = None,
        sun_needs: str = None,
        water_needs: str = None,
    ):
        fields = _agronomic_fields(
            germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max,
            spacing_in, sun_needs, water_needs,
        )
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE seed_varieties SET common_name = :common_name, name = :name, "
                    "plant_family = :plant_family, genus = :genus, species = :species, "
                    "germination_days_min = :germination_days_min, germination_days_max = :germination_days_max, "
                    "days_to_maturity_min = :days_to_maturity_min, days_to_maturity_max = :days_to_maturity_max, "
                    "spacing_in = :spacing_in, sun_needs = :sun_needs, water_needs = :water_needs WHERE id = :id"
                ),
                {
                    "id": variety_id, "common_name": common_name, "name": name, "plant_family": plant_family,
                    "genus": genus or None, "species": species or None, **fields,
                },
            )

    def delete_seed_variety(self, variety_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM seed_varieties WHERE id = :id"), {"id": variety_id})

    def list_plantings(self):
        "Joined with seed_varieties so callers get the variety's common name and maturity data for expected-window math."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT p.id, p.variety_id, p.bed_id, p.location, p.planted_date, p.quantity, "
                    "p.quantity_germinated, p.notes, p.cell_x, p.cell_y, p.created_at, "
                    "sv.name AS variety_name, sv.common_name, "
                    "sv.germination_days_min, sv.germination_days_max, "
                    "sv.days_to_maturity_min, sv.days_to_maturity_max "
                    "FROM plantings p "
                    "LEFT JOIN seed_varieties sv ON sv.id = p.variety_id "
                    "ORDER BY p.planted_date DESC, p.id DESC"
                )
            ).mappings().all()

    def list_plantings_for_bed(self, bed_id: int):
        "Joined with seed_varieties, like list_plantings, but scoped to one bed's cell-assigned plantings."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT p.id, p.variety_id, p.bed_id, p.location, p.planted_date, p.quantity, "
                    "p.quantity_germinated, p.notes, p.cell_x, p.cell_y, p.created_at, "
                    "sv.name AS variety_name, sv.common_name, "
                    "sv.germination_days_min, sv.germination_days_max, "
                    "sv.days_to_maturity_min, sv.days_to_maturity_max "
                    "FROM plantings p "
                    "LEFT JOIN seed_varieties sv ON sv.id = p.variety_id "
                    "WHERE p.bed_id = :bed_id "
                    "ORDER BY p.cell_y, p.cell_x"
                ),
                {"bed_id": bed_id},
            ).mappings().all()

    def get_planting(self, planting_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_PLANTING_COLUMNS} FROM plantings WHERE id = :id"),
                {"id": planting_id},
            ).mappings().first()

    def list_plantings_at_cell(self, bed_id: int, cell_x: int, cell_y: int):
        "A cell can hold more than one planting -- e.g. interplanting carrots and tomatoes in the same square."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT p.id, p.variety_id, p.bed_id, p.location, p.planted_date, p.quantity, "
                    "p.quantity_germinated, p.notes, p.cell_x, p.cell_y, p.created_at, "
                    "sv.name AS variety_name, sv.common_name, "
                    "sv.germination_days_min, sv.germination_days_max, "
                    "sv.days_to_maturity_min, sv.days_to_maturity_max "
                    "FROM plantings p "
                    "LEFT JOIN seed_varieties sv ON sv.id = p.variety_id "
                    "WHERE p.bed_id = :bed_id AND p.cell_x = :cell_x AND p.cell_y = :cell_y "
                    "ORDER BY p.id"
                ),
                {"bed_id": bed_id, "cell_x": cell_x, "cell_y": cell_y},
            ).mappings().all()

    @staticmethod
    def _normalize_planting_fields(bed_id, location, quantity, quantity_germinated, notes, cell_x=None, cell_y=None):
        return {
            "bed_id": bed_id,
            "location": location or None,
            "quantity": quantity,
            "quantity_germinated": quantity_germinated,
            "notes": notes or None,
            "cell_x": cell_x,
            "cell_y": cell_y,
        }

    def add_planting(
        self,
        variety_id: int,
        planted_date: str,
        bed_id: int = None,
        location: str = None,
        quantity: int = None,
        quantity_germinated: int = None,
        notes: str = None,
        cell_x: int = None,
        cell_y: int = None,
    ):
        "Returns the new planting's id. Regenerates its (or its bed's) linked farm_events."
        fields = self._normalize_planting_fields(bed_id, location, quantity, quantity_germinated, notes, cell_x, cell_y)
        with self.engine.begin() as db_connection:
            result = db_connection.execute(
                text(
                    "INSERT INTO plantings (variety_id, bed_id, location, planted_date, quantity, "
                    "quantity_germinated, notes, cell_x, cell_y) "
                    "VALUES (:variety_id, :bed_id, :location, :planted_date, :quantity, "
                    ":quantity_germinated, :notes, :cell_x, :cell_y)"
                ),
                {"variety_id": variety_id, "planted_date": planted_date, **fields},
            )
            planting_id = result.lastrowid
            if bed_id is not None:
                self._regenerate_bed_farm_events(db_connection, bed_id)
            else:
                self._regenerate_farm_events(db_connection, planting_id, variety_id, planted_date)
        return planting_id

    def update_planting(
        self,
        planting_id: int,
        variety_id: int,
        planted_date: str,
        bed_id: int = None,
        location: str = None,
        quantity: int = None,
        quantity_germinated: int = None,
        notes: str = None,
        cell_x: int = None,
        cell_y: int = None,
    ):
        fields = self._normalize_planting_fields(bed_id, location, quantity, quantity_germinated, notes, cell_x, cell_y)
        with self.engine.begin() as db_connection:
            old_bed_id = db_connection.execute(
                text("SELECT bed_id FROM plantings WHERE id = :id"), {"id": planting_id}
            ).scalar()
            db_connection.execute(
                text(
                    "UPDATE plantings SET variety_id = :variety_id, planted_date = :planted_date, "
                    "bed_id = :bed_id, location = :location, quantity = :quantity, "
                    "quantity_germinated = :quantity_germinated, notes = :notes, "
                    "cell_x = :cell_x, cell_y = :cell_y WHERE id = :id"
                ),
                {"id": planting_id, "variety_id": variety_id, "planted_date": planted_date, **fields},
            )
            if bed_id is not None:
                self._regenerate_bed_farm_events(db_connection, bed_id)
            else:
                self._regenerate_farm_events(db_connection, planting_id, variety_id, planted_date)
            if old_bed_id is not None and old_bed_id != bed_id:
                self._regenerate_bed_farm_events(db_connection, old_bed_id)

    def delete_planting(self, planting_id: int):
        with self.engine.begin() as db_connection:
            bed_id = db_connection.execute(
                text("SELECT bed_id FROM plantings WHERE id = :id"), {"id": planting_id}
            ).scalar()
            db_connection.execute(text("DELETE FROM farm_events WHERE linked_planting_id = :id"), {"id": planting_id})
            db_connection.execute(text("DELETE FROM plantings WHERE id = :id"), {"id": planting_id})
            if bed_id is not None:
                self._regenerate_bed_farm_events(db_connection, bed_id)

    def _insert_farm_event_row(self, db_connection, event_type, title, start_date, end_date, linked_planting_id, notes=None):
        db_connection.execute(
            text(
                "INSERT INTO farm_events (event_type, title, start_date, end_date, notes, linked_planting_id) "
                "VALUES (:event_type, :title, :start_date, :end_date, :notes, :linked_planting_id)"
            ),
            {
                "event_type": event_type, "title": title, "start_date": start_date, "end_date": end_date,
                "notes": notes, "linked_planting_id": linked_planting_id,
            },
        )

    def _insert_milestone_events(self, db_connection, linked_planting_id, variety, planted_date, variety_label):
        "Inserts germination-check/harvest rows for a variety's day-range fields, skipping any window that's unknown."
        germination_window = compute_window(
            planted_date, variety["germination_days_min"], variety["germination_days_max"]
        )
        if germination_window:
            self._insert_farm_event_row(
                db_connection, "germination-check", f"Check germination: {variety_label}",
                germination_window[0].isoformat(), germination_window[1].isoformat(), linked_planting_id,
            )
        harvest_window = compute_window(planted_date, variety["days_to_maturity_min"], variety["days_to_maturity_max"])
        if harvest_window:
            self._insert_farm_event_row(
                db_connection, "harvest", f"Expected harvest: {variety_label}",
                harvest_window[0].isoformat(), harvest_window[1].isoformat(), linked_planting_id,
            )

    def _regenerate_farm_events(self, db_connection, planting_id, variety_id, planted_date):
        "Non-bed path: one planting maps to up to one germination-check/harvest event pair, linked to itself."
        db_connection.execute(text("DELETE FROM farm_events WHERE linked_planting_id = :id"), {"id": planting_id})
        variety = db_connection.execute(
            text(f"SELECT {_SEED_VARIETY_COLUMNS} FROM seed_varieties WHERE id = :id"), {"id": variety_id}
        ).mappings().first()
        if variety is None:
            return
        variety_label = f"{variety['common_name']} - {variety['name']}"
        self._insert_milestone_events(db_connection, planting_id, variety, planted_date, variety_label)

    def _regenerate_bed_farm_events(self, db_connection, bed_id):
        """Bed-cell path: recomputes every event for the bed from scratch. Cell-plantings sharing a
        (variety, planted_date) key and 4-directionally adjacent cells collapse into one event pair,
        linked to the lowest planting id in that cluster -- so an edit anywhere in the bed can only be
        gotten right by throwing away and rebuilding the whole bed's events, not patching one planting.
        """
        db_connection.execute(
            text("DELETE FROM farm_events WHERE linked_planting_id IN (SELECT id FROM plantings WHERE bed_id = :bed_id)"),
            {"bed_id": bed_id},
        )
        cell_plantings = db_connection.execute(
            text(
                "SELECT p.id, p.variety_id, p.planted_date, p.cell_x, p.cell_y, "
                "sv.common_name, sv.name, sv.germination_days_min, sv.germination_days_max, "
                "sv.days_to_maturity_min, sv.days_to_maturity_max "
                "FROM plantings p JOIN seed_varieties sv ON sv.id = p.variety_id "
                "WHERE p.bed_id = :bed_id AND p.cell_x IS NOT NULL AND p.cell_y IS NOT NULL"
            ),
            {"bed_id": bed_id},
        ).mappings().all()
        groups = {}
        for row in cell_plantings:
            groups.setdefault((row["variety_id"], row["planted_date"]), []).append(row)
        for (_variety_id, planted_date), rows in groups.items():
            for cluster in _connected_components(rows):
                anchor = min(cluster, key=lambda row: row["id"])
                variety_label = f"{anchor['common_name']} - {anchor['name']}"
                self._insert_milestone_events(db_connection, anchor["id"], anchor, planted_date, variety_label)

    def add_farm_event(
        self, event_type: str, title: str, start_date: str, end_date: str, notes: str = None, linked_planting_id: int = None
    ):
        with self.engine.begin() as db_connection:
            self._insert_farm_event_row(
                db_connection, event_type, title, start_date, end_date, linked_planting_id, notes=notes
            )

    def list_farm_events_in_range(self, range_start: str, range_end: str):
        "Events whose [start_date, end_date] overlaps [range_start, range_end], inclusive."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_FARM_EVENT_COLUMNS}, sv.name AS variety_name, sv.common_name AS variety_common_name, "
                    "b.label AS bed_label, p.bed_id AS planting_bed_id "
                    "FROM farm_events fe "
                    "LEFT JOIN plantings p ON p.id = fe.linked_planting_id "
                    "LEFT JOIN seed_varieties sv ON sv.id = p.variety_id "
                    "LEFT JOIN beds b ON b.id = p.bed_id "
                    "WHERE fe.start_date <= :range_end AND fe.end_date >= :range_start "
                    "ORDER BY fe.start_date"
                ),
                {"range_start": range_start, "range_end": range_end},
            ).mappings().all()

    def get_farm_event(self, event_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_FARM_EVENT_COLUMNS} FROM farm_events fe WHERE fe.id = :id"), {"id": event_id}
            ).mappings().first()

    def delete_farm_event(self, event_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM farm_events WHERE id = :id"), {"id": event_id})

    def list_land_plots(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_LAND_PLOT_COLUMNS} FROM land_plots ORDER BY name")
            ).mappings().all()

    def get_land_plot(self, plot_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_LAND_PLOT_COLUMNS} FROM land_plots WHERE id = :id"),
                {"id": plot_id},
            ).mappings().first()

    def add_land_plot(self, name: str, width_ft: int, length_ft: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("INSERT INTO land_plots (name, width_ft, length_ft) VALUES (:name, :width_ft, :length_ft)"),
                {"name": name, "width_ft": width_ft, "length_ft": length_ft},
            )

    def update_land_plot(self, plot_id: int, name: str, width_ft: int, length_ft: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE land_plots SET name = :name, width_ft = :width_ft, length_ft = :length_ft "
                    "WHERE id = :id"
                ),
                {"id": plot_id, "name": name, "width_ft": width_ft, "length_ft": length_ft},
            )

    def delete_land_plot(self, plot_id: int):
        "Deletes the plot's beds and the plot itself in one transaction -- there's no FK ON DELETE CASCADE."
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM beds WHERE plot_id = :plot_id"), {"plot_id": plot_id})
            db_connection.execute(text("DELETE FROM land_plots WHERE id = :id"), {"id": plot_id})

    def list_beds_for_plot(self, plot_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_BED_COLUMNS} FROM beds WHERE plot_id = :plot_id ORDER BY label"),
                {"plot_id": plot_id},
            ).mappings().all()

    def get_bed(self, bed_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_BED_COLUMNS} FROM beds WHERE id = :id"), {"id": bed_id}
            ).mappings().first()

    def add_bed(
        self,
        plot_id: int,
        label: str,
        width_ft: int,
        length_ft: int,
        sun_exposure: str = None,
        irrigation_zone: str = None,
    ):
        "New beds start unplaced (x/y NULL) until dragged or 'added to map'."
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO beds (plot_id, label, width_ft, length_ft, sun_exposure, irrigation_zone) "
                    "VALUES (:plot_id, :label, :width_ft, :length_ft, :sun_exposure, :irrigation_zone)"
                ),
                {
                    "plot_id": plot_id, "label": label, "width_ft": width_ft, "length_ft": length_ft,
                    "sun_exposure": sun_exposure or None, "irrigation_zone": irrigation_zone or None,
                },
            )

    def update_bed(
        self,
        bed_id: int,
        label: str,
        width_ft: int,
        length_ft: int,
        rotation_deg: int,
        sun_exposure: str = None,
        irrigation_zone: str = None,
    ):
        "Full edit of a bed's metadata/size/rotation -- does not touch position, see update_bed_position."
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE beds SET label = :label, width_ft = :width_ft, length_ft = :length_ft, "
                    "rotation_deg = :rotation_deg, sun_exposure = :sun_exposure, irrigation_zone = :irrigation_zone "
                    "WHERE id = :id"
                ),
                {
                    "id": bed_id, "label": label, "width_ft": width_ft, "length_ft": length_ft,
                    "rotation_deg": rotation_deg, "sun_exposure": sun_exposure or None,
                    "irrigation_zone": irrigation_zone or None,
                },
            )

    def update_bed_position(self, bed_id: int, x: int, y: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("UPDATE beds SET x = :x, y = :y WHERE id = :id"), {"id": bed_id, "x": x, "y": y}
            )

    def update_bed_size(self, bed_id: int, width_ft: int, length_ft: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("UPDATE beds SET width_ft = :width_ft, length_ft = :length_ft WHERE id = :id"),
                {"id": bed_id, "width_ft": width_ft, "length_ft": length_ft},
            )

    def delete_bed(self, bed_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM beds WHERE id = :id"), {"id": bed_id})
