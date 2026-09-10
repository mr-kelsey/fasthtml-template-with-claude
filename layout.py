from fasthtml import common as fast

# Each entry is a "subdomain": its own nav-bar identity and link set. A page
# picks its subdomain via layout()'s `subdomain` kwarg (core pages default to
# "core"; other subdomains get a thin `<name>/layout.py` wrapper — see
# farm/layout.py — so their pages don't have to pass it at every call site).
# Adding a future subdomain (e.g. "finance") means adding one entry here plus
# that wrapper, nothing else in this file changes.
SUBDOMAINS = {
    "core": {
        "label": "FastHTML Template",
        "home": "/",
        "links": [
            ("Home", "/"),
            ("About", "/about"),
            ("Notes", "/notes"),
            ("Calendar", "/calendar"),
        ],
    },
    "farm": {
        "label": "Farm",
        "home": "/farm-calendar",
        "links": [
            ("Farm Calendar", "/farm-calendar"),
            ("Varieties", "/seed-varieties"),
            ("Inventory", "/inventory"),
            ("Plantings", "/plantings"),
            ("Products", "/products"),
            ("Land Map", "/land-plots"),
        ],
    },
}


def nav(subdomain: str = "core"):
    current = SUBDOMAINS[subdomain]
    other_subdomains = [info for key, info in SUBDOMAINS.items() if key != subdomain]
    return fast.Nav(
        fast.Ul(fast.Li(fast.Strong(current["label"]))),
        fast.Ul(*[fast.Li(fast.A(label, href=href)) for label, href in current["links"]]),
        fast.Ul(*[fast.Li(fast.A(other["label"], href=other["home"])) for other in other_subdomains]),
    )


def layout(title: str, *content, subdomain: str = "core"):
    return (
        fast.Title(f"{title} — FastHTML Template"),
        fast.Link(rel="stylesheet", href="/styles.css"),
        fast.Header(nav(subdomain), cls="container"),
        fast.Main(*content, cls="container"),
        fast.Footer(fast.P("FastHTML + SQLite template"), cls="container"),
    )
