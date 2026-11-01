from pathlib import Path

OUT = Path(__file__).resolve().parent / "test-results"
OUT.mkdir(exist_ok=True)
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chromium")
    page = browser.new_page()
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
    page.locator('.nav-menu a[href="contact.html"]').click()
    assert page.url.endswith("contact.html")
    assert page.locator("#contactForm").is_visible()
    assert page.locator("#contactSubmit").is_disabled()
    for width in (1440, 768, 390, 320):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#mobileMenuToggle").click()
    assert page.locator("#mobileMenuToggle").get_attribute("aria-expanded") == "true"
    page.keyboard.press("Escape")
    page.locator("#searchInput").fill("\u0641\u0644\u062a\u0631")
    page.locator("#searchForm button").click()
    page.wait_for_url("**/index.html?search=*")
    assert page.locator(".product-card:visible").count() == 2
    page.goto(Path("contact.html").resolve().as_uri())
    page.route(
        "**/store-config.js",
        lambda route: route.fulfill(
            content_type="application/javascript",
            body='window.storeConfig={whatsapp:"966500000000",email:"test@example.com",address:"Test address",hours:"Test hours"}',
        ),
    )
    page.reload()
    assert page.locator("#contactSubmit").is_enabled()
    assert page.locator("#contactWhatsapp").is_visible()
    page.locator('[name="customer"]').fill("Test")
    page.locator('[name="message"]').fill("Parts question")
    page.evaluate("window.open=(url)=>{window.testContactUrl=url;}")
    page.locator("#contactSubmit").click()
    assert page.evaluate("window.testContactUrl").startswith(
        "https://wa.me/966500000000?text="
    )
    assert not errors, errors
    page.screenshot(path=str(OUT / "legacy-contact-mobile.png"), full_page=True)
    browser.close()
print(
    "PASS: contact navigation, mobile layout/menu, cross-page search, configured contact form, no JavaScript errors."
)
