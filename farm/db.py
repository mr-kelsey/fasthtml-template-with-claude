from sqlalchemy import text

from farm.helpers import compute_window, inches_to_cell

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
    ("seed_varieties", "soil_type", "TEXT"),
    ("seed_varieties", "soil_ph_min", "REAL"),
    ("seed_varieties", "soil_ph_max", "REAL"),
    ("seed_varieties", "feeding_frequency_days", "INTEGER"),
    ("seed_varieties", "growth_npk_n", "REAL"),
    ("seed_varieties", "growth_npk_p", "REAL"),
    ("seed_varieties", "growth_npk_k", "REAL"),
    ("seed_varieties", "produce_npk_n", "REAL"),
    ("seed_varieties", "produce_npk_p", "REAL"),
    ("seed_varieties", "produce_npk_k", "REAL"),
    """
    CREATE TABLE IF NOT EXISTS seed_lots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        variety_id INTEGER NOT NULL,
        quantity_on_hand INTEGER,
        acquired_date TEXT,
        seed_source TEXT,
        notes TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    ("plantings", "seed_lot_id", "INTEGER"),
    ("plantings", "x_in", "REAL"),
    ("plantings", "y_in", "REAL"),
    """
    UPDATE plantings SET x_in = cell_x * 12, y_in = cell_y * 12
    WHERE x_in IS NULL AND cell_x IS NOT NULL
    """,
    """
    CREATE TABLE IF NOT EXISTS companion_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plant_a_common_name TEXT NOT NULL,
        plant_b_common_name TEXT NOT NULL,
        relation TEXT NOT NULL CHECK (relation IN ('companion', 'antagonist')),
        notes TEXT,
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
    """
    CREATE TABLE IF NOT EXISTS transplant_lots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        variety_id INTEGER NOT NULL,
        quantity_on_hand INTEGER,
        origin_planting_id INTEGER,
        purchased_source TEXT,
        purchased_vendor TEXT,
        purchased_date TEXT,
        notes TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    ("plantings", "transplant_lot_id", "INTEGER"),
    ("plantings", "source_type", "TEXT NOT NULL DEFAULT 'seed'"),
]

_AGRONOMIC_COLUMNS = (
    "germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, "
    "spacing_in, sun_needs, water_needs"
)

_SOIL_FEEDING_COLUMNS = (
    "soil_type, soil_ph_min, soil_ph_max, feeding_frequency_days, "
    "growth_npk_n, growth_npk_p, growth_npk_k, produce_npk_n, produce_npk_p, produce_npk_k"
)

_SEED_VARIETY_COLUMNS = (
    f"id, common_name, name, plant_family, genus, species, {_AGRONOMIC_COLUMNS}, {_SOIL_FEEDING_COLUMNS}, created_at"
)

_PLANTING_COLUMNS = (
    "id, variety_id, bed_id, location, planted_date, quantity, quantity_germinated, notes, "
    "cell_x, cell_y, x_in, y_in, seed_lot_id, transplant_lot_id, source_type, created_at"
)

_SEED_LOT_COLUMNS = "id, variety_id, quantity_on_hand, acquired_date, seed_source, notes, created_at"

_TRANSPLANT_LOT_COLUMNS = (
    "id, variety_id, quantity_on_hand, origin_planting_id, "
    "purchased_source, purchased_vendor, purchased_date, notes, created_at"
)

_COMPANION_RULE_COLUMNS = "id, plant_a_common_name, plant_b_common_name, relation, notes, created_at"

_LAND_PLOT_COLUMNS = "id, name, width_ft, length_ft, created_at"

_BED_COLUMNS = (
    "id, plot_id, label, x, y, width_ft, length_ft, rotation_deg, sun_exposure, irrigation_zone, created_at"
)

_FARM_EVENT_COLUMNS = "fe.id, fe.event_type, fe.title, fe.start_date, fe.end_date, fe.notes, fe.linked_planting_id, fe.created_at"


def _connected_components(rows):
    """Groups rows sharing a (variety, planted_date) key into clusters of 4-directionally adjacent whole-foot
    cells, the cells computed from each row's real x_in/y_in position rather than a stored cell_x/cell_y.
    """
    by_coord = {(inches_to_cell(row["x_in"]), inches_to_cell(row["y_in"])): row for row in rows}
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


def _soil_feeding_fields(
    soil_type: str,
    soil_ph_min: float,
    soil_ph_max: float,
    feeding_frequency_days: int,
    growth_npk_n: float,
    growth_npk_p: float,
    growth_npk_k: float,
    produce_npk_n: float,
    produce_npk_p: float,
    produce_npk_k: float,
):
    "Builds the dict of the soil/feeding columns shared by every seed_varieties row."
    return {
        "soil_type": soil_type or None,
        "soil_ph_min": soil_ph_min,
        "soil_ph_max": soil_ph_max,
        "feeding_frequency_days": feeding_frequency_days,
        "growth_npk_n": growth_npk_n,
        "growth_npk_p": growth_npk_p,
        "growth_npk_k": growth_npk_k,
        "produce_npk_n": produce_npk_n,
        "produce_npk_p": produce_npk_p,
        "produce_npk_k": produce_npk_k,
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
        soil_type: str = None,
        soil_ph_min: float = None,
        soil_ph_max: float = None,
        feeding_frequency_days: int = None,
        growth_npk_n: float = None,
        growth_npk_p: float = None,
        growth_npk_k: float = None,
        produce_npk_n: float = None,
        produce_npk_p: float = None,
        produce_npk_k: float = None,
    ):
        fields = _agronomic_fields(
            germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max,
            spacing_in, sun_needs, water_needs,
        )
        fields.update(_soil_feeding_fields(
            soil_type, soil_ph_min, soil_ph_max, feeding_frequency_days,
            growth_npk_n, growth_npk_p, growth_npk_k, produce_npk_n, produce_npk_p, produce_npk_k,
        ))
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO seed_varieties (common_name, name, plant_family, genus, species, "
                    "germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, "
                    "spacing_in, sun_needs, water_needs, "
                    "soil_type, soil_ph_min, soil_ph_max, feeding_frequency_days, "
                    "growth_npk_n, growth_npk_p, growth_npk_k, produce_npk_n, produce_npk_p, produce_npk_k) "
                    "VALUES (:common_name, :name, :plant_family, :genus, :species, "
                    ":germination_days_min, :germination_days_max, :days_to_maturity_min, :days_to_maturity_max, "
                    ":spacing_in, :sun_needs, :water_needs, "
                    ":soil_type, :soil_ph_min, :soil_ph_max, :feeding_frequency_days, "
                    ":growth_npk_n, :growth_npk_p, :growth_npk_k, :produce_npk_n, :produce_npk_p, :produce_npk_k)"
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
        soil_type: str = None,
        soil_ph_min: float = None,
        soil_ph_max: float = None,
        feeding_frequency_days: int = None,
        growth_npk_n: float = None,
        growth_npk_p: float = None,
        growth_npk_k: float = None,
        produce_npk_n: float = None,
        produce_npk_p: float = None,
        produce_npk_k: float = None,
    ):
        fields = _agronomic_fields(
            germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max,
            spacing_in, sun_needs, water_needs,
        )
        fields.update(_soil_feeding_fields(
            soil_type, soil_ph_min, soil_ph_max, feeding_frequency_days,
            growth_npk_n, growth_npk_p, growth_npk_k, produce_npk_n, produce_npk_p, produce_npk_k,
        ))
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE seed_varieties SET common_name = :common_name, name = :name, "
                    "plant_family = :plant_family, genus = :genus, species = :species, "
                    "germination_days_min = :germination_days_min, germination_days_max = :germination_days_max, "
                    "days_to_maturity_min = :days_to_maturity_min, days_to_maturity_max = :days_to_maturity_max, "
                    "spacing_in = :spacing_in, sun_needs = :sun_needs, water_needs = :water_needs, "
                    "soil_type = :soil_type, soil_ph_min = :soil_ph_min, soil_ph_max = :soil_ph_max, "
                    "feeding_frequency_days = :feeding_frequency_days, "
                    "growth_npk_n = :growth_npk_n, growth_npk_p = :growth_npk_p, growth_npk_k = :growth_npk_k, "
                    "produce_npk_n = :produce_npk_n, produce_npk_p = :produce_npk_p, produce_npk_k = :produce_npk_k "
                    "WHERE id = :id"
                ),
                {
                    "id": variety_id, "common_name": common_name, "name": name, "plant_family": plant_family,
                    "genus": genus or None, "species": species or None, **fields,
                },
            )

    def delete_seed_variety(self, variety_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM seed_varieties WHERE id = :id"), {"id": variety_id})

    def list_seed_lots_for_variety(self, variety_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_SEED_LOT_COLUMNS} FROM seed_lots WHERE variety_id = :variety_id "
                    "ORDER BY acquired_date DESC, id DESC"
                ),
                {"variety_id": variety_id},
            ).mappings().all()

    def get_seed_lot(self, seed_lot_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_SEED_LOT_COLUMNS} FROM seed_lots WHERE id = :id"),
                {"id": seed_lot_id},
            ).mappings().first()

    def add_seed_lot(
        self,
        variety_id: int,
        quantity_on_hand: int = None,
        acquired_date: str = None,
        seed_source: str = None,
        notes: str = None,
    ):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO seed_lots (variety_id, quantity_on_hand, acquired_date, seed_source, notes) "
                    "VALUES (:variety_id, :quantity_on_hand, :acquired_date, :seed_source, :notes)"
                ),
                {
                    "variety_id": variety_id, "quantity_on_hand": quantity_on_hand,
                    "acquired_date": acquired_date or None, "seed_source": seed_source or None,
                    "notes": notes or None,
                },
            )

    def update_seed_lot(
        self,
        seed_lot_id: int,
        quantity_on_hand: int = None,
        acquired_date: str = None,
        seed_source: str = None,
        notes: str = None,
    ):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE seed_lots SET quantity_on_hand = :quantity_on_hand, acquired_date = :acquired_date, "
                    "seed_source = :seed_source, notes = :notes WHERE id = :id"
                ),
                {
                    "id": seed_lot_id, "quantity_on_hand": quantity_on_hand,
                    "acquired_date": acquired_date or None, "seed_source": seed_source or None,
                    "notes": notes or None,
                },
            )

    def delete_seed_lot(self, seed_lot_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM seed_lots WHERE id = :id"), {"id": seed_lot_id})

    def list_seed_lots(self):
        "Every seed lot across every variety, joined for display; list_seed_lots_for_variety scopes to one variety."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT sl.id, sl.variety_id, sl.quantity_on_hand, sl.acquired_date, sl.seed_source, "
                    "sl.notes, sl.created_at, sv.name AS variety_name, sv.common_name "
                    "FROM seed_lots sl LEFT JOIN seed_varieties sv ON sv.id = sl.variety_id "
                    "ORDER BY sv.common_name, sv.name, sl.acquired_date DESC, sl.id DESC"
                )
            ).mappings().all()

    def list_transplant_lots_for_variety(self, variety_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_TRANSPLANT_LOT_COLUMNS} FROM transplant_lots WHERE variety_id = :variety_id "
                    "ORDER BY purchased_date DESC, id DESC"
                ),
                {"variety_id": variety_id},
            ).mappings().all()

    def list_transplant_lots(self):
        "Every transplant lot across every variety, joined for display."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT tl.id, tl.variety_id, tl.quantity_on_hand, tl.origin_planting_id, "
                    "tl.purchased_source, tl.purchased_vendor, tl.purchased_date, tl.notes, tl.created_at, "
                    "sv.name AS variety_name, sv.common_name "
                    "FROM transplant_lots tl LEFT JOIN seed_varieties sv ON sv.id = tl.variety_id "
                    "ORDER BY sv.common_name, sv.name, tl.purchased_date DESC, tl.id DESC"
                )
            ).mappings().all()

    def get_transplant_lot(self, transplant_lot_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_TRANSPLANT_LOT_COLUMNS} FROM transplant_lots WHERE id = :id"),
                {"id": transplant_lot_id},
            ).mappings().first()

    def add_transplant_lot(
        self,
        variety_id: int,
        quantity_on_hand: int = None,
        origin_planting_id: int = None,
        purchased_source: str = None,
        purchased_vendor: str = None,
        purchased_date: str = None,
        notes: str = None,
    ):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO transplant_lots (variety_id, quantity_on_hand, origin_planting_id, "
                    "purchased_source, purchased_vendor, purchased_date, notes) "
                    "VALUES (:variety_id, :quantity_on_hand, :origin_planting_id, "
                    ":purchased_source, :purchased_vendor, :purchased_date, :notes)"
                ),
                {
                    "variety_id": variety_id, "quantity_on_hand": quantity_on_hand,
                    "origin_planting_id": origin_planting_id, "purchased_source": purchased_source or None,
                    "purchased_vendor": purchased_vendor or None, "purchased_date": purchased_date or None,
                    "notes": notes or None,
                },
            )

    def update_transplant_lot(
        self,
        transplant_lot_id: int,
        quantity_on_hand: int = None,
        origin_planting_id: int = None,
        purchased_source: str = None,
        purchased_vendor: str = None,
        purchased_date: str = None,
        notes: str = None,
    ):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE transplant_lots SET quantity_on_hand = :quantity_on_hand, "
                    "origin_planting_id = :origin_planting_id, purchased_source = :purchased_source, "
                    "purchased_vendor = :purchased_vendor, purchased_date = :purchased_date, notes = :notes "
                    "WHERE id = :id"
                ),
                {
                    "id": transplant_lot_id, "quantity_on_hand": quantity_on_hand,
                    "origin_planting_id": origin_planting_id, "purchased_source": purchased_source or None,
                    "purchased_vendor": purchased_vendor or None, "purchased_date": purchased_date or None,
                    "notes": notes or None,
                },
            )

    def delete_transplant_lot(self, transplant_lot_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM transplant_lots WHERE id = :id"), {"id": transplant_lot_id})

    def list_companion_rules(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_COMPANION_RULE_COLUMNS} FROM companion_rules "
                    "ORDER BY plant_a_common_name, plant_b_common_name"
                )
            ).mappings().all()

    def get_companion_rule(self, rule_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_COMPANION_RULE_COLUMNS} FROM companion_rules WHERE id = :id"),
                {"id": rule_id},
            ).mappings().first()

    def add_companion_rule(self, plant_a_common_name: str, plant_b_common_name: str, relation: str, notes: str = None):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO companion_rules (plant_a_common_name, plant_b_common_name, relation, notes) "
                    "VALUES (:plant_a_common_name, :plant_b_common_name, :relation, :notes)"
                ),
                {
                    "plant_a_common_name": plant_a_common_name, "plant_b_common_name": plant_b_common_name,
                    "relation": relation, "notes": notes or None,
                },
            )

    def delete_companion_rule(self, rule_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM companion_rules WHERE id = :id"), {"id": rule_id})

    def list_plantings(self):
        "Joined with seed_varieties so callers get the variety's common name and maturity data for expected-window math."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT p.id, p.variety_id, p.bed_id, p.location, p.planted_date, p.quantity, "
                    "p.quantity_germinated, p.notes, p.cell_x, p.cell_y, p.x_in, p.y_in, p.seed_lot_id, "
                    "p.transplant_lot_id, p.source_type, p.created_at, "
                    "sv.name AS variety_name, sv.common_name, "
                    "sv.germination_days_min, sv.germination_days_max, "
                    "sv.days_to_maturity_min, sv.days_to_maturity_max "
                    "FROM plantings p "
                    "LEFT JOIN seed_varieties sv ON sv.id = p.variety_id "
                    "ORDER BY p.planted_date DESC, p.id DESC"
                )
            ).mappings().all()

    def list_plantings_for_bed(self, bed_id: int):
        "Joined with seed_varieties, like list_plantings, but scoped to one bed's positioned plantings."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT p.id, p.variety_id, p.bed_id, p.location, p.planted_date, p.quantity, "
                    "p.quantity_germinated, p.notes, p.cell_x, p.cell_y, p.x_in, p.y_in, p.seed_lot_id, "
                    "p.transplant_lot_id, p.source_type, p.created_at, "
                    "sv.name AS variety_name, sv.common_name, "
                    "sv.germination_days_min, sv.germination_days_max, "
                    "sv.days_to_maturity_min, sv.days_to_maturity_max "
                    "FROM plantings p "
                    "LEFT JOIN seed_varieties sv ON sv.id = p.variety_id "
                    "WHERE p.bed_id = :bed_id "
                    "ORDER BY p.y_in, p.x_in"
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
        """A cell can hold more than one planting -- e.g. interplanting carrots and tomatoes in the same square.
        The cell is a computed bucket of each planting's real x_in/y_in position, not a stored column.
        """
        return [
            planting
            for planting in self.list_plantings_for_bed(bed_id)
            if planting["x_in"] is not None
            and inches_to_cell(planting["x_in"]) == cell_x
            and inches_to_cell(planting["y_in"]) == cell_y
        ]

    @staticmethod
    def _normalize_planting_fields(
        bed_id, location, quantity, quantity_germinated, notes, x_in=None, y_in=None, seed_lot_id=None,
        transplant_lot_id=None, source_type="seed",
    ):
        return {
            "bed_id": bed_id,
            "location": location or None,
            "quantity": quantity,
            "quantity_germinated": quantity_germinated,
            "notes": notes or None,
            "x_in": x_in,
            "y_in": y_in,
            "seed_lot_id": seed_lot_id,
            "transplant_lot_id": transplant_lot_id,
            "source_type": source_type,
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
        x_in: float = None,
        y_in: float = None,
        seed_lot_id: int = None,
        transplant_lot_id: int = None,
        source_type: str = "seed",
    ):
        "Returns the new planting's id. Regenerates its (or its bed's) linked farm_events."
        fields = self._normalize_planting_fields(
            bed_id, location, quantity, quantity_germinated, notes, x_in, y_in, seed_lot_id,
            transplant_lot_id, source_type,
        )
        with self.engine.begin() as db_connection:
            result = db_connection.execute(
                text(
                    "INSERT INTO plantings (variety_id, bed_id, location, planted_date, quantity, "
                    "quantity_germinated, notes, x_in, y_in, seed_lot_id, transplant_lot_id, source_type) "
                    "VALUES (:variety_id, :bed_id, :location, :planted_date, :quantity, "
                    ":quantity_germinated, :notes, :x_in, :y_in, :seed_lot_id, :transplant_lot_id, :source_type)"
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
        x_in: float = None,
        y_in: float = None,
        seed_lot_id: int = None,
        transplant_lot_id: int = None,
        source_type: str = "seed",
    ):
        fields = self._normalize_planting_fields(
            bed_id, location, quantity, quantity_germinated, notes, x_in, y_in, seed_lot_id,
            transplant_lot_id, source_type,
        )
        with self.engine.begin() as db_connection:
            old_bed_id = db_connection.execute(
                text("SELECT bed_id FROM plantings WHERE id = :id"), {"id": planting_id}
            ).scalar()
            db_connection.execute(
                text(
                    "UPDATE plantings SET variety_id = :variety_id, planted_date = :planted_date, "
                    "bed_id = :bed_id, location = :location, quantity = :quantity, "
                    "quantity_germinated = :quantity_germinated, notes = :notes, "
                    "x_in = :x_in, y_in = :y_in, seed_lot_id = :seed_lot_id, "
                    "transplant_lot_id = :transplant_lot_id, source_type = :source_type WHERE id = :id"
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
                "SELECT p.id, p.variety_id, p.planted_date, p.x_in, p.y_in, "
                "sv.common_name, sv.name, sv.germination_days_min, sv.germination_days_max, "
                "sv.days_to_maturity_min, sv.days_to_maturity_max "
                "FROM plantings p JOIN seed_varieties sv ON sv.id = p.variety_id "
                "WHERE p.bed_id = :bed_id AND p.x_in IS NOT NULL AND p.y_in IS NOT NULL"
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
