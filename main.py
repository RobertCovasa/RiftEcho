import customtkinter as ctk
import os
import json
import pyglet
import random
import threading
from rift_backend import RiftBackend

# --- CONFIGURATION ---
ASSETS_DIR = "assets"
CONFIG_FILE = "events.json"

# --- HEXTECH THEME PALETTE ---
LOL_BG_DARK     = "#010A13"  # Deepest Blue/Black (Client BG)
LOL_PANEL       = "#091428"  # Panel Background
LOL_GOLD        = "#C8AA6E"  # Prestige Gold (Borders/Text)
LOL_GOLD_DIM    = "#785A28"  # Darker Gold for inactive elements
LOL_CYAN        = "#0AC8B9"  # Hextech Blue (Active Elements)
LOL_CYAN_HOVER  = "#46E6D8"  # Brighter Cyan for hover
LOL_TEXT_MAIN   = "#F0E6D2"  # Bone/Parchment White
LOL_TEXT_DIM    = "#A09B8C"  # Dimmed Text
LOL_RED         = "#D13639"  # Noxian Red (Offline/Error)
LOL_GREEN       = "#0397AB"  # Shadow Isle Green/Teal (Live)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class RiftEchoGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- AUDIO INIT ---
        self.player = pyglet.media.Player()
        self.current_pack_path = ""
        self.is_muted = False
        
        # --- GUI SETUP ---
        self.title("Rift Echo")
        self.geometry("480x300")
        
        # --- ICON SETUP ---
        icon_path = os.path.join(ASSETS_DIR, "icons8-commercial-40.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        self.resizable(False, False)
        self.configure(fg_color=LOL_BG_DARK)
        
        # Main Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.create_widgets()
        
        # --- BACKEND INIT ---
        self.event_map = self.load_config()
        self.update_pack_path()
        
        self.after(100, self.start_backend)

    def start_backend(self):
        self.backend = RiftBackend(self, self.event_map)
        self.backend.start()

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def create_widgets(self):
        # ================= HEADER =================
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        
        # Title
        title_label = ctk.CTkLabel(
            self.header_frame, 
            text="RIFT ECHO", 
            font=("Times New Roman", 24, "bold"), 
            text_color=LOL_GOLD
        )
        title_label.pack(side="left")
        
        # Status "Gem"
        self.status_frame = ctk.CTkFrame(
            self.header_frame, 
            fg_color="transparent", 
            border_width=1, 
            border_color=LOL_GOLD_DIM, 
            corner_radius=6
        )
        self.status_frame.pack(side="right")
        
        self.status_dot = ctk.CTkLabel(self.status_frame, text="◆", font=("Arial", 14), text_color=LOL_RED)
        self.status_dot.pack(side="left", padx=(8, 2), pady=3)
        
        self.status_text = ctk.CTkLabel(
            self.status_frame, 
            text="DISCONNECTED", 
            font=("Arial", 10, "bold"), 
            text_color=LOL_TEXT_DIM
        )
        self.status_text.pack(side="left", padx=(0, 8), pady=3)


        # ================= MAIN HEX-PANEL =================
        self.main_panel = ctk.CTkFrame(
            self, 
            fg_color=LOL_PANEL, 
            corner_radius=4, 
            border_width=1, 
            border_color=LOL_GOLD
        )
        self.main_panel.grid(row=1, column=0, sticky="nsew", padx=25, pady=(5, 25))
        self.main_panel.grid_columnconfigure(0, weight=1)

        # --- Voice Pack Selector Header ---
        lbl_pack = ctk.CTkLabel(self.main_panel, text="ANNOUNCER VOICE PACK", font=("Arial", 10, "bold"), text_color=LOL_GOLD)
        lbl_pack.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))

        # --- Voice Pack Selection Area ---
        sel_container = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        sel_container.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        sel_container.grid_columnconfigure(0, weight=1) 

        self.pack_options = self.scan_voice_packs()
        self.pack_var = ctk.StringVar(value=self.pack_options[0] if self.pack_options else "Default")
        
        self.pack_dropdown = ctk.CTkOptionMenu(
            sel_container,
            values=self.pack_options,
            variable=self.pack_var,
            width=300, 
            height=35,
            corner_radius=0, 
            fg_color="#1E2328", 
            button_color="#1E2328",
            button_hover_color="#2A3038",
            text_color=LOL_TEXT_MAIN,
            dropdown_fg_color=LOL_PANEL,
            dropdown_text_color=LOL_TEXT_MAIN,
            dropdown_hover_color="#1E2328",
            font=("Arial", 12),
            dropdown_font=("Arial", 12),
            dynamic_resizing=False,
            command=self.change_pack
        )
        self.pack_dropdown.grid(row=0, column=0, sticky="ew") 

        # Refresh Button
        self.refresh_btn = ctk.CTkButton(
            sel_container,
            text="⟳",
            font=("Arial", 16, "bold"),
            width=40,
            height=35,
            corner_radius=0,
            fg_color="#1E2328",
            hover_color="#2A3038",
            text_color=LOL_GOLD,
            border_width=0,
            command=self.refresh_packs
        )
        self.refresh_btn.grid(row=0, column=1, padx=(5, 0)) 

        # Divider
        div = ctk.CTkFrame(self.main_panel, fg_color=LOL_GOLD_DIM, height=1)
        div.grid(row=2, column=0, sticky="ew", padx=20)


        # --- Audio Controls ---
        controls = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        controls.grid(row=3, column=0, sticky="ew", padx=20, pady=20)
        controls.grid_columnconfigure(1, weight=1)

        # Volume Area
        vol_frame = ctk.CTkFrame(controls, fg_color="transparent")
        vol_frame.grid(row=0, column=0, sticky="w")
        
        self.vol_label_var = ctk.StringVar(value="MASTER VOLUME: 50%")
        ctk.CTkLabel(vol_frame, textvariable=self.vol_label_var, font=("Arial", 9, "bold"), text_color=LOL_TEXT_DIM).pack(anchor="w")

        self.vol_slider = ctk.CTkSlider(
            vol_frame, 
            from_=0, to=1, 
            width=160, 
            height=16,
            fg_color="#010A13",       
            progress_color=LOL_CYAN,  
            button_color=LOL_GOLD,    
            button_hover_color=LOL_TEXT_MAIN,
            command=self.update_volume
        )
        self.vol_slider.set(0.5)
        self.vol_slider.pack(pady=(5,0))

        # Actions Area
        actions_frame = ctk.CTkFrame(controls, fg_color="transparent")
        actions_frame.grid(row=0, column=2, sticky="e")

        # Test Button
        self.test_btn = ctk.CTkButton(
            actions_frame,
            text="TEST AUDIO",
            font=("Arial", 11, "bold"),
            fg_color="transparent",     # Transparent Background
            border_width=1,
            border_color=LOL_GOLD_DIM,  # Dim Gold Border
            text_color=LOL_GOLD,        # Gold Text
            hover_color=LOL_GOLD,       # Fills with Gold on Hover
            width=100,
            height=30,
            corner_radius=2,
            command=self.play_test_sound
        )
        # Text turns Dark Blue on hover
        self.test_btn.bind("<Enter>", lambda e: self.test_btn.configure(text_color=LOL_PANEL)) 
        self.test_btn.bind("<Leave>", lambda e: self.test_btn.configure(text_color=LOL_GOLD))
        self.test_btn.pack(side="left", padx=(0, 10))

        # Mute Toggle
        self.mute_var = ctk.StringVar(value="off")
        self.mute_btn = ctk.CTkCheckBox(
            actions_frame, 
            text="MUTE", 
            font=("Arial", 10, "bold"),
            text_color=LOL_TEXT_DIM,
            fg_color=LOL_RED,
            hover_color=LOL_RED,
            border_color=LOL_TEXT_MAIN,
            checkmark_color=LOL_TEXT_MAIN,
            variable=self.mute_var,
            onvalue="on",
            offvalue="off",
            width=50,
            height=20,
            corner_radius=4,
            command=self.toggle_mute
        )
        self.mute_btn.pack(side="left")

    # --- LOGIC ---
    def scan_voice_packs(self):
        if not os.path.exists(ASSETS_DIR): os.makedirs(ASSETS_DIR)
        packs = [d for d in os.listdir(ASSETS_DIR) if os.path.isdir(os.path.join(ASSETS_DIR, d))]
        return packs if packs else ["Default"]

    def refresh_packs(self):
        self.pack_options = self.scan_voice_packs()
        self.pack_dropdown.configure(values=self.pack_options)
        if self.pack_var.get() not in self.pack_options:
            self.pack_var.set(self.pack_options[0])
            self.update_pack_path()
        print("Assets refreshed.")

    def change_pack(self, choice):
        self.update_pack_path()

    def update_pack_path(self):
        self.current_pack_path = os.path.join(ASSETS_DIR, self.pack_var.get())

    def set_status(self, connected):
        if connected:
            self.status_dot.configure(text_color=LOL_GREEN)
            self.status_text.configure(text="CONNECTED", text_color=LOL_CYAN)
            self.status_frame.configure(border_color=LOL_CYAN)
        else:
            self.status_dot.configure(text_color=LOL_RED)
            self.status_text.configure(text="DISCONNECTED", text_color=LOL_TEXT_DIM)
            self.status_frame.configure(border_color=LOL_GOLD_DIM)

    def update_volume(self, val):
        percent = int(val * 100)
        self.vol_label_var.set(f"MASTER VOLUME: {percent}%")
        self.player.volume = float(val)

    def toggle_mute(self):
        self.is_muted = (self.mute_var.get() == "on")
        if self.is_muted:
            self.player.pause()
            self.mute_btn.configure(text_color=LOL_RED)
        else:
            self.mute_btn.configure(text_color=LOL_TEXT_DIM)

    def trigger_audio(self, category, key, log_msg=""):
        if self.is_muted: return
        filename = self.event_map.get(category, {}).get(key)
        if not filename: return

        full_path = os.path.join(self.current_pack_path, filename)
        if os.path.exists(full_path):
            try:
                source = pyglet.media.load(full_path, streaming=False)
                new_player = pyglet.media.Player()
                new_player.queue(source)
                new_player.volume = self.vol_slider.get()
                new_player.play()
                self.player = new_player 
            except: pass

    def play_test_sound(self):
        try:
            files = [f for f in os.listdir(self.current_pack_path) if f.endswith(".wav") or f.endswith(".mp3")]
            if files:
                f = random.choice(files)
                full_path = os.path.join(self.current_pack_path, f)
                source = pyglet.media.load(full_path, streaming=False)
                new_player = pyglet.media.Player()
                new_player.queue(source)
                new_player.volume = self.vol_slider.get()
                new_player.play()
                self.player = new_player
                print(f"Testing: {f}")
        except: pass

    def on_close(self):
        if hasattr(self, 'backend'):
            self.backend.stop()
        self.destroy()

if __name__ == "__main__":
    app = RiftEchoGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()