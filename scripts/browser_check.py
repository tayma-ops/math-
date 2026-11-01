"""End-to-end checks with a temporary DB, disposable accounts and localhost only."""

import re, json, os, secrets, socket, subprocess, sys, tempfile, time, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results"
OUT.mkdir(exist_ok=True)


def signup(page, url):
    page.goto(url + "/accounts/signup/")
    page.locator("[name=username]").fill("browser_" + secrets.token_hex(5))
    page.locator("[name=first_name]").fill("عميل اختبار")
    page.locator("[name=email]").fill("browser@example.test")
    password = secrets.token_urlsafe(22)
    page.locator("[name=password1]").fill(password)
    page.locator("[name=password2]").fill(password)
    page.locator("form.panel button").click()
    page.wait_for_url(url + "/")
    page.wait_for_load_state("networkidle")


def post(page, path, body):
    return page.evaluate(
        """async ({path,body})=>{const csrf=document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1]||'';const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(body)});return {status:r.status,body:await r.json()};}""",
        {"path": path, "body": body},
    )


def layout(page):
    for width in [1440, 768, 390, 320]:
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate(
            "document.documentElement.scrollWidth<=innerWidth"
        ), f"Horizontal overflow at {width}"
    page.set_viewport_size({"width": 1440, "height": 1000})


def run(page, url, browser):
    signup(page, url)
    expect(page.locator('body>a[href="/orders/"]')).to_be_visible()
    layout(page)
    page.screenshot(path=str(OUT / "home.png"), full_page=True)
    page.locator(".add-cart").first.click()
    page.reload(wait_until="networkidle")
    expect(page.locator("#cartCount")).to_have_text("1")
    page.locator("#searchInput").fill("فلتر")
    page.locator("#searchForm button").click()
    assert page.locator(".product-card:visible").count() == 2
    for name, value in [
        ("customer", "عميل اختبار"),
        ("phone", "0500000000"),
        ("vehicle", "سيارة تجريبية"),
        ("city", "الرياض"),
    ]:
        page.locator("[name=" + name + "]").fill(value)
    page.locator("#orderSubmit").click()

    page.wait_for_url("**/orders/checkout/")
    page.locator("[name=full_name]").fill("عميل اختبار")
    page.locator("[name=phone]").fill("0500000000")
    page.locator("[name=city]").fill("الرياض")
    page.locator("[name=address]").fill("عنوان تجريبي — لا يمثل طلبًا حقيقيًا")
    page.screenshot(path=str(OUT / "checkout.png"), full_page=True)
    page.locator("form.panel button").click()
    page.wait_for_url(re.compile(r"/orders/\d+/$"))
    expect(page.locator("h1")).to_contain_text("الطلب #")
    page.screenshot(path=str(OUT / "order.png"), full_page=True)
    page.locator("button").filter(has_text="إلغاء الطلب").click()
    expect(page.locator("main")).to_contain_text("ملغي")
    assert "Traceback" not in page.content()


def main():
    with tempfile.TemporaryDirectory(prefix="portfolio-browser-") as temporary:
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_DB_PATH": str(Path(temporary) / "test.sqlite3"),
                "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
                "DJANGO_DEBUG": "1",
                "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost",
                "OPENAI_API_KEY": "your_test_disabled",
            }
        )
        for args in [["migrate", "--noinput"], ["seed_demo"]]:
            result = subprocess.run(
                [sys.executable, "-B", "manage.py", *args],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode:
                raise RuntimeError(result.stderr)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        with (OUT / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "manage.py",
                    "runserver",
                    f"127.0.0.1:{port}",
                    "--noreload",
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                for attempt in range(100):
                    try:
                        with urllib.request.urlopen(
                            url + "/accounts/signup/", timeout=1
                        ):
                            break
                    except Exception:
                        if process.poll() is not None:
                            raise RuntimeError(
                                (OUT / "server.log").read_text(encoding="utf-8")
                            )
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Local server did not start")
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    errors = []
                    context = browser.new_context(
                        locale="ar-SA",
                        timezone_id="Asia/Riyadh",
                        reduced_motion="reduce",
                        viewport={"width": 1440, "height": 1000},
                    )
                    context.route(
                        "**/*",
                        lambda route: (
                            route.continue_()
                            if route.request.url.startswith((url, "data:", "blob:"))
                            else route.abort()
                        ),
                    )
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    try:
                        run(page, url, browser)
                        assert not errors, errors
                    except Exception:
                        page.screenshot(path=str(OUT / "failure.png"), full_page=True)
                        raise
                    finally:
                        browser.close()
                result = {
                    "passed": True,
                    "javascript_errors": errors,
                    "database": "temporary",
                    "external_requests": "blocked",
                    "original_database_modified": False,
                }
                (OUT / "browser-result.json").write_text(
                    json.dumps(result, indent=2), encoding="utf-8"
                )
                print(json.dumps(result))
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()
