import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import datetime
import os
import sys
import math
import time
import random
import subprocess
import webbrowser
import platform
import json
import re
import queue
from pathlib import Path

# ── Optional imports with graceful fallback ──────────────────────────────────
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import wikipedia
    WIKI_AVAILABLE = True
except ImportError:
    WIKI_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ── Colour Palette ────────────────────────────────────────────────────────────
BG_DEEP    = "#020b18"
BG_PANEL   = "#030f1e"
NEON_CYAN  = "#00f5ff"
NEON_BLUE  = "#0066ff"
NEON_GREEN = "#00ff88"
NEON_RED   = "#ff003c"
GOLD       = "#ffd700"
TEXT_MAIN  = "#c8e8ff"
TEXT_DIM   = "#4a7a9b"
ACCENT     = "#00d4ff"
PANEL_BORDER = "#0a3a5c"

# ── TTS Engine ────────────────────────────────────────────────────────────────
_tts_engine = None

def _init_tts():
    global _tts_engine
    if PYTTSX3_AVAILABLE and _tts_engine is None:
        try:
            _tts_engine = pyttsx3.init()
            _tts_engine.setProperty("rate", 175)
            _tts_engine.setProperty("volume", 0.95)
            voices = _tts_engine.getProperty("voices")
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    _tts_engine.setProperty("voice", v.id)
                    break
        except Exception:
            _tts_engine = None

def speak(text, app=None):
    """Speak text in a background thread."""
    if app:
        app.set_status("SPEAKING", NEON_GREEN)
    def _run():
        try:
            if PYTTSX3_AVAILABLE:
                _init_tts()
                if _tts_engine:
                    _tts_engine.say(text)
                    _tts_engine.runAndWait()
        except Exception:
            pass
        finally:
            if app:
                app.set_status("IDLE", TEXT_DIM)
    threading.Thread(target=_run, daemon=True).start()


# ── Brain: Command Handler ────────────────────────────────────────────────────
class Brain:
    def __init__(self, app):
        self.app = app
        self._reminders = []
        self._timer_thread = None

    # ── Entry point ──────────────────────────────────────────────────────────
    def process(self, text: str) -> str:
        text = text.strip()
        lower = text.lower()

        # Greetings
        if any(w in lower for w in ["hello", "hi edith", "hey edith", "good morning", "good evening", "good afternoon"]):
            hour = datetime.datetime.now().hour
            greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
            return f"{greeting}, sir! I'm EDITH, your personal AI assistant. How may I assist you today?"

        # Time / Date
        if re.search(r"\btime\b", lower):
            return f"The current time is {datetime.datetime.now().strftime('%I:%M:%S %p')}."
        if re.search(r"\bdate\b|\bday\b|\btoday\b", lower):
            return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."

        # Calculator
        calc = re.search(r"(?:calculate|compute|what is|what's|solve)\s+([\d\s\+\-\*\/\.\(\)\%\^]+)", lower)
        if calc or re.search(r"^\s*[\d\s\+\-\*\/\.\(\)\%]+\s*$", lower):
            expr = calc.group(1) if calc else lower
            return self._calculate(expr)

        # Wikipedia
        if re.search(r"who is|what is|tell me about|explain|define|wikipedia", lower):
            query = re.sub(r"who is|what is|tell me about|explain|define|wikipedia|please|\?", "", lower).strip()
            if query:
                return self._wiki(query)

        # Weather
        if "weather" in lower:
            city = re.sub(r"weather|what('s| is) the|in|at|for|today|now", "", lower).strip()
            return self._weather(city or "your city")

        # Open applications
        if re.search(r"\bopen\b|\blaunch\b|\bstart\b", lower):
            return self._open_app(lower)

        # Search
        if re.search(r"\bsearch\b|\bgoogle\b", lower):
            query = re.sub(r"search|google|for|please|on the web", "", lower).strip()
            webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            return f"Searching Google for: {query}"

        # YouTube
        if "youtube" in lower:
            query = re.sub(r"youtube|play|search|open|on", "", lower).strip()
            if query:
                webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
                return f"Opening YouTube search for: {query}"
            webbrowser.open("https://www.youtube.com")
            return "Opening YouTube."

        # Screenshot
        if "screenshot" in lower:
            return self._screenshot()

        # Battery
        if "battery" in lower:
            return self._battery()

        # System info
        if any(w in lower for w in ["cpu", "ram", "memory", "system info", "system status"]):
            return self._system_info()

        # Volume
        if "volume" in lower or "mute" in lower:
            return self._volume(lower)

        # Timer
        m = re.search(r"(?:set\s+)?(?:a\s+)?timer\s+(?:for\s+)?(\d+)\s*(second|minute|hour)s?", lower)
        if m:
            return self._set_timer(int(m.group(1)), m.group(2))

        # Reminder
        m = re.search(r"remind me (?:to\s+)?(.+?) (?:in|after) (\d+)\s*(second|minute|hour)s?", lower)
        if m:
            return self._set_reminder(m.group(1), int(m.group(2)), m.group(3))

        # Joke
        if "joke" in lower:
            return random.choice(JOKES)

        # Motivational quote
        if any(w in lower for w in ["quote", "motivate", "inspire", "motivation"]):
            return random.choice(QUOTES)

        # Flip coin
        if "flip" in lower and "coin" in lower:
            return f"🪙 The coin landed on: **{random.choice(['Heads','Tails'])}**!"

        # Random number
        m = re.search(r"random number(?: between (\d+) and (\d+))?", lower)
        if m:
            lo = int(m.group(1) or 1)
            hi = int(m.group(2) or 100)
            return f"🎲 Your random number is: {random.randint(lo, hi)}"

        # IP Address
        if "ip address" in lower or "my ip" in lower:
            return self._get_ip()

        # Shutdown / restart
        if "shutdown" in lower or "shut down" in lower:
            return "⚠️ Shutdown command received. Please confirm by typing 'confirm shutdown'."
        if lower.strip() == "confirm shutdown":
            os.system("shutdown /s /t 5" if platform.system() == "Windows" else "shutdown -h now")
            return "Initiating system shutdown in 5 seconds. Goodbye, sir."

        if "restart" in lower:
            return "⚠️ Restart command received. Please type 'confirm restart' to proceed."
        if lower.strip() == "confirm restart":
            os.system("shutdown /r /t 5" if platform.system() == "Windows" else "reboot")
            return "Restarting system in 5 seconds."

        # Clear log
        if any(w in lower for w in ["clear", "clean", "reset log"]):
            self.app.clear_log()
            return "Log cleared. Ready for new commands, sir."

        # Help
        if "help" in lower or "what can you do" in lower or "commands" in lower:
            return HELP_TEXT

        # Exit
        if any(w in lower for w in ["exit", "quit", "bye", "goodbye", "shut yourself"]):
            self.app.root.after(1500, self.app.root.destroy)
            return "Goodbye, sir. EDITH is powering down. Stay safe."

        # Fallback
        return f"I understood you said: '{text}'. I'm still learning! Try asking me for help to see what I can do."

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _calculate(self, expr):
        try:
            expr = expr.replace("^", "**").replace("%", "/100")
            result = eval(expr, {"__builtins__": {}}, {})
            return f"🧮 Result: {result}"
        except Exception:
            return "I couldn't compute that. Please check the expression."

    def _wiki(self, query):
        if not WIKI_AVAILABLE:
            webbrowser.open(f"https://en.wikipedia.org/w/index.php?search={query.replace(' ', '+')}")
            return f"Wikipedia module not installed. Opening browser for: {query}"
        try:
            summary = wikipedia.summary(query, sentences=3, auto_suggest=True)
            return f"📖 {summary}"
        except Exception as e:
            return f"I couldn't find information on '{query}'. Try being more specific."

    def _weather(self, city):
        if not REQUESTS_AVAILABLE:
            webbrowser.open(f"https://www.google.com/search?q=weather+{city.replace(' ', '+')}")
            return f"Opening weather for {city} in browser."
        try:
            url = f"https://wttr.in/{city.replace(' ', '+')}?format=3"
            r = requests.get(url, timeout=5)
            return f"🌤 {r.text.strip()}"
        except Exception:
            webbrowser.open(f"https://www.google.com/search?q=weather+{city.replace(' ', '+')}")
            return f"Opening weather for {city} in browser."

    def _open_app(self, cmd):
        apps = {
            "notepad":   ("notepad.exe",      "gedit"),
            "chrome":    ("chrome",            "google-chrome"),
            "firefox":   ("firefox",           "firefox"),
            "calculator":("calc.exe",          "gnome-calculator"),
            "paint":     ("mspaint.exe",       ""),
            "explorer":  ("explorer.exe",      "nautilus"),
            "task manager": ("taskmgr.exe",    "gnome-system-monitor"),
            "word":      ("winword.exe",       "libreoffice --writer"),
            "excel":     ("excel.exe",         "libreoffice --calc"),
            "vlc":       ("vlc",               "vlc"),
            "cmd":       ("cmd.exe",           "bash"),
            "terminal":  ("cmd.exe",           "gnome-terminal"),
            "spotify":   ("spotify",           "spotify"),
            "vs code":   ("code",              "code"),
            "vscode":    ("code",              "code"),
        }
        is_win = platform.system() == "Windows"
        for name, (win_cmd, lin_cmd) in apps.items():
            if name in cmd:
                app_cmd = win_cmd if is_win else lin_cmd
                if app_cmd:
                    try:
                        subprocess.Popen(app_cmd, shell=True)
                        return f"✅ Opening {name.title()}..."
                    except Exception:
                        return f"❌ Could not open {name.title()}."
        # Website fallback
        for site in ["google", "youtube", "facebook", "twitter", "instagram", "github", "whatsapp", "microsoft edge","microsoft store"]:
            if site in cmd:
                webbrowser.open(f"https://www.{site}.com")
                return f"🌐 Opening {site.title()} in your browser."
        return "I'm not sure which application to open. Please be more specific."

    def _screenshot(self):
        try:
            import pyautogui
            path = os.path.join(Path.home(), f"EDITH_screenshot_{int(time.time())}.png")
            pyautogui.screenshot(path)
            return f"📸 Screenshot saved to: {path}"
        except ImportError:
            return "⚠️ pyautogui not installed. Run: pip install pyautogui"
        except Exception as e:
            return f"❌ Screenshot failed: {e}"

    def _battery(self):
        if not PSUTIL_AVAILABLE:
            return "⚠️ psutil not installed. Run: pip install psutil"
        try:
            b = psutil.sensors_battery()
            if b is None:
                return "No battery detected (desktop system)."
            status = "Charging ⚡" if b.power_plugged else "Discharging 🔋"
            return f"🔋 Battery: {b.percent:.1f}% — {status}"
        except Exception:
            return "Could not retrieve battery info."

    def _system_info(self):
        if not PSUTIL_AVAILABLE:
            return "⚠️ psutil not installed. Run: pip install psutil"
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            return (f"💻 System Status:\n"
                    f"  CPU Usage : {cpu}%\n"
                    f"  RAM       : {ram.used/1e9:.1f} GB / {ram.total/1e9:.1f} GB ({ram.percent}%)\n"
                    f"  Disk      : {disk.used/1e9:.1f} GB / {disk.total/1e9:.1f} GB ({disk.percent}%)\n"
                    f"  OS        : {platform.system()} {platform.release()}")
        except Exception as e:
            return f"Error retrieving system info: {e}"

    def _volume(self, cmd):
        if platform.system() == "Windows":
            if "mute" in cmd:
                os.system("nircmd.exe mutesysvolume 2")
                return "🔇 Volume muted."
            elif "up" in cmd or "increase" in cmd or "max" in cmd:
                os.system("nircmd.exe setsysvolume 65535")
                return "🔊 Volume set to maximum."
            elif "down" in cmd or "decrease" in cmd or "low" in cmd:
                os.system("nircmd.exe setsysvolume 20000")
                return "🔉 Volume lowered."
        return "Volume control is available on Windows with nircmd. Opening mixer..."

    def _set_timer(self, amount, unit):
        seconds = amount * (60 if unit == "minute" else 3600 if unit == "hour" else 1)
        def _countdown():
            time.sleep(seconds)
            self.app.add_log("EDITH", f"⏰ Timer finished! {amount} {unit}(s) elapsed.")
            speak(f"Sir, your {amount} {unit} timer is complete.", self.app)
        threading.Thread(target=_countdown, daemon=True).start()
        return f"⏱ Timer set for {amount} {unit}(s). I'll alert you when done."

    def _set_reminder(self, task, amount, unit):
        seconds = amount * (60 if unit == "minute" else 3600 if unit == "hour" else 1)
        def _remind():
            time.sleep(seconds)
            self.app.add_log("EDITH", f"🔔 Reminder: {task}")
            speak(f"Sir, reminder: {task}", self.app)
        threading.Thread(target=_remind, daemon=True).start()
        return f"🔔 I'll remind you to {task} in {amount} {unit}(s)."

    def _get_ip(self):
        if REQUESTS_AVAILABLE:
            try:
                ip = requests.get("https://api.ipify.org", timeout=4).text
                return f"🌐 Your public IP address is: {ip}"
            except Exception:
                pass
        import socket
        try:
            ip = socket.gethostbyname(socket.gethostname())
            return f"🌐 Local IP address: {ip}"
        except Exception:
            return "Could not retrieve IP address."


# ── Static Data ───────────────────────────────────────────────────────────────
JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
    "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
    "Why was the math book sad? It had too many problems.",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
    "Why don't scientists trust atoms? Because they make up everything!",
    "How do you comfort a JavaScript bug? You console it.",
    "Why did the developer go broke? Because he used up all his cache.",
]

QUOTES = [
    "💡 'The only way to do great work is to love what you do.' — Steve Jobs",
    "🚀 'In the middle of every difficulty lies opportunity.' — Einstein",
    "⚡ 'It does not matter how slowly you go as long as you do not stop.' — Confucius",
    "🔥 'Success is not final, failure is not fatal: it is the courage to continue that counts.' — Churchill",
    "🌟 'Believe you can and you're halfway there.' — Theodore Roosevelt",
    "💪 'The future belongs to those who believe in the beauty of their dreams.' — Eleanor Roosevelt",
]

HELP_TEXT = """🤖 EDITH COMMAND GUIDE:

⏰ TIME & DATE
  • "What time is it?" / "What's today's date?"

🧮 CALCULATOR
  • "Calculate 25 * 4 + 10" / "What is 100 / 5?"

🌐 WEB & SEARCH
  • "Search for Python tutorials"
  • "Open YouTube" / "Open GitHub" 
  

📖 WIKIPEDIA
  • "Who is Elon Musk?"
  • "Tell me about black holes"

🌤 WEATHER
  • "What's the weather in Mumbai?"

💻 SYSTEM
  • "System info" / "Battery status"
  • "CPU usage" / "RAM usage"

📸 SCREENSHOT
  • "Take a screenshot"

⏱ TIMER & REMINDER
  • "Set a timer for 5 minutes"
  • "Remind me to drink water in 30 minutes"

🎮 FUN
  • "Tell me a joke"
  • "Give me a quote"
  • "Flip a coin"
  • "Random number between 1 and 50"

🖥 APPS
  • "Open Notepad" / "Open Chrome"
  • "Open Calculator" / "Open VS Code"

❌ EXIT
  • "Goodbye" / "Exit" / "Quit"
"""


# ── GUI Application ───────────────────────────────────────────────────────────
class EDITHApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EDITH — AI Assistant")
        self.root.geometry("1100x780")
        self.root.minsize(900, 680)
        self.root.configure(bg=BG_DEEP)
        self.root.resizable(True, True)

        # Set icon if possible
        try:
            self.root.iconbitmap("")
        except Exception:
            pass

        self.brain = Brain(self)
        self.listening = False
        self.orb_angle = 0
        self.wave_points = [0] * 60
        self.wave_phase = 0
        self._status_text = tk.StringVar(value="IDLE")
        self._status_color = TEXT_DIM
        self._speak_queue = queue.Queue()
        self._anim_after = None
        self._clock_after = None

        self._build_ui()
        self._start_animations()
        self._update_clock()

        # Greet on startup
        self.root.after(600, lambda: self._greet())

    # ── UI Build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        top = tk.Frame(self.root, bg=BG_PANEL, height=64)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        tk.Label(top, text="◈", font=("Courier New", 22, "bold"),
                 fg=NEON_CYAN, bg=BG_PANEL).pack(side="left", padx=(18, 6), pady=10)
        tk.Label(top, text="E.D.I.T.H", font=("Courier New", 22, "bold"),
                 fg=NEON_CYAN, bg=BG_PANEL).pack(side="left", pady=10)
        tk.Label(top, text="  Enhanced Defence Intelligence Tactical Hub",
                 font=("Courier New", 9), fg=TEXT_DIM, bg=BG_PANEL).pack(side="left", pady=10)

        self.clock_var = tk.StringVar()
        tk.Label(top, textvariable=self.clock_var, font=("Courier New", 13, "bold"),
                 fg=NEON_GREEN, bg=BG_PANEL).pack(side="right", padx=20)

        # Status dot
        self.status_label = tk.Label(top, textvariable=self._status_text,
                                      font=("Courier New", 10, "bold"),
                                      fg=TEXT_DIM, bg=BG_PANEL)
        self.status_label.pack(side="right", padx=10)

        # ── Separator ────────────────────────────────────────────────────────
        tk.Frame(self.root, bg=NEON_CYAN, height=1).pack(fill="x")

        # ── Main content ─────────────────────────────────────────────────────
        content = tk.Frame(self.root, bg=BG_DEEP)
        content.pack(fill="both", expand=True, padx=14, pady=12)

        # Left panel (orb + controls)
        left = tk.Frame(content, bg=BG_PANEL, width=300,
                        highlightbackground=PANEL_BORDER, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        # Orb canvas
        self.orb_canvas = tk.Canvas(left, width=280, height=280,
                                     bg=BG_PANEL, highlightthickness=0)
        self.orb_canvas.pack(pady=(20, 10))
        self._draw_orb_static()

        # Waveform canvas
        self.wave_canvas = tk.Canvas(left, width=280, height=70,
                                      bg=BG_PANEL, highlightthickness=0)
        self.wave_canvas.pack(pady=4)

        # Voice button
        self.voice_btn = tk.Button(
            left, text="🎙  ACTIVATE VOICE",
            font=("Courier New", 11, "bold"),
            fg=BG_DEEP, bg=NEON_CYAN,
            activebackground=NEON_BLUE, activeforeground="white",
            relief="flat", cursor="hand2", bd=0,
            command=self._toggle_voice,
            pady=10
        )
        self.voice_btn.pack(fill="x", padx=20, pady=(10, 6))

        tk.Button(left, text="⚡  SYSTEM STATUS",
                  font=("Courier New", 10), fg=NEON_GREEN, bg="#051a2e",
                  activebackground="#0a2a44", activeforeground=NEON_GREEN,
                  relief="flat", cursor="hand2", bd=0, pady=8,
                  command=lambda: self._send_command("system info")
                  ).pack(fill="x", padx=20, pady=3)

        tk.Button(left, text="📖  HELP",
                  font=("Courier New", 10), fg=GOLD, bg="#1a1200",
                  activebackground="#2a2000", activeforeground=GOLD,
                  relief="flat", cursor="hand2", bd=0, pady=8,
                  command=lambda: self._send_command("help")
                  ).pack(fill="x", padx=20, pady=3)

        tk.Button(left, text="🗑  CLEAR LOG",
                  font=("Courier New", 10), fg=NEON_RED, bg="#1a000a",
                  activebackground="#2a0012", activeforeground=NEON_RED,
                  relief="flat", cursor="hand2", bd=0, pady=8,
                  command=self.clear_log
                  ).pack(fill="x", padx=20, pady=3)

        # Quick commands grid
        tk.Label(left, text="── QUICK COMMANDS ──", font=("Courier New", 8),
                 fg=TEXT_DIM, bg=BG_PANEL).pack(pady=(14, 4))

        quick_frame = tk.Frame(left, bg=BG_PANEL)
        quick_frame.pack(fill="x", padx=12)

        quick_cmds = [
            ("🕐 Time", "what time is it"),
            ("📅 Date", "what is today's date"),
            ("🔋 Battery", "battery status"),
            ("🌤 Weather", "weather"),
            ("😂 Joke", "tell me a joke"),
            ("💡 Quote", "give me a quote"),
            ("🪙 Coin", "flip a coin"),
            ("🎲 Random", "random number"),
        ]
        for i, (label, cmd) in enumerate(quick_cmds):
            btn = tk.Button(quick_frame, text=label,
                            font=("Courier New", 8), fg=TEXT_MAIN,
                            bg="#071828", activebackground="#0d2a44",
                            activeforeground=NEON_CYAN,
                            relief="flat", cursor="hand2", bd=0, pady=5,
                            command=lambda c=cmd: self._send_command(c))
            btn.grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="ew")
        quick_frame.columnconfigure(0, weight=1)
        quick_frame.columnconfigure(1, weight=1)

        # ── Right panel (log + input) ─────────────────────────────────────────
        right = tk.Frame(content, bg=BG_DEEP)
        right.pack(side="left", fill="both", expand=True)

        # Log header
        log_header = tk.Frame(right, bg=BG_PANEL,
                               highlightbackground=PANEL_BORDER, highlightthickness=1)
        log_header.pack(fill="x", pady=(0, 4))
        tk.Label(log_header, text="◉  MISSION LOG", font=("Courier New", 11, "bold"),
                 fg=NEON_CYAN, bg=BG_PANEL, pady=8).pack(side="left", padx=14)
        tk.Label(log_header, text="SECURE CHANNEL", font=("Courier New", 8),
                 fg=TEXT_DIM, bg=BG_PANEL).pack(side="right", padx=14)

        # Log area
        self.log = scrolledtext.ScrolledText(
            right, bg="#010c18", fg=TEXT_MAIN,
            font=("Courier New", 10), wrap="word",
            bd=0, relief="flat", insertbackground=NEON_CYAN,
            selectbackground=NEON_BLUE,
            highlightbackground=PANEL_BORDER, highlightthickness=1,
            state="disabled"
        )
        self.log.pack(fill="both", expand=True)

        # Tag styles
        self.log.tag_config("user", foreground=NEON_GREEN)
        self.log.tag_config("edith", foreground=NEON_CYAN)
        self.log.tag_config("time", foreground=TEXT_DIM)
        self.log.tag_config("sep", foreground="#0a2a3c")

        # Input area
        input_frame = tk.Frame(right, bg=BG_PANEL,
                                highlightbackground=NEON_CYAN, highlightthickness=1)
        input_frame.pack(fill="x", pady=(8, 0))

        tk.Label(input_frame, text="›", font=("Courier New", 16, "bold"),
                 fg=NEON_CYAN, bg=BG_PANEL).pack(side="left", padx=8)

        self.entry = tk.Entry(input_frame, font=("Courier New", 12),
                               fg=TEXT_MAIN, bg=BG_PANEL,
                               insertbackground=NEON_CYAN,
                               relief="flat", bd=0)
        self.entry.pack(side="left", fill="both", expand=True, pady=12)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Up>", self._history_up)
        self.entry.bind("<Down>", self._history_down)
        self.entry.focus_set()

        tk.Button(input_frame, text="SEND ▶",
                  font=("Courier New", 10, "bold"),
                  fg=BG_DEEP, bg=NEON_CYAN,
                  activebackground=NEON_BLUE, activeforeground="white",
                  relief="flat", cursor="hand2", bd=0, padx=16,
                  command=self._on_send
                  ).pack(side="right", padx=8, pady=6)

        # Command history
        self._history = []
        self._history_idx = -1

        # ── Bottom bar ────────────────────────────────────────────────────────
        tk.Frame(self.root, bg=NEON_CYAN, height=1).pack(fill="x")
        bottom = tk.Frame(self.root, bg=BG_PANEL, height=28)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)
        tk.Label(bottom, text="  EDITH v2.0  |  Enhanced Defence Intelligence Tactical Hub  |  All systems nominal",
                 font=("Courier New", 8), fg=TEXT_DIM, bg=BG_PANEL).pack(side="left", pady=6)
        sr_status = "VOICE: ONLINE" if SR_AVAILABLE else "VOICE: INSTALL speech_recognition"
        tk.Label(bottom, text=f"{sr_status}  ",
                 font=("Courier New", 8), fg=NEON_GREEN if SR_AVAILABLE else NEON_RED,
                 bg=BG_PANEL).pack(side="right", pady=6)

    # ── Orb drawing ───────────────────────────────────────────────────────────
    def _draw_orb_static(self):
        cx, cy, r = 140, 140, 90
        c = self.orb_canvas
        c.delete("all")

        # Outer rings
        for i, (rad, col, w) in enumerate([
            (115, "#003344", 1), (105, "#004466", 1),
            (r+8, "#006688", 1),
        ]):
            c.create_oval(cx-rad, cy-rad, cx+rad, cy+rad,
                          outline=col, width=w, tags="ring")

        # Glow layers
        for off, col in [(25, "#001a2e"), (18, "#002a44"), (10, "#003a5c"), (4, "#004a6e")]:
            c.create_oval(cx-(r+off), cy-(r+off), cx+(r+off), cy+(r+off),
                          fill=col, outline="", tags="glow")

        # Core orb gradient-ish
        for off, col in [(r, "#0a3a5c"), (r-10, "#0d5a8c"), (r-22, "#0f7aac"),
                          (r-36, "#12a0d0"), (r-50, "#15c8f0"), (r-62, "#18e8ff")]:
            c.create_oval(cx-off, cy-off, cx+off, cy+off,
                          fill=col, outline="", tags="core")

        # Inner bright spot
        c.create_oval(cx-20, cy-30, cx+20, cy+10,
                      fill="#80f8ff", outline="", tags="spot")

        # Crosshair lines
        for pts, col in [
            ([(cx, cy-115), (cx, cy-r-8)], "#004466"),
            ([(cx, cy+r+8), (cx, cy+115)], "#004466"),
            ([(cx-115, cy), (cx-r-8, cy)], "#004466"),
            ([(cx+r+8, cy), (cx+115, cy)], "#004466"),
        ]:
            c.create_line(*pts[0], *pts[1], fill=col, width=1, tags="cross")

        # Text label
        c.create_text(cx, cy+r+28, text="NEURAL CORE", font=("Courier New", 8, "bold"),
                      fill=TEXT_DIM, tags="label")

        # Orbiting dots (static initial positions)
        self._orb_dots = []
        for angle_deg in [0, 120, 240]:
            rad = math.radians(angle_deg)
            ox = cx + 108 * math.cos(rad)
            oy = cy + 108 * math.sin(rad)
            dot = c.create_oval(ox-5, oy-5, ox+5, oy+5,
                                fill=NEON_CYAN, outline="", tags="dot")
            self._orb_dots.append(dot)

        self._orb_cx = cx
        self._orb_cy = cy

    def _animate_orb(self):
        self.orb_angle = (self.orb_angle + 1.5) % 360
        c = self.orb_canvas
        cx, cy = self._orb_cx, self._orb_cy

        # Move orbiting dots
        for i, dot in enumerate(self._orb_dots):
            angle_deg = self.orb_angle + i * 120
            rad = math.radians(angle_deg)
            ox = cx + 108 * math.cos(rad)
            oy = cy + 108 * math.sin(rad)
            c.coords(dot, ox-5, oy-5, ox+5, oy+5)

        # Pulse the inner bright spot
        pulse = abs(math.sin(math.radians(self.orb_angle * 2)))
        r = int(15 + 8 * pulse)
        c.coords("spot", cx-r, cy-r-10, cx+r, cy+r-10)

        # Flicker colour of dots
        col = NEON_CYAN if random.random() > 0.05 else GOLD
        for dot in self._orb_dots:
            c.itemconfig(dot, fill=col)

    def _animate_wave(self):
        self.wave_phase += 0.18
        speaking = self._status_text.get() == "SPEAKING"
        listening = self._status_text.get() == "LISTENING"

        for i in range(len(self.wave_points)):
            base = math.sin(self.wave_phase + i * 0.25) * (18 if speaking else (10 if listening else 3))
            noise = random.uniform(-2, 2) if (speaking or listening) else 0
            self.wave_points[i] = base + noise

        c = self.wave_canvas
        c.delete("all")
        W, H, CY = 280, 70, 35
        col = (NEON_GREEN if speaking else (NEON_CYAN if listening else TEXT_DIM))
        step = W / len(self.wave_points)

        pts = []
        for i, v in enumerate(self.wave_points):
            pts.extend([i * step, CY - v])

        if len(pts) >= 4:
            c.create_line(*pts, fill=col, width=2, smooth=True)

        # Centre line
        c.create_line(0, CY, W, CY, fill="#0a1e2e", width=1)

    # ── Animations ────────────────────────────────────────────────────────────
    def _start_animations(self):
        def loop():
            self._animate_orb()
            self._animate_wave()
            self._anim_after = self.root.after(40, loop)
        loop()

    def _update_clock(self):
        now = datetime.datetime.now()
        self.clock_var.set(now.strftime("  %H:%M:%S  |  %a %d %b %Y  "))
        self._clock_after = self.root.after(1000, self._update_clock)

    # ── Status ────────────────────────────────────────────────────────────────
    def set_status(self, text, color=TEXT_DIM):
        self._status_text.set(text)
        self.status_label.configure(fg=color)

    # ── Log ──────────────────────────────────────────────────────────────────
    def add_log(self, sender, message, speak_it=False):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"\n[{ts}] ", "time")
        if sender == "YOU":
            self.log.insert("end", f"YOU  › ", "user")
            self.log.insert("end", f"{message}\n", "user")
        else:
            self.log.insert("end", f"EDITH › ", "edith")
            self.log.insert("end", f"{message}\n")
        self.log.insert("end", "─" * 72 + "\n", "sep")
        self.log.configure(state="disabled")
        self.log.see("end")

        if speak_it:
            speak(message, self)

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ── Greet ─────────────────────────────────────────────────────────────────
    def _greet(self):
        hour = datetime.datetime.now().hour
        g = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
        msg = (f"{g}, sir! I am EDITH — Enhanced Defence Intelligence Tactical Hub. "
               "All systems are online and ready. How may I assist you today?")
        self.add_log("EDITH", msg, speak_it=True)

    # ── Input handlers ────────────────────────────────────────────────────────
    def _on_enter(self, event=None):
        self._on_send()

    def _on_send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._history.append(text)
        self._history_idx = len(self._history)
        self._send_command(text)

    def _send_command(self, text):
        self.add_log("YOU", text)
        self.set_status("THINKING…", GOLD)
        def _process():
            response = self.brain.process(text)
            self.root.after(0, lambda: self.add_log("EDITH", response, speak_it=True))
            self.root.after(0, lambda: self.set_status("IDLE", TEXT_DIM))
        threading.Thread(target=_process, daemon=True).start()

    def _history_up(self, event=None):
        if self._history and self._history_idx > 0:
            self._history_idx -= 1
            self.entry.delete(0, "end")
            self.entry.insert(0, self._history[self._history_idx])

    def _history_down(self, event=None):
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self.entry.delete(0, "end")
            self.entry.insert(0, self._history[self._history_idx])
        else:
            self._history_idx = len(self._history)
            self.entry.delete(0, "end")

    # ── Voice ─────────────────────────────────────────────────────────────────
    def _toggle_voice(self):
        if not SR_AVAILABLE:
            self.add_log("EDITH", "⚠️ Voice recognition unavailable. Please run:\n  pip install SpeechRecognition pyaudio")
            return
        if self.listening:
            self.listening = False
            self.voice_btn.configure(text="🎙  ACTIVATE VOICE", bg=NEON_CYAN, fg=BG_DEEP)
            self.set_status("IDLE", TEXT_DIM)
        else:
            self.listening = True
            self.voice_btn.configure(text="⏹  STOP LISTENING", bg=NEON_RED, fg="white")
            self.set_status("LISTENING", NEON_CYAN)
            threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.8)
            while self.listening:
                try:
                    self.set_status("LISTENING", NEON_CYAN)
                    audio = r.listen(source, timeout=5, phrase_time_limit=10)
                    self.set_status("PROCESSING VOICE…", GOLD)
                    text = r.recognize_google(audio)
                    self.root.after(0, lambda t=text: self._send_command(t))
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self.root.after(0, lambda: self.add_log("EDITH", "🎙 I didn't catch that. Please try again."))
                except Exception as e:
                    self.root.after(0, lambda: self.set_status("IDLE", TEXT_DIM))
                    break
        self.listening = False
        self.root.after(0, lambda: self.voice_btn.configure(text="🎙  ACTIVATE VOICE", bg=NEON_CYAN, fg=BG_DEEP))
        self.root.after(0, lambda: self.set_status("IDLE", TEXT_DIM))

    # ── Run ───────────────────────────────────────────────────────────────────
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self.listening = False
        if self._anim_after:
            self.root.after_cancel(self._anim_after)
        if self._clock_after:
            self.root.after_cancel(self._clock_after)
        self.root.destroy()


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = EDITHApp()
    app.run()
