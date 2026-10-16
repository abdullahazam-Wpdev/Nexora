"""Real local browser QA; expects both services running."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('docs/evidence');out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:3000',wait_until='networkidle')
    page.get_by_text('Local system connected',exact=True).wait_for()
    assert page.get_by_role('heading',name='Intelligence starts here.').is_visible()
    assert page.locator('.stat strong').first.inner_text().startswith('1')
    page.screenshot(path=str(out/'overview-desktop.png'),full_page=True)
    for name in ['Core Model Lab','Dataset Manager','Training Experiments','Evaluation Center','Model Playground','System Health','Storage','Settings']:
        page.get_by_role('button',name=name,exact=True).click()
        assert page.get_by_role('heading',name=name,exact=True).is_visible()
    page.get_by_role('button',name='Model Playground',exact=True).click()
    page.get_by_label('Prompt',exact=True).fill('2 + 3 =')
    page.get_by_role('button',name='Generate 32 tokens').click()
    page.wait_for_function("document.querySelector('#generated').textContent !== 'Generated tokens will appear here.'")
    output=page.locator('#generated').inner_text()
    assert len(output)>7
    page.screenshot(path=str(out/'playground.png'),full_page=True)
    page.get_by_role('button',name='Overview',exact=True).click()
    page.get_by_role('button',name='Toggle color theme').click()
    assert page.locator('.shell.light').count()==1
    page.screenshot(path=str(out/'overview-light.png'),full_page=True)
    page.get_by_role('button',name='Toggle color theme').click()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(out/'overview-mobile.png'),full_page=True)
    assert not errors, errors
    browser.close()
    result={'navigation_sections_checked':9,'inference_output':output,'themes_checked':2,'viewports':[1440,390],'horizontal_overflow':False,'page_errors':errors}
    (out/'browser-results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
