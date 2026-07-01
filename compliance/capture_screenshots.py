"""
Capture screenshots of the Verdent app for YouTube API Services compliance review.
Requires the server to be running at http://localhost:8000/
"""
import os
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8000"
OUTPUT_DIR = "/Users/takeshikinoshita/Documents/Verdent/compliance/screenshots"
VIEWPORT = {"width": 1280, "height": 800}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT)
        page = context.new_page()

        # ────────────────────────────────────────────────────────
        # Step 1: Homepage
        # ────────────────────────────────────────────────────────
        print("Step 1: Capturing homepage...")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "step1_homepage.png"),
            full_page=True,
        )
        print("  -> step1_homepage.png saved")

        # ────────────────────────────────────────────────────────
        # Step 2: Keyword search input (fill + click)
        # ────────────────────────────────────────────────────────
        print("Step 2: Entering keyword 'gaming' and submitting...")
        page.fill("#query", "gaming")
        page.wait_for_timeout(500)
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "step2_search_input.png"),
            full_page=True,
        )
        print("  -> step2_search_input.png saved")

        # Submit the form and wait for results
        page.click("button[type='submit']")
        try:
            page.wait_for_selector("#top10-results", state="visible", timeout=30000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        # ────────────────────────────────────────────────────────
        # Step 3: TOP 10 results section
        # ────────────────────────────────────────────────────────
        print("Step 3: Capturing TOP 10 results...")
        # Scroll to top first
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(800)
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "step3_top10_results.png"),
            full_page=False,
        )
        print("  -> step3_top10_results.png saved")

        # ────────────────────────────────────────────────────────
        # Step 4: Trend analysis section
        # ────────────────────────────────────────────────────────
        print("Step 4: Scrolling to trend analysis...")
        trend_section = page.query_selector("#trend-analysis")
        if trend_section:
            trend_section.scroll_into_view_if_needed()
            page.wait_for_timeout(1500)  # Wait for charts to render
        else:
            page.evaluate("window.scrollBy(0, 800)")
            page.wait_for_timeout(1500)
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "step4_trend_analysis.png"),
            full_page=False,
        )
        print("  -> step4_trend_analysis.png saved")

        # ────────────────────────────────────────────────────────
        # Step 5: Results section (card view)
        # ────────────────────────────────────────────────────────
        print("Step 5: Scrolling to results (card view)...")
        results_section = page.query_selector("#results")
        if results_section:
            results_section.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
        else:
            # Try scrolling down past trend analysis
            page.evaluate("window.scrollBy(0, 2000)")
            page.wait_for_timeout(1000)
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "step5_card_results.png"),
            full_page=False,
        )
        print("  -> step5_card_results.png saved")

        # ────────────────────────────────────────────────────────
        # Step 6: List view
        # ────────────────────────────────────────────────────────
        print("Step 6: Switching to list view...")
        # Try to find list view toggle button
        list_btn = page.query_selector("#view-list-btn")
        if list_btn is None:
            list_btn = page.query_selector("button[data-view='list']")
        if list_btn is None:
            # Try any button that mentions "list" or table icon
            list_btn = page.query_selector(".view-toggle-btn[data-view='list']")
        if list_btn is None:
            # Search for button with list-related text/ID
            list_btn = page.query_selector("[id*='list'][type='button']")

        if list_btn:
            list_btn.click()
            page.wait_for_timeout(1000)
        else:
            print("  (list view button not found, capturing current state)")

        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "step6_list_results.png"),
            full_page=False,
        )
        print("  -> step6_list_results.png saved")

        # ────────────────────────────────────────────────────────
        # Step 7: API Quota endpoint
        # ────────────────────────────────────────────────────────
        print("Step 7: Capturing /api/quota endpoint...")
        quota_page = context.new_page()
        quota_page.goto(f"{BASE_URL}/api/quota", wait_until="networkidle")
        quota_page.wait_for_timeout(1000)
        quota_page.screenshot(
            path=os.path.join(OUTPUT_DIR, "step7_api_quota.png"),
            full_page=True,
        )
        quota_page.close()
        print("  -> step7_api_quota.png saved")

        browser.close()

    # Verify output
    screenshots = sorted(os.listdir(OUTPUT_DIR))
    print(f"\nScreenshots saved to: {OUTPUT_DIR}")
    print(f"Files ({len(screenshots)}):")
    for f in screenshots:
        path = os.path.join(OUTPUT_DIR, f)
        size_kb = os.path.getsize(path) // 1024
        print(f"  {f}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
