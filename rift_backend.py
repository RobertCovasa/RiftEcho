import requests
import urllib3
import time
import threading

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GameStateTracker:
    """
    Tracks invisible game state: Kill Streaks, Timers, and Cooldowns.
    """
    def __init__(self):
        self.streaks = {}  # Format: {'SummonerName': int_count}
        self.timers = []   # Format: {'trigger_time': float, 'sound_key': str, 'category': str}
        self.processed_events = set() # To avoid duplicate processing
        
    def get_streak(self, summoner):
        return self.streaks.get(summoner, 0)

    def add_kill(self, killer):
        self.streaks[killer] = self.streaks.get(killer, 0) + 1
        return self.streaks[killer]

    def reset_streak(self, victim):
        was_shutdown = self.streaks.get(victim, 0) >= 3
        self.streaks[victim] = 0
        return was_shutdown

    def schedule_timer(self, current_time, delay, category, key):
        trigger_time = current_time + delay
        self.timers.append({
            "trigger_time": trigger_time,
            "category": category,
            "key": key
        })
        print(f"[Timer] Scheduled '{key}' for T+{delay}s")

    def check_timers(self, current_game_time):
        """Returns a list of sound keys to play if their time has come."""
        triggered = []
        remaining = []
        
        for t in self.timers:
            if current_game_time >= t["trigger_time"]:
                triggered.append((t["category"], t["key"]))
            else:
                remaining.append(t)
        
        self.timers = remaining
        return triggered

class RiftBackend(threading.Thread):
    def __init__(self, app_interface, config_map):
        super().__init__()
        self.app = app_interface
        self.event_map = config_map
        self.running = True
        self.connected = False
        
        self.base_url = "https://127.0.0.1:2999/liveclientdata"
        self.event_index = 0
        
        # Identity
        self.my_summoner = None
        self.my_team = None
        self.player_team_cache = {} # Name -> Team (ORDER/CHAOS)
        
        # Logic Module
        self.tracker = GameStateTracker()

    def fetch_api(self, endpoint):
        try:
            resp = requests.get(f"{self.base_url}/{endpoint}", verify=False, timeout=0.5)
            resp.raise_for_status()
            return resp.json()
        except:
            return None

    def setup_identity(self):
        active = self.fetch_api("activeplayer")
        players = self.fetch_api("playerlist")
        
        if active and players:
            try:
                # Resolve My Name
                self.my_summoner = active.get("summonerName")
                if not self.my_summoner: 
                    self.my_summoner = active.get("riotIdGameName")
                
                # Build Team Cache
                for p in players:
                    s_name = p.get("summonerName")
                    r_name = p.get("riotIdGameName")
                    team = p.get("team")
                    
                    if s_name: self.player_team_cache[s_name] = team
                    if r_name: self.player_team_cache[r_name] = team
                    
                    if s_name == self.my_summoner or r_name == self.my_summoner:
                        self.my_team = team
                
                print(f"[Backend] Identity Established: {self.my_summoner} ({self.my_team})")
                self.app.set_status(True) # This updates the GUI "Connected" gem
                return True
            except Exception as e:
                print(f"[Backend] Identity Error: {e}")
        return False

    def handle_kill_logic(self, killer, victim):
        """Calculates Spree, Shutdown, and Executions."""
        sounds_to_play = []

        # 1. Check for Execution (Non-Champion Killer)
        # Note: Minions/Turrets are not in player_team_cache
        is_execution = killer not in self.player_team_cache
        
        if is_execution:
            if victim == self.my_summoner:
                sounds_to_play.append(("player", "executed"))
            elif self.player_team_cache.get(victim) == self.my_team:
                sounds_to_play.append(("team", "executed_ally"))
            else:
                sounds_to_play.append(("team", "executed_enemy"))
            return sounds_to_play

        # 2. Update Streaks
        current_streak = self.tracker.add_kill(killer)
        was_shutdown = self.tracker.reset_streak(victim)

        killer_team = self.player_team_cache.get(killer)
        victim_team = self.player_team_cache.get(victim)

        # 3. Basic Kill Announcements (You slain / Ally slain)
        if killer == self.my_summoner:
            sounds_to_play.append(("player", "kill"))
        elif victim == self.my_summoner:
            sounds_to_play.append(("player", "death"))
        elif killer_team == self.my_team:
            sounds_to_play.append(("team", "enemy_slain"))
        else:
            sounds_to_play.append(("team", "ally_slain"))

        # 4. Spree Announcements (Rampage, Godlike, Legendary)
        spree_key = None
        if current_streak == 3: spree_key = "rampage"
        elif current_streak == 6: spree_key = "godlike"
        elif current_streak >= 8: spree_key = "legendary"

        if spree_key:
            if killer == self.my_summoner:
                sounds_to_play.append(("player", spree_key))
            elif killer_team == self.my_team:
                sounds_to_play.append(("team", f"ally_{spree_key}"))
            else:
                sounds_to_play.append(("team", f"enemy_{spree_key}"))

        # 5. Shutdown Announcements
        if was_shutdown:
            if killer == self.my_summoner:
                sounds_to_play.append(("player", "shutdown"))
            elif killer_team == self.my_team:
                sounds_to_play.append(("team", "shutdown_enemy")) # We shut them down
            else:
                sounds_to_play.append(("team", "shutdown_ally")) # We were shut down

        return sounds_to_play

    def process_event(self, event, game_time):
        name = event["EventName"]
        
        # Avoid duplicate processing using EventID if available
        event_id = event.get("EventID")
        if event_id is not None:
            if event_id in self.tracker.processed_events:
                return
            self.tracker.processed_events.add(event_id)

        category = None
        key = None

        # --- GLOBAL ---
        if name == "GameStart":
            category, key = "global", "GameStart"
            self.tracker.schedule_timer(game_time, 15.0, "global", "minions_soon")
        
        elif name == "MinionsSpawning":
            category, key = "global", "MinionsSpawning"
        
        elif name == "GameEnd":
            result = event.get("Result")
            key = "victory" if result == "Win" else "defeat"
            category = "global"

        # --- OBJECTIVES ---
        elif name == "InhibKilled":
            killer_team = self.player_team_cache.get(event["KillerName"])
            if killer_team == self.my_team:
                category, key = "team", "inhib_destroy"
            else:
                category, key = "team", "inhib_lost"
            self.tracker.schedule_timer(game_time, 285.0, "warnings", "inhib_respawning")

        elif name == "DragonKill":
            killer_team = self.player_team_cache.get(event["KillerName"])
            if killer_team == self.my_team:
                category, key = "team", "dragon_taken"
            else:
                category, key = "team", "dragon_lost"
            self.tracker.schedule_timer(game_time, 270.0, "warnings", "dragon_spawning")

        elif name == "BaronKill":
            killer_team = self.player_team_cache.get(event["KillerName"])
            if killer_team == self.my_team:
                category, key = "team", "baron_taken"
            else:
                category, key = "team", "baron_lost"
            self.tracker.schedule_timer(game_time, 330.0, "warnings", "baron_spawning")

        elif name == "HordeKill": # Grubs
            if self.player_team_cache.get(event["KillerName"]) == self.my_team:
                category, key = "team", "grubs_taken"
            else:
                category, key = "team", "grubs_lost"

        elif name == "HeraldKill":
            if self.player_team_cache.get(event["KillerName"]) == self.my_team:
                category, key = "team", "herald_taken"
            else:
                category, key = "team", "herald_lost"
        
        elif name == "TurretKilled":
            killer = event["KillerName"]
            killer_team = self.player_team_cache.get(killer)
            
            if killer == self.my_summoner or killer_team == self.my_team:
                category, key = "team", "turret_destroy"
            else:
                category, key = "team", "turret_lost"

        # --- MULTIKILL ---
        elif name == "Multikill":
            if event["KillerName"] == self.my_summoner:
                category, key = "player", f"multikill_{event['KillStreak']}"
        
        # --- ACE ---
        elif name == "Ace":
            acing_team = event.get("AcingTeam")
            key = "ace_enemy" if acing_team == self.my_team else "ace_us"
            category = "global"

        # --- CHAMPION KILLS (Complex Logic) ---
        elif name == "ChampionKill":
            kill_sounds = self.handle_kill_logic(event["KillerName"], event["VictimName"])
            for cat, k in kill_sounds:
                self.app.trigger_audio(cat, k, f"{name} -> {k}")
            return

        # Trigger Standard Events
        if category and key:
            self.app.trigger_audio(category, key, f"{name} -> {key}")

    def run(self):
        while self.running:
            # 1. Fetch Game Time
            all_data = self.fetch_api("allgamedata")
            
            if not all_data:
                if self.connected:
                    print("[Backend] Game Disconnected.")
                    self.app.set_status(False)
                    self.connected = False
                    self.event_index = 0
                    self.tracker = GameStateTracker()
                time.sleep(2)
                continue

            if not self.connected:
                print("[Backend] Game Found! Connecting...")
                if self.setup_identity():
                    self.connected = True
                else:
                    time.sleep(1)
                    continue

            # 2. Check Timers
            try:
                game_time = all_data["gameData"]["gameTime"]
                timer_events = self.tracker.check_timers(game_time)
                for cat, key in timer_events:
                    self.app.trigger_audio(cat, key, f"Timer -> {key}")

                # 3. Check Events
                events = all_data["events"]["Events"]
                if len(events) > self.event_index:
                    for ev in events[self.event_index:]:
                        self.process_event(ev, game_time)
                    self.event_index = len(events)
            except Exception:
                pass 

            time.sleep(0.25)

    def stop(self):
        self.running = False