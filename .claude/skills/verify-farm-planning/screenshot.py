#!/usr/bin/env python3
"""Screenshots a single farm-planning URL via headless Playwright, optionally clicking a
selector and/or scrolling a container first (e.g. to expand a collapsed sidebar group, or to
prove a sticky column stays put while its scroll container moves).

    python .claude/skills/verify-farm-planning/screenshot.py <url> <out.png> \
        [--click SELECTOR ...] [--element SELECTOR] [--scroll-into-view SELECTOR] \
        [--scroll-container SELECTOR --scroll-x PIXELS]

Run from the repo root with .venv active and the dev server already running (see SKILL.md).
"""
import argparse

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("out_path")
    parser.add_argument("--click", action="append", default=[], help="selector to click before the shot; repeatable")
    parser.add_argument("--element", help="screenshot just this locator's bounding box instead of the full page")
    parser.add_argument("--scroll-into-view", help="selector to scroll into view before the shot")
    parser.add_argument("--scroll-container", help="selector of a scrollable element to scroll horizontally")
    parser.add_argument("--scroll-x", type=int, default=0, help="pixels to scroll --scroll-container right")
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.goto(args.url)
        for selector in args.click:
            page.locator(selector).first.click()
        if args.scroll_into_view:
            page.locator(args.scroll_into_view).first.scroll_into_view_if_needed()
        if args.scroll_container:
            page.locator(args.scroll_container).first.evaluate(
                "(el, x) => el.scrollLeft = x", args.scroll_x
            )
        if args.element:
            page.locator(args.element).first.screenshot(path=args.out_path)
        else:
            page.screenshot(path=args.out_path)
        browser.close()
    print(f"wrote {args.out_path}")


if __name__ == "__main__":
    main()
