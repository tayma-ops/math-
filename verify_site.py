from pathlib import Path

OUT = Path(__file__).resolve().parent / "test-results"
OUT.mkdir(exist_ok=True)
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chromium")
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route(
        "**/*",
        lambda route: (
            route.continue_()
            if route.request.url.startswith(("file:", "data:", "blob:"))
            else route.abort()
        ),
    )
    page.route(
        "**/store-config.js",
        lambda route: route.fulfill(
            content_type="application/javascript",
            body='window.storeConfig={whatsapp:""};',
        ),
    )
    page.goto(Path("index.html").resolve().as_uri())
    page.wait_for_timeout(1500)
    assert page.locator("#siteHeader").count() == 1
    assert page.locator("#contact").count() == 1
    assert page.locator("#heroVideo").evaluate(
        "(v)=>v.muted && v.loop && v.playsInline"
    )
    page.locator(".add-cart").first.click()
    print(errors, page.locator("#cartCount").inner_text())
    assert page.locator("#cartCount").inner_text() == "1"
    page.locator(".cart-quantity button").last.click()
    assert page.locator("#cartCount").inner_text() == "2"
    page.reload()
    assert page.locator("#cartCount").inner_text() == "2"
    assert page.locator("#orderSubmit").is_disabled()
    page.locator("#searchInput").fill("فلتر")
    page.locator("#searchForm button").click()
    assert page.locator(".product-card:visible").count() == 2
    page.locator("#searchInput").fill("")
    page.locator("#searchForm button").click()
    assert page.locator(".product-card:visible").count() == 8
    for width in [1440, 768, 390, 320]:
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), width
    page.locator("#mobileMenuToggle").click()
    assert page.locator("#mobileMenuToggle").get_attribute("aria-expanded") == "true"
    page.keyboard.press("Escape")
    assert page.locator("#mobileMenuToggle").get_attribute("aria-expanded") == "false"
    page.emulate_media(reduced_motion="reduce")
    page.wait_for_timeout(150)
    assert page.locator("#heroVideo").evaluate("(v)=>v.paused")
    for link in page.locator('a[href^="#"]').all():
        target = link.get_attribute("href")[1:]
        assert page.locator('[id="' + target + '"]').count(), target
    page.screenshot(path=str(OUT / "legacy-site-mobile.png"), full_page=True)
    assert not errors, errors
    # Verify the order flow with a test-only contact; no message is sent.
    page.add_init_script("window.addEventListener('DOMContentLoaded',()=>{});")
    page.route(
        "**/store-config.js",
        lambda route: route.fulfill(
            content_type="application/javascript",
            body='window.storeConfig={whatsapp:"966500000000"};',
        ),
    )
    page.reload()
    assert page.locator("#orderSubmit").is_enabled()
    for name, value in [
        ("customer", "Test"),
        ("phone", "0500000000"),
        ("vehicle", "Camry 2020"),
        ("city", "Riyadh"),
    ]:
        page.locator('[name="' + name + '"]').fill(value)
    page.evaluate("window.open=(url)=>{window.testOrderUrl=url;}")
    page.locator("#orderSubmit").click()
    assert page.evaluate("window.testOrderUrl").startswith(
        "https://wa.me/966500000000?text="
    )
    browser.close()
print(
    "PASS: navigation, search, cart persistence and quantities, mobile menu, 4 screen widths, reduced motion, order URL, no JavaScript errors."
)
