from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent.parent
folder = root / "artifacts/cowork-verification"
folder.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.goto("http://127.0.0.1:3001")
    page.get_by_role("button", name="New conversation").click()
    page.get_by_role("textbox", name="Message", exact=True).fill("/help")
    page.get_by_role("button", name="Send message", exact=True).click()
    page.get_by_text("Commands: /files", exact=False).wait_for()
    page.reload()
    page.get_by_text("Commands: /files", exact=False).wait_for()
    page.screenshot(path=str(folder / "chat-desktop.png"), full_page=True)
    page.get_by_role("textbox", name="Message", exact=True).fill("Say hello briefly.")
    page.get_by_role("button", name="Send message", exact=True).click()
    page.get_by_text("Ollama • external SmolLM2 135M", exact=True).wait_for(
        timeout=90000
    )
    page.screenshot(path=str(folder / "model-reply.png"), full_page=True)
    page.get_by_role("combobox", name="Inference provider").select_option("localai")
    page.wait_for_function("document.querySelector('select').value === 'localai'")
    page.get_by_role("textbox", name="Message", exact=True).fill("Say hello briefly.")
    page.get_by_role("button", name="Send message", exact=True).click()
    page.get_by_text("LocalAI • external SmolLM2", exact=True).wait_for(timeout=90000)
    page.get_by_role("combobox", name="Inference provider").select_option("ollama")
    page.wait_for_function("document.querySelector('select').value === 'ollama'")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(folder / "chat-mobile.png"), full_page=True)
    browser.close()
print("Desktop, mobile, persisted tool reply and real Ollama chat passed")
