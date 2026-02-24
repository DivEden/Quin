"""
QUINIX 6-WORKER TAB MANAGER WITH UNIFIED CONSOLE
=================================================
This Python program manages 6 browser tabs running the worker scripts.
It keeps all tabs active by rotating focus and auto-refreshing them.

NEW FEATURES:
- 🖥️  Always-on-top unified console showing all worker logs
- 🔄 Automatic tab refresh every 5 minutes to keep workers active
- 📊 Real-time status updates for all 6 workers in one window
- 🎨 Color-coded logs for each worker

REQUIREMENTS:
- pip install selenium
- Edge browser installed
- EdgeDriver (will auto-download with selenium 4.6+)

USAGE:
1. Make sure you're logged into Quinyx in your default Edge profile
2. Update the QUINYX_URL below to your absence request page
3. Run: python quinix_tab_manager.py
4. A unified console window will appear (always on top)
5. All worker logs will appear in that window
"""

import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from pathlib import Path
import sys
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
from datetime import datetime
import subprocess
import os
import sqlite3
import shutil
from collections import deque

# ============================================================================
# CONFIGURATION
# ============================================================================

# Update this URL to your Quinyx absence request page
QUINYX_URL = "https://web.quinyx.com/schedule/191654?end=2026-02-28&start=2026-02-01&timeframe=multiday_month"

# Window arrangement settings
STATUS_CHECK_INTERVAL = 30  # Check worker status every 30 seconds
REFRESH_INTERVAL = 300  # Refresh all windows every 5 minutes to keep them active

# Worker names mapping
WORKER_NAMES = {
    'WORKER-1-TOP': 'Worker 1',
    'WORKER-2-SIXTH1': 'Worker 2',
    'WORKER-3-THIRD': 'Worker 3',
    'WORKER-4-HALF': 'Worker 4',
    'WORKER-5-TWOTHIRD': 'Worker 5',
    'WORKER-6-BOTTOM': 'Worker 6'
}

# Screen layout: 6 windows in 2 rows x 3 columns
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 540
STATUS_CHECK_INTERVAL = 30  # Check worker status every 30 seconds
REFRESH_INTERVAL = 300  # Refresh all windows every 5 minutes to keep them active

# Worker script files
WORKER_FILES = [
    "worker-1-top.txt",
    "worker-2-sixth1.txt",
    "worker-3-third.txt",
    "worker-4-half.txt",
    "worker-5-twothird.txt",
    "worker-6-bottom.txt"
]

# ============================================================================
# MAIN PROGRAM
# ============================================================================

class UnifiedConsole:
    """Always-on-top window showing combined logs from all workers"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎯 QUINIX Workers - Unified Console")
        self.root.geometry("1000x650")
        self.root.attributes('-topmost', True)  # Always on top
        
        # Create header frame
        header_frame = tk.Frame(self.root, bg='#2c3e50', height=50)
        header_frame.pack(fill=tk.X)
        
        self.status_label = tk.Label(
            header_frame, 
            text="⏳ Initializing...", 
            bg='#2c3e50', 
            fg='white',
            font=('Consolas', 12, 'bold'),
            pady=10
        )
        self.status_label.pack()
        
        # Create control frame with Start button
        control_frame = tk.Frame(self.root, bg='#34495e', height=60)
        control_frame.pack(fill=tk.X)
        
        self.start_button = tk.Button(
            control_frame,
            text="▶ START WORKERS",
            command=self.on_start_clicked,
            font=('Consolas', 14, 'bold'),
            bg='#27ae60',
            fg='white',
            activebackground='#2ecc71',
            activeforeground='white',
            cursor='hand2',
            relief=tk.RAISED,
            bd=3,
            padx=30,
            pady=10,
            state=tk.DISABLED  # Disabled until tabs are ready
        )
        self.start_button.pack(pady=10)
        
        # Create Done Logging In button (initially hidden)
        self.login_done_button = tk.Button(
            control_frame,
            text="✓ DONE LOGGING IN",
            command=self.on_login_done_clicked,
            font=('Consolas', 14, 'bold'),
            bg='#2980b9',
            fg='white',
            activebackground='#3498db',
            activeforeground='white',
            cursor='hand2',
            relief=tk.RAISED,
            bd=3,
            padx=30,
            pady=10,
            state=tk.DISABLED
        )
        # Don't pack it yet - will show when needed
        
        self.started = False
        self.login_done = False
        
        # Create scrolled text widget for logs
        self.log_text = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            width=120,
            height=26,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure text tags for colored output
        self.log_text.tag_config('worker1', foreground='#4ec9b0')
        self.log_text.tag_config('worker2', foreground='#ce9178')
        self.log_text.tag_config('worker3', foreground='#dcdcaa')
        self.log_text.tag_config('worker4', foreground='#569cd6')
        self.log_text.tag_config('worker5', foreground='#c586c0')
        self.log_text.tag_config('worker6', foreground='#9cdcfe')
        self.log_text.tag_config('system', foreground='#6a9955')
        self.log_text.tag_config('error', foreground='#f48771')
        self.log_text.tag_config('success', foreground='#4ec9b0')
        
        self.log_text.insert('1.0', '═' * 100 + '\n')
        self.log_text.insert('end', '  QUINIX 6-WORKER UNIFIED CONSOLE\n', 'success')
        self.log_text.insert('end', '  All worker logs combined in one place\n', 'system')
        self.log_text.insert('end', '═' * 100 + '\n\n')
        
        self.log_count = 0
    
    def on_start_clicked(self):
        """Handle Start button click"""
        self.started = True
        self.start_button.config(
            text="✓ WORKERS RUNNING",
            state=tk.DISABLED,
            bg='#95a5a6',
            cursor='arrow'
        )
        self.add_log("START button clicked - Beginning worker injection...", log_type='success')
    
    def on_login_done_clicked(self):
        """Handle Login Done button click"""
        self.login_done = True
        self.login_done_button.config(
            text="✓ LOGGED IN",
            state=tk.DISABLED,
            bg='#95a5a6',
            cursor='arrow'
        )
        self.add_log("Login complete! Proceeding...", log_type='success')
        # Hide the login done button after 1 second
        self.root.after(1000, lambda: self.login_done_button.pack_forget())
    
    def enable_start_button(self):
        """Enable the Start button"""
        try:
            if self.root.winfo_exists():
                self.start_button.config(state=tk.NORMAL)
        except:
            pass
        self.add_log("All tabs opened! Click the START WORKERS button when ready.", log_type='success')
        self.update_status("⏸️  Ready - Click START WORKERS to begin")
    
    def wait_for_start(self):
        """Block until Start button is clicked"""
        try:
            while not self.started and self.root.winfo_exists():
                self.root.update()
                time.sleep(0.1)  # Poll every 100ms
        except:
            pass
    
    def enable_login_done_button(self):
        """Enable the Login Done button"""
        try:
            if self.root.winfo_exists():
                self.login_done_button.pack(pady=10)
                self.login_done_button.config(state=tk.NORMAL)
        except:
            pass
    
    def wait_for_login_done(self):
        """Block until Login Done button is clicked"""
        try:
            while not self.login_done and self.root.winfo_exists():
                self.root.update()
                time.sleep(0.1)  # Poll every 100ms
        except:
            pass
        
    def update(self):
        """Update the window (call periodically)"""
        try:
            if self.root.winfo_exists():
                self.root.update()
        except:
            pass
        
    def add_log(self, message, worker_id=None, log_type='info'):
        """Add a log message to the console"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Determine tag based on worker or type
        if worker_id:
            worker_num = worker_id.replace('WORKER', '').replace('_', '').replace('TOP', '1').replace('SIXTH', '2').replace('THIRD', '3').replace('HALF', '4').replace('TWOTHIRD', '5').replace('BOTTOM', '6')
            if '1' in worker_num:
                tag = 'worker1'
            elif '2' in worker_num:
                tag = 'worker2'
            elif '3' in worker_num:
                tag = 'worker3'
            elif '4' in worker_num:
                tag = 'worker4'
            elif '5' in worker_num:
                tag = 'worker5'
            elif '6' in worker_num:
                tag = 'worker6'
            else:
                tag = 'system'
        elif log_type == 'error':
            tag = 'error'
        elif log_type == 'success':
            tag = 'success'
        else:
            tag = 'system'
        
        # Format message
        if worker_id:
            formatted = f"[{timestamp}] [{worker_id}] {message}\n"
        else:
            formatted = f"[{timestamp}] {message}\n"
        
        # Insert into text widget
        self.log_text.insert('end', formatted, tag)
        self.log_text.see('end')  # Auto-scroll to bottom
        self.log_count += 1
        
        # MEMORY FIX: Aggressively limit buffer to last 500 lines
        if self.log_count > 500:
            # Delete 100 lines at once to reduce memory
            self.log_text.delete('1.0', '100.0')
            self.log_count -= 100
    
    def update_status(self, status_text):
        """Update the header status"""
        try:
            if self.root.winfo_exists():
                self.status_label.config(text=status_text)
        except:
            pass


def kill_edge_processes():
    """Kill all Edge processes to free up the profile"""
    try:
        # Kill all Edge processes
        subprocess.run(['taskkill', '/F', '/IM', 'msedge.exe'], 
                      capture_output=True, 
                      timeout=5)
        time.sleep(2)  # Wait for processes to fully close
        return True
    except:
        return False

def setup_driver(window_position=None, window_size=None, profile_number=1):
    """Setup Edge driver with options - each window gets its own profile"""
    
    options = Options()
    # Keep browser open after script ends
    options.add_experimental_option("detach", True)
    
    # STABLE Memory saving options (only proven flags to avoid STATUS_BREAKPOINT)
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-sync")
    options.add_argument("--mute-audio")
    # Page load strategy to avoid hanging
    options.page_load_strategy = 'eager'
    
    # CRITICAL: Each browser gets its own profile to avoid crashes
    # (Multiple browsers cannot share same profile simultaneously)
    automation_profile = rf"C:\Users\MadsE\Desktop\quinix-workers\EdgeProfile{profile_number}"
    options.add_argument(f"user-data-dir={automation_profile}")
    
    driver = webdriver.Edge(options=options)
    
    # Position and size window if specified
    if window_position and window_size:
        driver.set_window_position(window_position[0], window_position[1])
        driver.set_window_size(window_size[0], window_size[1])
    
    return driver

def load_worker_script(filepath):
    """Load worker script from file"""
    script_path = Path(__file__).parent / filepath
    if not script_path.exists():
        print(f"❌ ERROR: Worker file not found: {filepath}")
        sys.exit(1)
    
    with open(script_path, 'r', encoding='utf-8') as f:
        return f.read()

def inject_script(driver, script, worker_name):
    """Inject JavaScript worker into the current tab"""
    try:
        driver.execute_script(script)
        print(f"✅ {worker_name} script injected and running")
        return True
    except Exception as e:
        print(f"❌ Failed to inject {worker_name}: {e}")
        return False

def get_worker_status(driver):
    """Get current worker status from console logs"""
    try:
        # Try to get the deleted/failed counts and recent logs from window variables
        script = """
        const workers = ['WORKER1_TOP', 'WORKER2_SIXTH1', 'WORKER3_THIRD', 
                        'WORKER4_HALF', 'WORKER5_TWOTHIRD', 'WORKER6_BOTTOM'];
        const status = {};
        workers.forEach(w => {
            const deleted = window[`${w}DeletedCount`] || 0;
            const failed = window[`${w}FailedCount`] || 0;
            if (deleted > 0 || failed > 0) {
                status[w] = {deleted, failed};
            }
        });
        return status;
        """
        return driver.execute_script(script)
    except:
        return {}

def get_worker_logs(driver):
    """Get recent console logs from the current tab"""
    try:
        script = """
        // Get the worker ID from current page
        const workers = ['WORKER1_TOP', 'WORKER2_SIXTH1', 'WORKER3_THIRD', 
                        'WORKER4_HALF', 'WORKER5_TWOTHIRD', 'WORKER6_BOTTOM'];
        let currentWorker = null;
        for (const w of workers) {
            if (window[`${w}DeletedCount`] !== undefined) {
                currentWorker = w;
                break;
            }
        }
        if (!currentWorker) return null;
        
        const deleted = window[`${currentWorker}DeletedCount`] || 0;
        const failed = window[`${currentWorker}FailedCount`] || 0;
        
        return {
            worker: currentWorker,
            deleted: deleted,
            failed: failed,
            timestamp: Date.now()
        };
        """
        return driver.execute_script(script)
    except:
        return None

def main():
    print("=" * 70)
    print("  QUINIX 6-WORKER TAB MANAGER WITH UNIFIED CONSOLE")
    print("=" * 70)
    print()
    
    # Check if URL is configured
    if "YOUR_COMPANY" in QUINYX_URL:
        print("❌ ERROR: Please update QUINYX_URL in the script first!")
        print(f"   Current URL: {QUINYX_URL}")
        print()
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Create unified console window
    print("🖥️  Creating unified console window...")
    console = UnifiedConsole()
    console.add_log("Unified console started", log_type='success')
    console.add_log("This window will show all worker logs combined", log_type='system')
    console.add_log("Window is set to ALWAYS ON TOP", log_type='system')
    console.update()
    
    # Setup multiple drivers (one per window)
    console.add_log("Setting up 6 separate Edge windows...", log_type='system')
    console.add_log("Each browser gets its own profile (no conflicts!)", log_type='success')
    console.add_log("Windows will be arranged in a 2x3 grid on your screen", log_type='success')
    console.add_log("(You'll need to login to Quinyx in the first window)", log_type='system')
    console.update_status("🌐 Starting Edge browsers...")
    console.update()
    
    drivers = []
    
    try:
        console.add_log(f"Loading {len(WORKER_FILES)} worker scripts...", log_type='system')
        workers = []
        for filename in WORKER_FILES:
            script = load_worker_script(filename)
            workers.append({
                'name': filename.replace('.txt', '').upper(),
                'script': script
            })
            console.add_log(f"Loaded: {filename}", log_type='system')
        
        console.update()  # Update once after loading all
        console.add_log(f"Opening {len(workers)} separate browser windows...", log_type='system')
        console.add_log("Arranging windows in 2 rows x 3 columns", log_type='system')
        console.update_status(f"🌐 Opening {len(workers)} windows...")
        
        # Calculate window positions for 2x3 grid
        # Row 0: Windows 1, 2, 3 (top)
        # Row 1: Windows 4, 5, 6 (bottom)
        positions = [
            (0, 0),                              # Top-left
            (WINDOW_WIDTH, 0),                   # Top-center
            (WINDOW_WIDTH * 2, 0),               # Top-right
            (0, WINDOW_HEIGHT),                  # Bottom-left
            (WINDOW_WIDTH, WINDOW_HEIGHT),       # Bottom-center
            (WINDOW_WIDTH * 2, WINDOW_HEIGHT)    # Bottom-right
        ]
        
        # Open each window
        for i, worker in enumerate(workers):
            console.add_log(f"Opening window {i+1} for {worker['name']}...", log_type='system')
            try:
                driver = setup_driver(
                    window_position=positions[i],
                    window_size=(WINDOW_WIDTH, WINDOW_HEIGHT),
                    profile_number=i+1  # Each browser gets its own profile
                )
                driver.get(QUINYX_URL)
                drivers.append(driver)
                console.add_log(f"Window {i+1} opened and positioned", log_type='success')
                console.update()
                
                # LONGER delay between windows to prevent crashes
                if i < len(workers) - 1:  # Don't wait after last window
                    console.add_log(f"Waiting 5 seconds before opening next window...", log_type='system')
                    for _ in range(5):
                        time.sleep(1)
                        console.update()
                        
            except Exception as e:
                console.add_log(f"ERROR opening window {i+1}: {e}", log_type='error')
                console.add_log(f"Will try to continue with other windows...", log_type='system')
                console.update()
        
        console.update()  # Update once after opening all windows
        
        if len(drivers) == 0:
            console.add_log("FATAL: No windows opened successfully!", log_type='error')
            console.update()
            input("\nPress Enter to exit...")
            return
        
        console.add_log(f"Successfully opened {len(drivers)} out of {len(workers)} windows", log_type='success')
        if len(drivers) < len(workers):
            console.add_log(f"⚠️ Warning: Only {len(drivers)} windows opened (expected {len(workers)})", log_type='error')
            console.add_log(f"Continuing with available windows...", log_type='system')
        else:
            console.add_log("All windows visible - no need to switch between tabs!", log_type='success')
        
        # First time setup - login to all windows once
        console.update_status("⏳ Waiting for login (FIRST TIME ONLY)...")
        console.add_log("=" * 80, log_type='success')
        console.add_log("🔑 FIRST TIME SETUP: Login to ALL 6 windows", log_type='error')
        console.add_log("=" * 80, log_type='success')
        console.add_log("⚠️ Each profile needs login ONCE - they'll remember it forever!", log_type='system')
        console.add_log("Login to window 1 (top-left), then 2, then 3, etc...", log_type='system')
        console.add_log("After logging into all 6, click DONE LOGGING IN button", log_type='system')
        console.add_log("Next time you run this script - AUTO LOGGED IN! ✅", log_type='success')
        console.add_log("=" * 80, log_type='success')
        console.enable_login_done_button()
        console.update()
        
        print("\n🔑 Login to all 6 windows, then click DONE LOGGING IN button...")
        
        # Wait for user to click Done button
        console.wait_for_login_done()
        
        console.add_log("=" * 80, log_type='success')
        console.add_log("✅ Profiles saved! Next run = AUTO LOGIN!", log_type='success')
        console.add_log("=" * 80, log_type='success')
        console.update()
        
        # Enable Start button and wait for user
        console.add_log("═" * 80, log_type='system')
        console.add_log("All tabs are ready!", log_type='success')
        console.add_log("Click the START WORKERS button to begin", log_type='success')
        console.add_log("═" * 80, log_type='system')
        console.enable_start_button()
        console.update()
        
        print("\n✅ All tabs opened and ready!")
        print("➡️  Click the START WORKERS button in the console window to begin...")
        
        # Wait for user to click Start button
        console.wait_for_start()
        
        # Inject scripts into each window
        console.update_status("💉 Injecting worker scripts...")
        console.add_log("Injecting worker scripts into windows...", log_type='system')
        for i, driver in enumerate(drivers):
            if i < len(workers):
                if inject_script(driver, workers[i]['script'], workers[i]['name']):
                    console.add_log(f"Script injected successfully", workers[i]['name'], 'success')
                else:
                    console.add_log(f"Failed to inject script", workers[i]['name'], 'error')
                time.sleep(1)
        
        console.update()  # Update once after all injections
        
        console.add_log("=" * 80, log_type='success')
        console.add_log(f"{len(drivers)} WORKERS STARTED! 🎉", log_type='success')
        console.add_log("=" * 80, log_type='success')
        if len(drivers) < len(workers):
            console.add_log(f"⚠️ Running with {len(drivers)} out of {len(workers)} workers", log_type='error')
        console.add_log(f"{len(drivers)} windows visible side-by-side - NO TAB SWITCHING!", log_type='success')
        console.add_log("Auto-refresh enabled - refreshing all windows every {} seconds".format(REFRESH_INTERVAL), log_type='system')
        console.add_log("Console window is ALWAYS ON TOP and will stay visible", log_type='system')
        console.add_log("Workers run in separate browser windows - your HBO is safe!", log_type='success')
        console.update()
        
        print("\n✅ Unified console window is running!")
        print(f"   {len(drivers)} browser windows arranged in grid")
        print("   All worker logs appear in the always-on-top console")
        print("   Your HBO stays open - separate browser profile!")
        print("   Press Ctrl+C here to stop (workers continue in browser)")
        
        # Main monitoring loop (no rotation needed - all windows visible!)
        last_status_check = time.time()
        last_refresh = time.time()
        last_update = time.time()
        worker_stats = {}
        cycle_count = 0
        
        console.update_status(f"👁️ Monitoring {len(drivers)} windows...")
        console.update()
        
        while True:
            # Update window every 2 seconds
            now = time.time()
            if now - last_update >= 2.0:
                console.update()
                last_update = now
                cycle_count += 1
            
            # Status check for all workers
            if now - last_status_check >= STATUS_CHECK_INTERVAL:
                console.add_log("─" * 80, log_type='system')
                console.add_log("📊 Status Update - All Windows:", log_type='system')
                
                # Check all windows
                for i, driver in enumerate(drivers):
                    try:
                        log_data = get_worker_logs(driver)
                        if log_data:
                            key = log_data['worker']
                            # Only log if stats changed
                            if key not in worker_stats or worker_stats[key] != (log_data['deleted'], log_data['failed']):
                                worker_stats[key] = (log_data['deleted'], log_data['failed'])
                                console.add_log(
                                    f"  → {log_data['deleted']} denied, {log_data['failed']} failed",
                                    log_data['worker'],
                                    'success'
                                )
                    except Exception as e:
                        console.add_log(f"  → Error checking window {i+1}: {e}", log_type='error')
                
                console.add_log("─" * 80, log_type='system')
                last_status_check = now
            
            # Refresh all windows periodically to keep them active
            if now - last_refresh >= REFRESH_INTERVAL:
                console.add_log("🔄 REFRESHING ALL WINDOWS to keep them active...", log_type='system')
                
                # Refresh each window
                for i, driver in enumerate(drivers):
                    try:
                        driver.refresh()
                        worker_name = workers[i]['name'] if i < len(workers) else f"Worker {i+1}"
                        console.add_log(f"Window {i+1} refreshed", worker_name, 'success')
                        time.sleep(1)
                        # Re-inject script after refresh
                        if i < len(workers):
                            inject_script(driver, workers[i]['script'], worker_name)
                            console.add_log(f"Script re-injected after refresh", worker_name, 'success')
                    except Exception as e:
                        console.add_log(f"Refresh error: {e}", f"Window {i+1}", 'error')
                    time.sleep(1)
                
                console.add_log("✅ All windows refreshed and scripts re-injected", log_type='success')
                last_refresh = now
            
            # Update status
            console.update_status(f"👁️ Monitoring {len(drivers)} windows - Cycle #{cycle_count} | Next refresh in {int(REFRESH_INTERVAL - (now - last_refresh))}s")
            
            time.sleep(2)  # Check every 2 seconds
    
    except KeyboardInterrupt:
        console.add_log("\n⏸️  Monitoring stopped by user", log_type='system')
        console.add_log("Workers are still running in browser windows!", log_type='system')
        console.update_status("⏸️  Stopped - Workers still running in browsers")
        console.update()
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        try:
            console.add_log(f"❌ ERROR: {e}", log_type='error')
            console.update_status("❌ Error occurred")
            console.update()
        except:
            pass
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            console.add_log("=" * 80, log_type='system')
            console.add_log("PROGRAM ENDED", log_type='system')
            console.add_log("⚠️  Browser windows are still open with workers running", log_type='system')
            console.add_log("Close the browser windows manually when workers are done", log_type='system')
            console.add_log("=" * 80, log_type='system')
            console.update()
        except:
            print("\n=" * 80)
            print("PROGRAM ENDED")
            print("⚠️  Browser windows are still open with workers running")
            print("Close the browser windows manually when workers are done")
            print("=" * 80)
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
