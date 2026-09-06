from fasthtml import common as fast

NAV_LINKS = [
    ("Home", "/"),
    ("About", "/about"),
    ("Notes", "/notes"),
    ("Calendar", "/calendar"),
    ("Varieties", "/seed-varieties"),
    ("Plantings", "/plantings"),
]


def nav():
    return fast.Nav(
        fast.Ul(fast.Li(fast.Strong("FastHTML Template"))),
        fast.Ul(*[fast.Li(fast.A(label, href=href)) for label, href in NAV_LINKS]),
    )


def layout(title: str, *content):
    return (
        fast.Title(f"{title} — FastHTML Template"),
        fast.Link(rel="stylesheet", href="/styles.css"),
        fast.Header(nav(), cls="container"),
        fast.Main(*content, cls="container"),
        fast.Footer(fast.P("FastHTML + SQLite template"), cls="container"),
    )
