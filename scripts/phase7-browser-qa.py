import os
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent.parent
folder = root / "artifacts/phase7/browser"
folder.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    target = os.environ.get("NEXORA_QA_API")
    if target:

        def forward(route):
            response = route.fetch(
                url=route.request.url.replace("http://127.0.0.1:3001", target)
            )
            route.fulfill(response=response)

        page.route("**/api/**", forward)
    page.add_init_script("localStorage.setItem('nexora-theme','light')")
    page.goto("http://127.0.0.1:3001")
    page.get_by_role("button", name="New conversation").click()
    page.get_by_role("textbox", name="Message", exact=True).fill("/help")
    page.get_by_role("button", name="Send message", exact=True).click()
    page.get_by_text("Commands: /files", exact=False).wait_for()
    page.screenshot(path=str(folder / "chat-light-desktop.png"))
    page.get_by_role("button", name="Library", exact=True).click()
    page.get_by_role("textbox", name="Memory note").fill(
        "Phase 7 browser verification note"
    )
    page.get_by_role("button", name="Save for 30 days").click()
    page.get_by_text("Phase 7 browser verification note", exact=True).wait_for()
    page.get_by_role("button", name="NEXORA Code", exact=True).click()
    page.get_by_role("button", name="Propose and test").wait_for()
    page.screenshot(path=str(folder / "coding-workspace.png"))
    page.get_by_role("button", name="Whisper speech", exact=True).click()
    page.get_by_role("heading", name="Whisper Large V3").wait_for()
    assert page.get_by_role("button", name="Transcribe audio").is_disabled()
    page.get_by_role("button", name="Chat", exact=True).click()
    page.get_by_role("combobox", name="Inference provider").select_option(
        "nvidia-gpt-oss-20b"
    )
    page.get_by_text("Allow sending chat to NVIDIA", exact=False).wait_for()
    page.get_by_role("combobox", name="Inference provider").select_option("ollama")
    page.wait_for_function("document.querySelector('select').value === 'ollama'")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(folder / "chat-light-mobile.png"))
    browser.close()
print(
    "Desktop/mobile, code controls, memory persistence, speech status and hosted consent UI passed"
)
