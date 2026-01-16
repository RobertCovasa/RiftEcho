import requests
import urllib3
import time
import threading

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GameStateTracker:
    def __init__(self):
        self.streaks = {} 
        self.timers = []   
        self.processed_events = set()
        
        self.grubs_killed = 0
        self.grubs_ally_score = 0
        self.grubs_enemy_score = 0
        
        self.static_timers = [
            {"time": 270, "category": "warnings", "key": "grubs_spawning", "announced": False},
            {"time": 300, "category": "warnings", "key": "grubs_live", "announced": False},     
            {"time": 270, "category": "warnings", "key": "dragon_spawning", "announced": False},
            {"time": 300, "category": "warnings", "key": "dragon_live", "announced": False},     
            {"time": 870, "category": "warnings", "key": "herald_spawning", "announced": False},
            {"time": 900, "category": "warnings", "key": "herald_live", "announced": False},     
            {"time": 1170, "category": "warnings", "key": "baron_spawning", "announced": False},
            {"time": 1200, "category": "warnings", "key": "baron_live", "announced": False},     
        ]

    def add_kill(self, killer):
        self.streaks[killer] = self.streaks.get(killer, 0) + 1
        return self.streaks[killer]

    def reset_streak(self, victim):
        was_shutdown = self.streaks.get(victim, 0) >= 3
        self.streaks[victim] = 0
        return was_shutdown

    def schedule_timer(self, current_time, delay, category, key):
        trigger_time = current_time + delay
        self.timers.append({"trigger_time": trigger_time, "category": category, "key": key})
        print(f"[Timer] Scheduled '{key}' for T+{delay}s")

    def check_timers(self, current_game_time):
        triggered = []
        remaining = []
        for t in self.timers:
            if current_game_time >= t["trigger_time"]:
                triggered.append((t["category"], t["key"]))
            else:
                remaining.append(t)
        self.timers = remaining
        
        for st in self.static_timers:
            if not st["announced"] and current_game_time >= st["time"]:
                triggered.append((st["category"], st["key"]))
                st["announced"] = True
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
        self.my_summoner = None
        self.my_team = None
        self.player_team_cache = {}
        self.tracker = GameStateTracker()
        
        # New: Connection Resilience
        self.failure_count = 0

    def fetch_api(self, endpoint):
        try:
            resp = requests.get(f"{self.base_url}/{endpoint}", verify=False, timeout=0.5)
            resp.raise_for_status()
            self.failure_count = 0 # Reset failure count on success
            return resp.json()
        except:
            return None

    def setup_identity(self):
        active = self.fetch_api("activeplayer")
        players = self.fetch_api("playerlist")
        if active and players:
            try:
                self.my_summoner = active.get("summonerName") or active.get("riotIdGameName")
                for p in players:
                    s_name = p.get("summonerName")
                    r_name = p.get("riotIdGameName")
                    team = p.get("team")
                    if s_name: self.player_team_cache[s_name] = team
                    if r_name: self.player_team_cache[r_name] = team
                    if s_name == self.my_summoner or r_name == self.my_summoner:
                        self.my_team = team
                print(f"[Backend] Identity: {self.my_summoner} ({self.my_team})")
                self.app.set_status(True)
                return True
            except: pass
        return False

    def handle_kill_logic(self, killer, victim):
        sounds = []
        killer_team = self.player_team_cache.get(killer)
        victim_team = self.player_team_cache.get(victim)
        is_execution = killer not in self.player_team_cache
        
        if is_execution:
            if victim == self.my_summoner: sounds.append(("player", "executed"))
            elif victim_team == self.my_team: sounds.append(("team", "executed_ally"))
            else: sounds.append(("team", "executed_enemy"))
            return sounds

        current_streak = self.tracker.add_kill(killer)
        was_shutdown = self.tracker.reset_streak(victim)

        if victim == self.my_summoner: sounds.append(("player", "death"))
        elif killer == self.my_summoner: sounds.append(("player", "kill"))
        elif victim_team == self.my_team: sounds.append(("team", "ally_slain"))
        elif killer_team == self.my_team: sounds.append(("team", "enemy_slain"))

        spree_key = None
        if current_streak == 3: spree_key = "rampage"
        elif current_streak == 6: spree_key = "godlike"
        elif current_streak >= 8: spree_key = "legendary"

        if spree_key:
            if killer == self.my_summoner: sounds.append(("player", spree_key))
            elif killer_team == self.my_team: sounds.append(("team", f"ally_{spree_key}"))
            else: sounds.append(("team", f"enemy_{spree_key}"))

        if was_shutdown:
            if killer == self.my_summoner: sounds.append(("player", "shutdown"))
            elif killer_team == self.my_team: sounds.append(("team", "shutdown_enemy"))
            else: sounds.append(("team", "shutdown_ally"))
        return sounds

    def process_event(self, event, game_time):
        name = event["EventName"]
        event_id = event.get("EventID")
        if event_id is not None:
            if event_id in self.tracker.processed_events: return
            self.tracker.processed_events.add(event_id)

        category, key = None, None
        
        if name == "GameStart":
            # Don't schedule if we are reconnecting late
            if game_time < 30: 
                category, key = "global", "GameStart"
                self.tracker.schedule_timer(game_time, 15.0, "global", "minions_soon")
        elif name == "MinionsSpawning":
            category, key = "global", "MinionsSpawning"
        elif name == "GameEnd":
            result = event.get("Result")
            key = "victory" if result == "Win" else "defeat"
            category = "global"
        elif name == "InhibKilled":
            killer_team = self.player_team_cache.get(event["KillerName"])
            if killer_team == self.my_team: category, key = "team", "inhib_destroy"
            else: category, key = "team", "inhib_lost"
            self.tracker.schedule_timer(game_time, 285.0, "warnings", "inhib_respawning")
            self.tracker.schedule_timer(game_time, 300.0, "warnings", "inhib_live")
        elif name == "DragonKill":
            killer_team = self.player_team_cache.get(event["KillerName"])
            if killer_team == self.my_team: category, key = "team", "dragon_taken"
            else: category, key = "team", "dragon_lost"
            self.tracker.schedule_timer(game_time, 270.0, "warnings", "dragon_spawning")
            self.tracker.schedule_timer(game_time, 300.0, "warnings", "dragon_live")
        elif name == "BaronKill":
            killer_team = self.player_team_cache.get(event["KillerName"])
            if killer_team == self.my_team: category, key = "team", "baron_taken"
            else: category, key = "team", "baron_lost"
            self.tracker.schedule_timer(game_time, 330.0, "warnings", "baron_spawning")
            self.tracker.schedule_timer(game_time, 360.0, "warnings", "baron_live")
        elif name == "HordeKill":
            killer_team = self.player_team_cache.get(event["KillerName"])
            if killer_team == self.my_team: self.tracker.grubs_ally_score += 1
            else: self.tracker.grubs_enemy_score += 1
            self.tracker.grubs_killed += 1
            if self.tracker.grubs_killed >= 3:
                if self.tracker.grubs_ally_score > self.tracker.grubs_enemy_score: category, key = "team", "grubs_taken"
                else: category, key = "team", "grubs_lost"
                self.tracker.grubs_killed = 0
                self.tracker.grubs_ally_score = 0
                self.tracker.grubs_enemy_score = 0
            else: return 
        elif name == "HeraldKill":
            if self.player_team_cache.get(event["KillerName"]) == self.my_team: category, key = "team", "herald_taken"
            else: category, key = "team", "herald_lost"
        elif name == "TurretKilled":
            killer = event["KillerName"]
            killer_team = self.player_team_cache.get(killer)
            if killer == self.my_summoner or killer_team == self.my_team: category, key = "team", "turret_destroy"
            else: category, key = "team", "turret_lost"
        elif name == "Multikill":
            if event["KillerName"] == self.my_summoner: category, key = "player", f"multikill_{event['KillStreak']}"
        elif name == "Ace":
            acing_team = event.get("AcingTeam")
            key = "ace_enemy" if acing_team == self.my_team else "ace_us"
            category = "global"
        elif name == "ChampionKill":
            kill_sounds = self.handle_kill_logic(event["KillerName"], event["VictimName"])
            for cat, k in kill_sounds: self.app.trigger_audio(cat, k)
            return
        if category and key:
            self.app.trigger_audio(category, key)

    def run(self):
        while self.running:
            all_data = self.fetch_api("allgamedata")
            
            # --- CONNECTION LOSS LOGIC ---
            if not all_data:
                self.failure_count += 1
                if self.connected and self.failure_count > 5:
                    print("[Backend] Connection lost.")
                    self.app.set_status(False)
                    self.connected = False
                    self.event_index = 0
                    self.tracker = GameStateTracker() # Reset state
                time.sleep(0.25)
                continue
            
            # --- CONNECT LOGIC ---
            if not self.connected:
                if self.setup_identity(): 
                    self.connected = True
                    # FIX: Fast-forward event index so we don't replay the whole game
                    events = all_data.get("events", {}).get("Events", [])
                    if events:
                        self.event_index = len(events)
                        print(f"[Backend] Synced {self.event_index} existing events. Listening for new...")
                else:
                    time.sleep(1)
                    continue

            try:
                game_time = all_data["gameData"]["gameTime"]
                for cat, key in self.tracker.check_timers(game_time):
                    self.app.trigger_audio(cat, key)
                
                events = all_data["events"]["Events"]
                if len(events) > self.event_index:
                    for ev in events[self.event_index:]:
                        self.process_event(ev, game_time)
                    self.event_index = len(events)
            except: pass 
            time.sleep(0.25)

    def stop(self):
        self.running = False