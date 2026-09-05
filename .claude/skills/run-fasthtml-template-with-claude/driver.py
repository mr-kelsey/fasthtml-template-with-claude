#!/usr/bin/env python3
"""Drives the FastHTML family calendar app end-to-end via headless Playwright.

Run from the repo root, with .venv active and the dev server already
running on :5001 (see SKILL.md):

    python .claude/skills/run-fasthtml-template-with-claude/driver.py

Adds one throwaway event ("Driver Smoke Test") to today's date under
Person 1 (selected via the calendar's filter row, which doubles as the
member picker), verifies it renders as a colored event bar and a
critical-day border, screenshots each step, then deletes the event
again via db.delete_event so the real dev database (data/app.db) is
left untouched. Requires `family.json` to exist (copy
family.example.json if you don't have a real one) and `pip install
playwright && playwright install chromium` (one-time; see SKILL.md
Prerequisites).
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5001")
    parser.add_argument(
        "--screenshot-dir",
        default=str(Path(__file__).resolve().parent / "screenshots"),
    )
    args = parser.parse_args()
    Path(args.screenshot_dir).mkdir(parents=True, exist_ok=True)

    import db

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        page.goto(f"{args.base_url}/calendar")
        page.wait_for_selector(".calendar-grid")
        page.click(".filter-row a:has-text('Person 1')")
        page.wait_for_selector(".calendar-grid")
        page.screenshot(path=f"{args.screenshot_dir}/01-grid.png")

        page.click(".day-square.today")
        page.wait_for_selector("#event-dialog[open]")
        page.screenshot(path=f"{args.screenshot_dir}/02-dialog.png")

        page.fill("#event-dialog input[name='title']", "Driver Smoke Test")
        page.check("#event-dialog input[name='is_critical']")
        page.click("#event-dialog button:has-text('Add Event')")
        page.wait_for_selector(".calendar-grid")
        page.screenshot(path=f"{args.screenshot_dir}/03-after-add.png")

        bars = page.query_selector_all(".event-bar")
        critical_squares = page.query_selector_all(".day-square.critical-day")
        print(f"event_bars={len(bars)} critical_day_squares={len(critical_squares)}")
        print(f"console_errors={console_errors!r}")

        browser.close()

    removed = 0
    for event in db.list_events():
        if event["title"] == "Driver Smoke Test":
            db.delete_event(event["id"])
            removed += 1
    print(f"cleaned up {removed} throwaway event(s)")


if __name__ == "__main__":
    main()
