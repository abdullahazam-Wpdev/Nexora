"""Fixture-only browser checks; do not export owner conversations/screenshots."""

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("http://127.0.0.1:3001")
    page.wait_for_function(
        "document.querySelector('option[value=\"qwen-coder\"]')?.disabled === true"
    )
    page.get_by_role("button", name="Workspace Code", exact=True).click()
    page.get_by_label("Patch format", exact=False).select_option("edits")
    assert page.get_by_label("Patch format", exact=False).input_value() == "edits"
    page.get_by_role("button", name="Evaluations", exact=True).click()
    page.get_by_role("heading", name="Phase 10", exact=True).wait_for()
    page.get_by_text(
        "Frozen coding suite: 0 passed, 23 failed, 8 blocked", exact=False
    ).wait_for()
    page.get_by_role("button", name="Library", exact=True).click()
    page.get_by_role("heading", name="Document retrieval", exact=True).wait_for()
    browser.close()
    print(
        "Phase10 UI passed: explicit minimal-edit control, disabled Qwen, real evaluation counts, Library"
    )
