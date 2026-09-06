from pathlib import Path

import pages
from pages import discover_page_modules

PAGES_DIR = Path(pages.__file__).parent


def test_discover_page_modules_includes_home():
    module_names = [module.__name__ for module in discover_page_modules()]
    assert "pages.home" in module_names


def test_discover_page_modules_includes_about():
    module_names = [module.__name__ for module in discover_page_modules()]
    assert "pages.about" in module_names


def test_discover_page_modules_includes_notes():
    module_names = [module.__name__ for module in discover_page_modules()]
    assert "pages.notes" in module_names


def test_discover_page_modules_includes_calendar():
    module_names = [module.__name__ for module in discover_page_modules()]
    assert "pages.calendar" in module_names


def test_discover_page_modules_skips_module_without_router():
    helper_path = PAGES_DIR / "_no_router_helper.py"
    helper_path.write_text("VALUE = 1\n")
    try:
        module_names = [module.__name__ for module in discover_page_modules()]
    finally:
        helper_path.unlink()
    assert "pages._no_router_helper" not in module_names
