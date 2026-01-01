import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import os
import csv
import pyttsx3
import threading
import datetime
import time
import numpy as np
from PIL import Image, ImageTk
import pandas as pd
from pathlib import Path
from cryptography.fernet import Fernet
import io

# ===================== CONFIGURATION =====================
CONFIG = {
    "APP_TITLE": "Face Recognition Attendance System",
    "VERSION": "v4.0",
    "AUTHOR": "Aditya Goyal | Tulsi Public School | Class XII",
    "ADMIN_PASS": "1234",
    "PATHS": {
        "TRAIN_IMAGES": "TrainingImage",
        "TRAIN_LABELS": "TrainingImageLabel",
        "DETAILS": "StudentDetails",
        "ATTENDANCE": "Attendance",
        "MODEL": "TrainingImageLabel/Trainner.yml",
        "CSV_DETAILS": "StudentDetails/StudentDetails.csv",
        "CASCADE": "haarcascade_frontalface_default.xml"
    },
    "THEME": {
        "BG": "#0f172a",       # Slate 900
        "CARD": "#1e293b",     # Slate 800
        "ACCENT": "#10b981",   # Emerald 500
        "WARN": "#f59e0b",     # Amber 500
        "DANGER": "#ef4444",   # Red 500
        "INFO": "#3b82f6",     # Blue 500
        "TEXT": "#f8fafc",     # Slate 50
        "MUTED": "#94a3b8",    # Slate 400
        "BORDER": "#334155"    # Slate 700
    },
    "FONTS": {
        "HEADING": ("Segoe UI", 24, "bold"),
        "SUBHEADING": ("Segoe UI", 16, "bold"),
        "BODY": ("Segoe UI", 11),
        "BUTTON": ("Segoe UI", 12, "bold"),
        "SMALL": ("Segoe UI", 9)
    }
}

# ===================== ENGINE: FACE RECOGNITION =====================
class FaceEngine:
    def __init__(self):
        self.cascade_path = CONFIG["PATHS"]["CASCADE"]
        if not os.path.exists(self.cascade_path):
            # Fallback to cv2 default if local file not found
            self.cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        
        self.face_cascade = cv2.CascadeClassifier(self.cascade_path)
        
        # Eye Cascade for Blink Detection
        self.eye_path = cv2.data.haarcascades + "haarcascade_eye.xml"
        self.eye_cascade = cv2.CascadeClassifier(self.eye_path)
        
        self.recognizer = None
        self.load_model()

    def load_model(self):
        model_path = CONFIG["PATHS"]["MODEL"]
        if os.path.exists(model_path):
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.recognizer.read(model_path)
        else:
            self.recognizer = None

    def detect_faces(self, gray_frame):
        return self.face_cascade.detectMultiScale(gray_frame, 1.3, 5)

    def detect_eyes(self, face_roi):
        """Returns list of eyes found in the face ROI."""
        return self.eye_cascade.detectMultiScale(face_roi, 1.1, 3)

    def is_anti_spoof(self, face_roi):
        """Simple check for image quality and texture to deter photos/screens."""
        laplacian_var = cv2.Laplacian(face_roi, cv2.CV_64F).var()
        std_dev = np.std(face_roi)
        # Thresholds tuned for typical webcam environments
        return laplacian_var > 45 and std_dev > 25

    def predict(self, face_roi):
        if self.recognizer is None:
            return None, 100
        face_roi = cv2.resize(face_roi, (200, 200))
        return self.recognizer.predict(face_roi)

    def find_match(self, face_roi, student_df):
        """Checks if a face matches anyone already in the database."""
        if self.recognizer is None:
            return None
        face_roi = cv2.resize(face_roi, (200, 200))
        serial, confidence = self.recognizer.predict(face_roi)
        # Threshold 50 means a solid match in LBPH
        if confidence < 50:
            match = student_df[student_df["SERIAL NO."] == serial]
            if not match.empty:
                return match.iloc[0]["NAME"]
        return None

# ===================== ENGINE: VOICE =====================
class VoiceEngine:
    def __init__(self):
        self.queue = []
        self._lock = threading.Lock()
        
    def say(self, text):
        threading.Thread(target=self._speak_thread, args=(text,), daemon=True).start()

    def _speak_thread(self, text):
        with self._lock:
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.say(text)
                engine.runAndWait()
                del engine
            except: pass

# ===================== ENGINE: SECURITY =====================
class SecurityManager:
    KEY_FILE = "secret.key"

    @classmethod
    def load_key(cls):
        if not os.path.exists(cls.KEY_FILE):
            key = Fernet.generate_key()
            with open(cls.KEY_FILE, "wb") as key_file:
                key_file.write(key)
        else:
            with open(cls.KEY_FILE, "rb") as key_file:
                key = key_file.read()
        return Fernet(key)

    @staticmethod
    def encrypt_file(file_path, data_str):
        fernet = SecurityManager.load_key()
        encrypted = fernet.encrypt(data_str.encode())
        with open(file_path, "wb") as f:
            f.write(encrypted)

    @staticmethod
    def decrypt_file(file_path):
        if not os.path.exists(file_path): return None
        fernet = SecurityManager.load_key()
        try:
            with open(file_path, "rb") as f:
                encrypted_data = f.read()
            # If empty
            if not encrypted_data: return ""
            decrypted = fernet.decrypt(encrypted_data).decode()
            return decrypted
        except:
            # Fallback for legacy plain CSVs (auto-encrypt them later)
            with open(file_path, "r") as f:
                return f.read()

# ===================== ENGINE: DATA MANAGER =====================
class DataManager:
    @staticmethod
    def ensure_dirs():
        for p in CONFIG["PATHS"].values():
            # Check if it's likely a directory (no extension) or a file path
            if "." not in os.path.basename(p):
                os.makedirs(p, exist_ok=True)
            else:
                dirname = os.path.dirname(p)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)

    @staticmethod
    def get_student_details():
        path = CONFIG["PATHS"]["CSV_DETAILS"]
        content = SecurityManager.decrypt_file(path)
        if content:
            return pd.read_csv(io.StringIO(content))
        return pd.DataFrame(columns=["SERIAL NO.", "ID", "NAME"])

    @staticmethod
    def save_student(serial, sid, name):
        path = CONFIG["PATHS"]["CSV_DETAILS"]
        
        df = DataManager.get_student_details()
        new_row = pd.DataFrame([[serial, sid, name]], columns=["SERIAL NO.", "ID", "NAME"])
        df = pd.concat([df, new_row], ignore_index=True)
        
        # Save Encrypted
        csv_str = df.to_csv(index=False)
        SecurityManager.encrypt_file(path, csv_str)

    @staticmethod
    def save_attendance(sid, name):
        DataManager.ensure_dirs()
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        f_path = f"{CONFIG['PATHS']['ATTENDANCE']}/Attendance_{date_str}.csv"
        
        # Read existing encrypted data
        content = SecurityManager.decrypt_file(f_path)
        if content:
            df = pd.read_csv(io.StringIO(content))
        else:
            df = pd.DataFrame(columns=["ID", "Name", "Date", "Time"])
            
        new_row = pd.DataFrame([[sid, name, date_str, time_str]], columns=["ID", "Name", "Date", "Time"])
        df = pd.concat([df, new_row], ignore_index=True)
        
        # Write back encrypted
        csv_str = df.to_csv(index=False)
        SecurityManager.encrypt_file(f_path, csv_str)

# ===================== UI: CUSTOM WIDGETS =====================
class StyledButton(tk.Button):
    def __init__(self, master, text, color_key="INFO", command=None, **kwargs):
        bg = CONFIG["THEME"][color_key]
        active_bg = self.lighten_color(bg)
        super().__init__(
            master, text=text, bg=bg, fg="white",
            font=CONFIG["FONTS"]["BUTTON"], relief="flat",
            cursor="hand2", activebackground=active_bg,
            activeforeground="white", command=command, **kwargs
        )
        self.bind("<Enter>", lambda e: self.config(bg=active_bg))
        self.bind("<Leave>", lambda e: self.config(bg=bg))

    @staticmethod
    def lighten_color(hex_color):
        """Simple hex color lightener for hover effect."""
        try:
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            new_rgb = tuple(min(255, c + 30) for c in rgb)
            return '#%02x%02x%02x' % new_rgb
        except:
            return hex_color

class ModernEntry(tk.Frame):
    def __init__(self, master, placeholder, **kwargs):
        super().__init__(master, bg=CONFIG["THEME"]["CARD"], highlightthickness=1, highlightbackground=CONFIG["THEME"]["BORDER"])
        self.placeholder = placeholder
        self.entry = tk.Entry(
            self, bg=CONFIG["THEME"]["CARD"], fg=CONFIG["THEME"]["MUTED"],
            insertbackground="white", font=CONFIG["FONTS"]["BODY"],
            relief="flat", borderwidth=0, **kwargs
        )
        self.entry.pack(padx=10, pady=8, fill="x")
        self.entry.insert(0, placeholder)
        
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, _):
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=CONFIG["THEME"]["TEXT"])
        self.config(highlightbackground=CONFIG["THEME"]["ACCENT"])

    def _on_focus_out(self, _):
        if not self.entry.get().strip():
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=CONFIG["THEME"]["MUTED"])
        self.config(highlightbackground=CONFIG["THEME"]["BORDER"])

    def get(self):
        val = self.entry.get()
        return "" if val == self.placeholder else val

    def clear(self):
        self.entry.delete(0, tk.END)
        self._on_focus_out(None)

class AdminAuth(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Security Check")
        self.geometry("350x200")
        self.configure(bg=CONFIG["THEME"]["CARD"])
        self.resizable(False, False)
        self.result = False
        
        # Center the window
        x = parent.winfo_rootx() + parent.winfo_width()//2 - 175
        y = parent.winfo_rooty() + parent.winfo_height()//2 - 100
        self.geometry(f"+{x}+{y}")
        
        tk.Label(self, text="ENTER ADMIN PIN", font=CONFIG["FONTS"]["SUBHEADING"], bg=CONFIG["THEME"]["CARD"], fg=CONFIG["THEME"]["WARN"]).pack(pady=(20, 10))
        
        self.pin_var = tk.StringVar()
        entry = tk.Entry(self, textvariable=self.pin_var, show="•", font=("Segoe UI", 20), justify="center", bg=CONFIG["THEME"]["BG"], fg=CONFIG["THEME"]["TEXT"], insertbackground="white", width=10, relief="flat")
        entry.pack(pady=10, ipady=5)
        entry.focus_set()
        
        btn_frame = tk.Frame(self, bg=CONFIG["THEME"]["CARD"])
        btn_frame.pack(fill="x", padx=40, pady=10)
        
        StyledButton(btn_frame, "CANCEL", "MUTED", self.destroy).pack(side="left", expand=True, fill="x", padx=(0, 5))
        StyledButton(btn_frame, "UNLOCK", "ACCENT", self.check_pin).pack(side="left", expand=True, fill="x", padx=(5, 0))
        
        self.bind("<Return>", lambda e: self.check_pin())

    def check_pin(self):
        if self.pin_var.get() == CONFIG["ADMIN_PASS"]:
            self.result = True
            self.destroy()
        else:
            self.pin_var.set("")
            messagebox.showerror("Access Denied", "Incorrect PIN!")

# ===================== MAIN APPLICATION =====================
class FRASApp:
    def __init__(self, root):
        self.root = root
        self.root.title(CONFIG["APP_TITLE"])
        # Use a more laptop-friendly size
        self.root.geometry("1200x750")
        self.root.configure(bg=CONFIG["THEME"]["BG"])
        
        self.engine = FaceEngine()
        self.voice = VoiceEngine()
        self.data_manager = DataManager()
        self.data_manager.ensure_dirs()

        # State Variables
        self.camera = None
        self.is_running = False
        self.stop_requested = False
        self.current_frame = None
        
        # TK Variables
        self.status_var = tk.StringVar(value="System Secure & Ready")
        self.datetime_var = tk.StringVar()
        self.progress_var = tk.DoubleVar(value=0)
        self.info_var = tk.StringVar(value="Wait for Action...")
        
        # Analytics Variables
        self.total_students = tk.StringVar(value="0")
        self.present_today = tk.StringVar(value="0")
        self.absent_today = tk.StringVar(value="0")
        
        self.authenticated = False  # Session-based auth state

        # Pre-load blank image to prevent layout shifts (560x420 is compact 4:3)
        self.blank_img = ImageTk.PhotoImage(Image.new('RGB', (560, 420), color='#020617'))

        self._setup_ui()
        self._update_clock()
        self._update_analytics()
        
        # Delayed greeting and periodic refresh
        self.root.after(1000, lambda: self.voice.say("System ready"))
        self._schedule_analytics_refresh()

    def _schedule_analytics_refresh(self):
        """Periodically refresh analytics every 30 seconds."""
        self._update_analytics()
        self.root.after(30000, self._schedule_analytics_refresh)

    def _setup_ui(self):
        # --- Footer (Pack first at bottom) ---
        footer = tk.Frame(self.root, bg=CONFIG["THEME"]["BG"], pady=10)
        footer.pack(side="bottom", fill="x")
        
        status_lbl = tk.Label(footer, textvariable=self.status_var, font=CONFIG["FONTS"]["BODY"], bg=CONFIG["THEME"]["BG"], fg=CONFIG["THEME"]["ACCENT"])
        status_lbl.pack()
        
        copy_lbl = tk.Label(footer, text=CONFIG["AUTHOR"] + " | " + CONFIG["VERSION"], font=CONFIG["FONTS"]["SMALL"], bg=CONFIG["THEME"]["BG"], fg=CONFIG["THEME"]["MUTED"])
        copy_lbl.pack()

        # --- Main Layout ---
        container = tk.Frame(self.root, bg=CONFIG["THEME"]["BG"])
        container.pack(fill="both", expand=True, padx=30, pady=5)

        # Right Column: Controls (Slimmer)
        right_col = tk.Frame(container, bg=CONFIG["THEME"]["CARD"], width=280, padx=15, pady=15)
        right_col.pack(side="right", fill="y", padx=(15, 0))
        right_col.pack_propagate(False)

        # Header moved inside container for better flow
        head_inner = tk.Frame(container, bg=CONFIG["THEME"]["BG"])
        head_inner.pack(fill="x", pady=(0, 10))
        tk.Label(head_inner, text=CONFIG["APP_TITLE"], font=CONFIG["FONTS"]["HEADING"], bg=CONFIG["THEME"]["BG"], fg=CONFIG["THEME"]["TEXT"]).pack(side="left")
        
        # Restored Clock
        clock_lbl = tk.Label(head_inner, textvariable=self.datetime_var, font=CONFIG["FONTS"]["BODY"], bg=CONFIG["THEME"]["BG"], fg=CONFIG["THEME"]["MUTED"])
        clock_lbl.pack(side="right")

        # --- Analytics HUD ---
        analytics_frame = tk.Frame(right_col, bg=CONFIG["THEME"]["CARD"])
        analytics_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(analytics_frame, text="LIVE ANALYTICS", font=CONFIG["FONTS"]["SMALL"], bg=CONFIG["THEME"]["CARD"], fg=CONFIG["THEME"]["WARN"]).pack(anchor="w")
        
        # Mini stat cards
        stats_box = tk.Frame(analytics_frame, bg=CONFIG["THEME"]["CARD"])
        stats_box.pack(fill="x", pady=5)

        def create_stat(parent, label, var, color):
            f = tk.Frame(parent, bg=CONFIG["THEME"]["BG"], padx=5, pady=5, highlightthickness=1, highlightbackground=CONFIG["THEME"]["BORDER"])
            f.pack(side="left", fill="x", expand=True, padx=2)
            tk.Label(f, text=label, font=("Segoe UI", 8), bg=CONFIG["THEME"]["BG"], fg=CONFIG["THEME"]["MUTED"]).pack()
            tk.Label(f, textvariable=var, font=("Segoe UI", 11, "bold"), bg=CONFIG["THEME"]["BG"], fg=color).pack()

        create_stat(stats_box, "TOTAL", self.total_students, CONFIG["THEME"]["INFO"])
        create_stat(stats_box, "PRESENT", self.present_today, CONFIG["THEME"]["ACCENT"])
        create_stat(stats_box, "ABSENT", self.absent_today, CONFIG["THEME"]["DANGER"])

        # Left Column: Video & Live Feed
        left_col = tk.Frame(container, bg=CONFIG["THEME"]["BG"])
        left_col.pack(side="left", fill="both", expand=True)

        video_card = tk.Frame(left_col, bg=CONFIG["THEME"]["CARD"], padx=5, pady=5)
        video_card.pack(fill="x") 
        
        self.video_lbl = tk.Label(video_card, bg="black", image=self.blank_img)
        self.video_lbl.pack()
        # Control Bar below video
        ctrl_bar = tk.Frame(left_col, bg=CONFIG["THEME"]["BG"], pady=10)
        ctrl_bar.pack(fill="x")
        
        StyledButton(ctrl_bar, "START ATTENDANCE", "WARN", self.start_attendance_thread).pack(side="left", fill="x", expand=True, padx=(0, 10))
        StyledButton(ctrl_bar, "STOP SYSTEM", "DANGER", self.stop_system).pack(side="left", fill="x", expand=True)

        # Attendance Table
        table_frame = tk.Frame(left_col, bg=CONFIG["THEME"]["CARD"])
        table_frame.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(table_frame, columns=("ID", "Name", "Time"), show="headings", height=5) # Reduced height
        self.tree.heading("ID", text="STUDENT ID")
        self.tree.heading("Name", text="STUDENT NAME")
        self.tree.heading("Time", text="TIMESTAMP")
        for col in ("ID", "Name", "Time"):
            self.tree.column(col, anchor="center")
        
        # Style Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=CONFIG["THEME"]["CARD"], foreground=CONFIG["THEME"]["TEXT"], fieldbackground=CONFIG["THEME"]["CARD"], borderwidth=0, font=CONFIG["FONTS"]["BODY"])
        style.configure("Treeview.Heading", background=CONFIG["THEME"]["BORDER"], foreground=CONFIG["THEME"]["TEXT"], relief="flat", font=CONFIG["FONTS"]["BODY"])
        style.map("Treeview", background=[('selected', CONFIG["THEME"]["INFO"])])
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tk.Label(right_col, text="REGISTRATION", font=CONFIG["FONTS"]["SMALL"], bg=CONFIG["THEME"]["CARD"], fg=CONFIG["THEME"]["ACCENT"]).pack(anchor="w", pady=(5, 5))
        
        self.id_entry = ModernEntry(right_col, "Student ID")
        self.id_entry.pack(fill="x", pady=4)
        
        self.name_entry = ModernEntry(right_col, "Student Name")
        self.name_entry.pack(fill="x", pady=4)

        StyledButton(right_col, "CAPTURE IMAGES", "INFO", self.register_student_thread).pack(fill="x", pady=(10, 5))
        StyledButton(right_col, "TRAIN AI MODEL", "ACCENT", self.train_model_thread).pack(fill="x", pady=5)
        
        # Tools
        tk.Label(right_col, text="TOOLS", font=CONFIG["FONTS"]["SMALL"], bg=CONFIG["THEME"]["CARD"], fg=CONFIG["THEME"]["MUTED"]).pack(anchor="w", pady=(8, 5))
        
        StyledButton(right_col, "VIEW HISTORY", "CARD", self.view_history, highlightbackground=CONFIG["THEME"]["BORDER"], highlightthickness=1).pack(fill="x", pady=2)
        StyledButton(right_col, "MANAGE DATABASE", "CARD", self.manage_students, highlightbackground=CONFIG["THEME"]["BORDER"], highlightthickness=1).pack(fill="x", pady=2)
        
        self.lock_btn = StyledButton(right_col, "LOCK SYSTEM", "MUTED", self.lock_system)
        # Only show if authenticated
        if not self.authenticated:
            self.lock_btn.pack_forget()
        else:
            self.lock_btn.pack(fill="x", pady=2)

        # Progress Box
        progress_box = tk.Frame(right_col, bg=CONFIG["THEME"]["BG"], pady=10)
        progress_box.pack(side="bottom", fill="x")
        
        tk.Label(progress_box, textvariable=self.info_var, font=CONFIG["FONTS"]["SMALL"], bg=CONFIG["THEME"]["BG"], fg=CONFIG["THEME"]["MUTED"]).pack()
        self.prog_bar = ttk.Progressbar(progress_box, variable=self.progress_var, maximum=100)
        self.prog_bar.pack(fill="x", pady=(5, 0))

    # --- HELPER LOGIC ---
    def _update_clock(self):
        now = datetime.datetime.now().strftime("%A | %d %B %Y | %H:%M:%S")
        self.datetime_var.set(now)
        self.root.after(1000, self._update_clock)

    def _update_analytics(self):
        """Calculates live stats from CSV files."""
        try:
            df_st = self.data_manager.get_student_details()
            total = len(df_st)
            
            date_str = datetime.date.today().strftime("%Y-%m-%d")
            f_path = f"{CONFIG['PATHS']['ATTENDANCE']}/Attendance_{date_str}.csv"
            
            present = 0
            content = SecurityManager.decrypt_file(f_path)
            if content:
                df_at = pd.read_csv(io.StringIO(content))
                present = len(df_at["ID"].unique())
            
            self.total_students.set(str(total))
            self.present_today.set(str(present))
            self.absent_today.set(str(max(0, total - present)))
        except: pass

    def _open_camera(self):
        if self.camera is None or not self.camera.isOpened():
            # Use CAP_DSHOW on Windows for faster initialization
            self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            # Warm up
            for _ in range(2): self.camera.read()
        return self.camera.isOpened()

    def stop_system(self):
        if not self._check_admin(): return
        self.stop_requested = True
        self.status_var.set("Stopping Camera...")

    def _check_admin(self):
        """Blocking call to verify admin with session support."""
        if self.authenticated:
            return True
            
        auth = AdminAuth(self.root)
        self.root.wait_window(auth)
        if auth.result:
            self.authenticated = True
            # Simply pack it at the bottom of its parent (right_col)
            self.lock_btn.pack(fill="x", pady=2)
            return True
        return False

    def lock_system(self):
        self.authenticated = False
        self.lock_btn.pack_forget()
        messagebox.showinfo("Locked", "System Locked Successfully")

    def show_frame(self, frame):
        """Displays OpenCV frame in TKinter label."""
        if frame is None: return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        # Resized to 560x420 for better laptop screen fit
        img = img.resize((560, 420), Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_lbl.config(image=imgtk)
        self.video_lbl.image = imgtk

    # --- THREADED ACTIONS ---
    def start_attendance_thread(self):
        if self.is_running: return
        if self.engine.recognizer is None:
            messagebox.showwarning("No Model", "Please train the model first!")
            return
        
        self.is_running = True
        self.stop_requested = False
        self.status_var.set("Attendance Mode Active")
        threading.Thread(target=self._attendance_loop, daemon=True).start()

    def _attendance_loop(self):
        if not self._open_camera():
            self.is_running = False
            return

        df = self.data_manager.get_student_details()
        marked_today = set()
        
        self.liveness_states = {} # {full_id: 'state'} -> WAITING, OPEN, BLINKED, VERIFIED
        
        while not self.stop_requested:
            ret, frame = self.camera.read()
            if not ret: break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.engine.detect_faces(gray)

            for (x, y, w, h) in faces:
                roi = gray[y:y+h, x:x+w]
                
                # Check for spoofing (Texture)
                if not self.engine.is_anti_spoof(roi):
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    cv2.putText(frame, "Fake Face?", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    continue

                # Identify
                sid, conf = self.engine.predict(roi)
                
                if conf < 50:
                    try:
                        name = df.loc[df["SERIAL NO."] == sid, "NAME"].values[0]
                        student_id = df.loc[df["SERIAL NO."] == sid, "ID"].values[0]
                        full_id = f"{student_id}_{name}"
                    except: 
                        name = "Unknown"
                        full_id = "Unknown"
                else:
                    name = "Unknown"
                    full_id = "Unknown"

                # Drawing Base Rectangle
                color = (255, 255, 255)
                
                if name != "Unknown":
                    # --- Liveness: Blink Challenge ---
                    if full_id in marked_today:
                        color = (0, 255, 0) # Green
                        cv2.putText(frame, f"{name} (Marked)", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    else:
                        # State Machine for Blink
                        state = self.liveness_states.get(full_id, "WAITING")
                        eyes = self.engine.detect_eyes(roi)
                        eyes_open = len(eyes) >= 1 # At least one eye visible
                        
                        msg = "Look at Camera"
                        color = (0, 165, 255) # Orange

                        if state == "WAITING":
                            if eyes_open:
                                self.liveness_states[full_id] = "OPEN"
                        
                        elif state == "OPEN":
                            msg = "Now BLINK!"
                            if not eyes_open: # Eyes disappeared (Blink)
                                self.liveness_states[full_id] = "BLINKED"
                        
                        elif state == "BLINKED":
                            msg = "Open Eyes"
                            if eyes_open: # Eyes reappeared
                                self.liveness_states[full_id] = "VERIFIED"
                                # MARK ATTENDANCE
                                marked_today.add(full_id)
                                self.data_manager.save_attendance(student_id, name)
                                self.root.after(0, lambda s=student_id, n=name: self.tree.insert("", 0, values=(s, n, datetime.datetime.now().strftime("%H:%M:%S"))))
                                self.info_var.set(f"Marked: {name}")
                                self.voice.say(f"Welcome {name}")
                                self._update_analytics()
                                color = (0, 255, 0)
                                del self.liveness_states[full_id] # Reset
                        
                        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                        cv2.putText(frame, f"{name}: {msg}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                else:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2) # Red for unknown

            self.show_frame(frame)
        
        self.camera.release()
        self.is_running = False
        self.status_var.set("System Secure & Ready")
        self.info_var.set("Camera Stopped")

    def register_student_thread(self):
        if not self._check_admin(): return
        if self.is_running: return
        sid = self.id_entry.get().strip()
        name = self.name_entry.get().strip()

        if not sid or not name:
            messagebox.showerror("Input Error", "Both ID and Name are required!")
            return
        
        # Validate ID
        if not sid.isdigit():
            messagebox.showerror("Input Error", "Student ID must be numeric!")
            return

        # Check if ID exists
        df = self.data_manager.get_student_details()
        if not df.empty and int(sid) in df["ID"].astype(int).values:
            messagebox.showwarning("Exists", f"Student with ID {sid} already exists!")
            return

        self.is_running = True
        self.stop_requested = False
        self.status_var.set("Capturing Student Images...")
        threading.Thread(target=self._capture_loop, args=(sid, name, len(df)+1), daemon=True).start()

    def _capture_loop(self, sid, name, serial):
        if not self._open_camera():
            self.is_running = False
            return

        count = 0
        target = 40
        self.progress_var.set(0)

        checked_duplicate = False
        
        while not self.stop_requested and count < target:
            ret, frame = self.camera.read()
            if not ret: break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.engine.detect_faces(gray)

            df = self.data_manager.get_student_details()

            for (x, y, w, h) in faces:
                roi = gray[y:y+h, x:x+w]
                
                if not self.engine.is_anti_spoof(roi):
                    continue

                if not checked_duplicate:
                    match_name = self.engine.find_match(roi, df)
                    if match_name:
                        self.voice.say(f"Face already registered as {match_name}")
                        self.root.after(0, lambda m=match_name: messagebox.showerror("Duplicate Detected", f"This person is already registered as {m}!"))
                        self.stop_requested = True
                        break
                    checked_duplicate = True
                count += 1
                img_path = f"{CONFIG['PATHS']['TRAIN_IMAGES']}/{name}.{serial}.{sid}.{count}.jpg"
                cv2.imwrite(img_path, cv2.resize(roi, (200, 200)))
                
                self.progress_var.set((count / target) * 100)
                self.info_var.set(f"Captured {count}/{target} samples")
                
                cv2.rectangle(frame, (x, y), (x+w, y+h), (16, 185, 129), 2)

            self.show_frame(frame)
            time.sleep(0.05) # Prevent CPU hogging
        
        self.camera.release()
        self.is_running = False
        
        if count >= target:
            self.data_manager.save_student(serial, sid, name)
            self.voice.say(f"Registration complete for {name}")
            messagebox.showinfo("Success", f"Registration complete for {name}!")
            self._update_analytics()
            self.id_entry.clear()
            self.name_entry.clear()
        else:
            self.status_var.set("Registration Cancelled")
            self.voice.say("Registration cancelled")


    def train_model_thread(self):
        if not self._check_admin(): return
        if self.is_running: return
        self.is_running = True
        self.info_var.set("Training AI Model...")
        threading.Thread(target=self._train_logic, daemon=True).start()

    def _train_logic(self):
        img_dir = CONFIG["PATHS"]["TRAIN_IMAGES"]
        image_paths = [os.path.join(img_dir, f) for f in os.listdir(img_dir) if f.endswith(".jpg")]
        
        if not image_paths:
            messagebox.showerror("Error", "No training data found!")
            self.is_running = False
            return

        faces, ids = [], []
        total = len(image_paths)

        for i, path in enumerate(image_paths):
            pil_img = Image.open(path).convert('L')
            np_img = np.array(pil_img, 'uint8')
            
            # Extract ID from filename: name.serial.sid.count.jpg
            sid_serial = int(os.path.split(path)[-1].split(".")[1])
            faces.append(np_img)
            ids.append(sid_serial)
            
            self.progress_var.set(((i+1)/total)*100)
            self.info_var.set(f"Processing: {i+1}/{total}")

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(ids))
        recognizer.save(CONFIG["PATHS"]["MODEL"])
        
        self.engine.load_model()
        self.is_running = False
        self.info_var.set("Model Trained Successfully")
        messagebox.showinfo("Ready", "AI Model Ready for Use!")

    def view_history(self):
        AttendanceViewer(self.root)

    def manage_students(self):
        if not self._check_admin(): return
        StudentManager(self, self.data_manager)

# ===================== SECONDARY WINDOWS =====================
class AttendanceViewer(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Attendance History")
        self.geometry("900x650")
        self.configure(bg=CONFIG["THEME"]["BG"])
        
        tk.Label(self, text="ATTENDANCE LOGS", font=CONFIG["FONTS"]["SUBHEADING"], bg=CONFIG["THEME"]["BG"], fg=CONFIG["THEME"]["TEXT"]).pack(pady=20)
        
        controls = tk.Frame(self, bg=CONFIG["THEME"]["BG"])
        controls.pack(fill="x", padx=40)
        
        files = [f for f in os.listdir(CONFIG["PATHS"]["ATTENDANCE"]) if f.endswith(".csv")]
        self.file_cb = ttk.Combobox(controls, values=files, state="readonly", width=40)
        self.file_cb.pack(side="left", padx=10)
        self.file_cb.bind("<<ComboboxSelected>>", self.load_data)
        
        StyledButton(controls, "LOAD FILE", "INFO", self.load_data).pack(side="left")

        tree_frame = tk.Frame(self, bg=CONFIG["THEME"]["CARD"])
        tree_frame.pack(fill="both", expand=True, padx=40, pady=20)

        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Name", "Date", "Time"), show="headings")
        for col in ("ID", "Name", "Date", "Time"):
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

    def load_data(self, _=None):
        filename = self.file_cb.get()
        if not filename: return
        
        for i in self.tree.get_children(): self.tree.delete(i)
        
        path = os.path.join(CONFIG["PATHS"]["ATTENDANCE"], filename)
        # Decrypt properly
        content = SecurityManager.decrypt_file(path)
        if content:
            reader = csv.reader(io.StringIO(content))
            next(reader) # Skip header
            for row in reader:
                self.tree.insert("", "end", values=row)

class StudentManager(tk.Toplevel):
    def __init__(self, app, data_manager):
        super().__init__(app.root)
        self.title("Manage Student Database")
        self.geometry("850x600")
        self.configure(bg=CONFIG["THEME"]["BG"])
        self.app = app
        self.dm = data_manager

        tree_frame = tk.Frame(self, bg=CONFIG["THEME"]["CARD"])
        tree_frame.pack(fill="both", expand=True, padx=40)

        self.tree = ttk.Treeview(tree_frame, columns=("Serial", "ID", "Name"), show="headings")
        self.tree.heading("Serial", text="S.NO")
        self.tree.heading("ID", text="STUDENT ID")
        self.tree.heading("Name", text="NAME")
        self.tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        
        self.load_students()
        
        btn_frame = tk.Frame(self, bg=CONFIG["THEME"]["BG"], pady=20)
        btn_frame.pack(fill="x", padx=40)
        
        StyledButton(btn_frame, "EDIT STUDENT", "INFO", self.edit_student).pack(side="left", expand=True, fill="x", padx=(0, 5))
        StyledButton(btn_frame, "DELETE STUDENT", "DANGER", self.delete_student).pack(side="left", expand=True, fill="x", padx=(5, 0))
        
        tk.Label(self, text="* Note: Editing/Deleting requires retraining the model.", font=CONFIG["FONTS"]["SMALL"], bg=CONFIG["THEME"]["BG"], fg=CONFIG["THEME"]["MUTED"]).pack(pady=5)

    def load_students(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        df = self.dm.get_student_details()
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=(row["SERIAL NO."], row["ID"], row["NAME"]))

    def edit_student(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection", "Please select a student to edit.")
            return
        
        item = self.tree.item(selected[0])
        serial = item['values'][0]
        old_sid = str(item['values'][1])
        old_name = item['values'][2]
        
        dialog = EditStudentDialog(self, old_sid, old_name)
        self.wait_window(dialog)
        
        if dialog.result:
            new_sid, new_name = dialog.result
            
            # Update Database
            df = self.dm.get_student_details()
            
            # Check if new SID exists (and is not the current one)
            # Ensure comparison is done between integers
            new_id_int = int(new_sid)
            if str(new_sid) != str(old_sid) and new_id_int in df["ID"].astype(int).values:
                messagebox.showerror("Error", f"ID {new_sid} already exists!")
                return

            df.loc[df["SERIAL NO."] == int(serial), ["ID", "NAME"]] = [new_id_int, new_name]
            
            # Save Encrypted
            path = CONFIG["PATHS"]["CSV_DETAILS"]
            csv_str = df.to_csv(index=False)
            SecurityManager.encrypt_file(path, csv_str)
            
            # Rename images
            img_dir = CONFIG["PATHS"]["TRAIN_IMAGES"]
            renamed_count = 0
            for f in os.listdir(img_dir):
                # Pattern: name.serial.sid.count.jpg
                parts = f.split('.')
                if len(parts) == 5 and parts[1] == str(serial):
                    new_filename = f"{new_name}.{serial}.{new_sid}.{parts[3]}.jpg"
                    try:
                        os.rename(os.path.join(img_dir, f), os.path.join(img_dir, new_filename))
                        renamed_count += 1
                    except Exception as e:
                        print(f"Failed to rename {f}: {e}")
            
            messagebox.showinfo("Success", f"Updated student details and {renamed_count} images. Please retrain.")
            self.load_students()
            self.app._update_analytics()

    def delete_student(self):
        selected = self.tree.selection()
        if not selected: return
        
        item = self.tree.item(selected[0])
        sid = item['values'][1]
        name = item['values'][2]
        
        if messagebox.askyesno("Confirm", f"Remove {name} (ID: {sid}) and all their images?"):
            df = self.dm.get_student_details()
            # Ensure we compare integers for deletion
            df = df[df["ID"].astype(int) != int(sid)]
            
            # Save Encrypted
            path = CONFIG["PATHS"]["CSV_DETAILS"]
            csv_str = df.to_csv(index=False)
            SecurityManager.encrypt_file(path, csv_str)
            
            # Remove images
            img_dir = CONFIG["PATHS"]["TRAIN_IMAGES"]
            for f in os.listdir(img_dir):
                if f".{sid}." in f or f.startswith(f"{name}."):
                    try: os.remove(os.path.join(img_dir, f))
                    except: pass
            
            messagebox.showinfo("Done", "Student data removed. Please retrain model.")
            self.load_students()
            self.app._update_analytics()

class EditStudentDialog(tk.Toplevel):
    def __init__(self, parent, old_sid, old_name):
        super().__init__(parent)
        self.title("Edit Student Details")
        self.geometry("400x300")
        self.configure(bg=CONFIG["THEME"]["CARD"])
        self.resizable(False, False)
        self.result = None
        
        # Center
        x = parent.winfo_rootx() + parent.winfo_width()//2 - 200
        y = parent.winfo_rooty() + parent.winfo_height()//2 - 150
        self.geometry(f"+{x}+{y}")
        
        tk.Label(self, text="EDIT STUDENT", font=CONFIG["FONTS"]["SUBHEADING"], bg=CONFIG["THEME"]["CARD"], fg=CONFIG["THEME"]["ACCENT"]).pack(pady=20)
        
        self.id_entry = ModernEntry(self, "Student ID")
        self.id_entry.pack(fill="x", padx=40, pady=5)
        self.id_entry.entry.delete(0, tk.END)
        self.id_entry.entry.insert(0, old_sid)
        self.id_entry.entry.config(fg=CONFIG["THEME"]["TEXT"])
        
        self.name_entry = ModernEntry(self, "Student Name")
        self.name_entry.pack(fill="x", padx=40, pady=5)
        self.name_entry.entry.delete(0, tk.END)
        self.name_entry.entry.insert(0, old_name)
        self.name_entry.entry.config(fg=CONFIG["THEME"]["TEXT"])
        
        btn_frame = tk.Frame(self, bg=CONFIG["THEME"]["CARD"])
        btn_frame.pack(fill="x", padx=40, pady=20)
        
        StyledButton(btn_frame, "CANCEL", "MUTED", self.destroy).pack(side="left", expand=True, fill="x", padx=(0, 5))
        StyledButton(btn_frame, "SAVE", "ACCENT", self.save).pack(side="left", expand=True, fill="x", padx=(5, 0))

    def save(self):
        sid = self.id_entry.get().strip()
        name = self.name_entry.get().strip()
        
        if not sid or not name:
            messagebox.showerror("Error", "All fields required!")
            return
        if not sid.isdigit():
            messagebox.showerror("Error", "ID must be numeric!")
            return
            
        self.result = (sid, name)
        self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FRASApp(root)
    root.mainloop()

