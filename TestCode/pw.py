from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
    page = context.new_page()
    page.set_default_timeout(60*1000)
    page.goto("https://www.reuters.com/world/middle-east/trumps-gulf-tour-reshapes-middle-east-diplomatic-map-2025-05-18/")
    html_content = page.content()
    print(html_content)
    browser.close()

