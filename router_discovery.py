from importlib import import_module
from pkgutil import iter_modules


def discover_router_modules(package):
    "Walks package.__path__ (submodules only, packages skipped) and returns every module defining `router`."
    modules = []
    for module_info in sorted(iter_modules(package.__path__), key=lambda m: m.name):
        if module_info.ispkg:
            continue
        module = import_module(f"{package.__name__}.{module_info.name}")
        if hasattr(module, "router"):
            modules.append(module)
    return modules
