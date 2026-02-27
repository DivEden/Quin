"""
Quinix Workers Dashboard - Full Auto-Login & Auto-Start for 6 Workers
Automatically logs in and starts all 6 workers in separate browser windows
Includes live web dashboard at http://localhost:8765/dashboard.html
"""
import time
import os
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import webbrowser

# ============================================================================
# CONFIGURATION - Change this to run more or fewer workers!
# ============================================================================
NUM_WORKERS = 3  # <-- CHANGE THIS NUMBER (recommended: 6-10, max: 20)
# ============================================================================

# Shared dashboard data
dashboard_data = {
    'workers': {},  # {worker_num: {'denied': 0, 'failed': 0, 'status': 'working', 'last_update': time}}
    'start_time': None,
    'lock': threading.Lock(),
    'num_workers': NUM_WORKERS
}

# Auto-generate worker configuration based on NUM_WORKERS
# All windows stack at position (0, 0) - they can overlap without freezing
WORKERS = []
for i in range(1, NUM_WORKERS + 1):
    profile = f"EdgeProfile{i}"
    WORKERS.append((profile, 0, 0))

def setup_driver(profile_name):
    """Setup Edge browser with specific profile"""
    options = Options()
    profile_dir = os.path.join(os.getcwd(), profile_name)
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Profile1")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--mute-audio")  # Mute all audio including notification sounds
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Edge(options=options)
    return driver

def auto_login(driver, password, worker_num):
    """Automated login through Quinyx -> DGBLOGIN -> Microsoft"""
    try:
        print(f"      [Worker {worker_num}] Step 1: Entering email on Quinyx page...")
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "emailOrProviderId"))
        )
        email_input.clear()
        email_input.send_keys("mfed@dengamleby.dk")
        
        time.sleep(1)
        submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        time.sleep(3)  # Increased wait for redirect
        
        print(f"      [Worker {worker_num}] Step 2: Waiting for DGBLOGIN option...")
        dgb_option = WebDriverWait(driver, 15).until(  # Increased timeout
            EC.element_to_be_clickable((By.XPATH, "//p[contains(text(), 'DGBLOGIN - Brug den her!!!')]"))
        )
        time.sleep(1)
        dgb_option.click()
        time.sleep(4)  # Increased wait for SSO redirect
        
        print(f"      [Worker {worker_num}] Step 3: Checking for Microsoft email field...")
        try:
            email_input2 = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "i0116"))
            )
            email_input2.clear()
            email_input2.send_keys("mfed@dengamleby.dk")
            
            time.sleep(1)
            next_button = driver.find_element(By.ID, "idSIButton9")
            next_button.click()
            time.sleep(3)
        except:
            print(f"      [Worker {worker_num}] ℹ Email field skipped (already remembered)")
        
        print(f"      [Worker {worker_num}] Step 4: Entering password...")
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "i0118"))
        )
        # Use JavaScript to set value directly (avoids auto-fill issues)
        driver.execute_script("arguments[0].value = '';", password_input)
        time.sleep(0.2)
        driver.execute_script("arguments[0].value = arguments[1];", password_input, password)
        
        time.sleep(1)
        signin_button = driver.find_element(By.ID, "idSIButton9")
        signin_button.click()
        
        # Wait for authentication to complete
        print(f"      [Worker {worker_num}] Waiting for authentication...")
        # First worker often needs extra time due to cold start
        wait_time = 8 if worker_num == 1 else 6
        time.sleep(wait_time)
        
        # Check if we hit an error page (Microsoft sometimes has redirect issues on first login)
        try:
            current_url = driver.current_url.lower()
            page_source = driver.page_source.lower()
            
            if "error" in current_url or "invalid" in page_source:
                print(f"      [Worker {worker_num}] ⚠ Redirect issue detected, refreshing...")
                driver.refresh()
                time.sleep(4)
            elif worker_num == 1 and ("login" in current_url or "auth" in current_url):
                # First worker sometimes stuck on auth page, give it a refresh
                print(f"      [Worker {worker_num}] ⚠ Auth stuck, refreshing...")
                driver.refresh()
                time.sleep(4)
        except:
            pass
        
        print(f"      [Worker {worker_num}] ✓ Login successful")
        return True
    except Exception as e:
        print(f"      [Worker {worker_num}] ✗ Login error: {e}")
        try:
            print(f"      [Worker {worker_num}] Current URL: {driver.current_url}")
        except:
            pass
        return False

def open_notification_panel(driver, worker_num):
    """Open and expand notification panel"""
    try:
        print(f"      [Worker {worker_num}] Clicking notification bell...")
        bell = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "notificationButtonSchedule"))
        )
        bell.click()
        time.sleep(3)
        
        print(f"      [Worker {worker_num}] Expanding absence requests...")
        expand_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="absenceRequestsNotificationsHeading__arrowBtn"]'))
        )
        
        # Always click to expand, even if already expanded (ensure it's open)
        if expand_btn.get_attribute('aria-expanded') == 'false':
            expand_btn.click()
            print(f"      [Worker {worker_num}] ✓ Clicked to expand")
        else:
            print(f"      [Worker {worker_num}] ✓ Already expanded")
        
        time.sleep(3)  # Extra wait for expansion animation to complete
        
        return True
    except Exception as e:
        print(f"      [Worker {worker_num}] ✗ Panel error: {e}")
        print(f"      [Worker {worker_num}] ⚠ Panel opening failed, but worker will retry automatically")
        return False
        return False

def update_dashboard(worker_num, denied, failed, status):
    """Update dashboard data for a worker"""
    with dashboard_data['lock']:
        dashboard_data['workers'][worker_num] = {
            'denied': denied,
            'failed': failed,
            'status': status,
            'last_update': time.time()
        }

def process_requests(driver, worker_num):
    """Process absence requests directly in Python - no JavaScript needed!"""
    denied_count = 0
    failed_count = 0
    no_items_attempts = 0
    
    print(f"      [Worker {worker_num}] 🚀 Starting request processor...")
    update_dashboard(worker_num, 0, 0, 'working')
    
    while True:
        try:
            # Find all visible request items
            items = driver.find_elements(By.CSS_SELECTOR, '[data-test-id="leaveRequestDataItem"]')
            
            if len(items) == 0:
                no_items_attempts += 1
                
                if no_items_attempts <= 2:
                    # Sidebar might have closed - try to reopen it
                    print(f"      [Worker {worker_num}] ⚠️ No items visible - sidebar may have closed. Reopening...")
                    
                    try:
                        # Click notification bell
                        bell = driver.find_element(By.ID, "notificationButtonSchedule")
                        bell.click()
                        time.sleep(2)
                        
                        # Expand absence requests section
                        expand_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="absenceRequestsNotificationsHeading__arrowBtn"]'))
                        )
                        if expand_btn.get_attribute('aria-expanded') == 'false':
                            expand_btn.click()
                        time.sleep(2)
                        
                        # Check again for items
                        items = driver.find_elements(By.CSS_SELECTOR, '[data-test-id="leaveRequestDataItem"]')
                        if len(items) == 0:
                            print(f"      [Worker {worker_num}] ✅ No more requests after reopening! Denied: {denied_count}, Failed: {failed_count}")
                            break
                        else:
                            print(f"      [Worker {worker_num}] ✓ Sidebar reopened - {len(items)} requests found")
                            no_items_attempts = 0  # Reset counter
                    except Exception as e:
                        print(f"      [Worker {worker_num}] ✗ Failed to reopen sidebar: {e}")
                        break
                else:
                    # After 2 attempts, truly no more requests
                    print(f"      [Worker {worker_num}] ✅ No more requests! Denied: {denied_count}, Failed: {failed_count}")
                    break
            else:
                no_items_attempts = 0  # Reset counter when items found
            
            if len(items) == 0:
                continue
            
            print(f"      [Worker {worker_num}] {len(items)} requests remaining...")
            
            # Calculate which position this worker should take from
            # Dynamically divides list based on NUM_WORKERS
            # Worker 1: position 0 (top)
            # Worker 2: position 1/NUM_WORKERS
            # Worker 3: position 2/NUM_WORKERS
            # ... and so on
            fraction = (worker_num - 1) / dashboard_data['num_workers']
            target_index = int(fraction * len(items))
            
            # Make sure we don't go out of bounds
            if target_index >= len(items):
                target_index = len(items) - 1
            
            item = items[target_index]
            print(f"      [Worker {worker_num}] Taking request at position {target_index + 1}/{len(items)}")
            
            try:
                # Click the request item to open detail panel
                item.click()
                time.sleep(1.5)
                
                # Wait for and fill the comment textarea
                textarea = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="absenceRequestManagerComment"]'))
                )
                textarea.clear()
                textarea.send_keys(".")  # Minimal comment (change if needed)
                time.sleep(0.5)
                
                # Find and click Deny button
                deny_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'DENY', 'deny'), 'deny') or contains(translate(., 'AFVIS', 'afvis'), 'afvis')]"))
                )
                deny_button.click()
                time.sleep(1)
                
                denied_count += 1
                print(f"      [Worker {worker_num}] ✓ Denied request #{denied_count}")
                
                # Small delay between requests to avoid overwhelming the system
                time.sleep(1)
                
                # Check if sidebar is still open after denying
                check_items = driver.find_elements(By.CSS_SELECTOR, '[data-test-id="leaveRequestDataItem"]')
                if len(check_items) == 0:
                    print(f"      [Worker {worker_num}] ⚠️ Sidebar closed after deny - reopening...")
                    try:
                        # Click notification bell
                        bell = driver.find_element(By.ID, "notificationButtonSchedule")
                        bell.click()
                        time.sleep(2)
                        
                        # Expand absence requests section
                        expand_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="absenceRequestsNotificationsHeading__arrowBtn"]'))
                        )
                        if expand_btn.get_attribute('aria-expanded') == 'false':
                            expand_btn.click()
                        time.sleep(2)
                        print(f"      [Worker {worker_num}] ✓ Sidebar reopened")
                    except Exception as e:
                        print(f"      [Worker {worker_num}] ✗ Failed to reopen: {e}")
                
                update_dashboard(worker_num, denied_count, failed_count, 'working')
                
            except Exception as e:
                print(f"      [Worker {worker_num}] ✗ Error processing request: {e}")
                failed_count += 1
                update_dashboard(worker_num, denied_count, failed_count, 'working')
                
                # Try to close any open panels with Escape key
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
                except:
                    pass
                
        except Exception as e:
            print(f"      [Worker {worker_num}] ✗ Main loop error: {e}")
            time.sleep(2)
            break
    
    print(f"      [Worker {worker_num}] 🏁 FINISHED! Total denied: {denied_count}, Failed: {failed_count}")
    update_dashboard(worker_num, denied_count, failed_count, 'finished')

def setup_worker(profile_name, pos_x, pos_y, worker_num, password):
    """Complete setup for one worker: browser, login, panel, processing"""
    try:
        print(f"\n   [Worker {worker_num}] Opening browser ({profile_name})...")
        driver = setup_driver(profile_name)
        
        # Set much larger size to ensure desktop UI (not mobile), stack at same position
        driver.set_window_position(0, 0)
        driver.set_window_size(1400, 900)
        
        print(f"   [Worker {worker_num}] Navigating to login page...")
        driver.get("https://login.quinyx.com/")
        time.sleep(2)
        
        print(f"   [Worker {worker_num}] Auto-logging in...")
        success = auto_login(driver, password, worker_num)
        
        if not success:
            print(f"   [Worker {worker_num}] ⚠ Auto-login failed, manual intervention needed")
            return None
        
        # Extra wait after login before navigation
        print(f"   [Worker {worker_num}] Stabilizing after login...")
        time.sleep(3)  # Reduced from 5
        
        # Verify browser is still alive before continuing
        try:
            _ = driver.current_url
        except:
            print(f"   [Worker {worker_num}] ✗ Browser crashed after login")
            return None
        
        print(f"   [Worker {worker_num}] Going to schedule page...")
        driver.get("https://web.quinyx.com/schedule/191654")
        time.sleep(5)  # Increased wait for page to fully load
        
        print(f"   [Worker {worker_num}] Opening notification panel...")
        panel_opened = open_notification_panel(driver, worker_num)
        
        # Wait for absence requests to actually load in the list (always wait, not just if panel opened)
        print(f"   [Worker {worker_num}] Waiting for absence request DATA ITEMS to load...")
        try:
            # Wait for the SAME element the workers look for: leaveRequestDataItem
            WebDriverWait(driver, 45).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-test-id="leaveRequestDataItem"]'))
            )
            
            # Count how many are visible
            items = driver.find_elements(By.CSS_SELECTOR, '[data-test-id="leaveRequestDataItem"]')
            print(f"   [Worker {worker_num}] ✓ {len(items)} absence request items loaded and visible")
            
            # Extra wait to ensure list is fully rendered and DOM is stable
            time.sleep(3)
        except:
            print(f"   [Worker {worker_num}] ⚠ Timeout waiting for leaveRequestDataItem elements")
            print(f"   [Worker {worker_num}] ⚠ Panel might not be expanded or list is empty")
            # Don't inject if we never saw the list - return None to mark failure
            return None
        
        # Start processing requests directly in Python
        print(f"   [Worker {worker_num}] Starting request processor...")
        process_requests(driver, worker_num)
        
        print(f"   [Worker {worker_num}] ✅ FINISHED PROCESSING")
        return driver
        
    except Exception as e:
        print(f"   [Worker {worker_num}] ✗ Setup error: {e}")
        return None

class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for dashboard"""
    def do_GET(self):
        if self.path == '/dashboard-data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with dashboard_data['lock']:
                workers = dashboard_data['workers']
                start_time = dashboard_data['start_time']
                
                # Calculate totals
                total_denied = sum(w['denied'] for w in workers.values())
                total_failed = sum(w['failed'] for w in workers.values())
                
                # Calculate rate and elapsed time
                if start_time:
                    elapsed_seconds = time.time() - start_time
                    elapsed_hours = elapsed_seconds / 3600
                    rate_per_hour = int(total_denied / elapsed_hours) if elapsed_hours > 0 else 0
                    
                    hours = int(elapsed_seconds // 3600)
                    minutes = int((elapsed_seconds % 3600) // 60)
                    seconds = int(elapsed_seconds % 60)
                    elapsed_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    rate_per_hour = 0
                    elapsed_str = "00:00:00"
                
                response = {
                    'total_denied': total_denied,
                    'total_failed': total_failed,
                    'rate_per_hour': rate_per_hour,
                    'elapsed_time': elapsed_str,
                    'workers': workers,
                    'num_workers': dashboard_data['num_workers']
                }
                
                self.wfile.write(json.dumps(response).encode())
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        """Suppress HTTP request logs"""
        pass

def run_dashboard_server():
    """Run HTTP server for dashboard"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(('localhost', 8765), DashboardHandler)
    print("   Dashboard server running on http://localhost:8765/dashboard.html")
    server.serve_forever()


def main():
    print("=" * 80)
    print("QUINIX WORKERS DASHBOARD - Full Auto-Start (Pure Python)")
    print("=" * 80)
    print(f"\nRunning with {NUM_WORKERS} workers")
    print("\nThis will automatically:")
    print(f"  • Open {NUM_WORKERS} browser windows with separate profiles")
    print("  • Log in to each one through Microsoft SSO")
    print("  • Navigate to the schedule page")
    print("  • Open and expand the notification panels")
    print("  • Process ALL absence requests (click, comment, deny)")
    print("  • Show live web dashboard with progress")
    print("\n" + "=" * 80)
    
    # Read password from password.txt file
    try:
        with open("password.txt", "r") as f:
            password = f.read().strip()
        if not password or password == "YOUR_PASSWORD_HERE":
            print("\n⚠ ERROR: Please edit password.txt and put your password in it")
            print("The file is in .gitignore so it won't be committed to git")
            return
        print("\n✓ Password loaded from password.txt")
    except FileNotFoundError:
        print("\n⚠ ERROR: password.txt not found")
        print("Create a file called 'password.txt' with your password in it")
        print("(It's already in .gitignore so it won't be committed)")
        return
    
    drivers = []
    
    # Start dashboard HTTP server
    print("\n" + "=" * 80)
    print("Starting web dashboard server...")
    print("=" * 80)
    server_thread = threading.Thread(target=run_dashboard_server, daemon=True)
    server_thread.start()
    time.sleep(1)  # Let server start
    
    # Open dashboard in browser
    webbrowser.open('http://localhost:8765/dashboard.html')
    print("✓ Dashboard opened in browser")
    
    print(f"\nPHASE 1: Setting up all {NUM_WORKERS} workers IN PARALLEL...")
    print("=" * 80)
    
    # Function to setup one worker in a thread
    def setup_worker_thread(profile, pos_x, pos_y, worker_num):
        print(f"\n→ Starting Worker {worker_num}/{NUM_WORKERS} setup...")
        driver = setup_worker(profile, pos_x, pos_y, worker_num, password)
        if driver:
            drivers.append(driver)
            print(f"✅ Worker {worker_num} COMPLETED")
        else:
            print(f"⚠ Worker {worker_num} FAILED")
    
    # Create and start all threads simultaneously
    threads = []
    for i, (profile, pos_x, pos_y) in enumerate(WORKERS, 1):
        thread = threading.Thread(
            target=setup_worker_thread,
            args=(profile, pos_x, pos_y, i)
        )
        threads.append(thread)
        thread.start()
        time.sleep(1)  # Small stagger to avoid overwhelming system
    
    # Wait for all threads to complete
    print("\n⏳ Starting all workers...")
    
    # Start dashboard data collection
    dashboard_data['start_time'] = time.time()
    
    time.sleep(3)  # Give workers a moment to start
    
    print("\n✓ All workers started!")
    print("✓ Monitor progress at: http://localhost:8765/dashboard.html")
    print("\nWorkers are processing in the background...")
    print("Press CTRL+C to stop all workers and close browsers\n")
    
    for thread in threads:
        thread.join()
    
    # All workers finished
    print("\n✅ All workers completed processing!")
    print("Check the dashboard for final stats")
    print("Press CTRL+C to close browsers\n")
    
    try:
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n✓ Stopping...")
        
    finally:
        print("\nClosing all browsers...")
        for i, driver in enumerate(drivers, 1):
            try:
                print(f"  Closing worker {i}...")
                driver.quit()
            except:
                pass
        print("✅ All workers stopped")

if __name__ == "__main__":
    main()
