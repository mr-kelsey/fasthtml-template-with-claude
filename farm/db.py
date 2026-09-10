from datetime import date, timedelta

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
    ("seed_varieties", "color_hex", "TEXT"),
    ("plantings", "soil_temp_f", "REAL"),
    """
    CREATE TABLE IF NOT EXISTS garden_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        product_type TEXT,
        npk_n REAL,
        npk_p REAL,
        npk_k REAL,
        benefit_notes TEXT,
        application_frequency_days INTEGER,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS product_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        applied_date TEXT NOT NULL,
        bed_id INTEGER,
        location TEXT,
        amount REAL,
        unit TEXT,
        notes TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    ("farm_events", "linked_product_application_id", "INTEGER"),
    ("plantings", "quantity_culled", "INTEGER"),
    """
    CREATE TABLE IF NOT EXISTS harvests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        planting_id INTEGER NOT NULL,
        harvest_date TEXT NOT NULL,
        weight_lb REAL NOT NULL,
        notes TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shade_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shade_polygons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shade_source_id INTEGER NOT NULL,
        season TEXT NOT NULL CHECK (season IN ('summer_solstice', 'winter_solstice')),
        shade_type TEXT NOT NULL CHECK (shade_type IN ('full', 'partial')),
        points TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (shade_source_id, season, shade_type)
    )
    """,
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
    f"id, common_name, name, plant_family, genus, species, {_AGRONOMIC_COLUMNS}, {_SOIL_FEEDING_COLUMNS}, "
    "color_hex, created_at"
)

_PLANTING_COLUMNS = (
    "id, variety_id, bed_id, location, planted_date, quantity, quantity_germinated, quantity_culled, notes, "
    "cell_x, cell_y, x_in, y_in, seed_lot_id, transplant_lot_id, source_type, soil_temp_f, created_at"
)

_HARVEST_COLUMNS = "id, planting_id, harvest_date, weight_lb, notes, created_at"

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

_GARDEN_PRODUCT_COLUMNS = (
    "id, name, product_type, npk_n, npk_p, npk_k, benefit_notes, application_frequency_days, created_at"
)

_PRODUCT_APPLICATION_COLUMNS = (
    "id, product_id, applied_date, bed_id, location, amount, unit, notes, created_at"
)

_SHADE_SOURCE_COLUMNS = "id, plot_id, label, created_at"

_SHADE_POLYGON_COLUMNS = "id, shade_source_id, season, shade_type, points, created_at"

_FARM_EVENT_COLUMNS = (
    "fe.id, fe.event_type, fe.title, fe.start_date, fe.end_date, fe.notes, "
    "fe.linked_planting_id, fe.linked_product_application_id, fe.created_at"
)


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
        color_hex: str = None,
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
                    "growth_npk_n, growth_npk_p, growth_npk_k, produce_npk_n, produce_npk_p, produce_npk_k, "
                    "color_hex) "
                    "VALUES (:common_name, :name, :plant_family, :genus, :species, "
                    ":germination_days_min, :germination_days_max, :days_to_maturity_min, :days_to_maturity_max, "
                    ":spacing_in, :sun_needs, :water_needs, "
                    ":soil_type, :soil_ph_min, :soil_ph_max, :feeding_frequency_days, "
                    ":growth_npk_n, :growth_npk_p, :growth_npk_k, :produce_npk_n, :produce_npk_p, :produce_npk_k, "
                    ":color_hex)"
                ),
                {
                    "common_name": common_name, "name": name, "plant_family": plant_family,
                    "genus": genus or None, "species": species or None, "color_hex": color_hex or None, **fields,
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
        color_hex: str = None,
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
                    "produce_npk_n = :produce_npk_n, produce_npk_p = :produce_npk_p, produce_npk_k = :produce_npk_k, "
                    "color_hex = :color_hex "
                    "WHERE id = :id"
                ),
                {
                    "id": variety_id, "common_name": common_name, "name": name, "plant_family": plant_family,
                    "genus": genus or None, "species": species or None, "color_hex": color_hex or None, **fields,
                },
            )

    def delete_seed_variety(self, variety_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM seed_varieties WHERE id = :id"), {"id": variety_id})

    def list_seed_varieties_with_seed_stock(self):
        "Existence-only gating (phase 4): any seed_lots row at all, regardless of quantity_on_hand."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_SEED_VARIETY_COLUMNS} FROM seed_varieties sv WHERE EXISTS "
                    "(SELECT 1 FROM seed_lots sl WHERE sl.variety_id = sv.id) "
                    "ORDER BY common_name, name"
                )
            ).mappings().all()

    def list_seed_varieties_with_transplant_stock(self):
        "Hard-cap gating (phase 4): a transplant_lots row with quantity_on_hand > 0."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_SEED_VARIETY_COLUMNS} FROM seed_varieties sv WHERE EXISTS "
                    "(SELECT 1 FROM transplant_lots tl WHERE tl.variety_id = sv.id AND tl.quantity_on_hand > 0) "
                    "ORDER BY common_name, name"
                )
            ).mappings().all()

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

    def list_available_transplant_lots_for_variety(self, variety_id: int):
        "Like list_transplant_lots_for_variety, but filtered to quantity_on_hand > 0 -- for the batch-plant lot picker."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_TRANSPLANT_LOT_COLUMNS} FROM transplant_lots "
                    "WHERE variety_id = :variety_id AND quantity_on_hand > 0 "
                    "ORDER BY purchased_date DESC, id DESC"
                ),
                {"variety_id": variety_id},
            ).mappings().all()

    def update_transplant_lot_quantity(self, transplant_lot_id: int, quantity_on_hand: int):
        "Single-field update for the bed-detail palette's inline qty editor -- update_transplant_lot is a full-form replace."
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("UPDATE transplant_lots SET quantity_on_hand = :quantity_on_hand WHERE id = :id"),
                {"id": transplant_lot_id, "quantity_on_hand": quantity_on_hand},
            )

    def list_plantings_by_transplant_lot(self, transplant_lot_id: int):
        "Every bed-planting drawn from this lot -- the lot side of phase 5's lineage view."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_PLANTING_COLUMNS} FROM plantings WHERE transplant_lot_id = :id "
                    "ORDER BY planted_date DESC, id DESC"
                ),
                {"id": transplant_lot_id},
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
                    "p.transplant_lot_id, p.source_type, p.soil_temp_f, p.created_at, "
                    "sv.name AS variety_name, sv.common_name, sv.color_hex, sv.spacing_in, "
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

    @staticmethod
    def _normalize_planting_fields(
        bed_id, location, quantity, quantity_germinated, notes, x_in=None, y_in=None, seed_lot_id=None,
        transplant_lot_id=None, source_type="seed", soil_temp_f=None, quantity_culled=None,
    ):
        return {
            "bed_id": bed_id,
            "location": location or None,
            "quantity": quantity,
            "quantity_germinated": quantity_germinated,
            "quantity_culled": quantity_culled,
            "notes": notes or None,
            "x_in": x_in,
            "y_in": y_in,
            "seed_lot_id": seed_lot_id,
            "transplant_lot_id": transplant_lot_id,
            "source_type": source_type,
            "soil_temp_f": soil_temp_f,
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
        soil_temp_f: float = None,
        quantity_culled: int = None,
    ):
        "Returns the new planting's id. Regenerates the (variety, planted_date) group's linked farm_events."
        fields = self._normalize_planting_fields(
            bed_id, location, quantity, quantity_germinated, notes, x_in, y_in, seed_lot_id,
            transplant_lot_id, source_type, soil_temp_f, quantity_culled,
        )
        with self.engine.begin() as db_connection:
            result = db_connection.execute(
                text(
                    "INSERT INTO plantings (variety_id, bed_id, location, planted_date, quantity, "
                    "quantity_germinated, quantity_culled, notes, x_in, y_in, seed_lot_id, transplant_lot_id, "
                    "source_type, soil_temp_f) "
                    "VALUES (:variety_id, :bed_id, :location, :planted_date, :quantity, "
                    ":quantity_germinated, :quantity_culled, :notes, :x_in, :y_in, :seed_lot_id, "
                    ":transplant_lot_id, :source_type, :soil_temp_f)"
                ),
                {"variety_id": variety_id, "planted_date": planted_date, **fields},
            )
            planting_id = result.lastrowid
            self._regenerate_farm_events(db_connection, variety_id, planted_date)
        return planting_id

    def batch_add_plantings(
        self,
        variety_id: int,
        planted_date: str,
        bed_id: int,
        source_type: str,
        points,
        transplant_lot_id: int = None,
        soil_temp_f: float = None,
    ):
        """Inserts one plantings row (quantity=1 -- a lattice stamp is one plant) per (x_in, y_in) in points,
        all in one transaction. Decrements transplant_lots.quantity_on_hand by len(points) once when
        transplant_lot_id is given, and regenerates the batch's (variety, planted_date) group's farm_events
        once at the end rather than once per point -- every point shares the same variety_id/planted_date,
        so one regen call covers the whole batch.
        Returns the list of new planting ids.
        """
        planting_ids = []
        with self.engine.begin() as db_connection:
            for x_in, y_in in points:
                result = db_connection.execute(
                    text(
                        "INSERT INTO plantings (variety_id, bed_id, planted_date, quantity, x_in, y_in, "
                        "source_type, transplant_lot_id, soil_temp_f) "
                        "VALUES (:variety_id, :bed_id, :planted_date, 1, :x_in, :y_in, "
                        ":source_type, :transplant_lot_id, :soil_temp_f)"
                    ),
                    {
                        "variety_id": variety_id, "bed_id": bed_id, "planted_date": planted_date,
                        "x_in": x_in, "y_in": y_in, "source_type": source_type,
                        "transplant_lot_id": transplant_lot_id, "soil_temp_f": soil_temp_f,
                    },
                )
                planting_ids.append(result.lastrowid)
            if transplant_lot_id is not None:
                db_connection.execute(
                    text(
                        "UPDATE transplant_lots SET quantity_on_hand = quantity_on_hand - :count WHERE id = :id"
                    ),
                    {"count": len(points), "id": transplant_lot_id},
                )
            self._regenerate_farm_events(db_connection, variety_id, planted_date)
        return planting_ids

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
        soil_temp_f: float = None,
        quantity_culled: int = None,
    ):
        fields = self._normalize_planting_fields(
            bed_id, location, quantity, quantity_germinated, notes, x_in, y_in, seed_lot_id,
            transplant_lot_id, source_type, soil_temp_f, quantity_culled,
        )
        with self.engine.begin() as db_connection:
            old = db_connection.execute(
                text("SELECT variety_id, planted_date FROM plantings WHERE id = :id"), {"id": planting_id}
            ).mappings().first()
            db_connection.execute(
                text(
                    "UPDATE plantings SET variety_id = :variety_id, planted_date = :planted_date, "
                    "bed_id = :bed_id, location = :location, quantity = :quantity, "
                    "quantity_germinated = :quantity_germinated, quantity_culled = :quantity_culled, notes = :notes, "
                    "x_in = :x_in, y_in = :y_in, seed_lot_id = :seed_lot_id, "
                    "transplant_lot_id = :transplant_lot_id, source_type = :source_type, "
                    "soil_temp_f = :soil_temp_f WHERE id = :id"
                ),
                {"id": planting_id, "variety_id": variety_id, "planted_date": planted_date, **fields},
            )
            self._regenerate_farm_events(db_connection, variety_id, planted_date)
            if old is not None and (old["variety_id"], old["planted_date"]) != (variety_id, planted_date):
                self._regenerate_farm_events(db_connection, old["variety_id"], old["planted_date"])

    def set_quantity_germinated(self, planting_id: int, quantity_germinated: int):
        "Single-field update for the germination-check calendar form -- update_planting is a full-form replace."
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("UPDATE plantings SET quantity_germinated = :quantity_germinated WHERE id = :id"),
                {"id": planting_id, "quantity_germinated": quantity_germinated},
            )

    def list_plantings_in_group(self, variety_id: int, planted_date: str):
        "Every planting sharing this (variety_id, planted_date) key -- the same group _regenerate_farm_events links one event to."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_PLANTING_COLUMNS} FROM plantings "
                    "WHERE variety_id = :variety_id AND planted_date = :planted_date ORDER BY id"
                ),
                {"variety_id": variety_id, "planted_date": planted_date},
            ).mappings().all()

    def delete_planting(self, planting_id: int):
        with self.engine.begin() as db_connection:
            row = db_connection.execute(
                text("SELECT variety_id, planted_date FROM plantings WHERE id = :id"), {"id": planting_id}
            ).mappings().first()
            db_connection.execute(text("DELETE FROM farm_events WHERE linked_planting_id = :id"), {"id": planting_id})
            db_connection.execute(text("DELETE FROM plantings WHERE id = :id"), {"id": planting_id})
            if row is not None:
                self._regenerate_farm_events(db_connection, row["variety_id"], row["planted_date"])

    def add_harvest(self, planting_id: int, harvest_date: str, weight_lb: float, notes: str = None):
        "Returns the new harvest's id. One planting can be harvested repeatedly -- this appends, never replaces."
        with self.engine.begin() as db_connection:
            result = db_connection.execute(
                text(
                    "INSERT INTO harvests (planting_id, harvest_date, weight_lb, notes) "
                    "VALUES (:planting_id, :harvest_date, :weight_lb, :notes)"
                ),
                {"planting_id": planting_id, "harvest_date": harvest_date, "weight_lb": weight_lb, "notes": notes or None},
            )
            return result.lastrowid

    def get_harvest(self, harvest_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_HARVEST_COLUMNS} FROM harvests WHERE id = :id"), {"id": harvest_id}
            ).mappings().first()

    def list_harvests_for_planting(self, planting_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_HARVEST_COLUMNS} FROM harvests WHERE planting_id = :planting_id "
                    "ORDER BY harvest_date DESC, id DESC"
                ),
                {"planting_id": planting_id},
            ).mappings().all()

    def update_harvest(self, harvest_id: int, harvest_date: str, weight_lb: float, notes: str = None):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE harvests SET harvest_date = :harvest_date, weight_lb = :weight_lb, notes = :notes "
                    "WHERE id = :id"
                ),
                {"id": harvest_id, "harvest_date": harvest_date, "weight_lb": weight_lb, "notes": notes or None},
            )

    def delete_harvest(self, harvest_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM harvests WHERE id = :id"), {"id": harvest_id})

    def _insert_farm_event_row(
        self, db_connection, event_type, title, start_date, end_date, linked_planting_id, notes=None,
        linked_product_application_id=None,
    ):
        db_connection.execute(
            text(
                "INSERT INTO farm_events (event_type, title, start_date, end_date, notes, linked_planting_id, "
                "linked_product_application_id) "
                "VALUES (:event_type, :title, :start_date, :end_date, :notes, :linked_planting_id, "
                ":linked_product_application_id)"
            ),
            {
                "event_type": event_type, "title": title, "start_date": start_date, "end_date": end_date,
                "notes": notes, "linked_planting_id": linked_planting_id,
                "linked_product_application_id": linked_product_application_id,
            },
        )

    def _insert_milestone_events(self, db_connection, linked_planting_id, variety, planted_date, variety_label, source_type):
        """Inserts germination-check/harvest rows for a variety's day-range fields, skipping any window that's
        unknown. Germination-check is additionally gated on source_type == 'seed' -- a transplant already
        germinated elsewhere (or was purchased), so there's nothing to check on-site.
        """
        germination_window = compute_window(
            planted_date, variety["germination_days_min"], variety["germination_days_max"]
        )
        if source_type == "seed" and germination_window:
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

    def _regenerate_farm_events(self, db_connection, variety_id, planted_date):
        """Recomputes the germination-check/harvest event pair for every planting sharing this
        (variety, planted_date) key -- same variety, same day is one calendar reminder regardless of bed
        placement. Linked to the lowest planting id in the group, so an edit anywhere in the group can only
        be gotten right by throwing away and rebuilding the whole group's events, not patching one planting.
        """
        db_connection.execute(
            text(
                "DELETE FROM farm_events WHERE event_type IN ('germination-check', 'harvest') "
                "AND linked_planting_id IN "
                "(SELECT id FROM plantings WHERE variety_id = :variety_id AND planted_date = :planted_date)"
            ),
            {"variety_id": variety_id, "planted_date": planted_date},
        )
        group_rows = db_connection.execute(
            text(
                "SELECT p.id, p.source_type, sv.common_name, sv.name, "
                "sv.germination_days_min, sv.germination_days_max, "
                "sv.days_to_maturity_min, sv.days_to_maturity_max "
                "FROM plantings p JOIN seed_varieties sv ON sv.id = p.variety_id "
                "WHERE p.variety_id = :variety_id AND p.planted_date = :planted_date"
            ),
            {"variety_id": variety_id, "planted_date": planted_date},
        ).mappings().all()
        if not group_rows:
            return
        anchor = min(group_rows, key=lambda row: row["id"])
        variety_label = f"{anchor['common_name']} - {anchor['name']}"
        self._insert_milestone_events(db_connection, anchor["id"], anchor, planted_date, variety_label, anchor["source_type"])

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
                    "b.label AS bed_label, p.bed_id AS planting_bed_id, gp.name AS product_name "
                    "FROM farm_events fe "
                    "LEFT JOIN plantings p ON p.id = fe.linked_planting_id "
                    "LEFT JOIN seed_varieties sv ON sv.id = p.variety_id "
                    "LEFT JOIN beds b ON b.id = p.bed_id "
                    "LEFT JOIN product_applications pa ON pa.id = fe.linked_product_application_id "
                    "LEFT JOIN garden_products gp ON gp.id = pa.product_id "
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

    def list_beds(self):
        "Every bed across every plot, joined with its plot's name -- for the product-application form's bed picker."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT b.id, b.plot_id, b.label, b.x, b.y, b.width_ft, b.length_ft, b.rotation_deg, "
                    "b.sun_exposure, b.irrigation_zone, b.created_at, lp.name AS plot_name "
                    "FROM beds b JOIN land_plots lp ON lp.id = b.plot_id "
                    "ORDER BY lp.name, b.label"
                )
            ).mappings().all()

    def list_garden_products(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_GARDEN_PRODUCT_COLUMNS} FROM garden_products ORDER BY name")
            ).mappings().all()

    def get_garden_product(self, product_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_GARDEN_PRODUCT_COLUMNS} FROM garden_products WHERE id = :id"),
                {"id": product_id},
            ).mappings().first()

    @staticmethod
    def _normalize_garden_product_fields(product_type, npk_n, npk_p, npk_k, benefit_notes, application_frequency_days):
        return {
            "product_type": product_type or None,
            "npk_n": npk_n,
            "npk_p": npk_p,
            "npk_k": npk_k,
            "benefit_notes": benefit_notes or None,
            "application_frequency_days": application_frequency_days,
        }

    def add_garden_product(
        self,
        name: str,
        product_type: str = None,
        npk_n: float = None,
        npk_p: float = None,
        npk_k: float = None,
        benefit_notes: str = None,
        application_frequency_days: int = None,
    ):
        fields = self._normalize_garden_product_fields(
            product_type, npk_n, npk_p, npk_k, benefit_notes, application_frequency_days
        )
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO garden_products (name, product_type, npk_n, npk_p, npk_k, benefit_notes, "
                    "application_frequency_days) "
                    "VALUES (:name, :product_type, :npk_n, :npk_p, :npk_k, :benefit_notes, "
                    ":application_frequency_days)"
                ),
                {"name": name, **fields},
            )

    def update_garden_product(
        self,
        product_id: int,
        name: str,
        product_type: str = None,
        npk_n: float = None,
        npk_p: float = None,
        npk_k: float = None,
        benefit_notes: str = None,
        application_frequency_days: int = None,
    ):
        fields = self._normalize_garden_product_fields(
            product_type, npk_n, npk_p, npk_k, benefit_notes, application_frequency_days
        )
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE garden_products SET name = :name, product_type = :product_type, npk_n = :npk_n, "
                    "npk_p = :npk_p, npk_k = :npk_k, benefit_notes = :benefit_notes, "
                    "application_frequency_days = :application_frequency_days "
                    "WHERE id = :id"
                ),
                {"id": product_id, "name": name, **fields},
            )

    def delete_garden_product(self, product_id: int):
        "Cascades to this product's applications and their farm_events, since there's no FK ON DELETE CASCADE."
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "DELETE FROM farm_events WHERE linked_product_application_id IN "
                    "(SELECT id FROM product_applications WHERE product_id = :product_id)"
                ),
                {"product_id": product_id},
            )
            db_connection.execute(
                text("DELETE FROM product_applications WHERE product_id = :product_id"), {"product_id": product_id}
            )
            db_connection.execute(text("DELETE FROM garden_products WHERE id = :id"), {"id": product_id})

    def list_product_applications(self):
        "Joined with garden_products and beds/land_plots so callers get display labels for both sides of the target."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT pa.id, pa.product_id, pa.applied_date, pa.bed_id, pa.location, pa.amount, pa.unit, "
                    "pa.notes, pa.created_at, gp.name AS product_name, gp.product_type, "
                    "b.label AS bed_label, lp.name AS plot_name "
                    "FROM product_applications pa "
                    "LEFT JOIN garden_products gp ON gp.id = pa.product_id "
                    "LEFT JOIN beds b ON b.id = pa.bed_id "
                    "LEFT JOIN land_plots lp ON lp.id = b.plot_id "
                    "ORDER BY pa.applied_date DESC, pa.id DESC"
                )
            ).mappings().all()

    def get_product_application(self, application_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_PRODUCT_APPLICATION_COLUMNS} FROM product_applications WHERE id = :id"),
                {"id": application_id},
            ).mappings().first()

    def _regenerate_product_reminder(self, db_connection, application_id, product_id, bed_id, location, applied_date):
        "Supersedes the prior reminder for this exact (product_id, bed_id, location) target, mirroring _regenerate_farm_events."
        db_connection.execute(
            text(
                "DELETE FROM farm_events WHERE event_type = 'product-reminder' AND linked_product_application_id IN ("
                "SELECT pa.id FROM product_applications pa WHERE pa.product_id = :product_id "
                "AND pa.bed_id IS :bed_id AND pa.location IS :location)"
            ),
            {"product_id": product_id, "bed_id": bed_id, "location": location},
        )
        product = db_connection.execute(
            text(f"SELECT {_GARDEN_PRODUCT_COLUMNS} FROM garden_products WHERE id = :id"), {"id": product_id}
        ).mappings().first()
        if product is None or product["application_frequency_days"] is None:
            return
        next_due = (date.fromisoformat(applied_date) + timedelta(days=product["application_frequency_days"])).isoformat()
        self._insert_farm_event_row(
            db_connection, "product-reminder", f"Reapply: {product['name']}", next_due, next_due,
            None, notes=None, linked_product_application_id=application_id,
        )

    def add_product_application(
        self,
        product_id: int,
        applied_date: str,
        bed_id: int = None,
        location: str = None,
        amount: float = None,
        unit: str = None,
        notes: str = None,
    ):
        "Returns the new application's id. Regenerates the (product_id, bed_id, location) target's reminder."
        with self.engine.begin() as db_connection:
            result = db_connection.execute(
                text(
                    "INSERT INTO product_applications (product_id, applied_date, bed_id, location, amount, unit, "
                    "notes) "
                    "VALUES (:product_id, :applied_date, :bed_id, :location, :amount, :unit, :notes)"
                ),
                {
                    "product_id": product_id, "applied_date": applied_date, "bed_id": bed_id,
                    "location": location or None, "amount": amount, "unit": unit or None, "notes": notes or None,
                },
            )
            application_id = result.lastrowid
            self._regenerate_product_reminder(db_connection, application_id, product_id, bed_id, location or None, applied_date)
        return application_id

    def update_product_application(
        self,
        application_id: int,
        product_id: int,
        applied_date: str,
        bed_id: int = None,
        location: str = None,
        amount: float = None,
        unit: str = None,
        notes: str = None,
    ):
        "Full-field update. Does not touch farm_events -- reminder regeneration only happens on logging a new application."
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE product_applications SET product_id = :product_id, applied_date = :applied_date, "
                    "bed_id = :bed_id, location = :location, amount = :amount, unit = :unit, notes = :notes "
                    "WHERE id = :id"
                ),
                {
                    "id": application_id, "product_id": product_id, "applied_date": applied_date, "bed_id": bed_id,
                    "location": location or None, "amount": amount, "unit": unit or None, "notes": notes or None,
                },
            )

    def delete_product_application(self, application_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("DELETE FROM farm_events WHERE linked_product_application_id = :id"), {"id": application_id}
            )
            db_connection.execute(text("DELETE FROM product_applications WHERE id = :id"), {"id": application_id})

    def list_shade_sources_for_plot(self, plot_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_SHADE_SOURCE_COLUMNS} FROM shade_sources WHERE plot_id = :plot_id ORDER BY label"),
                {"plot_id": plot_id},
            ).mappings().all()

    def get_shade_source(self, source_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_SHADE_SOURCE_COLUMNS} FROM shade_sources WHERE id = :id"), {"id": source_id}
            ).mappings().first()

    def add_shade_source(self, plot_id: int, label: str):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("INSERT INTO shade_sources (plot_id, label) VALUES (:plot_id, :label)"),
                {"plot_id": plot_id, "label": label},
            )

    def delete_shade_source(self, source_id: int):
        "Deletes the source's polygons and the source itself in one transaction -- there's no FK ON DELETE CASCADE."
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("DELETE FROM shade_polygons WHERE shade_source_id = :id"), {"id": source_id}
            )
            db_connection.execute(text("DELETE FROM shade_sources WHERE id = :id"), {"id": source_id})

    def list_shade_polygons_for_source(self, source_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_SHADE_POLYGON_COLUMNS} FROM shade_polygons WHERE shade_source_id = :id "
                    "ORDER BY season, shade_type"
                ),
                {"id": source_id},
            ).mappings().all()

    def list_shade_polygons_for_plot(self, plot_id: int):
        "Every polygon across every shade source on a plot -- what the classifier and the map's data blob both need."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT sp.id, sp.shade_source_id, sp.season, sp.shade_type, sp.points, sp.created_at, "
                    "ss.label AS source_label "
                    "FROM shade_polygons sp JOIN shade_sources ss ON ss.id = sp.shade_source_id "
                    "WHERE ss.plot_id = :plot_id"
                ),
                {"plot_id": plot_id},
            ).mappings().all()

    def get_shade_polygon(self, polygon_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_SHADE_POLYGON_COLUMNS} FROM shade_polygons WHERE id = :id"), {"id": polygon_id}
            ).mappings().first()

    def save_shade_polygon(self, shade_source_id: int, season: str, shade_type: str, points: str):
        """Upserts by the (shade_source_id, season, shade_type) unique key -- a source has at most one
        polygon per combo (up to 4: full/partial x summer/winter). Returns the polygon's id."""
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO shade_polygons (shade_source_id, season, shade_type, points) "
                    "VALUES (:shade_source_id, :season, :shade_type, :points) "
                    "ON CONFLICT (shade_source_id, season, shade_type) DO UPDATE SET points = excluded.points"
                ),
                {"shade_source_id": shade_source_id, "season": season, "shade_type": shade_type, "points": points},
            )
            return db_connection.execute(
                text(
                    "SELECT id FROM shade_polygons WHERE shade_source_id = :shade_source_id "
                    "AND season = :season AND shade_type = :shade_type"
                ),
                {"shade_source_id": shade_source_id, "season": season, "shade_type": shade_type},
            ).scalar_one()

    def delete_shade_polygon(self, polygon_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM shade_polygons WHERE id = :id"), {"id": polygon_id})
