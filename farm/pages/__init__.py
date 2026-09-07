import sys

from router_discovery import discover_router_modules


def discover_page_modules():
    return discover_router_modules(sys.modules[__name__])
