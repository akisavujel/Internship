import csv
import time
from playwright.sync_api import sync_playwright

SEARCH_URL = "https://www.google.com/maps/search/salons+spa+navi+mumbai/@19.0539869,72.9301609,13z"
OUTPUT_FILE = "results.csv"
MAX_SCROLLS = 40          
MAX_LISTINGS = 200       
HEADLESS = False          
SCROLL_PAUSE = 1.5        
DETAIL_PAUSE = 1.2       
# -------------------------------------------


def scroll_feed_and_collect_links(page):
    """Scroll the left-hand results panel and collect unique listing URLs."""
    feed_selector = 'div[role="feed"]'
    page.wait_for_selector(feed_selector, timeout=30000)

    links = set()
    same_count_rounds = 0
    last_count = 0

    for i in range(MAX_SCROLLS):
        page.evaluate(
            """(sel) => {
                const el = document.querySelector(sel);
                if (el) el.scrollTop = el.scrollHeight;
            }""",
            feed_selector,
        )
        time.sleep(SCROLL_PAUSE)

        anchors = page.query_selector_all(f'{feed_selector} a[href*="/maps/place/"]')
        for a in anchors:
            href = a.get_attribute("href")
            if href:
                links.add(href)

        print(f"  scroll {i+1}/{MAX_SCROLLS} -> {len(links)} listings found so far")

        if len(links) >= MAX_LISTINGS:
            break

        if len(links) == last_count:
            same_count_rounds += 1
            if same_count_rounds >= 4:
                print("  no new listings after several scrolls, stopping.")
                break
        else:
            same_count_rounds = 0
        last_count = len(links)

    return list(links)[:MAX_LISTINGS]


def get_text_safe(page, selector):
    el = page.query_selector(selector)
    if el:
        return el.inner_text().strip()
    return ""


def scrape_listing(page, url):
    page.goto(url, timeout=30000)
    page.wait_for_timeout(int(DETAIL_PAUSE * 1000))
    try:
        page.wait_for_selector("h1", timeout=10000)
    except Exception:
        pass

    data = {"url": url}

    data["name"] = get_text_safe(page, "h1")

    data["category"] = get_text_safe(page, 'button[jsaction*="category"]')

    data["rating"] = get_text_safe(page, 'div.F7nice span[aria-hidden="true"]')
    reviews_el = page.query_selector('div.F7nice span[aria-label*="review"]')
    data["review_count"] = reviews_el.inner_text().strip("() ") if reviews_el else ""

    addr_el = page.query_selector('button[data-item-id="address"]')
    data["address"] = addr_el.get_attribute("aria-label").replace("Address:", "").strip() if addr_el else ""

    phone_el = page.query_selector('button[data-item-id^="phone:tel:"]')
    data["phone"] = phone_el.get_attribute("aria-label").replace("Phone:", "").strip() if phone_el else ""

    site_el = page.query_selector('a[data-item-id="authority"]')
    data["website"] = site_el.get_attribute("href") if site_el else ""

    return data


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        page.goto(SEARCH_URL, timeout=60000)
        print("Loading search results...")
        page.wait_for_timeout(3000)

        try:
            page.click('button:has-text("Accept all")', timeout=3000)
        except Exception:
            pass

        print("Scrolling to collect listing links...")
        links = scroll_feed_and_collect_links(page)
        print(f"Total listings to scrape: {len(links)}")

        fieldnames = ["name", "category", "rating", "review_count", "address", "phone", "website", "url"]
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for i, link in enumerate(links):
                try:
                    print(f"[{i+1}/{len(links)}] scraping...")
                    row = scrape_listing(page, link)
                    writer.writerow(row)
                    f.flush()  
                except Exception as e:
                    print(f"  failed on {link}: {e}")

        browser.close()
        print(f"Done. Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()