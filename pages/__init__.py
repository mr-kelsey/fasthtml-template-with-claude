from importlib import import_module
from pkgutil import iter_modules


def discover_page_modules():
    modules = []
    for module_info in sorted(iter_modules(__path__), key=lambda m: m.name):
        if module_info.ispkg:
            continue
        module = import_module(f"{__name__}.{module_info.name}")
        if hasattr(module, "router"):
            modules.append(module)
    return modules
