from playwright.sync_api import sync_playwright
import time
import sys

def run():
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print("Navigating to Dashboard...")
            page.goto("http://localhost:5173")

            # Open War Room
            print("Opening War Room...")
            page.wait_for_selector('button[title="Toggle War Room"]', state="visible", timeout=10000)
            page.click('button[title="Toggle War Room"]')

            # Wait for App Load
            print("Waiting for War Room to load...")
            page.wait_for_selector("text=WAR ROOM", state="visible", timeout=10000)

            # Handle Auth Modal if present
            try:
                print("Checking for Auth Modal...")
                auth_modal = page.wait_for_selector("text=AUTHENTICATION REQUIRED", state="visible", timeout=3000)
                if auth_modal:
                    print("Auth Modal detected. Clicking Cancel...")
                    page.click("text=CANCEL")
                    # Wait for modal to disappear
                    page.wait_for_selector("text=AUTHENTICATION REQUIRED", state="hidden", timeout=3000)
            except:
                print("No Auth Modal detected (or timed out waiting for it). Proceeding.")

            # Open Command Modal
            print("Opening Command Modal...")
            page.wait_for_selector('[data-testid="open-command-modal"]', state="visible")
            page.click('[data-testid="open-command-modal"]')

            # Check Modal
            print("Verifying Modal...")
            page.wait_for_selector("text=NEW AUTOMATION", state="visible")

            # Fill Form
            print("Filling Automation Form...")
            # Title
            page.fill('input[placeholder="e.g. Bug Fix Routine"]', "Test Interval Routine")

            # Trigger -> Schedule
            page.select_option('select:has-text("MANUAL")', "schedule")

            # Wait for schedule options to appear
            page.wait_for_selector("text=FREQUENCY", state="visible")

            # Click Interval Button (text=INTERVAL)
            page.click("text=INTERVAL")

            # Fill Interval Minutes
            page.fill('input[type="number"]', "45")

            # Action -> Notify (Action selector is the second select usually, or identify by label)
            # The form has two selects.
            # 1. Trigger (value=manual/schedule...)
            # 2. Action (value=jules_task/notify...)
            # Use specific targeting by traversing from label

            # We can select by value if we find the select element
            # page.select_option('select:has-text("JULES TASK")', "notify")
            # Better to find the select following the ACTION label

            # Using nth-match if labels are standard, or select by value content
            # The select options are unique enough?
            # Trigger has "MANUAL", "SCHEDULE"...
            # Action has "JULES TASK", "NOTIFY"...

            # Select Action = Notify
            # Finding the select that contains "NOTIFY" option
            page.locator('select').filter(has_text="NOTIFY").select_option("notify")

            # Fill Message
            page.fill('input[placeholder="Notification Text"]', "System Check Complete")

            # Save
            print("Saving Routine...")
            page.click('[data-testid="save-routine"]')

            # Verify Modal Closes
            print("Verifying Modal Closure...")
            page.wait_for_selector("text=NEW AUTOMATION", state="hidden", timeout=5000)

            print("SUCCESS: Automation created and modal closed.")

        except Exception as e:
            print(f"FAILURE: {e}")
            page.screenshot(path="verification_failure.png")
            print("Screenshot saved to verification_failure.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
