from layout import layout as _layout


def layout(title: str, *content):
    return _layout(title, *content, subdomain="farm")
