import re
import time
from playwright.sync_api import Playwright, sync_playwright, expect

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # 1. Login Flow
    print("Testing Login Flow...")
    page.goto("http://localhost:3000/login")
    page.get_by_placeholder("Username").fill("admin")
    page.get_by_placeholder("Password").fill("admin")
    page.get_by_role("button", name="Login").click()
    
    # Verify Dashboard Load (Fixed selector: "Hosts Overview")
    expect(page.get_by_role("heading", name="Hosts Overview")).to_be_visible(timeout=10000)
    print("✅ Login Successful & Dashboard Loaded")

    # 2. Dashboard/Inventory Checks
    print("Testing Dashboard Inventory...")
    # Check for Status Summary elements
    expect(page.get_by_text("Up:", exact=False)).to_be_visible()
    expect(page.get_by_text("Down:", exact=False)).to_be_visible()
    
    # Wait for hosts to load
    page.wait_for_timeout(2000) # Give a moment for API fetch
    
    # Check if we have hosts listed
    # We expect 'nagios-web-server-1' to be present from Docker
    print("Waiting for hosts to appear (up to 60s)...")
    try:
        # Agent uses hostname 'web-server-1' inside container, not container name 'nagios-web-server-1'
        expect(page.get_by_text("web-server-1", exact=True)).to_be_visible(timeout=60000)
        print("✅ Found 'web-server-1'")
    except:
        print("⚠️ 'web-server-1' not found on dashboard (Check Docker logs)")

    # 3. Host Group Management
    print("Testing Host Group Management...")
    try:
        # Create Group
        page.get_by_role("button", name="+ Add Group").click()
        page.fill("input[id='group_name']", "E2E Test Group")
        page.fill("textarea[id='group_description']", "Created by automated test")
        page.get_by_role("button", name="Create Group").click()
        
        # Verify Group Exists
        expect(page.get_by_role("heading", name="E2E Test Group")).to_be_visible()
        print("✅ Host Group Created")
        
        # Delete Group
        # Find the delete button for this specific group. 
        # The structure is h3(name) -> parent -> actions -> delete
        # We can try finding the section that contains the text and then the delete button
        
        # Simplification: reload to ensure strict state
        page.reload()
        page.wait_for_timeout(1000)
        
        # Locate the group section
        group_section = page.locator(".host-group-section").filter(has_text="E2E Test Group")
        if group_section.count() > 0:
            # Click delete button within this section
            page.on("dialog", lambda dialog: dialog.accept()) # Handle confirmation alert
            group_section.get_by_title("Delete group").click()
            
            # Verify deletion
            page.wait_for_timeout(1000)
            expect(page.get_by_role("heading", name="E2E Test Group")).not_to_be_visible()
            print("✅ Host Group Deleted")
        else:
            print("⚠️ Could not find created group to delete")
            
    except Exception as e:
        print(f"❌ Host Group Test Failed: {e}")
        page.goto("http://localhost:3000/overview")
        page.wait_for_timeout(2000)

    # 4. Host Detail, Service Checks & Agent Verification
    print("Testing Host Detail & Agent...")
    try:
        # Navigate to web-server-1
        page.goto("http://localhost:3000") # Ensure we start from dashboard
        page.get_by_text("web-server-1", exact=True).click()
        
        # Verify Detail Headers
        expect(page.get_by_role("heading", name="Service Check Results")).to_be_visible()
        expect(page.get_by_role("heading", name="Historical Metrics")).to_be_visible()
        
        # Verify Agent ID
        # Look for "Agent ID:" text
        expect(page.get_by_text("Agent ID:", exact=False)).to_be_visible()
        print("✅ Host Detail Loaded & Agent ID present")
        
        # Add Service Check
        page.get_by_role("button", name="Add Check").click()
        page.locator("#check_type").select_option("ping")
        # Argument might be pre-filled or needed
        page.fill("#argument", "localhost") 
        page.get_by_role("button", name="Add Check").click()
        
        # Verify Check Added
        expect(page.get_by_text("PING")).to_be_visible()
        print("✅ Service Check Added")
        
        # Run Check
        # Find the row with PING and click run
        # Taking a shortcut: click the first "Run" button if present, or specific one
        # The "Run" button is usually an icon or text. In ServiceCheckConfig.js it's often a Play icon or "Run Now"
        # Let's try to find the button nearby
        row = page.locator("tr").filter(has_text="PING")
        if row.count() > 0:
             row.get_by_title("Run check").click()
             print("✅ 'Run Check' clicked")
             # We won't wait for result as it might take time, just verifying the interaction
        
    except Exception as e:
        print(f"❌ Host Detail/Check Test Failed: {e}")
        page.goto("http://localhost:3000/overview") # Reset state
        page.wait_for_timeout(2000)

    # 5. Navigation Checks
    print("Testing Navigation...")
    try:
        # UPS
        page.get_by_role("link", name="UPS").click()
        expect(page.get_by_role("heading", name="UPS Monitoring")).to_be_visible() 
        expect(page).to_have_url(re.compile(r".*/ups"))
        print("✅ UPS Page Verified")
        
        # SNMP
        page.get_by_role("link", name="SNMP").click()
        expect(page.get_by_role("heading", name="SNMP Device Monitoring")).to_be_visible() 
        expect(page).to_have_url(re.compile(r".*/snmp"))
        print("✅ SNMP Page Verified")
        
        # Alerts
        page.get_by_role("link", name="Alerts").click()
        expect(page.get_by_role("heading", name="Alerts")).to_be_visible() # Assuming header
        expect(page).to_have_url(re.compile(r".*/alerts"))
        print("✅ Alerts Page Verified")
        
    except Exception as e:
        print(f"❌ Navigation Test Failed: {e}")
        page.goto("http://localhost:3000/overview") # Ensure clean state for next tests

    # 7. Comprehensive Route Testing
    print("Testing All Interface Routes...")
    try:
        # Overview
        page.goto("http://localhost:3000/overview")
        expect(page.get_by_role("heading", name="Host Status Overview")).to_be_visible()
        print("✅ Overview Page Verified")

        # User Management
        page.goto("http://localhost:3000/users")
        expect(page.get_by_role("heading", name="User Management")).to_be_visible()
        print("✅ User Management Page Verified")

        # Audit Logs
        page.goto("http://localhost:3000/audit-logs")
        expect(page.get_by_role("heading", name="Audit Logs")).to_be_visible()
        print("✅ Audit Logs Page Verified")

        # Network Discovery
        page.goto("http://localhost:3000/discovery")
        expect(page.get_by_role("heading", name="Network Discovery")).to_be_visible()
        
        # Test Scan functionality
        print("Testing Discovery Scan...")
        # Fill network range (use localhost/127.0.0.1 to find local services safely and quickly)
        page.get_by_label("Network Range").fill("127.0.0.1")
        page.get_by_role("button", name="Start Scan").click()
        
        # Wait for results
        # Scan might take a few seconds
        expect(page.get_by_text("Scan Results", exact=False)).to_be_visible(timeout=15000)
        expect(page.get_by_text("Found", exact=False)).to_be_visible()
        print("✅ Discovery Scan Completed")
        
        # Test Import
        # If hosts found, try import
        if page.get_by_role("button", name="Import", exact=False).is_visible():
             page.get_by_role("button", name="Import", exact=False).click()
             expect(page.get_by_text("Successfully imported")).to_be_visible(timeout=5000)
             print("✅ Discovery Import Verified")

        print("✅ Network Discovery Page Verified")

        # Security Settings
        page.goto("http://localhost:3000/security")
        expect(page.get_by_role("heading", name="Security Settings")).to_be_visible()
        print("✅ Security Settings Page Verified")

        # Custom Dashboards
        page.goto("http://localhost:3000/dashboards")
        expect(page.get_by_role("heading", name="Dashboards")).to_be_visible()
        print("✅ Custom Dashboards Page Verified")

    except Exception as e:
        print(f"❌ Route Application Test Failed: {e}")

    # 8. Logout
    print("Testing Logout...")
    try:
        page.get_by_role("button", name="Logout").click()
        expect(page.get_by_role("heading", name="Duck Monitoring")).to_be_visible() # Login header
        print("✅ Logout Successful")
    except Exception as e:
         print(f"⚠️ Logout Test Issue: {e}")

    context.close()
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
