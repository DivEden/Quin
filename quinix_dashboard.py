"""
QUINIX 6-WORKER DASHBOARD WITH MULTI-PANEL MONITORING
======================================================
Enhanced Python program with 4-panel dashboard:
1. Heartbeat Monitor - Animated hearts showing browser status
2. Completion Stats - Table with each worker's progress
3. Hourly Graph - Completions per hour visualization
4. Overall Progress - Total progress, ETA, speed

REQUIREMENTS:
- pip install selenium
- Edge browser installed
- EdgeDriver (will auto-download with selenium 4.6+)

USAGE:
1. Run: python quinix_dashboard.py
2. Login to all 6 windows once (profiles will remember)
3. Click DONE LOGGING IN button
4. Click START WORKERS button
5. Watch the dashboard!
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
import ctypes

# Windows sleep prevention
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# ============================================================================
# CONFIGURATION
# ============================================================================

# Update this URL to your Quinyx absence request page
QUINYX_URL = "https://web.quinyx.com/schedule/191654?end=2026-02-28&start=2026-02-01&timeframe=multiday_month"

# Window arrangement settings
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 540
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
# MULTI-PANEL DASHBOARD CONSOLE
# ============================================================================

class DashboardConsole:
    """Multi-panel dashboard console window for monitoring all workers"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("QUINIX-SYS :: WORKER CONTROL TERMINAL")
        self.root.geometry("1400x900")
        self.root.configure(bg='#0a0a1a')  # Dark navy
        
        # Make window always on top
        self.root.attributes('-topmost', True)
        
        # Worker tracking data
        self.worker_heartbeats = {i: {'alive': True, 'last_beat': time.time()} for i in range(1, 7)}
        self.worker_stats = {i: {'deleted': 0, 'failed': 0, 'last_update': time.time()} for i in range(1, 7)}
        self.hourly_data = deque(maxlen=60)  # Last 60 data points (1 per minute)
        self.start_time = time.time()
        self.total_processed = 0
        self.total_target = 11903  # Total absence requests
        
        self.started = False
        self.login_done = False
        
        # Create main layout
        self._create_header()
        self._create_dashboard()
        self._create_log_panel()
        
        # Start update loop (no animation needed)
        self._update_graphs()
    
    def _create_header(self):
        """Create header with title and buttons"""
        header_frame = tk.Frame(self.root, bg='#0a0a1a', height=120)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        # Title with ASCII art border
        title_label = tk.Label(
            header_frame,
            text="╔═══════════════════════════════════════════════════════════════════╗\n║  QUINIX-SYS :: DISTRIBUTED WORKER CONTROL TERMINAL v2.6.0      ║\n╚═══════════════════════════════════════════════════════════════════╝",
            font=('Courier New', 10, 'bold'),
            bg='#0a0a1a',
            fg='#00d4ff',  # Bright cyan
            justify='left'
        )
        title_label.pack(pady=5)
        
        # Sleep prevention status indicator
        self.sleep_status_label = tk.Label(
            header_frame,
            text="[SLEEP: ALLOWED]",
            font=('Courier New', 9),
            bg='#0a0a1a',
            fg='#4a5f7a'
        )
        self.sleep_status_label.pack(pady=2)
        
        # Button frame
        button_frame = tk.Frame(header_frame, bg='#0a0a1a')
        button_frame.pack()
        
        self.login_done_button = tk.Button(
            button_frame,
            text="[√] AUTH COMPLETE",
            command=self.on_login_done_clicked,
            font=('Courier New', 10, 'bold'),
            bg='#002244',
            fg='#4dd0e1',  # Light cyan
            activebackground='#003366',
            activeforeground='#4dd0e1',
            cursor='hand2',
            relief=tk.FLAT,
            bd=1,
            padx=15,
            pady=6,
            state=tk.DISABLED
        )
        self.login_done_button.pack(side=tk.LEFT, padx=5)
        
        self.start_button = tk.Button(
            button_frame,
            text="[>] INITIATE WORKERS",
            command=self.on_start_clicked,
            font=('Courier New', 10, 'bold'),
            bg='#001a33',
            fg='#00d4ff',  # Bright cyan
            activebackground='#003366',
            activeforeground='#00d4ff',
            cursor='hand2',
            relief=tk.FLAT,
            bd=1,
            padx=15,
            pady=6,
            state=tk.DISABLED
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
    
    def _create_dashboard(self):
        """Create 4-panel dashboard"""
        dashboard_frame = tk.Frame(self.root, bg='#0a0a1a')
        dashboard_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top row (Heartbeat + Stats)
        top_frame = tk.Frame(dashboard_frame, bg='#0a0a1a')
        top_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        
        self._create_status_panel(top_frame)
        self._create_stats_panel(top_frame)
        
        # Bottom row (Graph + Progress)
        bottom_frame = tk.Frame(dashboard_frame, bg='#0a0a1a')
        bottom_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        
        self._create_graph_panel(bottom_frame)
        self._create_progress_panel(bottom_frame)
    
    def _create_status_panel(self, parent):
        """Create worker status monitor panel (no blinking!)"""
        panel = tk.LabelFrame(
            parent,
            text="┌─[ WORKER NODE STATUS ]─────────────────────┐",
            font=('Courier New', 10, 'bold'),
            bg='#0a0a1a',
            fg='#00d4ff',
            relief=tk.FLAT,
            bd=2
        )
        panel.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=2, pady=2)
        
        self.status_labels = {}
        for i in range(1, 7):
            frame = tk.Frame(panel, bg='#0a0a1a')
            frame.pack(fill=tk.X, padx=10, pady=6)
            
            # Worker ID
            id_label = tk.Label(
                frame,
                text=f"[WORKER-{i}]",
                font=('Courier New', 9, 'bold'),
                bg='#0a0a1a',
                fg='#4dd0e1',  # Light cyan
                width=12,
                anchor='w'
            )
            id_label.pack(side=tk.LEFT, padx=5)
            
            # Status bar (ASCII)
            status_bar = tk.Label(
                frame,
                text="████████████",
                font=('Courier New', 9),
                bg='#0a0a1a',
                fg='#00d4ff',  # Cyan when alive
                width=15,
                anchor='w'
            )
            status_bar.pack(side=tk.LEFT, padx=5)
            
            # Status text
            status_text = tk.Label(
                frame,
                text="[ONLINE]",
                font=('Courier New', 9, 'bold'),
                bg='#0a0a1a',
                fg='#00d4ff'
            )
            status_text.pack(side=tk.RIGHT, padx=5)
            
            self.status_labels[i] = {'bar': status_bar, 'text': status_text}
        
        # Remove the heartbeat animation
        self.heartbeat_labels = self.status_labels  # Compatibility
    
    def _create_stats_panel(self, parent):
        """Create completion statistics panel"""
        panel = tk.LabelFrame(
            parent,
            text="┌─[ TASK COMPLETION METRICS ]───────────────┐",
            font=('Courier New', 10, 'bold'),
            bg='#0a0a1a',
            fg='#00d4ff',
            relief=tk.FLAT,
            bd=2
        )
        panel.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=2, pady=2)
        
        # Create table
        self.stats_tree = ttk.Treeview(
            panel,
            columns=('worker', 'denied', 'failed', 'total', 'rate'),
            show='headings',
            height=6
        )
        
        self.stats_tree.heading('worker', text='NODE')
        self.stats_tree.heading('denied', text='DENIED')
        self.stats_tree.heading('failed', text='FAILED')
        self.stats_tree.heading('total', text='TOTAL')
        self.stats_tree.heading('rate', text='RATE/MIN')
        
        self.stats_tree.column('worker', width=120, anchor='center')
        self.stats_tree.column('denied', width=90, anchor='center')
        self.stats_tree.column('failed', width=90, anchor='center')
        self.stats_tree.column('total', width=90, anchor='center')
        self.stats_tree.column('rate', width=100, anchor='center')
        
        # Style the treeview - CYBERPUNK
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Treeview', 
            background='#0a0a1a', 
            foreground='#00d4ff', 
            fieldbackground='#0a0a1a',
            font=('Courier New', 9))
        style.configure('Treeview.Heading', 
            background='#001a33', 
            foreground='#00d4ff', 
            font=('Courier New', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#003366')])
        
        self.stats_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize rows
        for i in range(1, 7):
            self.stats_tree.insert('', 'end', iid=i, values=(f'WORKER-{i}', '0', '0', '0', '0.0'))
    
    def _create_graph_panel(self, parent):
        """Create hourly completion graph panel"""
        panel = tk.LabelFrame(
            parent,
            text="┌─[ THROUGHPUT ANALYSIS ]────────────────────┐",
            font=('Courier New', 10, 'bold'),
            bg='#0a0a1a',
            fg='#00d4ff',
            relief=tk.FLAT,
            bd=2
        )
        panel.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=2, pady=2)
        
        self.graph_canvas = tk.Canvas(
            panel,
            bg='#0a0a1a',
            highlightthickness=1,
            highlightbackground='#001a33'
        )
        self.graph_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_progress_panel(self, parent):
        """Create overall progress panel"""
        panel = tk.LabelFrame(
            parent,
            text="┌─[ MISSION PROGRESS ]───────────────────────┐",
            font=('Courier New', 10, 'bold'),
            bg='#0a0a1a',
            fg='#00d4ff',
            relief=tk.FLAT,
            bd=2
        )
        panel.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=2, pady=2)
        
        # Progress bar
        self.progress_label = tk.Label(
            panel,
            text="[=====>              ] 0 / 11,903 (0.00%)",
            font=('Courier New', 11, 'bold'),
            bg='#0a0a1a',
            fg='#00d4ff'
        )
        self.progress_label.pack(pady=10)
        
        # ASCII progress bar
        self.progress_bar_ascii = tk.Label(
            panel,
            text="[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]",
            font=('Courier New', 10),
            bg='#0a0a1a',
            fg='#4dd0e1'
        )
        self.progress_bar_ascii.pack(pady=5)
        
        # Stats frame
        stats_frame = tk.Frame(panel, bg='#0a0a1a')
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.speed_label = tk.Label(
            stats_frame,
            text=">> THROUGHPUT: 0.0 tasks/min",
            font=('Courier New', 10),
            bg='#0a0a1a',
            fg='#4dd0e1'
        )
        self.speed_label.pack(pady=5)
        
        self.eta_label = tk.Label(
            stats_frame,
            text=">> ETA: CALCULATING...",
            font=('Courier New', 10),
            bg='#0a0a1a',
            fg='#4dd0e1'
        )
        self.eta_label.pack(pady=5)
        
        self.runtime_label = tk.Label(
            stats_frame,
            text=">> UPTIME: 00:00:00",
            font=('Courier New', 10),
            bg='#0a0a1a',
            fg='#4dd0e1'
        )
        self.runtime_label.pack(pady=5)
    
    def _create_log_panel(self):
        """Create collapsible log panel at bottom"""
        log_frame = tk.LabelFrame(
            self.root,
            text="└─[ SYSTEM LOG ]────────────────────────────────────────────────────────────────────────┘",
            font=('Courier New', 9),
            bg='#0a0a1a',
            fg='#00d4ff',
            relief=tk.FLAT,
            bd=2
        )
        log_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=160,
            height=6,
            font=('Courier New', 8),
            bg='#0a0a1a',
            fg='#00d4ff'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Configure text tags - CYBERPUNK COLORS
        self.log_text.tag_config('worker1', foreground='#00d4ff')  # Cyan
        self.log_text.tag_config('worker2', foreground='#4dd0e1')  # Light Cyan
        self.log_text.tag_config('worker3', foreground='#ffff00')  # Yellow
        self.log_text.tag_config('worker4', foreground='#ff00ff')  # Magenta
        self.log_text.tag_config('worker5', foreground='#ff8800')  # Orange
        self.log_text.tag_config('worker6', foreground='#7bb3ff')  # Sky Blue
        self.log_text.tag_config('system', foreground='#00d4ff')    # Cyan
        self.log_text.tag_config('error', foreground='#ff4444')     # Light Red
        self.log_text.tag_config('success', foreground='#4dd0e1')   # Light Cyan
        
        self.log_count = 0
    
    def update_worker_heartbeat(self, worker_num, alive=True):
        """Update worker status (no animation)"""
        if 1 <= worker_num <= 6:
            self.worker_heartbeats[worker_num]['alive'] = alive
            self.worker_heartbeats[worker_num]['last_beat'] = time.time()
            
            # Update status display
            try:
                if alive:
                    self.status_labels[worker_num]['bar'].config(fg='#00d4ff', text="████████████")  # Cyan filled
                    self.status_labels[worker_num]['text'].config(text="[ONLINE]", fg='#00d4ff')
                else:
                    self.status_labels[worker_num]['bar'].config(fg='#1a1a2e', text="░░░░░░░░░░░░")  # Dark/empty
                    self.status_labels[worker_num]['text'].config(text="[OFFLINE]", fg='#ff4444')
            except:
                pass
    def _update_graphs(self):
        """Update graph and progress displays"""
        try:
            if not self.root.winfo_exists():
                return
            
            # Update ASCII progress bar
            percentage = (self.total_processed / self.total_target) * 100 if self.total_target > 0 else 0
            filled = int((percentage / 100) * 40)  # 40 char wide bar
            bar = "█" * filled + "░" * (40 - filled)
            self.progress_label.config(text=f"[{bar[:5]}{'>' if filled > 0 else ''}{bar[5:18]}] {self.total_processed:,} / {self.total_target:,} ({percentage:.2f}%)")
            self.progress_bar_ascii.config(text=f"[{bar}]")
            
            # Calculate speed
            runtime = time.time() - self.start_time
            speed = (self.total_processed / runtime) * 60 if runtime > 0 else 0  # per minute
            self.speed_label.config(text=f">> THROUGHPUT: {speed:.1f} tasks/min")
            
            # Calculate ETA
            remaining = self.total_target - self.total_processed
            if speed > 0:
                eta_minutes = remaining / speed
                eta_hours = int(eta_minutes // 60)
                eta_mins = int(eta_minutes % 60)
                self.eta_label.config(text=f">> ETA: {eta_hours:02d}h {eta_mins:02d}m")
            else:
                self.eta_label.config(text=">> ETA: CALCULATING...")
            
            # Update runtime
            runtime_hours = int(runtime // 3600)
            runtime_mins = int((runtime % 3600) // 60)
            runtime_secs = int(runtime % 60)
            self.runtime_label.config(text=f">> UPTIME: {runtime_hours:02d}:{runtime_mins:02d}:{runtime_secs:02d}")
            
            # Add current data point to hourly graph
            self.hourly_data.append(self.total_processed)
            
            # Draw graph
            self._draw_graph()
            
            # Schedule next update
            self.root.after(2000, self._update_graphs)
        except:
            pass
    
    def _draw_graph(self):
        """Draw completion graph on canvas - CYBERPUNK STYLE"""
        try:
            canvas = self.graph_canvas
            canvas.delete('all')  # Clear previous
            
            width = canvas.winfo_width()
            height = canvas.winfo_height()
            
            if width < 10 or height < 10 or len(self.hourly_data) < 2:
                # Draw "NO DATA" message
                canvas.create_text(width//2, height//2, 
                    text=">> AWAITING DATA <<", 
                    fill='#00d4ff', 
                    font=('Courier New', 12, 'bold'))
                return
            
            # Draw axes
            margin = 30
            graph_width = width - 2 * margin
            graph_height = height - 2 * margin
            
            # Y axis
            canvas.create_line(margin, margin, margin, height - margin, fill='#00d4ff', width=2)
            # X axis
            canvas.create_line(margin, height - margin, width - margin, height - margin, fill='#00d4ff', width=2)
            
            # Grid lines
            for i in range(5):
                y = margin + (graph_height // 5) * i
                canvas.create_line(margin, y, width - margin, y, fill='#001a33', width=1, dash=(2, 4))
            
            # Plot data
            if len(self.hourly_data) > 1:
                points = list(self.hourly_data)
                max_val = max(points) if points else 1
                
                coords = []
                for i, val in enumerate(points):
                    x = margin + (i / (len(points) - 1)) * graph_width if len(points) > 1 else margin
                    y = height - margin - (val / max_val) * graph_height if max_val > 0 else height - margin
                    coords.extend([x, y])
                
                if len(coords) >= 4:
                    # Draw line with glow effect
                    canvas.create_line(coords, fill='#0066cc', width=4, smooth=True)  # Glow
                    canvas.create_line(coords, fill='#4dd0e1', width=2, smooth=True)  # Main line
                    
                    # Draw points
                    for i in range(0, len(coords), 2):
                        x, y = coords[i], coords[i+1]
                        canvas.create_oval(x-4, y-4, x+4, y+4, fill='#0066cc', outline='')  # Glow
                        canvas.create_oval(x-2, y-2, x+2, y+2, fill='#4dd0e1', outline='#4dd0e1')  # Point
            
            # Labels
            canvas.create_text(margin - 5, margin - 10, text=f"MAX:{max(self.hourly_data) if self.hourly_data else 0}", 
                             fill='#00d4ff', font=('Courier New', 8, 'bold'), anchor='w')
            canvas.create_text(width - margin, height - margin + 15, text=f"T+{len(self.hourly_data)}min", 
                             fill='#00d4ff', font=('Courier New', 8, 'bold'), anchor='e')
        except:
            pass
    
    def update_worker_heartbeat(self, worker_num, alive=True):
        """Update worker heartbeat status"""
        if 1 <= worker_num <= 6:
            self.worker_heartbeats[worker_num]['alive'] = alive
            self.worker_heartbeats[worker_num]['last_beat'] = time.time()
    
    def update_worker_stats(self, worker_num, deleted, failed):
        """Update worker statistics"""
        if 1 <= worker_num <= 6:
            old_total = self.worker_stats[worker_num]['deleted'] + self.worker_stats[worker_num]['failed']
            self.worker_stats[worker_num]['deleted'] = deleted
            self.worker_stats[worker_num]['failed'] = failed
            new_total = deleted + failed
            
            # Update total processed
            self.total_processed = sum(s['deleted'] + s['failed'] for s in self.worker_stats.values())
            
            # Calculate rate
            time_diff = time.time() - self.worker_stats[worker_num]['last_update']
            if time_diff > 0:
                rate = ((new_total - old_total) / time_diff) * 60  # per minute
            else:
                rate = 0.0
            
            self.worker_stats[worker_num]['last_update'] = time.time()
            
            # Update table
            try:
                self.stats_tree.item(worker_num, values=(
                    f'WORKER-{worker_num}',
                    f'{deleted:,}',
                    f'{failed:,}',
                    f'{new_total:,}',
                    f'{rate:.1f}'
                ))
            except:
                pass
    
    def on_start_clicked(self):
        """Handle Start button click"""
        self.started = True
        self.start_button.config(
            text="[*] WORKERS ACTIVE",
            state=tk.DISABLED,
            bg='#000f1a',
            fg='#00d4ff',
            cursor='arrow'
        )
        self.add_log(">> WORKERS INITIATED - MONITORING ACTIVE", log_type='success')
        self.start_time = time.time()  # Reset start time when workers actually start
    
    def on_login_done_clicked(self):
        """Handle Login Done button click"""
        self.login_done = True
        self.login_done_button.config(
            text="[*] AUTHENTICATED",
            state=tk.DISABLED,
            bg='#001f3f',
            fg='#4dd0e1',
            cursor='arrow'
        )
        self.add_log(">> AUTHENTICATION COMPLETE - PROCEEDING", log_type='success')
        self.root.after(1000, lambda: self.login_done_button.pack_forget())
    
    def enable_start_button(self):
        """Enable the Start button"""
        try:
            if self.root.winfo_exists():
                self.start_button.config(state=tk.NORMAL)
        except:
            pass
    
    def enable_login_done_button(self):
        """Enable the Login Done button"""
        try:
            if self.root.winfo_exists():
                self.login_done_button.pack(side=tk.LEFT, padx=5)
                self.login_done_button.config(state=tk.NORMAL)
        except:
            pass
    
    def wait_for_start(self):
        """Block until Start button is clicked"""
        try:
            while not self.started and self.root.winfo_exists():
                self.root.update()
                time.sleep(0.1)
        except:
            pass
    
    def wait_for_login_done(self):
        """Block until Login Done button is clicked"""
        try:
            while not self.login_done and self.root.winfo_exists():
                self.root.update()
                time.sleep(0.1)
        except:
            pass
    
    def update(self):
        """Update the window"""
        try:
            if self.root.winfo_exists():
                self.root.update()
        except:
            pass
    
    def update_status(self, status):
        """Update status (kept for compatibility)"""
        pass  # Status now shown in individual panels
    
    def set_sleep_prevention(self, active):
        """Update sleep prevention status indicator"""
        try:
            if self.root.winfo_exists():
                if active:
                    self.sleep_status_label.config(text="[SLEEP: PREVENTED ⚡]", fg='#00d4ff')
                else:
                    self.sleep_status_label.config(text="[SLEEP: ALLOWED]", fg='#4a5f7a')
        except:
            pass
    
    def add_log(self, message, worker_id=None, log_type='info'):
        """Add a log message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Determine tag
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
        
        try:
            if self.root.winfo_exists():
                self.log_text.insert('end', formatted, tag)
                self.log_text.see('end')
                
                # Limit log size
                self.log_count += 1
                if self.log_count > 500:
                    self.log_text.delete('1.0', '50.0')
                    self.log_count = 450
        except:
            pass

# ============================================================================
# WINDOWS SLEEP PREVENTION
# ============================================================================

def prevent_sleep():
    """Prevent Windows from going to sleep"""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        return True
    except:
        return False

def allow_sleep():
    """Allow Windows to sleep again"""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        return True
    except:
        return False

# ============================================================================
# BROWSER AUTOMATION FUNCTIONS  
# ============================================================================

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
    options.add_argument("--mute-audio")
    # Page load strategy to avoid hanging
    options.page_load_strategy = 'eager'
    
    # Enable profile persistence and session storage
    options.add_argument("--disable-session-crashed-bubble")
    options.add_argument("--disable-infobars")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # CRITICAL: Each browser gets its own profile to avoid crashes
    # (Multiple browsers cannot share same profile simultaneously)
    automation_profile = rf"C:\Users\MadsE\Desktop\quinix-workers\EdgeProfile{profile_number}"
    options.add_argument(f"user-data-dir={automation_profile}")
    options.add_argument(f"profile-directory=Profile{profile_number}")
    
    driver = webdriver.Edge(options=options)
    
    # Position and size window if specified
    if window_position and window_size:
        driver.set_window_position(window_position[0], window_position[1])
        driver.set_window_size(window_size[0], window_size[1])
    
    return driver


def inject_script(driver, script, worker_name):
    """Inject JavaScript worker script into the page"""
    try:
        driver.execute_script(script)
        return True
    except Exception as e:
        print(f"Error injecting script for {worker_name}: {e}")
        return False


def get_worker_logs(driver):
    """Get logs from worker via console"""
    try:
        logs = driver.execute_script("""
            if (window.workerLogs && window.workerLogs.length > 0) {
                const latest = window.workerLogs[window.workerLogs.length - 1];
                return latest;
            }
            return null;
        """)
        return logs
    except:
        return None


# ============================================================================
# MAIN PROGRAM
# ============================================================================

def main():
    print("╔════════════════════════════════════════════════════════════════════════════════╗")
    print("║   QUINIX-SYS :: DISTRIBUTED WORKER CONTROL TERMINAL v2.6.0        ║")
    print("║   [CYBERPUNK EDITION] - MATRIX INTERFACE ACTIVE                   ║")
    print("╚════════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Create enhanced dashboard console
    console = DashboardConsole()
    console.add_log(">> TERMINAL INITIALIZED - 4 PANELS ACTIVE", log_type='success')
    console.add_log(">> [PANEL-1] WORKER NODE STATUS MONITOR", log_type='system')
    console.add_log(">> [PANEL2] TASK COMPLETION METRICS", log_type='system')
    console.add_log(">> [PANEL-3] THROUGHPUT ANALYSIS GRAPH", log_type='system')
    console.add_log(">> [PANEL-4] MISSION PROGRESS TRACKER", log_type='system')
    console.update()
    
    # Load worker scripts
    workers = []
    for i, filename in enumerate(WORKER_FILES):
        try:
            script_path = Path(filename)
            if not script_path.exists():
                console.add_log(f"ERROR: Worker script not found: {filename}", log_type='error')
                continue
            
            with open(script_path, 'r', encoding='utf-8') as f:
                script = f.read()
            
            worker_name = f"WORKER-{i+1}-{filename.replace('worker-', '').replace('.txt', '').replace('-', '').upper()}"
            workers.append({'name': worker_name, 'script': script})
            console.add_log(f"Loaded {filename}", worker_name, 'success')
        except Exception as e:
            console.add_log(f"ERROR loading {filename}: {e}", log_type='error')
    
    if len(workers) == 0:
        console.add_log("FATAL: No worker scripts loaded!", log_type='error')
        console.update()
        input("\nPress Enter to exit...")
        return
    
    # Setup multiple drivers (one per window)
    console.add_log("Setting up 6 separate Edge windows...", log_type='system')
    console.add_log("Each browser gets its own profile (no conflicts!)", log_type='success')
    console.add_log("Windows will be arranged in a 2x3 grid on your screen", log_type='success')
    console.update()
    
    drivers = []
    
    try:
        console.update()
        console.add_log(f"Opening {len(workers)} separate browser windows...", log_type='system')
        console.add_log("Arranging windows in 2 rows x 3 columns", log_type='system')
        
        # Calculate window positions for 2x3 grid
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
                    profile_number=i+1
                )
                driver.get(QUINYX_URL)
                drivers.append(driver)
                console.add_log(f"Window {i+1} opened and positioned", log_type='success')
                console.update()
                
                # Update heartbeat - window alive
                console.update_worker_heartbeat(i+1, alive=True)
                
                if i < len(workers) - 1:
                    console.add_log(f"Waiting 5 seconds before opening next window...", log_type='system')
                    for _ in range(5):
                        time.sleep(1)
                        console.update()
                        
            except Exception as e:
                console.add_log(f"ERROR opening window {i+1}: {e}", log_type='error')
                console.update_worker_heartbeat(i+1, alive=False)
        
        console.update()
        
        if len(drivers) == 0:
            console.add_log("FATAL: No windows opened successfully!", log_type='error')
            console.update()
            input("\nPress Enter to exit...")
            return
        
        console.add_log(f"Successfully opened {len(drivers)} out of {len(workers)} windows", log_type='success')
        if len(drivers) < len(workers):
            console.add_log(f"⚠️ Warning: Only {len(drivers)} windows opened (expected {len(workers)})", log_type='error')
        
        # First time setup - login to all windows once
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
        console.add_log("All windows are ready!", log_type='success')
        console.add_log("Click the START WORKERS button to begin", log_type='success')
        console.enable_start_button()
        console.update()
        
        print("\n✅ All windows opened and ready!")
        print("➡️  Click the START WORKERS button in the dashboard to begin...")
        
        # Wait for user to click Start
        console.wait_for_start()
        
        # Prevent computer from sleeping
        console.add_log(">> ACTIVATING SLEEP PREVENTION...", log_type='system')
        if prevent_sleep():
            console.add_log(">> [OK] SLEEP MODE DISABLED - PC WILL STAY AWAKE", log_type='success')
            console.set_sleep_prevention(True)
        else:
            console.add_log(">> [WARN] Could not disable sleep mode", log_type='error')
        console.update()
        
        # Inject scripts into each window
        console.add_log(">> INJECTING WORKER SCRIPTS INTO NODES...", log_type='system')
        for i, driver in enumerate(drivers):
            if i < len(workers):
                if inject_script(driver, workers[i]['script'], workers[i]['name']):
                    console.add_log(f"Script injected successfully", workers[i]['name'], 'success')
                else:
                    console.add_log(f"Failed to inject script", workers[i]['name'], 'error')
                time.sleep(1)
        
        console.add_log("=" * 80, log_type='success')
        console.add_log(f"{len(drivers)} WORKERS STARTED! 🎉", log_type='success')
        console.add_log("=" * 80, log_type='success')
        console.add_log("Dashboard showing live stats from all workers!", log_type='success')
        console.update()
        
        print("\n✅ Multi-panel dashboard is running!")
        print(f"   {len(drivers)} browser windows with workers active")
        print("   💓 Heartbeat monitor shows browser status")
        print("   📊 Stats table shows completion progress")
        print("   📈 Graph tracks completions per hour")
        print("   🎯 Progress panel shows ETA and speed")
        print("   Press Ctrl+C here to stop (workers continue in browser)")
        
        # Main monitoring loop
        last_status_check = time.time()
        last_refresh = time.time()
        last_update = time.time()
        worker_stats = {}
        cycle_count = 0
        
        console.update()
        
        while True:
            now = time.time()
            if now - last_update >= 2.0:
                console.update()
                last_update = now
                cycle_count += 1
            
            # Status check for all workers
            if now - last_status_check >= STATUS_CHECK_INTERVAL:
                # Check all windows
                for i, driver in enumerate(drivers):
                    try:
                        log_data = get_worker_logs(driver)
                        if log_data:
                            worker_num = i + 1
                            
                            # Update heartbeat - worker is alive
                            console.update_worker_heartbeat(worker_num, alive=True)
                            
                            # Update stats
                            console.update_worker_stats(
                                worker_num,
                                log_data.get('deleted', 0),
                                log_data.get('failed', 0)
                            )
                            
                            key = log_data['worker']
                            if key not in worker_stats or worker_stats[key] != (log_data['deleted'], log_data['failed']):
                                worker_stats[key] = (log_data['deleted'], log_data['failed'])
                                console.add_log(
                                    f"✓ {log_data['deleted']} denied, {log_data['failed']} failed",
                                    log_data['worker'],
                                    'success'
                                )
                    except Exception as e:
                        # Worker might be dead
                        console.update_worker_heartbeat(i+1, alive=False)
                        console.add_log(f"⚠️ Error checking window {i+1}: {e}", log_type='error')
                
                last_status_check = now
            
            # Refresh all windows periodically
            if now - last_refresh >= REFRESH_INTERVAL:
                console.add_log("🔄 REFRESHING ALL WINDOWS to keep them active...", log_type='system')
                
                for i, driver in enumerate(drivers):
                    try:
                        driver.refresh()
                        worker_name = workers[i]['name'] if i < len(workers) else f"Worker {i+1}"
                        console.add_log(f"Window {i+1} refreshed", worker_name, 'success')
                        time.sleep(1)
                        
                        if i < len(workers):
                            inject_script(driver, workers[i]['script'], worker_name)
                            console.add_log(f"Script re-injected after refresh", worker_name, 'success')
                    except Exception as e:
                        console.add_log(f"Refresh error: {e}", f"Window {i+1}", 'error')
                        console.update_worker_heartbeat(i+1, alive=False)
                    time.sleep(1)
                
                console.add_log("✅ All windows refreshed and scripts re-injected", log_type='success')
                last_refresh = now
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        console.add_log("\n⏸️  Monitoring stopped by user", log_type='system')
        console.add_log("Workers are still running in browser windows!", log_type='system')
        console.update()
        
    finally:
        # Re-enable sleep mode
        allow_sleep()
        try:
            console.set_sleep_prevention(False)
        except:
            pass
        
        try:
            console.add_log("=" * 80, log_type='system')
            console.add_log(">> PROGRAM TERMINATED", log_type='system')
            console.add_log(">> SLEEP MODE RE-ENABLED", log_type='success')
            console.add_log(">> [!] Browser windows still open with active workers", log_type='system')
            console.add_log(">> Close browser windows manually when complete", log_type='system')
            console.add_log("=" * 80, log_type='system')
            console.update()
        except:
            print("\n" + "╔" + "═" * 78 + "╗")
            print("║ >> PROGRAM TERMINATED" + " " * 55 + "║")
            print("║ >> SLEEP MODE RE-ENABLED" + " " * 52 + "║")
            print("║ >> [!] Browser windows still open with active workers" + " " * 23 + "║")
            print("╚" + "═" * 78 + "╝")
        input("\n>> Press Enter to exit...")


if __name__ == "__main__":
    main()

