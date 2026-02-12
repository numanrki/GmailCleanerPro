"""
Gmail Cleaner Pro - Open Source Desktop Application
Clean your Gmail inbox with ease!

GitHub: https://github.com/numanrki/GmailCleanerPro
Author: numanrki
License: MIT
"""

import os
import sys
import pickle
import re
import json
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import defaultdict
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError

# Google API imports - must be at top level for PyInstaller
GOOGLE_API_AVAILABLE = False
GOOGLE_IMPORT_ERROR = None
Request = None
InstalledAppFlow = None
build = None

try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError as e:
    GOOGLE_IMPORT_ERROR = str(e)
except Exception as e:
    GOOGLE_IMPORT_ERROR = f"Unexpected error: {e}"

# App Info
APP_NAME = "Gmail Cleaner Pro"
APP_VERSION = "2.0.0"
AUTHOR = "numanrki"
GITHUB_REPO = "numanrki/GmailCleanerPro"
GITHUB_URL = "https://github.com/numanrki"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
UPDATE_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
TWITTER_URL = "https://x.com/numanrki"
COFFEE_URL = "https://buymeacoffee.com/numanrki"

# OAuth Config
OAUTH_CONFIG = {
    "installed": {
        "client_id": "1084554418167-fpf6ujk3ehvd0r2if68jsg12bhlmmae2.apps.googleusercontent.com",
        "project_id": "itsnuman-223013",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": ["http://localhost"]
    }
}

SCOPES = ['https://mail.google.com/']


class DeletionProgressDialog:
    """A modal dialog showing live deletion progress."""
    
    def __init__(self, parent, title="Deleting Emails"):
        self.parent = parent
        self.cancelled = False
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        width, height = 500, 320
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg="#f5f5f5")
        
        # Header
        header = tk.Frame(self.dialog, bg="#d32f2f", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="🗑️ Deleting Emails...", font=("Segoe UI", 14, "bold"),
                 bg="#d32f2f", fg="white").pack(pady=12)
        
        # Content
        content = tk.Frame(self.dialog, bg="#f5f5f5", padx=25, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Overall progress
        tk.Label(content, text="Overall Progress:", font=("Segoe UI", 10, "bold"),
                 bg="#f5f5f5", fg="#333").pack(anchor=tk.W)
        
        self.overall_progress = ttk.Progressbar(content, mode='determinate', length=450)
        self.overall_progress.pack(fill=tk.X, pady=(5, 2))
        
        self.overall_label = tk.Label(content, text="0 / 0 senders processed",
                                       font=("Segoe UI", 9), bg="#f5f5f5", fg="#666")
        self.overall_label.pack(anchor=tk.W)
        
        # Current sender
        tk.Label(content, text="\nCurrent Sender:", font=("Segoe UI", 10, "bold"),
                 bg="#f5f5f5", fg="#333").pack(anchor=tk.W, pady=(10, 0))
        
        self.sender_label = tk.Label(content, text="Preparing...",
                                      font=("Consolas", 10), bg="#f5f5f5", fg="#1a73e8")
        self.sender_label.pack(anchor=tk.W, pady=(2, 0))
        
        self.sender_progress = ttk.Progressbar(content, mode='determinate', length=450)
        self.sender_progress.pack(fill=tk.X, pady=(5, 2))
        
        self.sender_status = tk.Label(content, text="",
                                       font=("Segoe UI", 9), bg="#f5f5f5", fg="#666")
        self.sender_status.pack(anchor=tk.W)
        
        # Stats
        stats_frame = tk.Frame(content, bg="#e8f5e9", padx=15, pady=10)
        stats_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.stats_label = tk.Label(stats_frame, text="📊 Total deleted: 0 emails",
                                     font=("Segoe UI", 11, "bold"), bg="#e8f5e9", fg="#2e7d32")
        self.stats_label.pack()
        
        # Cancel button
        btn_frame = tk.Frame(self.dialog, bg="#f5f5f5", pady=15)
        btn_frame.pack(fill=tk.X)
        
        self.cancel_btn = tk.Button(btn_frame, text="⏹️ Cancel", font=("Segoe UI", 10),
                                     command=self.cancel, bg="#757575", fg="white",
                                     relief=tk.FLAT, padx=20, pady=8, cursor="hand2")
        self.cancel_btn.pack()
        
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
    
    def update_overall(self, current, total, sender_email):
        """Update overall progress."""
        progress = (current / total * 100) if total > 0 else 0
        self.overall_progress['value'] = progress
        self.overall_label.config(text=f"{current} / {total} senders processed ({progress:.0f}%)")
        self.sender_label.config(text=f"📧 {sender_email}")
        self.sender_progress['value'] = 0
        self.sender_status.config(text="Finding emails...")
        self.dialog.update_idletasks()
    
    def update_sender(self, found_count, deleted_count, finding=True):
        """Update current sender progress."""
        if finding:
            self.sender_status.config(text=f"Found {found_count} emails...")
            self.sender_progress['value'] = 25
        else:
            progress = 25 + (deleted_count / found_count * 75) if found_count > 0 else 100
            self.sender_progress['value'] = progress
            self.sender_status.config(text=f"Deleted {deleted_count} / {found_count} emails")
        self.dialog.update_idletasks()
    
    def update_stats(self, total_deleted):
        """Update total stats."""
        self.stats_label.config(text=f"📊 Total deleted: {total_deleted} emails")
        self.dialog.update_idletasks()
    
    def set_complete(self):
        """Mark as complete."""
        self.overall_progress['value'] = 100
        self.sender_progress['value'] = 100
        self.cancel_btn.config(text="✅ Done", bg="#4caf50")
    
    def cancel(self):
        """Cancel the deletion."""
        self.cancelled = True
        self.cancel_btn.config(text="Cancelling...", state=tk.DISABLED)
    
    def close(self):
        """Close the dialog."""
        try:
            self.dialog.grab_release()
            self.dialog.destroy()
        except:
            pass


def get_app_data_dir():
    """Get app data directory."""
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    
    app_dir = os.path.join(base, 'GmailCleanerPro')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


class GmailCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.configure(bg="#f5f5f5")
        
        # Set icon
        self.set_app_icon()
        
        # Set window size and position within screen bounds
        self.setup_window()
        
        self.service = None
        self.is_connected = False
        self.all_senders = {}
        self.marked_for_delete = set()
        self.current_email = ""
        self.all_sender_items = []
        self.stop_scan = False
        self.domain_groups = {}  # {domain: {emails: [list], count: int, senders: int}}
        self.selected_domains = set()  # Domains selected for deletion
        self.all_domain_items = []  # For filtering domains
        
        # Multi-account support
        self.accounts = {}  # {email: token_filename}
        self.active_account = None
        self.load_accounts()
        
        self.create_ui()
        self.check_dependencies()
        
        # Check for updates on startup
        self.check_for_updates_async()
        
        # Auto-connect to last active account if exists
        self.auto_connect_last_account()
    
    def set_app_icon(self):
        """Set the application icon for window and taskbar."""
        try:
            # Try to load icon from various locations
            icon_paths = [
                os.path.join(os.path.dirname(sys.executable), 'app_icon.ico'),
                os.path.join(os.path.dirname(__file__), 'app_icon.ico'),
                'app_icon.ico',
                os.path.join(get_app_data_dir(), 'app_icon.ico')
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
                    break
        except Exception:
            pass  # Use default icon if not found
    
    def setup_window(self):
        """Setup window size and ensure it stays within screen bounds."""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Desired window size
        width = 1100
        height = 800
        
        # Adjust if window is larger than screen
        if width > screen_width - 50:
            width = screen_width - 50
        if height > screen_height - 100:
            height = screen_height - 100
        
        # Set minimum size
        self.root.minsize(min(1000, width), min(700, height))
        
        # Center window within screen bounds
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2 - 30)  # Slight offset for taskbar
        
        # Ensure window doesn't go off screen
        if x + width > screen_width:
            x = screen_width - width
        if y + height > screen_height - 50:  # Account for taskbar
            y = screen_height - height - 50
        
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def center_window(self):
        """Legacy method - now handled by setup_window."""
        pass
    
    def check_dependencies(self):
        """Dependencies are now lazily loaded when connecting."""
        pass  # Lazy loading - check when user clicks Connect
    
    def create_ui(self):
        """Create the user interface."""
        # ===== HEADER =====
        header = tk.Frame(self.root, bg="#1a73e8", height=90)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Logo and title
        title_frame = tk.Frame(header, bg="#1a73e8")
        title_frame.pack(side=tk.LEFT, padx=25, pady=12)
        
        tk.Label(title_frame, text="📧", font=("Segoe UI", 28),
                 bg="#1a73e8", fg="white").pack(side=tk.LEFT)
        
        title_text = tk.Frame(title_frame, bg="#1a73e8")
        title_text.pack(side=tk.LEFT, padx=10)
        
        tk.Label(title_text, text=APP_NAME, font=("Segoe UI", 20, "bold"),
                 bg="#1a73e8", fg="white").pack(anchor=tk.W)
        tk.Label(title_text, text=f"v{APP_VERSION} by @{AUTHOR}",
                 font=("Segoe UI", 10), bg="#1a73e8", fg="#a8c7fa").pack(anchor=tk.W)
        
        # Social links
        social_frame = tk.Frame(header, bg="#1a73e8")
        social_frame.pack(side=tk.RIGHT, padx=20)
        
        tk.Button(social_frame, text="⭐ GitHub", font=("Segoe UI", 9),
                  command=lambda: webbrowser.open(GITHUB_URL),
                  bg="#24292e", fg="white", relief=tk.FLAT,
                  padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=3)
        
        tk.Button(social_frame, text="𝕏 Twitter", font=("Segoe UI", 9),
                  command=lambda: webbrowser.open(TWITTER_URL),
                  bg="#000000", fg="white", relief=tk.FLAT,
                  padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=3)
        
        tk.Button(social_frame, text="☕ Support", font=("Segoe UI", 9, "bold"),
                  command=lambda: webbrowser.open(COFFEE_URL),
                  bg="#ffdd00", fg="#000000", relief=tk.FLAT,
                  padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=3)
        
        # Connect button
        connect_frame = tk.Frame(header, bg="#1a73e8")
        connect_frame.pack(side=tk.RIGHT, padx=15)
        
        # Account dropdown for multi-account
        account_row = tk.Frame(connect_frame, bg="#1a73e8")
        account_row.pack(side=tk.TOP, pady=(5, 2))
        
        self.account_var = tk.StringVar(value="Select Account")
        self.account_dropdown = ttk.Combobox(account_row, textvariable=self.account_var,
                                              values=[], state="readonly", width=25,
                                              font=("Segoe UI", 9))
        self.account_dropdown.pack(side=tk.LEFT, padx=(0, 5))
        self.account_dropdown.bind("<<ComboboxSelected>>", self.on_account_selected)
        
        # Add account button
        self.add_account_btn = tk.Button(account_row, text="➕",
                                          font=("Segoe UI", 10),
                                          command=self.add_new_account, bg="white", fg="#1a73e8",
                                          relief=tk.FLAT, padx=8, pady=3, cursor="hand2")
        self.add_account_btn.pack(side=tk.LEFT, padx=2)
        
        # Remove account button
        self.remove_account_btn = tk.Button(account_row, text="➖",
                                             font=("Segoe UI", 10),
                                             command=self.remove_current_account, bg="#ffcdd2", fg="#c62828",
                                             relief=tk.FLAT, padx=8, pady=3, cursor="hand2",
                                             state=tk.DISABLED)
        self.remove_account_btn.pack(side=tk.LEFT, padx=2)
        
        self.status_label = tk.Label(connect_frame, text="Click ➕ to add account",
                                      font=("Segoe UI", 9), bg="#1a73e8", fg="#a8c7fa")
        self.status_label.pack(side=tk.TOP)
        
        # Update dropdown with saved accounts
        self.refresh_account_dropdown()
        
        # ===== NOTEBOOK FOR TABS =====
        notebook_frame = tk.Frame(self.root, bg="#f5f5f5", padx=20, pady=10)
        notebook_frame.pack(fill=tk.BOTH, expand=True)
        
        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Scan & Clean
        self.tab_scan = tk.Frame(self.notebook, bg="#f5f5f5")
        self.notebook.add(self.tab_scan, text="  📊 Scan & Clean  ")
        self.create_scan_tab()
        
        # Tab 2: Domain Groups
        self.tab_groups = tk.Frame(self.notebook, bg="#f5f5f5")
        self.notebook.add(self.tab_groups, text="  🏢 Domain Groups  ")
        self.create_groups_tab()
        
        # Tab 3: Manual Delete
        self.tab_manual = tk.Frame(self.notebook, bg="#f5f5f5")
        self.notebook.add(self.tab_manual, text="  ✍️ Manual Delete  ")
        self.create_manual_tab()
        
        # ===== FOOTER =====
        footer = tk.Frame(self.root, bg="#f0f0f0", padx=20, pady=10)
        footer.pack(fill=tk.X)
        
        progress_frame = tk.Frame(footer, bg="#f0f0f0")
        progress_frame.pack(side=tk.LEFT)
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate', length=250)
        self.progress.pack(side=tk.LEFT)
        
        self.progress_label = tk.Label(progress_frame, text="Ready",
                                        font=("Segoe UI", 9), bg="#f0f0f0", fg="#666")
        self.progress_label.pack(side=tk.LEFT, padx=15)
        
        # Update notification bar (hidden by default)
        self.update_bar = tk.Frame(footer, bg="#fff3cd", padx=10, pady=5)
        self.update_label = tk.Label(self.update_bar, text="",
                                      font=("Segoe UI", 9), bg="#fff3cd", fg="#856404")
        self.update_label.pack(side=tk.LEFT)
        tk.Button(self.update_bar, text="Download", font=("Segoe UI", 8, "bold"),
                  command=lambda: webbrowser.open(GITHUB_RELEASES_URL),
                  bg="#ffc107", fg="#000", relief=tk.FLAT, padx=8, pady=2,
                  cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(self.update_bar, text="✕", font=("Segoe UI", 8),
                  command=lambda: self.update_bar.pack_forget(),
                  bg="#fff3cd", fg="#856404", relief=tk.FLAT, padx=5, pady=2,
                  cursor="hand2").pack(side=tk.LEFT)
        # Don't pack update_bar initially - shown when update available
        
        tk.Button(footer, text="🔄 Updates", font=("Segoe UI", 9),
                  command=self.check_for_updates_manual, bg="#e0e0e0", fg="#333",
                  relief=tk.FLAT, padx=10, pady=3, cursor="hand2").pack(side=tk.RIGHT)
        
        tk.Label(footer, text=f"Made with ❤️ by @{AUTHOR}",
                 font=("Segoe UI", 9), bg="#f0f0f0", fg="#999").pack(side=tk.RIGHT, padx=20)
    
    def create_scan_tab(self):
        """Create the Scan & Clean tab."""
        main = tk.Frame(self.tab_scan, bg="#f5f5f5", padx=10, pady=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        panels = tk.Frame(main, bg="#f5f5f5")
        panels.pack(fill=tk.BOTH, expand=True)
        
        # ===== LEFT PANEL =====
        left_frame = tk.LabelFrame(panels, text="📋 All Email Senders",
                                    font=("Segoe UI", 11, "bold"),
                                    bg="#ffffff", fg="#333", padx=15, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Scan button row
        scan_frame = tk.Frame(left_frame, bg="#ffffff")
        scan_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.scan_btn = tk.Button(scan_frame, text="🔍 Load All Senders",
                                   font=("Segoe UI", 10, "bold"),
                                   command=self.scan_emails, bg="#1a73e8", fg="white",
                                   relief=tk.FLAT, padx=15, pady=8, cursor="hand2",
                                   state=tk.DISABLED)
        self.scan_btn.pack(side=tk.LEFT)
        
        # Stop button
        self.stop_btn = tk.Button(scan_frame, text="⏹️ Stop",
                                   font=("Segoe UI", 9),
                                   command=self.stop_scanning, bg="#f44336", fg="white",
                                   relief=tk.FLAT, padx=10, pady=6, cursor="hand2",
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Export button
        self.export_btn = tk.Button(scan_frame, text="📥 Export to TXT",
                                     font=("Segoe UI", 9),
                                     command=self.export_senders, bg="#4caf50", fg="white",
                                     relief=tk.FLAT, padx=12, pady=6, cursor="hand2",
                                     state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT, padx=10)
        
        self.scan_status = tk.Label(scan_frame, text="Connect Gmail first",
                                     font=("Segoe UI", 9), bg="#ffffff", fg="#666")
        self.scan_status.pack(side=tk.LEFT, padx=10)
        
        self.live_counter = tk.Label(scan_frame, text="",
                                      font=("Consolas", 10, "bold"),
                                      bg="#ffffff", fg="#1a73e8")
        self.live_counter.pack(side=tk.RIGHT, padx=10)
        
        # Filter
        filter_frame = tk.Frame(left_frame, bg="#ffffff")
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(filter_frame, text="🔎 Filter:", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#666").pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add('write', self.filter_senders)
        ttk.Entry(filter_frame, textvariable=self.filter_var, width=30).pack(side=tk.LEFT, padx=5)
        
        # Column headers
        header_frame = tk.Frame(left_frame, bg="#e3f2fd")
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text="EMAILS", font=("Segoe UI", 9, "bold"),
                 bg="#e3f2fd", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        tk.Label(header_frame, text="SENDER NAME", font=("Segoe UI", 9, "bold"),
                 bg="#e3f2fd", width=22, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(header_frame, text="EMAIL ADDRESS", font=("Segoe UI", 9, "bold"),
                 bg="#e3f2fd", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Listbox
        list_frame = tk.Frame(left_frame, bg="#ffffff")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.sender_listbox = tk.Listbox(list_frame, font=("Consolas", 10),
                                          selectmode=tk.EXTENDED, height=16,
                                          yscrollcommand=scrollbar.set,
                                          bg="white", relief=tk.FLAT,
                                          selectbackground="#1a73e8",
                                          selectforeground="white",
                                          activestyle='none', borderwidth=0)
        self.sender_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.sender_listbox.yview)
        
        # Button row
        btn_frame = tk.Frame(left_frame, bg="#ffffff")
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame, text="➡️ Add to Delete List",
                  font=("Segoe UI", 10, "bold"),
                  command=self.mark_for_delete, bg="#ff9800", fg="white",
                  relief=tk.FLAT, padx=15, pady=8, cursor="hand2").pack(side=tk.LEFT)
        
        self.copy_emails_btn = tk.Button(btn_frame, text="📋 Copy Emails",
                  font=("Segoe UI", 9),
                  command=self.copy_emails_to_clipboard, bg="#2196f3", fg="white",
                  relief=tk.FLAT, padx=10, pady=5, cursor="hand2", state=tk.DISABLED)
        self.copy_emails_btn.pack(side=tk.LEFT, padx=10)
        
        tk.Button(btn_frame, text="Select All", font=("Segoe UI", 9),
                  command=lambda: self.sender_listbox.select_set(0, tk.END),
                  bg="#757575", fg="white", relief=tk.FLAT, padx=10, pady=5,
                  cursor="hand2").pack(side=tk.RIGHT)
        
        # ===== RIGHT PANEL =====
        right_frame = tk.LabelFrame(panels, text="🗑️ Marked for Deletion",
                                     font=("Segoe UI", 11, "bold"),
                                     bg="#fff5f5", fg="#c62828", padx=15, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Header
        header_frame2 = tk.Frame(right_frame, bg="#ffcdd2")
        header_frame2.pack(fill=tk.X)
        tk.Label(header_frame2, text="EMAILS", font=("Segoe UI", 9, "bold"),
                 bg="#ffcdd2", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        tk.Label(header_frame2, text="SENDER NAME", font=("Segoe UI", 9, "bold"),
                 bg="#ffcdd2", width=22, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(header_frame2, text="EMAIL ADDRESS", font=("Segoe UI", 9, "bold"),
                 bg="#ffcdd2", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Delete listbox
        delete_list_frame = tk.Frame(right_frame, bg="#fff5f5")
        delete_list_frame.pack(fill=tk.BOTH, expand=True)
        
        delete_scrollbar = ttk.Scrollbar(delete_list_frame)
        delete_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.delete_listbox = tk.Listbox(delete_list_frame, font=("Consolas", 10),
                                          selectmode=tk.EXTENDED, height=16,
                                          yscrollcommand=delete_scrollbar.set,
                                          bg="#fff8f8", relief=tk.FLAT,
                                          selectbackground="#d32f2f",
                                          selectforeground="white",
                                          activestyle='none', borderwidth=0)
        self.delete_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        delete_scrollbar.config(command=self.delete_listbox.yview)
        
        # Remove buttons
        btn_frame2 = tk.Frame(right_frame, bg="#fff5f5")
        btn_frame2.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame2, text="⬅️ Remove Selected", font=("Segoe UI", 10),
                  command=self.unmark_for_delete, bg="#757575", fg="white",
                  relief=tk.FLAT, padx=12, pady=6, cursor="hand2").pack(side=tk.LEFT)
        
        tk.Button(btn_frame2, text="Clear All", font=("Segoe UI", 9),
                  command=self.clear_delete_list, bg="#9e9e9e", fg="white",
                  relief=tk.FLAT, padx=10, pady=5, cursor="hand2").pack(side=tk.RIGHT)
        
        # Summary
        self.summary_label = tk.Label(right_frame, text="No emails selected",
                                       font=("Segoe UI", 12, "bold"),
                                       bg="#fff5f5", fg="#c62828")
        self.summary_label.pack(pady=(15, 5))
        
        # DELETE BUTTON - Using proper Button widget
        self.delete_btn = tk.Button(right_frame,
                                     text="🗑️  DELETE ALL MARKED EMAILS",
                                     font=("Segoe UI", 14, "bold"),
                                     command=self.delete_all_selected,
                                     bg="#d32f2f", fg="white",
                                     activebackground="#b71c1c", activeforeground="white",
                                     relief=tk.FLAT, padx=30, pady=15, cursor="hand2",
                                     state=tk.DISABLED)
        self.delete_btn.pack(pady=10)
    
    def create_groups_tab(self):
        """Create the Domain Groups tab for bulk email management by domain."""
        main = tk.Frame(self.tab_groups, bg="#f5f5f5", padx=10, pady=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        info_frame = tk.Frame(main, bg="#e8f5e9", padx=15, pady=12)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(info_frame, text="🏢 Domain Groups - Fast Bulk Email Management", 
                 font=("Segoe UI", 12, "bold"),
                 bg="#e8f5e9", fg="#2e7d32").pack(anchor=tk.W)
        tk.Label(info_frame, 
                 text="Emails are grouped by domain (e.g., amazon.com, facebook.com). Select domains to add ALL emails from those domains to the delete list. Much faster than selecting individual senders!",
                 font=("Segoe UI", 10), bg="#e8f5e9", fg="#388e3c", wraplength=1000,
                 justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))
        
        panels = tk.Frame(main, bg="#f5f5f5")
        panels.pack(fill=tk.BOTH, expand=True)
        
        # ===== LEFT PANEL - Domain Groups =====
        left_frame = tk.LabelFrame(panels, text="📋 All Domain Groups",
                                    font=("Segoe UI", 11, "bold"),
                                    bg="#ffffff", fg="#333", padx=15, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Scan button row
        scan_frame = tk.Frame(left_frame, bg="#ffffff")
        scan_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.group_scan_btn = tk.Button(scan_frame, text="🔍 Scan Domain Groups",
                                         font=("Segoe UI", 10, "bold"),
                                         command=self.scan_domain_groups, bg="#1a73e8", fg="white",
                                         relief=tk.FLAT, padx=15, pady=8, cursor="hand2",
                                         state=tk.DISABLED)
        self.group_scan_btn.pack(side=tk.LEFT)
        
        self.groups_status = tk.Label(scan_frame, text="Connect Gmail first",
                                       font=("Segoe UI", 9), bg="#ffffff", fg="#666")
        self.groups_status.pack(side=tk.LEFT, padx=10)
        
        self.groups_live_counter = tk.Label(scan_frame, text="",
                                             font=("Consolas", 10, "bold"),
                                             bg="#ffffff", fg="#1a73e8")
        self.groups_live_counter.pack(side=tk.RIGHT, padx=10)
        
        # Filter for domains
        filter_frame = tk.Frame(left_frame, bg="#ffffff")
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(filter_frame, text="🔎 Filter domains:", font=("Segoe UI", 9),
                 bg="#ffffff", fg="#666").pack(side=tk.LEFT)
        
        self.domain_filter_var = tk.StringVar()
        self.domain_filter_var.trace_add('write', self.filter_domains)
        ttk.Entry(filter_frame, textvariable=self.domain_filter_var, width=30).pack(side=tk.LEFT, padx=5)
        
        # Column headers
        header_frame = tk.Frame(left_frame, bg="#e8f5e9")
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text="EMAILS", font=("Segoe UI", 9, "bold"),
                 bg="#e8f5e9", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        tk.Label(header_frame, text="SENDERS", font=("Segoe UI", 9, "bold"),
                 bg="#e8f5e9", width=10, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(header_frame, text="DOMAIN", font=("Segoe UI", 9, "bold"),
                 bg="#e8f5e9", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Domain listbox
        list_frame = tk.Frame(left_frame, bg="#ffffff")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.domain_listbox = tk.Listbox(list_frame, font=("Consolas", 10),
                                          selectmode=tk.EXTENDED, height=14,
                                          yscrollcommand=scrollbar.set,
                                          bg="white", relief=tk.FLAT,
                                          selectbackground="#2e7d32",
                                          selectforeground="white",
                                          activestyle='none', borderwidth=0)
        self.domain_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.domain_listbox.yview)
        
        # Button row
        btn_frame = tk.Frame(left_frame, bg="#ffffff")
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame, text="➡️ Add Domains to Delete",
                  font=("Segoe UI", 10, "bold"),
                  command=self.add_domains_to_delete, bg="#ff9800", fg="white",
                  relief=tk.FLAT, padx=15, pady=8, cursor="hand2").pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Select All", font=("Segoe UI", 9),
                  command=lambda: self.domain_listbox.select_set(0, tk.END),
                  bg="#757575", fg="white", relief=tk.FLAT, padx=10, pady=5,
                  cursor="hand2").pack(side=tk.RIGHT)
        
        tk.Button(btn_frame, text="Deselect All", font=("Segoe UI", 9),
                  command=lambda: self.domain_listbox.selection_clear(0, tk.END),
                  bg="#757575", fg="white", relief=tk.FLAT, padx=10, pady=5,
                  cursor="hand2").pack(side=tk.RIGHT, padx=5)
        
        # ===== RIGHT PANEL - Selected Domains for Deletion =====
        right_frame = tk.LabelFrame(panels, text="🗑️ Domains Marked for Deletion",
                                     font=("Segoe UI", 11, "bold"),
                                     bg="#fff5f5", fg="#c62828", padx=15, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Header
        header_frame2 = tk.Frame(right_frame, bg="#ffcdd2")
        header_frame2.pack(fill=tk.X)
        tk.Label(header_frame2, text="EMAILS", font=("Segoe UI", 9, "bold"),
                 bg="#ffcdd2", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        tk.Label(header_frame2, text="SENDERS", font=("Segoe UI", 9, "bold"),
                 bg="#ffcdd2", width=10, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(header_frame2, text="DOMAIN", font=("Segoe UI", 9, "bold"),
                 bg="#ffcdd2", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Selected domains listbox
        delete_list_frame = tk.Frame(right_frame, bg="#fff5f5")
        delete_list_frame.pack(fill=tk.BOTH, expand=True)
        
        delete_scrollbar = ttk.Scrollbar(delete_list_frame)
        delete_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.domain_delete_listbox = tk.Listbox(delete_list_frame, font=("Consolas", 10),
                                                 selectmode=tk.EXTENDED, height=14,
                                                 yscrollcommand=delete_scrollbar.set,
                                                 bg="#fff8f8", relief=tk.FLAT,
                                                 selectbackground="#d32f2f",
                                                 selectforeground="white",
                                                 activestyle='none', borderwidth=0)
        self.domain_delete_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        delete_scrollbar.config(command=self.domain_delete_listbox.yview)
        
        # Remove buttons
        btn_frame2 = tk.Frame(right_frame, bg="#fff5f5")
        btn_frame2.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame2, text="⬅️ Remove Selected", font=("Segoe UI", 10),
                  command=self.remove_domains_from_delete, bg="#757575", fg="white",
                  relief=tk.FLAT, padx=12, pady=6, cursor="hand2").pack(side=tk.LEFT)
        
        tk.Button(btn_frame2, text="Clear All", font=("Segoe UI", 9),
                  command=self.clear_domain_delete_list, bg="#9e9e9e", fg="white",
                  relief=tk.FLAT, padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        # DELETE BUTTON for domains (in button row)
        self.domain_delete_btn = tk.Button(btn_frame2,
                                            text="🗑️ DELETE",
                                            font=("Segoe UI", 10, "bold"),
                                            command=self.delete_all_from_domains,
                                            bg="#d32f2f", fg="white",
                                            activebackground="#b71c1c", activeforeground="white",
                                            relief=tk.FLAT, padx=15, pady=6, cursor="hand2",
                                            state=tk.DISABLED)
        self.domain_delete_btn.pack(side=tk.RIGHT)
        
        # Summary
        self.domain_summary_label = tk.Label(right_frame, text="No domains selected",
                                              font=("Segoe UI", 12, "bold"),
                                              bg="#fff5f5", fg="#c62828")
        self.domain_summary_label.pack(pady=(15, 5))
    
    def create_manual_tab(self):
        """Create the Manual Delete tab."""
        main = tk.Frame(self.tab_manual, bg="#f5f5f5", padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        info_frame = tk.Frame(main, bg="#e3f2fd", padx=15, pady=12)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(info_frame, text="✍️ Manual Email Deletion", font=("Segoe UI", 12, "bold"),
                 bg="#e3f2fd", fg="#1565c0").pack(anchor=tk.W)
        tk.Label(info_frame, 
                 text="Paste email addresses below (one per line or comma-separated) and click Delete to remove all emails from these senders.",
                 font=("Segoe UI", 10), bg="#e3f2fd", fg="#1976d2", wraplength=800,
                 justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))
        
        # Input area
        input_frame = tk.LabelFrame(main, text="📝 Paste Email Addresses Here",
                                     font=("Segoe UI", 11, "bold"),
                                     bg="#ffffff", fg="#333", padx=15, pady=10)
        input_frame.pack(fill=tk.BOTH, expand=True)
        
        # Text area with scrollbar
        text_frame = tk.Frame(input_frame, bg="#ffffff")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_scroll = ttk.Scrollbar(text_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.manual_text = tk.Text(text_frame, font=("Consolas", 11),
                                    height=15, wrap=tk.WORD,
                                    yscrollcommand=text_scroll.set,
                                    bg="#fafafa", relief=tk.FLAT,
                                    padx=10, pady=10)
        self.manual_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.config(command=self.manual_text.yview)
        
        # Placeholder
        self.manual_text.insert("1.0", "example1@gmail.com\nexample2@yahoo.com\nnewsletter@company.com")
        self.manual_text.config(fg="#999")
        self.manual_text.bind("<FocusIn>", self.on_text_focus_in)
        self.manual_text.bind("<FocusOut>", self.on_text_focus_out)
        
        # Buttons
        btn_frame = tk.Frame(input_frame, bg="#ffffff")
        btn_frame.pack(fill=tk.X, pady=(15, 5))
        
        tk.Button(btn_frame, text="📋 Paste from Clipboard",
                  font=("Segoe UI", 10),
                  command=self.paste_from_clipboard, bg="#2196f3", fg="white",
                  relief=tk.FLAT, padx=15, pady=8, cursor="hand2").pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="🧹 Clear", font=("Segoe UI", 10),
                  command=self.clear_manual_text, bg="#757575", fg="white",
                  relief=tk.FLAT, padx=15, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=10)
        
        # Delete button - moved to same row, right of Clear
        self.manual_delete_btn = tk.Button(btn_frame,
                                            text="🗑️ Delete All",
                                            font=("Segoe UI", 10, "bold"),
                                            command=self.delete_manual_emails,
                                            bg="#d32f2f", fg="white",
                                            relief=tk.FLAT, padx=15, pady=8,
                                            cursor="hand2", state=tk.DISABLED)
        self.manual_delete_btn.pack(side=tk.RIGHT)
        
        # Email count
        self.manual_count_label = tk.Label(btn_frame, text="0 emails entered",
                                            font=("Segoe UI", 10), bg="#ffffff", fg="#666")
        self.manual_count_label.pack(side=tk.LEFT, padx=20)
        
        # Update count on text change
        self.manual_text.bind("<KeyRelease>", self.update_manual_count)
        
        # Note
        tk.Label(input_frame, 
                 text="⚠️ Warning: This will permanently delete ALL emails from the entered email addresses!",
                 font=("Segoe UI", 9), bg="#ffffff", fg="#c62828").pack(pady=(10, 0))
    
    def on_text_focus_in(self, event):
        """Clear placeholder on focus."""
        if self.manual_text.get("1.0", "end-1c") == "example1@gmail.com\nexample2@yahoo.com\nnewsletter@company.com":
            self.manual_text.delete("1.0", tk.END)
            self.manual_text.config(fg="#000")
    
    def on_text_focus_out(self, event):
        """Restore placeholder if empty."""
        if not self.manual_text.get("1.0", "end-1c").strip():
            self.manual_text.insert("1.0", "example1@gmail.com\nexample2@yahoo.com\nnewsletter@company.com")
            self.manual_text.config(fg="#999")
    
    def paste_from_clipboard(self):
        """Paste from clipboard."""
        try:
            clipboard = self.root.clipboard_get()
            self.manual_text.delete("1.0", tk.END)
            self.manual_text.insert("1.0", clipboard)
            self.manual_text.config(fg="#000")
            self.update_manual_count()
        except:
            messagebox.showinfo("Clipboard Empty", "Nothing to paste from clipboard.")
    
    def clear_manual_text(self):
        """Clear manual text area."""
        self.manual_text.delete("1.0", tk.END)
        self.manual_text.config(fg="#999")
        self.manual_text.insert("1.0", "example1@gmail.com\nexample2@yahoo.com\nnewsletter@company.com")
        self.update_manual_count()
    
    def update_manual_count(self, event=None):
        """Update manual email count."""
        text = self.manual_text.get("1.0", "end-1c")
        if text == "example1@gmail.com\nexample2@yahoo.com\nnewsletter@company.com":
            self.manual_count_label.config(text="0 emails entered")
            self.manual_delete_btn.config(state=tk.DISABLED)
            return
        
        emails = self.extract_emails_from_text(text)
        count = len(emails)
        self.manual_count_label.config(text=f"{count} email{'s' if count != 1 else ''} entered")
        
        if count > 0 and self.is_connected:
            self.manual_delete_btn.config(state=tk.NORMAL)
        else:
            self.manual_delete_btn.config(state=tk.DISABLED)
    
    def extract_emails_from_text(self, text):
        """Extract email addresses from text."""
        # Find all email patterns
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text.lower())
        return list(set(emails))  # Remove duplicates
    
    def delete_manual_emails(self):
        """Delete emails from manually entered addresses."""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect to Gmail first!")
            return
        
        text = self.manual_text.get("1.0", "end-1c")
        emails = self.extract_emails_from_text(text)
        
        if not emails:
            messagebox.showinfo("No Emails", "Please enter valid email addresses.")
            return
        
        if not messagebox.askyesno("⚠️ Confirm Delete",
            f"This will PERMANENTLY DELETE all emails from:\n\n"
            f"📧 {len(emails)} email addresses\n\n"
            f"First 5:\n" + "\n".join(f"• {e}" for e in emails[:5]) +
            (f"\n...and {len(emails)-5} more" if len(emails) > 5 else "") +
            f"\n\nThis CANNOT be undone!"):
            return
        
        # Create progress dialog
        progress_dialog = DeletionProgressDialog(self.root, "Deleting Manual Emails")
        
        def do_delete():
            total_deleted = 0
            failed_senders = []
            
            try:
                for i, email in enumerate(emails):
                    if progress_dialog.cancelled:
                        break
                    
                    # Update overall progress - use default args to capture values
                    def update_overall(x=i, t=len(emails), e=email):
                        progress_dialog.update_overall(x, t, e)
                    self.root.after(0, update_overall)
                    
                    messages = []
                    page_token = None
                    
                    # Find all messages from this sender using quoted email for proper search
                    search_query = f'from:"{email}"'
                    while True:
                        if progress_dialog.cancelled:
                            break
                        response = self.service.users().messages().list(
                            userId='me', q=search_query, maxResults=500, pageToken=page_token
                        ).execute()
                        found = response.get('messages', [])
                        messages.extend(found)
                        msg_count = len(messages)
                        self.root.after(0, lambda c=msg_count: progress_dialog.update_sender(c, 0, finding=True))
                        page_token = response.get('nextPageToken')
                        if not page_token:
                            break
                    
                    if not messages:
                        # No messages found for this sender
                        failed_senders.append(email)
                        continue
                    
                    if messages and not progress_dialog.cancelled:
                        ids = [m['id'] for m in messages]
                        deleted_in_batch = 0
                        total_msgs = len(messages)
                        for j in range(0, len(ids), 1000):
                            if progress_dialog.cancelled:
                                break
                            batch = ids[j:j+1000]
                            try:
                                self.service.users().messages().batchDelete(
                                    userId='me', body={'ids': batch}
                                ).execute()
                                deleted_in_batch += len(batch)
                                total_deleted += len(batch)
                                self.root.after(0, lambda d=deleted_in_batch, t=total_msgs:
                                    progress_dialog.update_sender(t, d, finding=False))
                                self.root.after(0, lambda td=total_deleted:
                                    progress_dialog.update_stats(td))
                            except Exception as batch_error:
                                # If batch fails, try deleting one by one
                                for msg_id in batch:
                                    try:
                                        self.service.users().messages().delete(
                                            userId='me', id=msg_id
                                        ).execute()
                                        deleted_in_batch += 1
                                        total_deleted += 1
                                    except:
                                        pass
                                self.root.after(0, lambda d=deleted_in_batch, t=total_msgs:
                                    progress_dialog.update_sender(t, d, finding=False))
                                self.root.after(0, lambda td=total_deleted:
                                    progress_dialog.update_stats(td))
                
                # Final update
                total_emails_count = len(emails)
                self.root.after(0, lambda: progress_dialog.update_overall(total_emails_count, total_emails_count, "Complete!"))
                self.root.after(0, progress_dialog.set_complete)
                
                if progress_dialog.cancelled:
                    self.root.after(500, progress_dialog.close)
                    self.root.after(600, lambda d=total_deleted: messagebox.showinfo("Cancelled",
                        f"Deletion cancelled.\nDeleted {d} emails before stopping."))
                else:
                    self.root.after(1000, progress_dialog.close)
                    # Show result with info about failures
                    result_msg = f"Deleted {total_deleted} emails\nfrom {len(emails)} senders!"
                    if failed_senders:
                        result_msg += f"\n\n⚠️ No emails found for {len(failed_senders)} sender(s)."
                    self.root.after(1100, lambda m=result_msg: messagebox.showinfo("✅ Complete!", m))
                
                self.root.after(0, self.clear_manual_text)
                
            except Exception as e:
                self.root.after(0, progress_dialog.close)
                self.root.after(100, lambda err=str(e): messagebox.showerror("Error", err))
        
        threading.Thread(target=do_delete, daemon=True).start()
    
    def export_senders(self):
        """Export fetched senders to txt file."""
        if not self.all_sender_items:
            messagebox.showinfo("No Data", "Please scan emails first.")
            return
        
        # Ask where to save
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfilename=f"gmail_senders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"Gmail Cleaner Pro - Email Senders Export\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Account: {self.current_email}\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Total Senders: {len(self.all_senders)}\n")
                f.write(f"Total Emails: {sum(s['count'] for s in self.all_senders.values())}\n\n")
                
                f.write("-" * 80 + "\n")
                f.write(f"{'COUNT':<8} {'SENDER NAME':<25} {'EMAIL ADDRESS'}\n")
                f.write("-" * 80 + "\n")
                
                sorted_senders = sorted(self.all_senders.items(), key=lambda x: -x[1]['count'])
                for email, data in sorted_senders:
                    f.write(f"{data['count']:<8} {data['name']:<25} {email}\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("Email addresses only (for easy copy-paste):\n")
                f.write("=" * 80 + "\n")
                for email, _ in sorted_senders:
                    f.write(f"{email}\n")
            
            messagebox.showinfo("✅ Exported!", f"Saved to:\n{filename}")
            
            # Open the file
            if messagebox.askyesno("Open File?", "Do you want to open the exported file?"):
                os.startfile(filename)
                
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
    
    def enable_delete_button(self, enable=True):
        """Enable/disable delete button."""
        if enable:
            self.delete_btn.config(state=tk.NORMAL, bg="#d32f2f")
        else:
            self.delete_btn.config(state=tk.DISABLED, bg="#cccccc")
    
    def stop_scanning(self):
        """Stop the scan process."""
        self.stop_scan = True
        self.stop_btn.config(state=tk.DISABLED)
        self.scan_status.config(text="⏹️ Stopping...")
    
    def set_progress(self, text, running=True):
        self.progress_label.config(text=text)
        if running:
            self.progress.start(10)
        else:
            self.progress.stop()
        self.root.update_idletasks()
    
    def connect_gmail(self, token_filename=None):
        """Connect to Gmail with optional specific token file for multi-account."""
        if not GOOGLE_API_AVAILABLE:
            error_detail = GOOGLE_IMPORT_ERROR if GOOGLE_IMPORT_ERROR else "Unknown import error"
            messagebox.showerror("Missing Dependencies",
                f"Required packages not found!\n\n"
                f"Error: {error_detail}\n\n"
                f"Install: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            return
        
        def do_connect():
            self.set_progress("Connecting to Gmail...", True)
            
            try:
                creds = None
                # Use specific token file or generate new one
                if token_filename:
                    token_path = os.path.join(get_app_data_dir(), token_filename)
                else:
                    token_path = None  # Will be set after we know the email
                
                # Try to load existing token
                if token_path and os.path.exists(token_path):
                    with open(token_path, 'rb') as token:
                        creds = pickle.load(token)
                
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_config(OAUTH_CONFIG, SCOPES)
                        creds = flow.run_local_server(port=0)
                
                # Build service and get email
                self.service = build('gmail', 'v1', credentials=creds)
                profile = self.service.users().getProfile(userId='me').execute()
                email = profile.get('emailAddress', 'unknown')
                self.current_email = email
                
                # Generate token filename from email if not provided
                if not token_filename:
                    safe_email = email.replace('@', '_at_').replace('.', '_')
                    token_filename = f"token_{safe_email}.pickle"
                    token_path = os.path.join(get_app_data_dir(), token_filename)
                
                # Save token
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                
                # Save to accounts
                self.accounts[email] = token_filename
                self.active_account = email
                self.save_accounts()
                
                self.is_connected = True
                self.root.after(0, lambda: self.on_connected(email))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            
            self.set_progress("", False)
        
        threading.Thread(target=do_connect, daemon=True).start()
    
    def on_connected(self, email):
        """Called when successfully connected to an account."""
        self.status_label.config(text=f"✅ {email}", fg="white")
        self.scan_btn.config(state=tk.NORMAL)
        self.group_scan_btn.config(state=tk.NORMAL)
        self.scan_status.config(text="Click to load senders")
        self.groups_status.config(text="Click to scan domain groups")
        self.remove_account_btn.config(state=tk.NORMAL)
        self.update_manual_count()
        self.refresh_account_dropdown()
        # Set dropdown to current account
        self.account_var.set(email)
        messagebox.showinfo("Connected!", f"Connected to: {email}")
    
    def clear_current_state(self):
        """Clear all data for current account (used when switching accounts)."""
        self.service = None
        self.is_connected = False
        self.all_senders = {}
        self.marked_for_delete.clear()
        self.sender_listbox.delete(0, tk.END)
        self.delete_listbox.delete(0, tk.END)
        
        # Clear domain groups
        self.domain_groups = {}
        self.selected_domains.clear()
        self.domain_listbox.delete(0, tk.END)
        self.domain_delete_listbox.delete(0, tk.END)
        self.groups_status.config(text="Click to scan domain groups")
        self.groups_live_counter.config(text="")
        self.group_scan_btn.config(state=tk.DISABLED)
        self.update_domain_summary()
        
        self.status_label.config(text="Click ➕ to add account", fg="#a8c7fa")
        self.scan_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        self.copy_emails_btn.config(state=tk.DISABLED)
        self.scan_status.config(text="Connect account first")
        self.live_counter.config(text="")
        self.remove_account_btn.config(state=tk.DISABLED)
        self.update_summary()
        self.update_manual_count()
    
    # ===== Multi-Account Management =====
    def get_accounts_file(self):
        """Get path to accounts.json file."""
        return os.path.join(get_app_data_dir(), 'accounts.json')
    
    def load_accounts(self):
        """Load saved accounts from accounts.json."""
        accounts_file = self.get_accounts_file()
        if os.path.exists(accounts_file):
            try:
                with open(accounts_file, 'r') as f:
                    data = json.load(f)
                    self.accounts = data.get('accounts', {})
                    self.active_account = data.get('active_account', None)
            except:
                self.accounts = {}
                self.active_account = None
        else:
            self.accounts = {}
            self.active_account = None
    
    def save_accounts(self):
        """Save accounts to accounts.json."""
        accounts_file = self.get_accounts_file()
        try:
            with open(accounts_file, 'w') as f:
                json.dump({
                    'accounts': self.accounts,
                    'active_account': self.active_account
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving accounts: {e}")
    
    def auto_connect_last_account(self):
        """Auto-connect to last active account on startup."""
        if self.active_account and self.active_account in self.accounts:
            # Auto-connect silently
            token_filename = self.accounts[self.active_account]
            self.connect_gmail(token_filename)
        elif self.accounts:
            # Connect to first available account
            first_email = list(self.accounts.keys())[0]
            token_filename = self.accounts[first_email]
            self.connect_gmail(token_filename)
    
    def refresh_account_dropdown(self):
        """Refresh the account dropdown with current accounts."""
        account_list = list(self.accounts.keys())
        self.account_dropdown['values'] = account_list
        
        if self.active_account and self.active_account in account_list:
            self.account_var.set(self.active_account)
        elif account_list:
            self.account_var.set(account_list[0])
        else:
            self.account_var.set("No accounts")
    
    def add_new_account(self):
        """Add a new Gmail account."""
        self.connect_gmail()  # Will prompt for new OAuth
    
    def remove_current_account(self):
        """Remove the currently selected account."""
        if not self.active_account or self.active_account not in self.accounts:
            messagebox.showwarning("No Account", "No account selected to remove.")
            return
        
        if not messagebox.askyesno("Remove Account", 
            f"Remove account {self.active_account}?\n\nThis will delete the saved login for this account."):
            return
        
        # Delete token file
        token_file = self.accounts.get(self.active_account)
        if token_file:
            token_path = os.path.join(get_app_data_dir(), token_file)
            if os.path.exists(token_path):
                try:
                    os.remove(token_path)
                except:
                    pass
        
        # Remove from accounts
        del self.accounts[self.active_account]
        self.active_account = None
        self.save_accounts()
        
        # Clear state
        self.clear_current_state()
        
        # Refresh dropdown
        self.refresh_account_dropdown()
        
        # If other accounts exist, switch to first one
        if self.accounts:
            first_account = list(self.accounts.keys())[0]
            self.switch_to_account(first_account)
        else:
            self.account_var.set("No accounts")
        
        messagebox.showinfo("Removed", "Account removed successfully.")
    
    def on_account_selected(self, event):
        """Handle account selection from dropdown."""
        selected = self.account_var.get()
        if selected and selected != "No accounts" and selected in self.accounts:
            if selected != self.active_account:
                self.switch_to_account(selected)
    
    def switch_to_account(self, email):
        """Switch to a different account."""
        if email not in self.accounts:
            return
        
        # Clear current state
        self.clear_current_state()
        
        # Load this account's token
        token_filename = self.accounts[email]
        self.connect_gmail(token_filename)
    
    # ===== Update Checker =====
    def check_for_updates_async(self):
        """Check for updates in background on startup."""
        def do_check():
            update_info = self.check_for_updates()
            if update_info and update_info.get('available'):
                self.root.after(0, lambda: self.show_update_notification(update_info))
        
        threading.Thread(target=do_check, daemon=True).start()
    
    def check_for_updates(self):
        """Check GitHub releases for newer version."""
        try:
            with urlopen(UPDATE_CHECK_URL, timeout=10) as response:
                data = json.loads(response.read().decode())
                
            latest_tag = data.get('tag_name', '').lstrip('v')
            download_url = None
            
            # Find exe asset
            for asset in data.get('assets', []):
                if asset.get('name', '').endswith('.exe'):
                    download_url = asset.get('browser_download_url')
                    break
            
            # Compare versions
            if latest_tag and self.compare_versions(latest_tag, APP_VERSION) > 0:
                return {
                    'available': True,
                    'current': APP_VERSION,
                    'latest': latest_tag,
                    'download_url': download_url or GITHUB_RELEASES_URL
                }
            
            return {'available': False, 'current': APP_VERSION, 'latest': latest_tag}
            
        except URLError:
            return None
        except Exception as e:
            print(f"Update check error: {e}")
            return None
    
    def compare_versions(self, v1, v2):
        """Compare two version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal."""
        def normalize(v):
            return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split('.')]
        
        try:
            n1, n2 = normalize(v1), normalize(v2)
            return (n1 > n2) - (n1 < n2)
        except:
            return 0
    
    def show_update_notification(self, update_info):
        """Show update notification bar."""
        version = update_info.get('latest', 'new version')
        self.update_label.config(text=f"🔄 Update available: v{version}")
        self.update_bar.pack(side=tk.LEFT, padx=20)
    
    def check_for_updates_manual(self):
        """Manual update check triggered by user."""
        self.set_progress("Checking for updates...", True)
        
        def do_check():
            update_info = self.check_for_updates()
            self.root.after(0, lambda: self.show_update_result(update_info))
            self.set_progress("Ready", False)
        
        threading.Thread(target=do_check, daemon=True).start()
    
    def show_update_result(self, update_info):
        """Show update check result to user."""
        if update_info is None:
            messagebox.showwarning("Update Check", 
                "Could not check for updates.\nPlease check your internet connection.")
        elif update_info.get('available'):
            if messagebox.askyesno("Update Available",
                f"New version available!\n\n"
                f"Current: v{update_info['current']}\n"
                f"Latest: v{update_info['latest']}\n\n"
                f"Open download page?"):
                webbrowser.open(GITHUB_RELEASES_URL)
        else:
            messagebox.showinfo("Up to Date", 
                f"You're running the latest version (v{APP_VERSION})!")
    
    def scan_emails(self):
        if not self.is_connected:
            return
        
        self.stop_scan = False
        self.stop_btn.config(state=tk.NORMAL)
        self.scan_btn.config(state=tk.DISABLED)
        
        def do_scan():
            self.set_progress("Fetching emails...", True)
            self.sender_listbox.delete(0, tk.END)
            self.all_senders = {}
            self.all_sender_items = []
            
            try:
                all_messages = {}
                page_token = None
                
                while not self.stop_scan:
                    response = self.service.users().messages().list(
                        userId='me', maxResults=500, pageToken=page_token
                    ).execute()
                    
                    new_count = 0
                    for msg in response.get('messages', []):
                        all_messages[msg['id']] = msg
                        new_count += 1
                    
                    count = len(all_messages)
                    self.root.after(0, lambda c=count, n=new_count:
                        self.update_live_status(f"📥 Fetching... {c} emails", f"+{n}"))
                    
                    page_token = response.get('nextPageToken')
                    if not page_token or count >= 5000:
                        break
                
                self.root.after(0, lambda: self.live_counter.config(text=""))
                
                senders = defaultdict(lambda: {'count': 0, 'name': '', 'email': ''})
                messages = list(all_messages.values())
                total = len(messages)
                
                for i, msg in enumerate(messages):
                    if self.stop_scan:
                        break
                    
                    if i % 10 == 0:
                        self.root.after(0, lambda x=i, t=total:
                            self.update_live_status(f"📊 Analyzing... {x}/{t}", ""))
                    
                    try:
                        data = self.service.users().messages().get(
                            userId='me', id=msg['id'], format='metadata',
                            metadataHeaders=['From']
                        ).execute()
                        
                        headers = {h['name']: h['value'] for h in data['payload']['headers']}
                        from_header = headers.get('From', 'Unknown')
                        
                        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
                        email = match.group(0).lower() if match else from_header.lower()
                        
                        name_match = re.match(r'^"?([^"<]+)"?\s*<', from_header)
                        name = name_match.group(1).strip() if name_match else email.split('@')[0]
                        
                        senders[email]['count'] += 1
                        senders[email]['name'] = name[:22]
                        senders[email]['email'] = email
                        
                        if senders[email]['count'] == 1:
                            display = f"{senders[email]['count']:>5}   {name[:22]:<22}   {email}"
                            self.root.after(0, lambda d=display:
                                self.sender_listbox.insert(tk.END, d))
                    except:
                        pass
                
                self.all_senders = dict(senders)
                
                def finalize():
                    self.sender_listbox.delete(0, tk.END)
                    sorted_senders = sorted(senders.items(), key=lambda x: -x[1]['count'])
                    
                    self.all_sender_items = []
                    for email, data in sorted_senders:
                        display = f"{data['count']:>5}   {data['name']:<22}   {email}"
                        self.all_sender_items.append(display)
                        self.sender_listbox.insert(tk.END, display)
                    
                    total_emails = sum(s['count'] for s in senders.values())
                    status = "⏹️ Stopped" if self.stop_scan else "✅"
                    self.scan_status.config(text=f"{status} {len(senders)} senders • {total_emails} emails")
                    self.live_counter.config(text="")
                    self.export_btn.config(state=tk.NORMAL)
                    self.copy_emails_btn.config(state=tk.NORMAL)
                    self.scan_btn.config(state=tk.NORMAL)
                    self.stop_btn.config(state=tk.DISABLED)
                    
                    # Update domain groups after scan complete
                    self.update_domain_groups()
                
                self.root.after(0, finalize)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.scan_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            
            self.set_progress("Ready", False)
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def update_live_status(self, status, counter):
        self.scan_status.config(text=status)
        self.live_counter.config(text=counter)
    
    def filter_senders(self, *args):
        search_text = self.filter_var.get().lower()
        self.sender_listbox.delete(0, tk.END)
        
        for item in self.all_sender_items:
            if search_text in item.lower():
                self.sender_listbox.insert(tk.END, item)
    
    def get_email_from_display(self, text):
        # Use regex to find email in the display text
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text.lower())
        if match:
            return match.group(0)
        return None
    
    def mark_for_delete(self):
        selected = self.sender_listbox.curselection()
        
        if not selected:
            messagebox.showinfo("No Selection", "Select senders first.")
            return
        
        for idx in selected:
            item = self.sender_listbox.get(idx)
            email = self.get_email_from_display(item)
            
            if email and email not in self.marked_for_delete:
                self.marked_for_delete.add(email)
                self.delete_listbox.insert(tk.END, item)
        
        self.update_summary()
        self.sender_listbox.selection_clear(0, tk.END)
    
    def unmark_for_delete(self):
        selected = list(self.delete_listbox.curselection())
        
        for idx in reversed(selected):
            item = self.delete_listbox.get(idx)
            email = self.get_email_from_display(item)
            if email:
                self.marked_for_delete.discard(email)
            self.delete_listbox.delete(idx)
        
        self.update_summary()
    
    def clear_delete_list(self):
        self.delete_listbox.delete(0, tk.END)
        self.marked_for_delete.clear()
        self.update_summary()
    
    def update_summary(self):
        total = sum(self.all_senders.get(e, {}).get('count', 0) for e in self.marked_for_delete)
        count = len(self.marked_for_delete)
        
        if count > 0:
            if total > 0:
                self.summary_label.config(text=f"📧 {count} senders • {total} emails")
            else:
                self.summary_label.config(text=f"📧 {count} senders selected")
            self.enable_delete_button(True)
        else:
            self.summary_label.config(text="No emails selected")
            self.enable_delete_button(False)
    
    # ===== Domain Groups Methods =====
    def scan_domain_groups(self):
        """Scan emails and group by domain directly - faster than full sender scan."""
        if not self.is_connected:
            return
        
        self.group_scan_btn.config(state=tk.DISABLED)
        
        def do_scan():
            self.set_progress("Scanning domain groups...", True)
            self.root.after(0, lambda: self.groups_status.config(text="📥 Fetching emails..."))
            
            try:
                # Collect all emails with minimal data
                all_messages = {}
                page_token = None
                
                while True:
                    response = self.service.users().messages().list(
                        userId='me', maxResults=500, pageToken=page_token
                    ).execute()
                    
                    for msg in response.get('messages', []):
                        all_messages[msg['id']] = msg
                    
                    count = len(all_messages)
                    self.root.after(0, lambda c=count: self.groups_status.config(
                        text=f"📥 Fetching... {c} emails"))
                    self.root.after(0, lambda c=count: self.groups_live_counter.config(
                        text=f"{c}"))
                    
                    page_token = response.get('nextPageToken')
                    if not page_token or count >= 5000:
                        break
                
                # Now analyze each email for domain
                messages = list(all_messages.values())
                total = len(messages)
                domain_data = {}  # {domain: {count: 0, senders: set()}}
                
                self.root.after(0, lambda: self.groups_status.config(
                    text=f"📊 Analyzing {total} emails..."))
                
                for i, msg in enumerate(messages):
                    if i % 20 == 0:
                        self.root.after(0, lambda x=i, t=total: self.groups_status.config(
                            text=f"📊 Analyzing... {x}/{t}"))
                        self.root.after(0, lambda x=i, t=total: self.groups_live_counter.config(
                            text=f"{x}/{t}"))
                    
                    try:
                        data = self.service.users().messages().get(
                            userId='me', id=msg['id'], format='metadata',
                            metadataHeaders=['From']
                        ).execute()
                        
                        headers = {h['name']: h['value'] for h in data['payload']['headers']}
                        from_header = headers.get('From', 'Unknown')
                        
                        # Extract email
                        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
                        email = match.group(0).lower() if match else from_header.lower()
                        
                        # Extract domain
                        domain = email.split('@')[-1].lower() if '@' in email else 'unknown'
                        
                        if domain not in domain_data:
                            domain_data[domain] = {'count': 0, 'senders': set()}
                        
                        domain_data[domain]['count'] += 1
                        domain_data[domain]['senders'].add(email)
                        
                    except:
                        pass
                
                # Convert to domain_groups format
                self.domain_groups = {}
                for domain, data in domain_data.items():
                    self.domain_groups[domain] = {
                        'emails': list(data['senders']),
                        'count': data['count'],
                        'senders': len(data['senders'])
                    }
                
                def finalize():
                    self.refresh_domain_listbox()
                    total_domains = len(self.domain_groups)
                    total_emails = sum(d['count'] for d in self.domain_groups.values())
                    self.groups_status.config(text=f"✅ {total_domains} domains • {total_emails} emails")
                    self.groups_live_counter.config(text="")
                    self.group_scan_btn.config(state=tk.NORMAL)
                
                self.root.after(0, finalize)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.group_scan_btn.config(state=tk.NORMAL))
            
            self.set_progress("Ready", False)
        
        threading.Thread(target=do_scan, daemon=True).start()
    
    def update_domain_groups(self):
        """Group all senders by their email domain."""
        self.domain_groups = {}
        
        for email, data in self.all_senders.items():
            # Extract domain from email
            domain = email.split('@')[-1].lower() if '@' in email else 'unknown'
            
            if domain not in self.domain_groups:
                self.domain_groups[domain] = {
                    'emails': [],
                    'count': 0,
                    'senders': 0
                }
            
            self.domain_groups[domain]['emails'].append(email)
            self.domain_groups[domain]['count'] += data.get('count', 0)
            self.domain_groups[domain]['senders'] += 1
        
        # Update the domain listbox
        self.refresh_domain_listbox()
        
        # Update status
        total_domains = len(self.domain_groups)
        total_emails = sum(d['count'] for d in self.domain_groups.values())
        self.groups_status.config(text=f"✅ {total_domains} domains • {total_emails} emails")
    
    def refresh_domain_listbox(self):
        """Refresh the domain listbox with current domain groups."""
        self.domain_listbox.delete(0, tk.END)
        self.all_domain_items = []
        
        # Sort by email count descending
        sorted_domains = sorted(self.domain_groups.items(), 
                                key=lambda x: -x[1]['count'])
        
        for domain, data in sorted_domains:
            display = f"{data['count']:>5}   {data['senders']:>6}     {domain}"
            self.all_domain_items.append((display, domain))
            self.domain_listbox.insert(tk.END, display)
    
    def filter_domains(self, *args):
        """Filter domain list based on search text."""
        search_text = self.domain_filter_var.get().lower()
        self.domain_listbox.delete(0, tk.END)
        
        for display, domain in self.all_domain_items:
            if search_text in domain.lower() or search_text in display.lower():
                self.domain_listbox.insert(tk.END, display)
    
    def get_domain_from_display(self, text):
        """Extract domain from display text."""
        # Domain is the last part after whitespace
        parts = text.strip().split()
        if parts:
            return parts[-1].lower()
        return None
    
    def add_domains_to_delete(self):
        """Add selected domains to the deletion list."""
        selected = self.domain_listbox.curselection()
        
        if not selected:
            messagebox.showinfo("No Selection", "Select domains first.")
            return
        
        for idx in selected:
            item = self.domain_listbox.get(idx)
            domain = self.get_domain_from_display(item)
            
            if domain and domain not in self.selected_domains:
                self.selected_domains.add(domain)
                self.domain_delete_listbox.insert(tk.END, item)
        
        self.update_domain_summary()
        self.domain_listbox.selection_clear(0, tk.END)
    
    def remove_domains_from_delete(self):
        """Remove selected domains from deletion list."""
        selected = list(self.domain_delete_listbox.curselection())
        
        for idx in reversed(selected):
            item = self.domain_delete_listbox.get(idx)
            domain = self.get_domain_from_display(item)
            if domain:
                self.selected_domains.discard(domain)
            self.domain_delete_listbox.delete(idx)
        
        self.update_domain_summary()
    
    def clear_domain_delete_list(self):
        """Clear all domains from deletion list."""
        self.domain_delete_listbox.delete(0, tk.END)
        self.selected_domains.clear()
        self.update_domain_summary()
    
    def update_domain_summary(self):
        """Update the domain deletion summary."""
        total_emails = 0
        total_senders = 0
        count = len(self.selected_domains)
        
        for domain in self.selected_domains:
            if domain in self.domain_groups:
                total_emails += self.domain_groups[domain]['count']
                total_senders += self.domain_groups[domain]['senders']
        
        if count > 0:
            self.domain_summary_label.config(
                text=f"🏢 {count} domains • {total_senders} senders • {total_emails} emails")
            self.domain_delete_btn.config(state=tk.NORMAL, bg="#d32f2f")
        else:
            self.domain_summary_label.config(text="No domains selected")
            self.domain_delete_btn.config(state=tk.DISABLED, bg="#cccccc")
    
    def delete_all_from_domains(self):
        """Delete all emails from selected domains."""
        if not self.selected_domains:
            return
        
        # Gather all email addresses from selected domains
        emails_to_delete = []
        for domain in self.selected_domains:
            if domain in self.domain_groups:
                emails_to_delete.extend(self.domain_groups[domain]['emails'])
        
        if not emails_to_delete:
            messagebox.showinfo("No Emails", "No emails found in selected domains.")
            return
        
        total_emails = sum(self.domain_groups.get(d, {}).get('count', 0) 
                          for d in self.selected_domains)
        total_senders = len(emails_to_delete)
        domain_count = len(self.selected_domains)
        
        # Show sample domains
        sample_domains = list(self.selected_domains)[:5]
        domains_text = "\n".join(f"• {d}" for d in sample_domains)
        if len(self.selected_domains) > 5:
            domains_text += f"\n...and {len(self.selected_domains) - 5} more"
        
        msg = (f"PERMANENTLY DELETE all emails from:\n\n"
               f"🏢 {domain_count} domain{'s' if domain_count > 1 else ''}\n"
               f"👤 {total_senders} sender{'s' if total_senders != 1 else ''}\n"
               f"📬 ~{total_emails} emails\n\n"
               f"Domains:\n{domains_text}\n\n"
               f"This CANNOT be undone!")
        
        if not messagebox.askyesno("⚠️ Confirm Delete", msg):
            return
        
        # Create progress dialog
        progress_dialog = DeletionProgressDialog(self.root, "Deleting Domain Emails")
        
        def do_delete():
            deleted = 0
            failed_senders = []
            senders = emails_to_delete
            
            try:
                for i, email in enumerate(senders):
                    if progress_dialog.cancelled:
                        break
                    
                    # Update overall progress
                    def update_overall(x=i, t=len(senders), e=email):
                        progress_dialog.update_overall(x, t, e)
                    self.root.after(0, update_overall)
                    
                    messages = []
                    page_token = None
                    
                    # Find all messages from this sender
                    search_query = f'from:"{email}"'
                    while True:
                        if progress_dialog.cancelled:
                            break
                        response = self.service.users().messages().list(
                            userId='me', q=search_query, maxResults=500, pageToken=page_token
                        ).execute()
                        found = response.get('messages', [])
                        messages.extend(found)
                        msg_count = len(messages)
                        self.root.after(0, lambda c=msg_count: progress_dialog.update_sender(c, 0, finding=True))
                        page_token = response.get('nextPageToken')
                        if not page_token:
                            break
                    
                    if not messages:
                        failed_senders.append(email)
                        continue
                    
                    if messages and not progress_dialog.cancelled:
                        ids = [m['id'] for m in messages]
                        deleted_in_batch = 0
                        total_msgs = len(messages)
                        for j in range(0, len(ids), 1000):
                            if progress_dialog.cancelled:
                                break
                            batch = ids[j:j+1000]
                            try:
                                self.service.users().messages().batchDelete(
                                    userId='me', body={'ids': batch}
                                ).execute()
                                deleted_in_batch += len(batch)
                                deleted += len(batch)
                                self.root.after(0, lambda d=deleted_in_batch, t=total_msgs:
                                    progress_dialog.update_sender(t, d, finding=False))
                                self.root.after(0, lambda td=deleted:
                                    progress_dialog.update_stats(td))
                            except Exception as batch_error:
                                for msg_id in batch:
                                    try:
                                        self.service.users().messages().delete(
                                            userId='me', id=msg_id
                                        ).execute()
                                        deleted_in_batch += 1
                                        deleted += 1
                                    except:
                                        pass
                                self.root.after(0, lambda d=deleted_in_batch, t=total_msgs:
                                    progress_dialog.update_sender(t, d, finding=False))
                                self.root.after(0, lambda td=deleted:
                                    progress_dialog.update_stats(td))
                
                # Final update
                total_senders_count = len(senders)
                self.root.after(0, lambda: progress_dialog.update_overall(total_senders_count, total_senders_count, "Complete!"))
                self.root.after(0, progress_dialog.set_complete)
                
                if progress_dialog.cancelled:
                    self.root.after(500, progress_dialog.close)
                    self.root.after(600, lambda d=deleted: messagebox.showinfo("Cancelled",
                        f"Deletion cancelled.\nDeleted {d} emails before stopping."))
                else:
                    self.root.after(0, lambda: self.domain_delete_listbox.delete(0, tk.END))
                    self.selected_domains.clear()
                    self.root.after(0, self.update_domain_summary)
                    self.root.after(1000, progress_dialog.close)
                    
                    result_msg = f"Deleted {deleted} emails\nfrom {domain_count} domains ({len(senders)} senders)!"
                    if failed_senders:
                        result_msg += f"\n\n⚠️ No emails found for {len(failed_senders)} sender(s)."
                    self.root.after(1100, lambda m=result_msg: messagebox.showinfo("✅ Complete!", m))
                    self.root.after(1200, self.scan_emails)
                
            except Exception as e:
                self.root.after(0, progress_dialog.close)
                self.root.after(100, lambda err=str(e): messagebox.showerror("Error", err))
        
        threading.Thread(target=do_delete, daemon=True).start()
    
    def copy_emails_to_clipboard(self):
        """Copy all email addresses from the sender list to clipboard."""
        if not self.all_senders:
            messagebox.showinfo("No Data", "Please scan emails first.")
            return
        
        # Get all email addresses only (no names, no counts)
        emails = list(self.all_senders.keys())
        email_text = "\n".join(emails)
        
        # Copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(email_text)
        self.root.update()  # Required for clipboard to persist
        
        messagebox.showinfo("✅ Copied!", f"Copied {len(emails)} email addresses to clipboard.\n\nYou can now paste them in the Manual Delete section.")
    
    def delete_all_selected(self):
        if not self.marked_for_delete:
            return
        
        total = sum(self.all_senders.get(e, {}).get('count', 0) for e in self.marked_for_delete)
        count = len(self.marked_for_delete)
        
        msg = f"PERMANENTLY DELETE all emails from:\n\n📧 {count} sender{'s' if count > 1 else ''}"
        if total > 0:
            msg += f"\n📬 ~{total} emails"
        msg += "\n\nThis CANNOT be undone!"
        
        if not messagebox.askyesno("⚠️ Confirm Delete", msg):
            return
        
        # Create progress dialog
        progress_dialog = DeletionProgressDialog(self.root, "Deleting Selected Emails")
        
        def do_delete():
            deleted = 0
            failed_senders = []
            senders = list(self.marked_for_delete)
            
            try:
                for i, email in enumerate(senders):
                    if progress_dialog.cancelled:
                        break
                    
                    # Update overall progress - use default args to capture values
                    def update_overall(x=i, t=len(senders), e=email):
                        progress_dialog.update_overall(x, t, e)
                    self.root.after(0, update_overall)
                    
                    messages = []
                    page_token = None
                    
                    # Find all messages from this sender using quoted email for proper search
                    search_query = f'from:"{email}"'
                    while True:
                        if progress_dialog.cancelled:
                            break
                        response = self.service.users().messages().list(
                            userId='me', q=search_query, maxResults=500, pageToken=page_token
                        ).execute()
                        found = response.get('messages', [])
                        messages.extend(found)
                        msg_count = len(messages)
                        self.root.after(0, lambda c=msg_count: progress_dialog.update_sender(c, 0, finding=True))
                        page_token = response.get('nextPageToken')
                        if not page_token:
                            break
                    
                    if not messages:
                        # No messages found for this sender
                        failed_senders.append(email)
                        continue
                    
                    if messages and not progress_dialog.cancelled:
                        ids = [m['id'] for m in messages]
                        deleted_in_batch = 0
                        total_msgs = len(messages)
                        for j in range(0, len(ids), 1000):
                            if progress_dialog.cancelled:
                                break
                            batch = ids[j:j+1000]
                            try:
                                self.service.users().messages().batchDelete(
                                    userId='me', body={'ids': batch}
                                ).execute()
                                deleted_in_batch += len(batch)
                                deleted += len(batch)
                                self.root.after(0, lambda d=deleted_in_batch, t=total_msgs: 
                                    progress_dialog.update_sender(t, d, finding=False))
                                self.root.after(0, lambda td=deleted: 
                                    progress_dialog.update_stats(td))
                            except Exception as batch_error:
                                # If batch fails, try deleting one by one
                                for msg_id in batch:
                                    try:
                                        self.service.users().messages().delete(
                                            userId='me', id=msg_id
                                        ).execute()
                                        deleted_in_batch += 1
                                        deleted += 1
                                    except:
                                        pass
                                self.root.after(0, lambda d=deleted_in_batch, t=total_msgs: 
                                    progress_dialog.update_sender(t, d, finding=False))
                                self.root.after(0, lambda td=deleted: 
                                    progress_dialog.update_stats(td))
                
                # Final update
                total_senders = len(senders)
                self.root.after(0, lambda: progress_dialog.update_overall(total_senders, total_senders, "Complete!"))
                self.root.after(0, progress_dialog.set_complete)
                
                if progress_dialog.cancelled:
                    self.root.after(500, progress_dialog.close)
                    self.root.after(600, lambda d=deleted: messagebox.showinfo("Cancelled",
                        f"Deletion cancelled.\nDeleted {d} emails before stopping."))
                else:
                    self.root.after(0, lambda: self.delete_listbox.delete(0, tk.END))
                    self.marked_for_delete.clear()
                    self.root.after(0, self.update_summary)
                    self.root.after(1000, progress_dialog.close)
                    
                    # Show result with info about failures
                    result_msg = f"Deleted {deleted} emails from {len(senders)} senders!"
                    if failed_senders:
                        result_msg += f"\n\n⚠️ No emails found for {len(failed_senders)} sender(s)."
                    self.root.after(1100, lambda m=result_msg: messagebox.showinfo("✅ Complete!", m))
                    self.root.after(1200, self.scan_emails)
                
            except Exception as e:
                self.root.after(0, progress_dialog.close)
                self.root.after(100, lambda err=str(e): messagebox.showerror("Error", err))
        
        threading.Thread(target=do_delete, daemon=True).start()


def main():
    root = tk.Tk()
    
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = GmailCleanerApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
