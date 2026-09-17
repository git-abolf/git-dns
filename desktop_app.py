import customtkinter as ctk
import subprocess
import threading
import dns.resolver
import json
import os
import sys
import time
import random
import re
import urllib.request
import webbrowser
import winreg
import winsound
from datetime import datetime
from tkinter import messagebox
from tkinter import colorchooser
from PIL import Image, ImageDraw
import pystray
try:
    import keyring
except ImportError:
    keyring = None
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from app.core.logger import get_logger
from app.platform import windows_dns

log = get_logger("desktop")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

APP_NAME = "DNS Master Pro"
VERSION = "15.0.0 Global AI Edition"
# PyInstaller unpacks `datas` next to sys._MEIPASS at runtime; when running
# from source, assets/ simply lives at the project root.
_BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ASSETS_DIR = os.path.join(_BASE_DIR, "assets")
ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")
TRAY_ICON_PNG = os.path.join(ASSETS_DIR, "tray_icon.png")
APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DNSMasterPro")
os.makedirs(APP_DATA_DIR, exist_ok=True)
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "dns_settings.json")
PROFILES_FILE = os.path.join(APP_DATA_DIR, "dns_profiles.json")
HISTORY_FILE = os.path.join(APP_DATA_DIR, "dns_history.json")
LIVE_FILE = os.path.join(APP_DATA_DIR, "live_dns.json")
TELEGRAM_SUPPORT = "@Abolf_85_i"
STARTUP_NAME = "DNSMasterPro"
KEYRING_SERVICE = "DNSMasterPro"
DEFAULT_AI_MODEL = "gpt-5.5"
UPDATE_REPO = os.environ.get("DNS_MASTER_PRO_UPDATE_REPO", "")  # e.g. owner/repository

TRUSTED_URLS = [
    "https://raw.githubusercontent.com/pingproxies/public-dns-directory/main/resolvers/global/trusted.txt",
    "https://raw.githubusercontent.com/trickest/resolvers/main/resolvers-trusted.txt",
]

class DNSMasterFinal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  •  {VERSION}")
        self.geometry("1220x780")
        self.minsize(1120, 720)
        self.configure(fg_color="#05050a")
        try:
            if os.path.exists(ICON_ICO):
                self.iconbitmap(ICON_ICO)
        except Exception as exc:
            log.warning("Could not set window icon: %s", exc)

        self.is_admin = self.check_admin()
        self.is_online = False
        self.running = True
        self.live_active = False
        self.live_list = self.load_json(LIVE_FILE, [])
        self.history = self.load_json(HISTORY_FILE, [])
        self.last_live = "—"
        self.tray_icon = None

        # تنظیمات کاربر؛ در فایل محلی ذخیره می‌شوند
        self.settings = self.load_json(SETTINGS_FILE, {
            "theme": "آبی فیروزه‌ای",
            "first_name": "",
            "last_name": "",
            "phone": "",
            "email": "",
            "sound": True,
            "minimize_to_tray": True,
            "ai_enabled": True,
            "ai_model": DEFAULT_AI_MODEL,
            "ai_web_search": False,
        })
        self.sound_enabled = bool(self.settings.get("sound", True))
        self.theme_name = self.settings.get("theme", "آبی فیروزه‌ای")
        self.theme_colors = {
            "آبی فیروزه‌ای": "#00e5ff",
            "بنفش": "#7c4dff",
            "صورتی": "#ff4081",
            "قرمز": "#ff5252",
            "نارنجی": "#ff9800",
            "سبز": "#00c853",
            "آبی": "#2979ff",
            "طلایی": "#ffc107",
            "صورتی تیره": "#e040fb",
            "سبزآبی": "#00bfa5",
            "سفید": "#ffffff",
            "مشکی": "#000000",
            "خاکستری روشن": "#b0bec5",
            "خاکستری تیره": "#37474f",
            "خاکستری فولادی": "#607d8b",
            "نقره‌ای": "#cfd8dc",
            "قرمز تیره": "#c62828",
            "قرمز آجری": "#d84315",
            "صورتی کم‌رنگ": "#f48fb1",
            "گلبهی": "#ff8a65",
            "صورتی توت‌فرنگی": "#ff1744",
            "قرمز گلبهی": "#ff5c8d",
            "نارنجی تیره": "#e65100",
            "کهربایی": "#ffab00",
            "زرد": "#ffeb3b",
            "زرد لیمویی": "#cddc39",
            "سبز لیمویی": "#aeea00",
            "سبز چمنی": "#4caf50",
            "سبز جنگلی": "#2e7d32",
            "سبز نعنایی": "#1de9b6",
            "سبز زمردی": "#00e676",
            "سبز استخری": "#009688",
            "فیروزه‌ای تیره": "#00838f",
            "آبی آسمانی": "#29b6f6",
            "آبی روشن": "#40c4ff",
            "آبی نفتی": "#01579b",
            "آبی دریایی": "#006064",
            "آبی سلطنتی": "#304ffe",
            "نیلی": "#3d5afe",
            "سرمه‌ای": "#1a237e",
            "بنفش روشن": "#b388ff",
            "بنفش تیره": "#6200ea",
            "ارغوانی": "#aa00ff",
            "یاسی": "#ce93d8",
            "قهوه‌ای": "#795548",
            "قهوه‌ای روشن": "#a1887f",
            "برنزی": "#8d6e63",
            "مسی": "#b87333",
            "کرم": "#fff8e1",
            "طلایی روشن": "#ffd54f",
        }
        custom_hex = self.settings.get("custom_theme_hex", "")
        if custom_hex:
            self.theme_colors["رنگ سفارشی"] = custom_hex
        if self.theme_name not in self.theme_colors:
            self.theme_name = "آبی فیروزه‌ای"
        self.accent_color = self.theme_colors[self.theme_name]

        self.presets = {
            "Cloudflare": {"ipv4": ["1.1.1.1", "1.0.0.1"], "ipv6": ["2606:4700:4700::1111", "2606:4700:4700::1001"], "score": 96},
            "Google": {"ipv4": ["8.8.8.8", "8.8.4.4"], "ipv6": ["2001:4860:4860::8888", "2001:4860:4860::8844"], "score": 92},
            "Shecan": {"ipv4": ["178.22.122.100", "185.51.200.2"], "ipv6": [], "score": 98},
            "403.online": {"ipv4": ["10.202.10.202", "10.202.10.102"], "ipv6": [], "score": 94},
            "Radar Game": {"ipv4": ["10.202.10.10", "10.202.10.11"], "ipv6": [], "score": 95},
            "Quad9": {"ipv4": ["9.9.9.9", "149.112.112.112"], "ipv6": ["2620:fe::fe", "2620:fe::9"], "score": 93},
            "AdGuard": {"ipv4": ["94.140.14.14", "94.140.15.15"], "ipv6": ["2a10:50c0::ad1:ff", "2a10:50c0::ad2:ff"], "score": 90},
            "OpenDNS": {"ipv4": ["208.67.222.222", "208.67.220.220"], "ipv6": ["2620:119:35::35", "2620:119:53::53"], "score": 88},
            "CleanBrowsing": {"ipv4": ["185.228.168.9", "185.228.169.9"], "ipv6": ["2a0d:2a00:1::2", "2a0d:2a00:2::2"], "score": 87},
            "Control D": {"ipv4": ["76.76.2.0", "76.76.10.0"], "ipv6": ["2606:1a40::", "2606:1a40:1::"], "score": 89},
            "Mullvad": {"ipv4": ["194.242.2.2", "194.242.2.3"], "ipv6": ["2a07:e340::2", "2a07:e340::3"], "score": 86},
            "DNS4EU": {"ipv4": ["86.54.11.1", "86.54.11.201"], "ipv6": ["2a13:1001::86:54:11:1", "2a13:1001::86:54:11:201"], "score": 85},
            "Custom IPv6": {"ipv4": [], "ipv6": ["2a02:4799:ec6f:761e:e06d:7f8e:9c7e:b3f0"], "score": 80},
        }

        self.game_plans = {
            "Valorant": ["Cloudflare", "Radar Game"],
            "CS2": ["Cloudflare", "Google"],
            "Fortnite": ["Cloudflare", "Google"],
            "GTA Online": ["Cloudflare", "Shecan"],
            "League of Legends": ["Cloudflare", "Google"],
            "Apex Legends": ["Cloudflare", "Quad9"],
            "Warzone": ["Cloudflare", "Radar Game"],
            "PUBG": ["Shecan", "403.online"],
            "Roblox": ["Cloudflare", "Google"],
            "Minecraft": ["Cloudflare", "Google"],
            "Free Fire": ["Shecan", "Radar Game"],
            "Call of Duty Mobile": ["Cloudflare", "Radar Game"],
            "Dota 2": ["Cloudflare", "Google"],
            "Overwatch 2": ["Cloudflare", "Google"],
            "Rocket League": ["Cloudflare", "Google"],
            "Rainbow Six Siege": ["Cloudflare", "Quad9"],
            "FIFA / EA FC": ["Cloudflare", "Shecan"],
            "Genshin Impact": ["Cloudflare", "Google"],
        }

        self.doh_providers = {
            "Cloudflare DoH": "https://cloudflare-dns.com/dns-query",
            "Google DoH": "https://dns.google/dns-query",
            "Quad9 DoH": "https://dns.quad9.net/dns-query",
            "AdGuard DoH": "https://dns.adguard.com/dns-query",
            "NextDNS": "https://dns.nextdns.io",
        }

        self.build_ui()
        self._theme_widgets(self, self.accent_color)
        self.start_services()
        self.setup_tray()
        self.show_dashboard()
        threading.Thread(target=self.background_worker, daemon=True).start()

    def play_click(self):
        if not self.sound_enabled:
            return
        try:
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except:
            try:
                winsound.Beep(800, 40)
            except:
                pass

    def build_ui(self):
        # Header
        header = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#0a0a12")
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="⚡ DNS Master Pro", font=("Segoe UI", 22, "bold"),
                     text_color="#00f5ff").pack(side="left", padx=22, pady=16)

        self.live_label = ctk.CTkLabel(header, text="● LIVE", font=("Segoe UI", 12, "bold"), text_color="#00e676")
        self.live_label.pack(side="left", padx=8)

        self.profile_label = ctk.CTkLabel(header, text=self.profile_display_name(), font=("Segoe UI", 12, "bold"), text_color="#aaa")
        self.profile_label.pack(side="left", padx=10)

        self.clock = ctk.CTkLabel(header, text="", font=("Consolas", 14), text_color="#888")
        self.clock.pack(side="left", padx=14)

        self.online_label = ctk.CTkLabel(header, text="", font=("Segoe UI", 12))
        self.online_label.pack(side="right", padx=14)

        self.admin_label = ctk.CTkLabel(header, text="", font=("Segoe UI", 12, "bold"))
        self.admin_label.pack(side="right", padx=10)
        self.update_admin()

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = ctk.CTkFrame(body, width=245, corner_radius=0, fg_color="#0b0b14")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        menus = [
            ("🏠   داشبورد", self.show_dashboard),
            ("🔥   Live Hunter", self.show_live),
            ("🎮   پلن بازی‌ها", self.show_games),
            ("📋   DNS آماده", self.show_presets),
            ("🔒   DNS over HTTPS", self.show_doh),
            ("🛡️   VPN / WireGuard", self.show_vpn),
            ("🤖   دستیار AI", self.show_ai),
            ("➕   دستی", self.show_custom),
            ("🧪   تست", self.show_test),
            ("🛠️   ابزارها", self.show_tools),
            ("⚙️   تنظیمات", self.show_settings),
            ("📜   تاریخچه", self.show_history),
            ("💬   پشتیبانی", self.show_support),
        ]
        for text, cmd in menus:
            btn = ctk.CTkButton(
                self.sidebar, text=text, command=lambda c=cmd: self.menu_click(c),
                height=44, font=("Segoe UI", 14), anchor="w",
                fg_color="transparent", text_color="#c8c8d0",
                hover_color="#16162a", corner_radius=10,
                border_width=0
            )
            btn.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(self.sidebar, text="آداپتر شبکه", font=("Segoe UI", 12), text_color="#666").pack(pady=(18, 4), padx=14, anchor="w")
        self.adapter_var = ctk.StringVar(value="...")
        self.adapter_menu = ctk.CTkOptionMenu(self.sidebar, variable=self.adapter_var, values=["..."], height=34,
                                              fg_color="#16162a", button_color="#1e1e35", button_hover_color="#2a2a4a")
        self.adapter_menu.pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(self.sidebar, text="↻  تازه‌سازی", command=self.refresh_adapters,
                      height=32, fg_color="#16162a", hover_color="#252545", corner_radius=8).pack(fill="x", padx=12, pady=8)

        # Content
        self.content = ctk.CTkFrame(body, fg_color="#07070f")
        self.content.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        # Status bar
        self.status = ctk.CTkLabel(self, text="  سیستم آماده است", height=28, font=("Segoe UI", 12),
                                   text_color="#777", anchor="w", fg_color="#0a0a12")
        self.status.pack(fill="x", side="bottom")

    def menu_click(self, cmd):
        self.play_click()
        cmd()

    def clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def set_status(self, txt):
        self.status.configure(text=f"  {txt}  •  {datetime.now().strftime('%H:%M:%S')}")

    def start_services(self):
        self.update_clock()
        self.blink()
        self.check_net()
        self.refresh_adapters()

    def update_clock(self):
        if self.running:
            self.clock.configure(text=datetime.now().strftime("%Y-%m-%d   %H:%M:%S"))
            self.after(1000, self.update_clock)

    def blink(self):
        if self.running:
            c = self.live_label.cget("text_color")
            self.live_label.configure(text_color="#00e676" if c == "#004d00" else "#004d00")
            self.after(750, self.blink)

    def check_net(self):
        def w():
            while self.running:
                try:
                    urllib.request.urlopen("https://www.google.com", timeout=3)
                    self.is_online = True
                    self.online_label.configure(text="● Online", text_color="#00e676")
                except:
                    self.is_online = False
                    self.online_label.configure(text="● Offline", text_color="#ff5252")
                time.sleep(12)
        threading.Thread(target=w, daemon=True).start()

    def background_worker(self):
        while self.running:
            time.sleep(300)
            if self.live_active and self.is_online:
                self.fetch_live()

    def setup_tray(self):
        def create_image():
            if os.path.exists(TRAY_ICON_PNG):
                try:
                    return Image.open(TRAY_ICON_PNG).convert("RGBA")
                except Exception as exc:
                    log.warning("Could not load tray icon asset, using fallback: %s", exc)
            # Fallback: draw a simple placeholder if the asset is missing.
            img = Image.new('RGB', (64, 64), color=(10, 10, 18))
            d = ImageDraw.Draw(img)
            d.ellipse([6, 6, 58, 58], fill=(0, 245, 255))
            d.ellipse([18, 18, 46, 46], fill=(10, 10, 18))
            return img

        menu = pystray.Menu(
            pystray.MenuItem("نمایش برنامه", self.show_from_tray),
            pystray.MenuItem("مخفی کردن", self.hide_to_tray),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("خروج", self.quit_app)
        )
        self.tray_icon = pystray.Icon("DNSMaster", create_image(), "DNS Master Pro", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)

    def hide_to_tray(self, icon=None, item=None):
        self.withdraw()

    def quit_app(self, icon=None, item=None):
        self.running = False
        self.live_active = False
        self.save_settings()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

    def on_close(self):
        if bool(self.settings.get("minimize_to_tray", True)):
            self.hide_to_tray()
        else:
            self.quit_app()

    # ==================== DASHBOARD ====================
    def show_dashboard(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(main, text="داشبورد", font=("Segoe UI", 26, "bold"), text_color="#eee").pack(anchor="w", pady=(0, 12))

        cards = ctk.CTkFrame(main, fg_color="transparent")
        cards.pack(fill="x")
        self.make_card(cards, "دسترسی", "Admin" if self.is_admin else "عادی",
                       "#00e676" if self.is_admin else "#ff6b35").pack(side="left", expand=True, fill="both", padx=(0, 8))
        self.make_card(cards, "Live DNS", str(len(self.live_list)), "#00e5ff").pack(side="left", expand=True, fill="both", padx=8)
        self.make_card(cards, "وضعیت", "LIVE", "#7c4dff").pack(side="left", expand=True, fill="both", padx=(8, 0))

        ctk.CTkLabel(main, text="DNS فعلی سیستم", font=("Segoe UI", 15, "bold"), text_color="#ccc").pack(anchor="w", pady=(20, 8))
        self.dns_box = ctk.CTkTextbox(main, height=210, font=("Consolas", 12), fg_color="#0c0c16",
                                      border_width=1, border_color="#1a1a2e", corner_radius=10)
        self.dns_box.pack(fill="x")
        self.show_current_dns()

        q = ctk.CTkFrame(main, fg_color="transparent")
        q.pack(fill="x", pady=16)
        self.premium_btn(q, "🇮🇷  Shecan", lambda: self.apply_preset("Shecan"), "#00c853").pack(side="left", padx=5)
        self.premium_btn(q, "⚡  Cloudflare", lambda: self.apply_preset("Cloudflare"), "#0090e0").pack(side="left", padx=5)
        self.premium_btn(q, "🔄  DHCP", self.reset_dhcp, "#ff6b35").pack(side="left", padx=5)
        self.premium_btn(q, "🧹  Flush", self.flush, "#2a2a4a").pack(side="left", padx=5)

    def make_card(self, parent, title, value, color):
        f = ctk.CTkFrame(parent, height=90, fg_color="#0f0f1a", border_width=1, border_color="#1f1f35", corner_radius=12)
        f.pack_propagate(False)
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 13), text_color="#888").pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(f, text=value, font=("Segoe UI", 20, "bold"), text_color=color).pack(anchor="w", padx=16, pady=(4, 0))
        return f

    def premium_btn(self, parent, text, command, color):
        return ctk.CTkButton(parent, text=text, command=lambda: self.btn_click(command), height=42,
                             fg_color=color, hover_color=self.darken(color), corner_radius=10,
                             font=("Segoe UI", 14, "bold"), border_width=0)

    def darken(self, hex_color, factor=0.78):
        return self._scale_color(hex_color, factor)

    def lighten(self, hex_color, amount=0.35):
        # Blend toward white (additive) rather than multiply, so this also
        # works on pure black (0 * anything is still 0).
        try:
            hex_color = hex_color.lstrip("#")
            r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            r, g, b = (max(0, min(255, round(c + (255 - c) * amount))) for c in (r, g, b))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color if hex_color.startswith("#") else f"#{hex_color}"

    def _scale_color(self, hex_color, factor):
        try:
            hex_color = hex_color.lstrip("#")
            r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            r, g, b = (max(0, min(255, int(c * factor))) for c in (r, g, b))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color if hex_color.startswith("#") else f"#{hex_color}"

    def hover_variant(self, hex_color):
        # Very dark accents (e.g. black) barely change with darken(), so
        # lighten instead; everything else gets the usual subtle darken.
        if self._luminance(hex_color) < 0.12:
            return self.lighten(hex_color, 0.18)
        return self.darken(hex_color)

    def _luminance(self, hex_color):
        try:
            hex_color = hex_color.lstrip("#")
            r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        except Exception:
            return 0.5

    def contrast_text(self, hex_color):
        return "#111111" if self._luminance(hex_color) > 0.6 else "#ffffff"

    def btn_click(self, cmd):
        self.play_click()
        cmd()

    # ==================== Online AI ====================
    def show_ai(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)

        head = ctk.CTkFrame(main, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text="🤖  DNS Master Pro AI", font=("Segoe UI", 24, "bold")).pack(side="left")
        self.ai_status_label = ctk.CTkLabel(head, text=self.ai_connection_status(), font=("Segoe UI", 12, "bold"))
        self.ai_status_label.pack(side="right", padx=8)
        ctk.CTkLabel(main, text="دستیار آنلاین برای تحلیل DNS، شبکه و تنظیمات برنامه. برای پاسخ آنلاین به کلید API نیاز است.",
                     font=("Segoe UI", 13), text_color="#888").pack(anchor="w", pady=(4, 12))

        self.ai_box = ctk.CTkTextbox(main, height=400, font=("Segoe UI", 14), fg_color="#0c0c16",
                                     border_width=1, border_color="#1a1a2e", corner_radius=12)
        self.ai_box.pack(fill="both", expand=True)
        self.ai_box.insert("end", "DNS Master Pro AI آنلاین آماده است.\n\n"
                                   "از تنظیمات، کلید API را وارد کن. می‌توانی جستجوی وب را هم فعال کنی.\n"
                                   "مثال: «وضعیت DNS فعلی من را تحلیل کن» یا «برای این شبکه چه تستی انجام بدهم؟»\n")

        opts = ctk.CTkFrame(main, fg_color="transparent")
        opts.pack(fill="x", pady=(10, 0))
        self.ai_web_var = ctk.BooleanVar(value=bool(self.settings.get("ai_web_search", False)))
        ctk.CTkSwitch(opts, text="جستجوی وب برای پاسخ‌های به‌روز", variable=self.ai_web_var,
                      command=lambda: self.set_ai_web_search(self.ai_web_var.get())).pack(side="left")
        ctk.CTkButton(opts, text="⚙ تنظیم AI", width=110, height=32,
                      command=self.show_settings).pack(side="right")

        fr = ctk.CTkFrame(main, fg_color="transparent")
        fr.pack(fill="x", pady=12)
        self.ai_entry = ctk.CTkEntry(fr, height=42, placeholder_text="پیام خود را بنویس...", font=("Segoe UI", 14), corner_radius=10)
        self.ai_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.ai_entry.bind("<Return>", lambda e: self.ai_reply())
        self.ai_send_btn = ctk.CTkButton(fr, text="ارسال", width=100, height=42, corner_radius=10,
                                         fg_color="#00c853", hover_color="#00a844", font=("Segoe UI", 14, "bold"),
                                         command=self.ai_reply)
        self.ai_send_btn.pack(side="right")

    def ai_connection_status(self):
        if not self.settings.get("ai_enabled", True):
            return "● AI خاموش"
        if self.get_ai_api_key():
            return "● AI متصل"
        return "● کلید API تنظیم نشده"

    def get_ai_api_key(self):
        # کلید در Keyring ویندوز نگهداری می‌شود؛ در صورت نبود keyring، متغیر محیطی پشتیبانی می‌شود.
        if keyring:
            try:
                value = keyring.get_password(KEYRING_SERVICE, "openai_api_key")
                if value:
                    return value.strip()
            except Exception:
                pass
        return os.environ.get("OPENAI_API_KEY", "").strip()

    def save_ai_api_key(self, key):
        key = key.strip()
        if keyring:
            try:
                if key:
                    keyring.set_password(KEYRING_SERVICE, "openai_api_key", key)
                else:
                    try:
                        keyring.delete_password(KEYRING_SERVICE, "openai_api_key")
                    except Exception:
                        pass
                return True
            except Exception:
                pass
        return False

    def confirm_ai_privacy_notice(self):
        """Show a one-time notice that AI prompts leave the device and go to
        OpenAI's servers. Returns True if the user may proceed."""
        if self.settings.get("ai_privacy_ack"):
            return True
        proceed = messagebox.askokcancel(
            "حریم خصوصی هوش مصنوعی",
            "وقتی از «هوش مصنوعی آنلاین» استفاده می‌کنی، متن پیامت برای پاسخ‌گویی "
            "به سرورهای OpenAI ارسال می‌شود (طبق سیاست حریم خصوصی OpenAI پردازش می‌شود).\n\n"
            "این پیام فقط یک‌بار نمایش داده می‌شود. برای ادامه OK را بزن.",
        )
        if proceed:
            self.settings["ai_privacy_ack"] = True
            self.save_settings()
        return proceed

    def ai_reply(self):
        q = self.ai_entry.get().strip()
        if not q:
            return
        if not self.confirm_ai_privacy_notice():
            return
        self.play_click()
        self.ai_box.insert("end", f"\n👤 شما: {q}\n")
        self.ai_entry.delete(0, "end")
        self.ai_send_btn.configure(state="disabled", text="در حال پاسخ...")
        threading.Thread(target=self._online_ai_worker, args=(q,), daemon=True).start()

    def _online_ai_worker(self, q):
        try:
            answer = self.call_online_ai(q)
        except Exception as exc:
            answer = f"خطا در AI آنلاین:\n{self.friendly_ai_error(exc)}"
        self.after(0, lambda: self._finish_ai_reply(answer))

    def _finish_ai_reply(self, answer):
        if hasattr(self, "ai_box"):
            self.ai_box.insert("end", f"🤖 DNS Master Pro AI: {answer}\n")
            self.ai_box.see("end")
        if hasattr(self, "ai_send_btn"):
            self.ai_send_btn.configure(state="normal", text="ارسال")
        if hasattr(self, "ai_status_label"):
            self.ai_status_label.configure(text=self.ai_connection_status())

    def build_ai_context(self):
        profile = self.profile_display_name()
        live = self.live_list[-8:] if isinstance(self.live_list, list) else []
        live_text = ", ".join(str(x.get("ip", "")) for x in live if isinstance(x, dict)) or "none"
        return (f"Application: DNS Master Pro {VERSION}\n"
                f"User profile: {profile}\n"
                f"Admin: {self.is_admin}\n"
                f"Online: {self.is_online}\n"
                f"Recent Live DNS4: {live_text}\n"
                "Important: DNS latency is not the same thing as game-server ping. Never claim a DNS change guarantees lower in-game ping.")

    def call_online_ai(self, question):
        if not self.settings.get("ai_enabled", True):
            return "AI آنلاین در تنظیمات خاموش است."
        if OpenAI is None:
            return "کتابخانه OpenAI نصب نیست. requirements.txt را نصب کن."
        key = self.get_ai_api_key()
        if not key:
            return "ابتدا از بخش تنظیمات، کلید API را وارد و ذخیره کن."
        client = OpenAI(api_key=key, timeout=45.0, max_retries=2)
        instructions = ("You are DNS Master Pro AI, a technical network assistant. "
                        "Answer in the user's language. Be factual and concise. "
                        "Focus on DNS, IPv4/IPv6, DNS-over-HTTPS, DNS-over-TLS, Windows networking, "
                        "benchmarking, troubleshooting and gaming connectivity. "
                        "Do not invent benchmark results. Distinguish DNS resolution latency from game-server latency. "
                        "If current information is needed and web search is enabled, use web search.\n\n"
                        f"Current application context:\n{self.build_ai_context()}")
        kwargs = {
            "model": self.settings.get("ai_model") or DEFAULT_AI_MODEL,
            "instructions": instructions,
            "input": question,
        }
        if self.settings.get("ai_web_search", False):
            kwargs["tools"] = [{"type": "web_search"}]
        response = client.responses.create(**kwargs)
        text = getattr(response, "output_text", "") or ""
        if not text:
            return "AI پاسخی برنگرداند. دوباره تلاش کن."
        return text.strip()

    def friendly_ai_error(self, exc):
        text = str(exc)
        if "401" in text or "Authentication" in text or "api_key" in text.lower():
            return "کلید API معتبر نیست یا دسترسی آن رد شده است."
        if "429" in text or "rate" in text.lower():
            return "محدودیت نرخ یا اعتبار حساب API رخ داده است."
        if "timeout" in text.lower():
            return "اتصال به سرویس AI به پایان زمان رسید. اینترنت و دسترسی API را بررسی کن."
        return text[:500]

    def set_ai_web_search(self, enabled):
        self.settings["ai_web_search"] = bool(enabled)
        self.save_settings()
        self.set_status("جستجوی وب AI " + ("روشن شد" if enabled else "خاموش شد"))

    # ==================== سایر صفحات (خلاصه برای جلوگیری از طولانی شدن) ====================
    def show_live(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        ctk.CTkLabel(main, text="🔥 Live DNS Hunter • DNS4 (IPv4)", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ctk.CTkLabel(main, text="کشف، تست و نمایش DNSهای IPv4 زنده از منابع معتبر", font=("Segoe UI", 13), text_color="#888").pack(anchor="w", pady=(4, 12))

        st = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=12, border_width=1, border_color="#1a1a2e")
        st.pack(fill="x", pady=6)
        self.live_status = ctk.CTkLabel(st, text="وضعیت: خاموش", font=("Segoe UI", 14, "bold"))
        self.live_status.pack(side="left", padx=16, pady=12)
        self.live_count = ctk.CTkLabel(st, text=f"تعداد: {len(self.live_list)}", font=("Segoe UI", 13))
        self.live_count.pack(side="left", padx=16)
        self.live_time = ctk.CTkLabel(st, text=f"آخرین: {self.last_live}", font=("Segoe UI", 12), text_color="#aaa")
        self.live_time.pack(side="right", padx=16)

        bf = ctk.CTkFrame(main, fg_color="transparent")
        bf.pack(fill="x", pady=10)
        self.live_btn = ctk.CTkButton(bf, text="▶  شروع Live Hunter", command=lambda: self.btn_click(self.toggle_live),
                                      height=42, fg_color="#00c853", hover_color="#00a844", corner_radius=10, width=180)
        self.live_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(bf, text="🔄 آپدیت الان", command=lambda: self.btn_click(self.manual_fetch), height=42, width=130, corner_radius=10).pack(side="left", padx=6)
        ctk.CTkButton(bf, text="🧹 پاک کردن", command=lambda: self.btn_click(self.clear_live), height=42, fg_color="#c62828", hover_color="#b71c1c", width=120, corner_radius=10).pack(side="left", padx=6)

        filter_frame = ctk.CTkFrame(main, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(12, 6))
        ctk.CTkLabel(filter_frame, text="DNSهای زنده:", font=("Segoe UI", 14, "bold")).pack(side="left")
        ctk.CTkLabel(filter_frame, text="  •  فقط IPv4 / DNS4", font=("Segoe UI", 12), text_color="#00e5ff").pack(side="left")
        self.live_frame = ctk.CTkScrollableFrame(main, fg_color="transparent")
        self.live_frame.pack(fill="both", expand=True)
        self.refresh_live_ui()

    def show_games(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        ctk.CTkLabel(main, text="🎮 پلن اختصاصی بازی‌ها", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 10))
        scroll = ctk.CTkScrollableFrame(main, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        colors = ["#ff4655", "#de9b35", "#9d4dbb", "#fcaf17", "#c89b3c", "#da292a", "#5cba47", "#f2a900", "#e2231a", "#5d9b3e"]
        for i, (name, _) in enumerate(self.game_plans.items()):
            card = ctk.CTkFrame(scroll, fg_color="#0f0f1a", border_width=2, border_color=colors[i % len(colors)], corner_radius=12)
            card.pack(fill="x", pady=5)
            ctk.CTkLabel(card, text=name, font=("Segoe UI", 16, "bold"), text_color=colors[i % len(colors)]).pack(side="left", padx=16, pady=14)
            ctk.CTkButton(card, text="اعمال پلن", width=110, height=36, fg_color=colors[i % len(colors)], text_color="#000",
                          hover_color="#ffffff", corner_radius=8, command=lambda n=name: self.btn_click(lambda: self.apply_game(n))).pack(side="right", padx=14)

    def show_presets(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        ctk.CTkLabel(main, text="DNSهای آماده", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 10))
        scroll = ctk.CTkScrollableFrame(main, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        for name, data in self.presets.items():
            card = ctk.CTkFrame(scroll, fg_color="#0f0f1a", border_width=1, border_color="#1a1a2e", corner_radius=12)
            card.pack(fill="x", pady=4)
            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True, padx=14, pady=10)
            ctk.CTkLabel(left, text=f"{name}  •  امتیاز {data['score']}", font=("Segoe UI", 15, "bold")).pack(anchor="w")
            ctk.CTkLabel(left, text="IPv4: " + "  •  ".join(data["ipv4"]), font=("Consolas", 12), text_color="#00e5ff").pack(anchor="w")
            if data.get("ipv6"):
                ctk.CTkLabel(left, text="IPv6: " + "  •  ".join(data["ipv6"]), font=("Consolas", 11), text_color="#7c4dff").pack(anchor="w")
            ctk.CTkButton(card, text="اعمال", width=90, height=34, corner_radius=8, hover_color="#3a3a6a",
                          command=lambda n=name: self.btn_click(lambda: self.apply_preset(n))).pack(side="right", padx=12)

    def show_doh(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        ctk.CTkLabel(main, text="🔒 DNS over HTTPS (DoH)", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(main, text="رمزنگاری کوئری‌های DNS برای حریم خصوصی بیشتر", font=("Segoe UI", 13), text_color="#888").pack(anchor="w", pady=(0, 12))
        for name, url in self.doh_providers.items():
            card = ctk.CTkFrame(main, fg_color="#0f0f1a", border_width=1, border_color="#1a1a2e", corner_radius=10)
            card.pack(fill="x", pady=5)
            ctk.CTkLabel(card, text=name, font=("Segoe UI", 14, "bold")).pack(side="left", padx=16, pady=12)
            ctk.CTkLabel(card, text=url, font=("Consolas", 12), text_color="#00e5ff").pack(side="left", padx=10)
            ctk.CTkButton(card, text="کپی", width=80, height=32, corner_radius=8, command=lambda u=url: self.btn_click(lambda: self.copy_text(u))).pack(side="right", padx=12)

    def show_custom(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        ctk.CTkLabel(main, text="اضافه کردن دستی DNS", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 14))
        form = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=12)
        form.pack(fill="x")
        self.e1 = ctk.CTkEntry(form, width=300, height=38, placeholder_text="DNS4 / IPv4 اولیه (مثلاً 1.1.1.1)", corner_radius=8)
        self.e1.pack(padx=20, pady=(16, 8))
        self.e2 = ctk.CTkEntry(form, width=300, height=38, placeholder_text="DNS4 / IPv4 ثانویه (اختیاری)", corner_radius=8)
        self.e2.pack(padx=20, pady=8)
        self.e6_1 = ctk.CTkEntry(form, width=300, height=38, placeholder_text="IPv6 اولیه (اختیاری)", corner_radius=8)
        self.e6_1.pack(padx=20, pady=8)
        self.e6_2 = ctk.CTkEntry(form, width=300, height=38, placeholder_text="IPv6 ثانویه (اختیاری)", corner_radius=8)
        self.e6_2.pack(padx=20, pady=(8, 16))
        ctk.CTkButton(main, text="اعمال DNS", command=lambda: self.btn_click(self.apply_custom), height=44, fg_color="#00c853",
                      hover_color="#00a844", width=160, corner_radius=10, font=("Segoe UI", 15, "bold")).pack(pady=16)

    def show_test(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        ctk.CTkLabel(main, text="تست و آنالیز", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 10))
        self.test_box = ctk.CTkTextbox(main, height=430, font=("Consolas", 13), fg_color="#0c0c16", corner_radius=12)
        self.test_box.pack(fill="both", expand=True)
        bf = ctk.CTkFrame(main, fg_color="transparent")
        bf.pack(pady=12)
        ctk.CTkButton(bf, text="تست Resolve", command=lambda: self.btn_click(self.test_resolve), width=150, height=40, corner_radius=10).pack(side="left", padx=6)
        ctk.CTkButton(bf, text="تست سرعت کامل", command=lambda: self.btn_click(self.test_speed), width=170, height=40, fg_color="#7c4dff", hover_color="#6a5acd", corner_radius=10).pack(side="left", padx=6)

    def show_tools(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        ctk.CTkLabel(main, text="ابزارها", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 14))
        for t, c in [("🧹  Flush DNS Cache", self.flush), ("🔄  بازگشت به DHCP", self.reset_dhcp),
                     ("📋  کپی وضعیت کامل", self.copy_status), ("📌  مخفی کردن در System Tray", self.hide_to_tray)]:
            ctk.CTkButton(main, text=t, command=lambda cmd=c: self.btn_click(cmd), height=48, anchor="w",
                          fg_color="#0f0f1a", hover_color="#1a1a2e", border_width=1, border_color="#1a1a2e",
                          corner_radius=10, font=("Segoe UI", 14)).pack(fill="x", pady=5)

    def show_settings(self):
        self.clear()
        main = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(main, text="⚙️ تنظیمات", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(main, text="شخصی‌سازی ظاهر، پروفایل و رفتار برنامه", font=("Segoe UI", 13), text_color="#888").pack(anchor="w", pady=(0, 12))

        # ---------- تم ----------
        theme_frame = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=12, border_width=1, border_color="#1a1a2e")
        theme_frame.pack(fill="x", pady=7)
        ctk.CTkLabel(theme_frame, text="🎨 رنگ تم برنامه", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(theme_frame, text=f"یکی از {len(self.theme_colors)} رنگ را انتخاب کن، یا با «رنگ سفارشی» هر رنگی که خواستی بساز؛ انتخابت ذخیره می‌شود.",
                     font=("Segoe UI", 12), text_color="#888").pack(anchor="w", padx=16)
        theme_var = ctk.StringVar(value=self.theme_name)
        theme_menu = ctk.CTkOptionMenu(theme_frame, variable=theme_var, values=list(self.theme_colors.keys()), height=40, width=250,
                                       fg_color="#16162a", button_color=self.accent_color, button_hover_color=self.hover_variant(self.accent_color),
                                       text_color=self.contrast_text(self.accent_color))
        theme_menu.pack(anchor="w", padx=16, pady=(10, 14))
        theme_btns = ctk.CTkFrame(theme_frame, fg_color="transparent")
        theme_btns.pack(anchor="w", padx=16, pady=(0, 14))
        ctk.CTkButton(theme_btns, text="اعمال رنگ تم", height=38, width=150, corner_radius=8,
                      fg_color=self.accent_color, hover_color=self.hover_variant(self.accent_color), text_color=self.contrast_text(self.accent_color),
                      command=lambda: self.apply_theme(theme_var.get())).pack(side="left", padx=(0, 8))
        ctk.CTkButton(theme_btns, text="🎨 رنگ سفارشی...", height=38, width=150, corner_radius=8,
                      fg_color="#2a2a4a", hover_color="#34345a",
                      command=self.pick_custom_color).pack(side="left")

        # ---------- پروفایل ----------
        profile_frame = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=12, border_width=1, border_color="#1a1a2e")
        profile_frame.pack(fill="x", pady=7)
        ctk.CTkLabel(profile_frame, text="👤 پروفایل کاربر", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(profile_frame, text="اطلاعات فقط به‌صورت محلی در تنظیمات برنامه ذخیره می‌شوند.", font=("Segoe UI", 12), text_color="#888").pack(anchor="w", padx=16, pady=(0, 10))

        form = ctk.CTkFrame(profile_frame, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=(0, 10))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(2, weight=1)
        form.grid_columnconfigure(3, weight=1)

        first_var = ctk.StringVar(value=self.settings.get("first_name", ""))
        last_var = ctk.StringVar(value=self.settings.get("last_name", ""))
        phone_var = ctk.StringVar(value=self.settings.get("phone", ""))
        email_var = ctk.StringVar(value=self.settings.get("email", ""))

        fields = [("نام", first_var), ("نام خانوادگی", last_var), ("شماره تلفن", phone_var), ("ایمیل", email_var)]
        for i, (label, var) in enumerate(fields):
            col = i % 2
            row = i // 2
            ctk.CTkLabel(form, text=label, font=("Segoe UI", 12), text_color="#aaa").grid(row=row*2, column=col, sticky="w", padx=5, pady=(5, 2))
            ctk.CTkEntry(form, textvariable=var, height=38, corner_radius=8).grid(row=row*2+1, column=col, sticky="ew", padx=5, pady=(0, 5))

        ctk.CTkButton(profile_frame, text="ذخیره پروفایل", height=40, width=170, corner_radius=9,
                      fg_color=self.accent_color, hover_color=self.hover_variant(self.accent_color), text_color=self.contrast_text(self.accent_color),
                      command=lambda: self.save_user_profile(first_var.get(), last_var.get(), phone_var.get(), email_var.get())).pack(anchor="w", padx=21, pady=(4, 14))

        # ---------- صدا ----------
        sound_frame = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=12, border_width=1, border_color="#1a1a2e")
        sound_frame.pack(fill="x", pady=7)
        ctk.CTkLabel(sound_frame, text="🔊 صدای برنامه", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(sound_frame, text="صدای کلیک و اعلان‌های برنامه را روشن یا خاموش کنید.", font=("Segoe UI", 12), text_color="#888").pack(anchor="w", padx=16)
        sound_var = ctk.BooleanVar(value=self.sound_enabled)
        ctk.CTkSwitch(sound_frame, text="صدای برنامه روشن باشد", variable=sound_var, onvalue=True, offvalue=False,
                      command=lambda: self.set_sound(sound_var.get())).pack(anchor="w", padx=16, pady=12)

        # ---------- هوش مصنوعی آنلاین ----------
        ai_frame = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=12, border_width=1, border_color="#1a1a2e")
        ai_frame.pack(fill="x", pady=7)
        ctk.CTkLabel(ai_frame, text="🤖 هوش مصنوعی آنلاین", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(ai_frame, text="برای استفاده از AI آنلاین، کلید API را در حافظه امن ویندوز ذخیره کن. کلید داخل فایل تنظیمات JSON ذخیره نمی‌شود.", font=("Segoe UI", 12), text_color="#888").pack(anchor="w", padx=16, pady=(0, 10))
        ai_form = ctk.CTkFrame(ai_frame, fg_color="transparent")
        ai_form.pack(fill="x", padx=16, pady=(0, 8))
        ai_form.grid_columnconfigure(0, weight=1)
        ai_form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(ai_form, text="کلید API", text_color="#aaa").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        ctk.CTkLabel(ai_form, text="مدل", text_color="#aaa").grid(row=0, column=1, sticky="w", padx=5, pady=3)
        api_var = ctk.StringVar(value=self.get_ai_api_key())
        api_entry = ctk.CTkEntry(ai_form, textvariable=api_var, show="•", height=38, corner_radius=8)
        api_entry.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 8))
        model_var = ctk.StringVar(value=self.settings.get("ai_model", DEFAULT_AI_MODEL))
        model_entry = ctk.CTkEntry(ai_form, textvariable=model_var, height=38, corner_radius=8)
        model_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 8))
        ai_enabled_var = ctk.BooleanVar(value=bool(self.settings.get("ai_enabled", True)))
        web_var = ctk.BooleanVar(value=bool(self.settings.get("ai_web_search", False)))
        switches = ctk.CTkFrame(ai_frame, fg_color="transparent")
        switches.pack(fill="x", padx=16)
        ctk.CTkSwitch(switches, text="AI آنلاین فعال باشد", variable=ai_enabled_var,
                      command=lambda: self.set_ai_enabled(ai_enabled_var.get())).pack(side="left", padx=(0, 20))
        ctk.CTkSwitch(switches, text="جستجوی وب", variable=web_var,
                      command=lambda: self.set_ai_web_search(web_var.get())).pack(side="left")
        def save_ai_settings():
            key = api_var.get().strip()
            if key and not key.startswith("sk-"):
                messagebox.showwarning("کلید API", "فرمت کلید را بررسی کن.")
                return
            if key and not self.save_ai_api_key(key):
                messagebox.showwarning("ذخیره امن", "Windows Credential Manager در دسترس نیست. برای امنیت، کلید را با متغیر محیطی OPENAI_API_KEY تنظیم کن.")
                return
            self.settings["ai_model"] = model_var.get().strip() or DEFAULT_AI_MODEL
            self.settings["ai_enabled"] = bool(ai_enabled_var.get())
            self.settings["ai_web_search"] = bool(web_var.get())
            self.save_settings()
            messagebox.showinfo("AI", "تنظیمات AI ذخیره شد.")
        ai_btns = ctk.CTkFrame(ai_frame, fg_color="transparent")
        ai_btns.pack(fill="x", padx=16, pady=(10, 14))
        ctk.CTkButton(ai_btns, text="ذخیره تنظیمات AI", height=38, width=170, command=save_ai_settings,
                      fg_color=self.accent_color, hover_color=self.hover_variant(self.accent_color), text_color=self.contrast_text(self.accent_color)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(ai_btns, text="تست اتصال AI", height=38, width=140, command=lambda: self.test_ai_connection(api_var.get().strip(), model_var.get().strip())).pack(side="left")

        # ---------- بروزرسانی ----------
        update_frame = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=12, border_width=1, border_color="#1a1a2e")
        update_frame.pack(fill="x", pady=7)
        ctk.CTkLabel(update_frame, text="🔄 بروزرسانی برنامه", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(update_frame, text="سیستم بروزرسانی از GitHub Releases استفاده می‌کند؛ مخزن را در متغیر DNS_MASTER_PRO_UPDATE_REPO تنظیم کن.", font=("Segoe UI", 12), text_color="#888").pack(anchor="w", padx=16)
        ctk.CTkButton(update_frame, text="بررسی بروزرسانی", height=38, width=170, command=self.check_for_updates).pack(anchor="w", padx=16, pady=14)

        # ---------- رفتار برنامه ----------
        behavior_frame = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=12, border_width=1, border_color="#1a1a2e")
        behavior_frame.pack(fill="x", pady=7)
        ctk.CTkLabel(behavior_frame, text="🛠️ رفتار برنامه", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        tray_var = ctk.BooleanVar(value=bool(self.settings.get("minimize_to_tray", True)))
        ctk.CTkSwitch(behavior_frame, text="با زدن × برنامه به سینی سیستم برود", variable=tray_var, onvalue=True, offvalue=False,
                      command=lambda: self.set_minimize_to_tray(tray_var.get())).pack(anchor="w", padx=16, pady=8)
        ctk.CTkButton(behavior_frame, text="بازنشانی تنظیمات", height=38, width=170, corner_radius=8, fg_color="#c62828", hover_color="#b71c1c",
                      command=lambda: self.reset_settings()).pack(anchor="w", padx=16, pady=(2, 14))

        # ---------- راهنما ----------
        info = ctk.CTkFrame(main, fg_color="#0c0c16", corner_radius=10, border_width=1, border_color="#1a1a2e")
        info.pack(fill="x", pady=7)
        ctk.CTkLabel(info, text="ℹ️ اطلاعات ذخیره‌سازی", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(info, text=f"فایل تنظیمات: {os.path.abspath(SETTINGS_FILE)}", font=("Consolas", 10), text_color="#777").pack(anchor="w", padx=16, pady=(0, 12))

        # تنظیمات موجودِ اجرای خودکار ویندوز
        start_frame = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=12, border_width=1, border_color="#1a1a2e")
        start_frame.pack(fill="x", pady=7)
        ctk.CTkLabel(start_frame, text="اجرای خودکار با ویندوز", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(start_frame, text="برنامه هنگام روشن شدن ویندوز خودکار اجرا شود", font=("Segoe UI", 13), text_color="#888").pack(anchor="w", padx=16)
        btn_f = ctk.CTkFrame(start_frame, fg_color="transparent")
        btn_f.pack(anchor="w", padx=16, pady=14)
        ctk.CTkButton(btn_f, text="فعال کردن", command=lambda: self.btn_click(self.enable_startup), height=38, fg_color="#00c853", corner_radius=8).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_f, text="غیرفعال کردن", command=lambda: self.btn_click(self.disable_startup), height=38, fg_color="#c62828", corner_radius=8).pack(side="left")

    def profile_display_name(self):
        first = self.settings.get("first_name", "").strip()
        last = self.settings.get("last_name", "").strip()
        full = f"{first} {last}".strip()
        return f"👤 {full}" if full else "👤 مهمان"

    def save_settings(self):
        self.settings["theme"] = self.theme_name
        self.settings["sound"] = self.sound_enabled
        self.save_json(SETTINGS_FILE, self.settings)

    def save_user_profile(self, first, last, phone, email):
        self.settings["first_name"] = first.strip()
        self.settings["last_name"] = last.strip()
        self.settings["phone"] = phone.strip()
        self.settings["email"] = email.strip()
        self.save_settings()
        if hasattr(self, "profile_label"):
            self.profile_label.configure(text=self.profile_display_name())
        self.set_status("پروفایل با موفقیت ذخیره شد")
        messagebox.showinfo("پروفایل", "اطلاعات پروفایل ذخیره شد.")

    def set_sound(self, enabled):
        self.sound_enabled = bool(enabled)
        self.settings["sound"] = self.sound_enabled
        self.save_settings()
        self.set_status("صدای برنامه روشن شد" if self.sound_enabled else "صدای برنامه خاموش شد")

    def set_ai_enabled(self, enabled):
        self.settings["ai_enabled"] = bool(enabled)
        self.save_settings()
        self.set_status("AI آنلاین " + ("فعال شد" if enabled else "خاموش شد"))

    def test_ai_connection(self, api_key, model):
        if not api_key:
            messagebox.showwarning("AI", "کلید API وارد نشده است.")
            return
        if OpenAI is None:
            messagebox.showerror("AI", "کتابخانه openai نصب نشده است.")
            return
        def worker():
            try:
                client = OpenAI(api_key=api_key, timeout=30.0, max_retries=1)
                r = client.responses.create(model=model or DEFAULT_AI_MODEL, input="Reply only with: DNS Master Pro AI OK")
                text = getattr(r, "output_text", "").strip()
                self.after(0, lambda: messagebox.showinfo("AI", "اتصال موفق بود.\n\n" + (text or "پاسخ دریافت شد.")))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("AI", self.friendly_ai_error(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def check_for_updates(self):
        if not UPDATE_REPO:
            messagebox.showinfo("بروزرسانی", "مخزن بروزرسانی هنوز تنظیم نشده است.\n\nDNS_MASTER_PRO_UPDATE_REPO را به شکل owner/repository تنظیم کن.")
            return
        def worker():
            try:
                url = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"
                req = urllib.request.Request(url, headers={"User-Agent": "DNS-Master-Pro"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                tag = str(data.get("tag_name", "")).lstrip("v")
                current = VERSION.split()[0]
                assets = data.get("assets", [])
                download = assets[0].get("browser_download_url", "") if assets else data.get("html_url", "")
                msg = f"نسخه فعلی: {current}\nآخرین نسخه: {tag or 'نامشخص'}\n\n"
                if tag and tag != current:
                    msg += "نسخه جدید موجود است.\n" + download
                else:
                    msg += "نسخه فعلی آخرین Release شناخته‌شده است."
                self.after(0, lambda: messagebox.showinfo("بروزرسانی", msg))
            except Exception as exc:
                err = str(exc)
                self.after(0, lambda err=err: messagebox.showerror("بروزرسانی", f"بررسی بروزرسانی ناموفق بود.\n{err}"))
        threading.Thread(target=worker, daemon=True).start()

    def set_minimize_to_tray(self, enabled):
        self.settings["minimize_to_tray"] = bool(enabled)
        self.save_settings()
        self.set_status("مخفی شدن با × فعال شد" if enabled else "با × برنامه بسته می‌شود")

    def apply_theme(self, theme_name):
        if theme_name not in self.theme_colors:
            return
        self.theme_name = theme_name
        self.accent_color = self.theme_colors[theme_name]
        self.settings["theme"] = theme_name
        self.save_settings()
        self._theme_widgets(self, self.accent_color)
        self.set_status(f"رنگ تم به «{theme_name}» تغییر کرد")
        # صفحه تنظیمات را دوباره بساز تا همه کنترل‌ها رنگ جدید بگیرند
        self.show_settings()

    def pick_custom_color(self):
        rgb, hex_color = colorchooser.askcolor(color=self.accent_color, title="انتخاب رنگ سفارشی")
        if not hex_color:
            return
        self.theme_colors["رنگ سفارشی"] = hex_color
        self.settings["custom_theme_hex"] = hex_color
        self.apply_theme("رنگ سفارشی")

    def _theme_widgets(self, widget, accent):
        # رنگ کنترل‌های اصلی را بدون تغییر رنگ پس‌زمینه‌های تاریک تنظیم می‌کند.
        try:
            cls = widget.__class__.__name__
            if cls == "CTkButton":
                text = str(widget.cget("text"))
                if not any(x in text for x in ["غیرفعال", "پاک کردن", "بازنشانی"]):
                    widget.configure(
                        fg_color=accent,
                        hover_color=self.hover_variant(accent),
                        text_color=self.contrast_text(accent),
                        border_width=1,
                        border_color=self.lighten(accent, 0.3) if self._luminance(accent) < 0.12 else accent,
                    )
            elif cls == "CTkSwitch":
                widget.configure(progress_color=accent, button_color=self.lighten(accent, 0.2) if self._luminance(accent) < 0.12 else accent)
            elif cls == "CTkOptionMenu":
                widget.configure(button_color=accent, button_hover_color=self.hover_variant(accent), text_color=self.contrast_text(accent))
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._theme_widgets(child, accent)
        except Exception:
            pass

    def reset_settings(self):
        if not messagebox.askyesno("بازنشانی", "همه تنظیمات شخصی، رنگ و صدا به حالت پیش‌فرض برگردد؟"):
            return
        self.settings = {
            "theme": "آبی فیروزه‌ای", "first_name": "", "last_name": "",
            "phone": "", "email": "", "sound": True, "minimize_to_tray": True,
            "ai_enabled": True, "ai_model": DEFAULT_AI_MODEL, "ai_web_search": False
        }
        self.theme_colors.pop("رنگ سفارشی", None)
        self.sound_enabled = True
        self.theme_name = "آبی فیروزه‌ای"
        self.accent_color = self.theme_colors[self.theme_name]
        self.save_settings()
        if hasattr(self, "profile_label"):
            self.profile_label.configure(text=self.profile_display_name())
        self.show_settings()
        self.set_status("تنظیمات بازنشانی شد")

    def show_history(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        ctk.CTkLabel(main, text="تاریخچه", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 10))
        box = ctk.CTkTextbox(main, font=("Segoe UI", 13), fg_color="#0c0c16", corner_radius=12)
        box.pack(fill="both", expand=True)
        for item in reversed(self.history[-60:]):
            box.insert("end", item + "\n")


    def show_vpn(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(main, text="🛡️  VPN / WireGuard (نسخه ایمن)", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(main, text="این بخش فقط منابع معتبر و امکان وارد کردن دستی کانفیگ را ارائه می‌دهد", 
                     font=("Segoe UI", 13), text_color="#888").pack(anchor="w", pady=(0, 12))

        # Warning
        warn = ctk.CTkFrame(main, fg_color="#1a1000", border_width=1, border_color="#ff6b35", corner_radius=10)
        warn.pack(fill="x", pady=8)
        ctk.CTkLabel(warn, text="⚠️ هشدار امنیتی مهم", font=("Segoe UI", 15, "bold"), text_color="#ff6b35").pack(anchor="w", padx=14, pady=(10, 4))
        ctk.CTkLabel(warn, text="هرگز به سرورهای رایگان ناشناس به صورت خودکار وصل نشوید.\nسرورهای عمومی رایگان ممکن است ناامن باشند و ترافیک شما را ببینند.\nفقط از منابع معتبر استفاده کنید و کانفیگ را خودتان بررسی کنید.",
                     font=("Segoe UI", 12), text_color="#ffccaa", justify="left").pack(anchor="w", padx=14, pady=(0, 12))

        # Resources
        ctk.CTkLabel(main, text="منابع معتبر و شناخته‌شده:", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(14, 8))

        resources = [
            ("Proton VPN (رایگان محدود)", "https://protonvpn.com/"),
            ("Windscribe (رایگان محدود)", "https://windscribe.com/"),
            ("Cloudflare WARP (رایگان)", "https://10.0.0.1/"),
            ("WireGuard رسمی", "https://www.wireguard.com/install/"),
            ("لیست کانفیگ‌های عمومی (با احتیاط)", "https://github.com/search?q=wireguard+config"),
        ]

        for name, url in resources:
            card = ctk.CTkFrame(main, fg_color="#0f0f1a", border_width=1, border_color="#1a1a2e", corner_radius=10)
            card.pack(fill="x", pady=4)
            ctk.CTkLabel(card, text=name, font=("Segoe UI", 14)).pack(side="left", padx=14, pady=10)
            ctk.CTkButton(card, text="باز کردن", width=90, height=32, corner_radius=8,
                          command=lambda u=url: self.btn_click(lambda: webbrowser.open(u))).pack(side="right", padx=12)

        # Paste config
        ctk.CTkLabel(main, text="وارد کردن کانفیگ WireGuard (Paste):", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(18, 6))
        self.wg_text = ctk.CTkTextbox(main, height=140, font=("Consolas", 12), fg_color="#0c0c16", corner_radius=10)
        self.wg_text.pack(fill="x", pady=4)
        self.wg_text.insert("end", "[Interface]\nPrivateKey = ...\nAddress = ...\n\n[Peer]\nPublicKey = ...\nEndpoint = ...\nAllowedIPs = 0.0.0.0/0\n")

        btnf = ctk.CTkFrame(main, fg_color="transparent")
        btnf.pack(fill="x", pady=10)
        ctk.CTkButton(btnf, text="ذخیره کانفیگ به فایل", height=40, corner_radius=10,
                      command=lambda: self.btn_click(self.save_wg_config)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btnf, text="باز کردن WireGuard رسمی", height=40, corner_radius=10, fg_color="#0088cc",
                      command=lambda: self.btn_click(self.open_wireguard)).pack(side="left", padx=8)

    def save_wg_config(self):
        conf = self.wg_text.get("1.0", "end").strip()
        if not conf or "PrivateKey" not in conf:
            messagebox.showwarning("خطا", "کانفیگ معتبر وارد کنید")
            return
        try:
            path = os.path.join(os.path.expanduser("~"), "Desktop", "wireguard_config.conf")
            with open(path, "w", encoding="utf-8") as f:
                f.write(conf)
            messagebox.showinfo("موفق", f"کانفیگ روی دسکتاپ ذخیره شد:\n{path}\n\nحالا آن را در نرم‌افزار WireGuard Import کنید.")
        except Exception as e:
            messagebox.showerror("خطا", str(e))

    def open_wireguard(self):
        # Try to open WireGuard if installed
        possible = [
            r"C:\Program Files\WireGuard\wireguard.exe",
            r"C:\Program Files (x86)\WireGuard\wireguard.exe",
        ]
        for p in possible:
            if os.path.exists(p):
                subprocess.Popen([p])
                return
        webbrowser.open("https://www.wireguard.com/install/")
        messagebox.showinfo("WireGuard", "نرم‌افزار WireGuard پیدا نشد.\nصفحه دانلود باز شد.")

    def show_support(self):
        self.clear()
        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        ctk.CTkLabel(main, text="💬 پشتیبانی", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 16))

        card = ctk.CTkFrame(main, fg_color="#0f0f1a", corner_radius=16, border_width=1, border_color="#1a1a2e")
        card.pack(fill="x", pady=10)
        ctk.CTkLabel(card, text="پشتیبانی تلگرام", font=("Segoe UI", 16, "bold")).pack(pady=(24, 8))
        ctk.CTkLabel(card, text=TELEGRAM_SUPPORT, font=("Segoe UI", 26, "bold"), text_color="#00e5ff").pack(pady=6)
        ctk.CTkLabel(card, text="برای گزارش باگ یا پیشنهاد با این آیدی در ارتباط باشید", font=("Segoe UI", 13), text_color="#aaa").pack(pady=(6, 18))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=(0, 24))
        ctk.CTkButton(btn_frame, text="کپی آیدی", command=lambda: self.btn_click(self.copy_telegram), height=42, width=140, corner_radius=10).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="باز کردن تلگرام", command=lambda: self.btn_click(self.open_telegram), height=42, width=160, fg_color="#0088cc", hover_color="#0077b5", corner_radius=10).pack(side="left", padx=8)

        ctk.CTkLabel(main, text=f"نسخه: {VERSION}", font=("Segoe UI", 13), text_color="#666").pack(pady=20)

    # ==================== منطق اصلی ====================
    def toggle_live(self):
        if not self.is_online:
            messagebox.showwarning("اینترنت", "برای Live Hunter باید آنلاین باشی")
            return
        self.live_active = not self.live_active
        if self.live_active:
            self.live_btn.configure(text="⏸  توقف", fg_color="#ff6b35")
            self.live_status.configure(text="وضعیت: ● فعال", text_color="#00e676")
            self.set_status("Live Hunter روشن شد")
            threading.Thread(target=self.fetch_live, daemon=True).start()
        else:
            self.live_btn.configure(text="▶  شروع Live Hunter", fg_color="#00c853")
            self.live_status.configure(text="وضعیت: خاموش", text_color="#ccc")
            self.set_status("Live Hunter خاموش شد")

    def manual_fetch(self):
        if not self.is_online:
            messagebox.showwarning("آفلاین", "اینترنت نیست")
            return
        threading.Thread(target=self.fetch_live, daemon=True).start()

    def fetch_live(self):
        self.set_status("در حال شکار DNS4 (IPv4) زنده...")
        added = 0
        try:
            for url in TRUSTED_URLS:
                try:
                    with urllib.request.urlopen(url, timeout=7) as r:
                        text = r.read().decode("utf-8", errors="ignore")
                        lines = [l.strip().split()[0] for l in text.splitlines() if l.strip()]
                        random.shuffle(lines)
                        for ip in lines[:25]:
                            if self.valid_ip(ip) and not any(x["ip"] == ip for x in self.live_list):
                                if self.quick_test(ip):
                                    self.live_list.append({
                                        "ip": ip,
                                        "version": "IPv4",
                                        "source": url.split("/")[2],
                                        "latency_ms": self.measure_dns_latency(ip),
                                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    })
                                    added += 1
                                    if added >= 6:
                                        break
                        if added >= 6:
                            break
                except:
                    continue
            self.last_live = datetime.now().strftime("%H:%M:%S")
            self.save_json(LIVE_FILE, self.live_list[-80:])
            self.set_status(f"{added} DNS4 جدید اضافه شد")
            if hasattr(self, "live_frame"):
                self.refresh_live_ui()
                self.live_count.configure(text=f"تعداد: {len(self.live_list)}")
                self.live_time.configure(text=f"آخرین: {self.last_live}")
        except Exception as e:
            self.set_status(f"خطا در Live: {str(e)[:35]}")

    def measure_dns_latency(self, ip):
        try:
            start = time.perf_counter()
            res = dns.resolver.Resolver()
            res.nameservers = [ip]
            res.lifetime = 1.4
            res.resolve("google.com", "A")
            return round((time.perf_counter() - start) * 1000, 1)
        except Exception:
            return None

    def quick_test(self, ip):
        try:
            res = dns.resolver.Resolver()
            res.nameservers = [ip]
            res.lifetime = 1.4
            res.resolve("google.com", "A")
            return True
        except:
            return False

    def refresh_live_ui(self):
        for w in self.live_frame.winfo_children():
            w.destroy()
        if not self.live_list:
            ctk.CTkLabel(self.live_frame, text="هنوز چیزی کشف نشده. Live Hunter را روشن کنید.", text_color="#888").pack(pady=20)
            return
        for item in reversed(self.live_list[-35:]):
            card = ctk.CTkFrame(self.live_frame, fg_color="#0f0f1a", border_width=1, border_color="#1a1a2e", corner_radius=8)
            card.pack(fill="x", pady=3)
            ctk.CTkLabel(card, text=item["ip"], font=("Consolas", 14, "bold"), text_color="#00e5ff").pack(side="left", padx=(14, 8), pady=8)
            ctk.CTkLabel(card, text="IPv4 / DNS4", font=("Segoe UI", 10, "bold"), text_color="#7c4dff").pack(side="left", padx=4)
            latency = item.get("latency_ms")
            latency_text = f"{latency} ms" if latency is not None else "—"
            ctk.CTkLabel(card, text=f"تاخیر: {latency_text}", font=("Consolas", 11), text_color="#00e676").pack(side="left", padx=8)
            ctk.CTkLabel(card, text=item.get("time", "—"), font=("Segoe UI", 10), text_color="#888").pack(side="left", padx=8)
            ctk.CTkButton(card, text="اعمال DNS4", width=100, height=30, corner_radius=6, command=lambda ip=item["ip"]: self.btn_click(lambda: self.apply_dns(ip))).pack(side="right", padx=10)

    def clear_live(self):
        self.live_list = []
        self.save_json(LIVE_FILE, [])
        self.refresh_live_ui()
        self.live_count.configure(text="تعداد: 0")
        self.set_status("لیست زنده پاک شد")

    def apply_game(self, name):
        dns_name = self.game_plans[name][0]
        self.apply_preset(dns_name)
        self.add_hist(f"Game Plan: {name}")
        messagebox.showinfo("موفق", f"پلن {name} اعمال شد")

    def apply_preset(self, name):
        data = self.presets[name]
        ipv4_1 = data["ipv4"][0] if data.get("ipv4") else ""
        ipv4_2 = data["ipv4"][1] if data.get("ipv4") and len(data["ipv4"]) > 1 else ""
        ipv6_1 = data["ipv6"][0] if data.get("ipv6") else ""
        ipv6_2 = data["ipv6"][1] if data.get("ipv6") and len(data["ipv6"]) > 1 else ""
        self.apply_dns(ipv4_1, ipv4_2, ipv6_1, ipv6_2)
        self.add_hist(f"Preset: {name}")
        self.set_status(f"{name} اعمال شد")

    def apply_custom(self):
        d1 = self.e1.get().strip()
        if not d1 or not self.valid_ip(d1):
            messagebox.showwarning("خطا", "DNS اولیه IPv4 معتبر وارد کن")
            return
        self.apply_dns(d1, self.e2.get().strip(), self.e6_1.get().strip(), self.e6_2.get().strip())

    def apply_dns(self, primary, secondary="", ipv6_1="", ipv6_2=""):
        adapter = self.adapter_var.get()
        if not adapter or adapter in ["...", "Loading..."]:
            messagebox.showwarning("هشدار", "آداپتر را انتخاب کنید")
            return
        try:
            windows_dns.apply_dns(adapter, primary, secondary, ipv6_1, ipv6_2)
            messagebox.showinfo("موفق", "DNS با موفقیت اعمال شد")
            self.add_hist(f"Apply DNS {primary} on {adapter}")
            if hasattr(self, "dns_box"):
                self.show_current_dns()
        except Exception as e:
            log.exception("apply_dns failed for adapter=%s", adapter)
            messagebox.showerror("خطا", f"اعمال نشد.\nبا Run as Administrator اجرا کنید.\n\n{e}")

    def flush(self):
        try:
            windows_dns.flush_cache()
            messagebox.showinfo("موفق", "کش DNS پاک شد")
            self.add_hist("Flush DNS")
            self.set_status("کش پاک شد")
        except Exception as e:
            log.exception("flush failed")
            messagebox.showerror("خطا", str(e))

    def reset_dhcp(self):
        adapter = self.adapter_var.get()
        try:
            windows_dns.reset_dhcp(adapter)
            messagebox.showinfo("موفق", "به DHCP بازگشت")
            self.add_hist("Reset to DHCP")
            self.set_status("DHCP فعال شد")
        except Exception as e:
            log.exception("reset_dhcp failed for adapter=%s", adapter)
            messagebox.showerror("خطا", str(e))

    def enable_startup(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            path = os.path.abspath(sys.argv[0]) if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            winreg.SetValueEx(key, STARTUP_NAME, 0, winreg.REG_SZ, f'"{path}"')
            winreg.CloseKey(key)
            messagebox.showinfo("موفق", "اجرای خودکار فعال شد")
        except Exception as e:
            messagebox.showerror("خطا", str(e))

    def disable_startup(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, STARTUP_NAME)
            winreg.CloseKey(key)
            messagebox.showinfo("موفق", "اجرای خودکار غیرفعال شد")
        except:
            messagebox.showinfo("اطلاع", "قبلاً فعال نبوده")

    def test_resolve(self):
        self.test_box.delete("1.0", "end")
        self.test_box.insert("end", "▶ تست Resolve شروع شد...\n\n")
        def run():
            for d in ["google.com", "youtube.com", "github.com", "cloudflare.com"]:
                try:
                    ips = [r.address for r in dns.resolver.resolve(d, "A")]
                    self.test_box.insert("end", f"  ✓  {d:<18} → {', '.join(ips)}\n")
                except:
                    self.test_box.insert("end", f"  ✗  {d:<18} → Failed\n")
            self.test_box.insert("end", "\n✔ تست تمام شد")
        threading.Thread(target=run, daemon=True).start()

    def test_speed(self):
        self.test_box.delete("1.0", "end")
        self.test_box.insert("end", "▶ تست سرعت تمام DNSها...\n\n")
        def run():
            results = []
            for name, data in self.presets.items():
                ip = data["ipv4"][0]
                try:
                    res = dns.resolver.Resolver()
                    res.nameservers = [ip]
                    res.lifetime = 2.0
                    t = time.time()
                    res.resolve("google.com", "A")
                    ms = (time.time() - t) * 1000
                    results.append((ms, name, ip))
                    self.test_box.insert("end", f"  {name:<14} {ip:<16} {ms:6.1f} ms\n")
                except:
                    self.test_box.insert("end", f"  {name:<14} {ip:<16} Timeout\n")
            results.sort()
            if results:
                self.test_box.insert("end", f"\n🏆 بهترین: {results[0][1]} → {results[0][0]:.1f} ms\n")
            self.test_box.insert("end", "\n✔ تست تمام شد")
        threading.Thread(target=run, daemon=True).start()

    def show_current_dns(self):
        try:
            out = windows_dns.current_status()
            self.dns_box.delete("1.0", "end")
            self.dns_box.insert("end", out)
        except Exception as exc:
            log.warning("show_current_dns failed: %s", exc)
            self.dns_box.insert("end", "خطا در خواندن وضعیت")

    def refresh_adapters(self):
        try:
            ads = windows_dns.list_adapters()
            if ads:
                self.adapter_menu.configure(values=ads)
                self.adapter_var.set(ads[0])
        except Exception as exc:
            log.warning("refresh_adapters failed: %s", exc)

    def copy_status(self):
        try:
            out = windows_dns.current_status()
            self.clipboard_clear()
            self.clipboard_append(out)
            messagebox.showinfo("کپی", "وضعیت کپی شد")
        except Exception as exc:
            log.warning("copy_status failed: %s", exc)

    def copy_telegram(self):
        self.clipboard_clear()
        self.clipboard_append(TELEGRAM_SUPPORT)
        messagebox.showinfo("کپی شد", f"آیدی {TELEGRAM_SUPPORT} کپی شد")

    def open_telegram(self):
        webbrowser.open(f"https://t.me/{TELEGRAM_SUPPORT.replace('@', '')}")

    def copy_text(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("کپی", "کپی شد")

    def add_hist(self, text):
        self.history.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}")
        self.save_json(HISTORY_FILE, self.history[-70:])

    def valid_ip(self, ip):
        if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", ip):
            return False
        return all(0 <= int(x) <= 255 for x in ip.split("."))

    def load_json(self, path, default):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
        return default

    def save_json(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def check_admin(self):
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except:
            return False

    def update_admin(self):
        if self.is_admin:
            self.admin_label.configure(text="● Admin", text_color="#00e676")
        else:
            self.admin_label.configure(text="● No Admin", text_color="#ff6b35")


if __name__ == "__main__":
    app = DNSMasterFinal()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
