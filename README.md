# Rift Echo
**A Custom Announcer Tool for League of Legends**

Rift Echo replaces the default League of Legends announcer with a fully customizable, real-time audio engine. It tracks game state, kill streaks, and objective timers using the local League Client API (LCU) to deliver a responsive and immersive audio experience.

<img width="362" height="249" alt="Image" src="https://github.com/user-attachments/assets/7d4a4d07-75b1-4653-ba4d-ef9cb71221da"/>

## Features

* **Real-Time Event Tracking:** Reacts instantly to kills, deaths, turret plates, and objectives.
* **Smart Logic Engine:**
    * **Kill Streaks:** Tracks *Rampage*, *Godlike*, and *Legendary* streaks for both allies and enemies.
    * **Shutdowns:** Detects when a streak is ended.
    * **Smart Timers:** Automatically warns you 30 seconds before objectives spawn and announces the exact moment they go live.
* **Hextech UI:** A sleek, dark-mode interface inspired by the League client, built with CustomTkinter.
* **Voice Packs:** Seamless switching between different announcer packs without restarting.
* **Reliable Audio:** Uses `pyglet` with a custom queuing system to prevent audio overlaps and ensure every event is heard.

## Installation

### Prerequisites
* **Python 3.8+**
* **League of Legends** (Must be in game to connect)

### Setup
1.  **Clone or Download** this repository.
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Launch the App:**
    ```bash
    python main.py
    ```

## Usage

1.  **Start League of Legends:** The app status will show **DISCONNECTED** until you enter a match (loading screen or Rift).
2.  **Wait for Connection:** Once the game API is live, the status will turn **GREEN (CONNECTED)**.
3.  **Select Voice Pack:** Use the dropdown menu to choose your announcer.
4.  **Audio Controls:**
    * **Test Audio:** Plays a random sound from the current pack to check volume.
    * **Mute:** Temporarily disables all sounds.
    * **Refresh (⟳):** If you add a new pack folder while running, click this to detect it.

## Known Issues

* None

## Fixed Issues

* **[x]**: Announcements interrupt eachother, when more than one event happens at the same time or shortly after eachother, where they overlap.
* **[x]**: In 2 - 3 cases the wrong announcement is being played, when the event happens.
* **[x]**: Grubs & Herald announcement was played 30s too early.

## Creating Custom Voice Packs

Rift Echo supports unlimited custom voice packs. To create one:

1.  Navigate to the `assets/` folder.
2.  Create a new folder (e.g., `MyCustomPack`).
3.  Add your `.wav` files inside. **They must be named EXACTLY as listed below** to be recognized by the engine.

### Required Filenames

**Global & Game Flow**
* `GameStart.wav`
* `MinionsSpawning.wav`
* `minions_soon.wav` (Plays at 0:15)
* `FirstBlood.wav`
* `victory.wav`
* `defeat.wav`
* `ace_enemy.wav` (We aced them)
* `ace_us.wav` (We got aced)

**Player Events (You)**
* `kill.wav`
* `death.wav`
* `executed.wav`
* `multikill_2.wav` (Double Kill)
* `multikill_3.wav` (Triple Kill)
* `multikill_4.wav` (Quadra Kill)
* `multikill_5.wav` (Penta Kill)
* `rampage.wav` (3 kill streak)
* `godlike.wav` (6 kill streak)
* `legendary.wav` (8+ kill streak)
* `shutdown.wav` (You lost your streak)

**Team Events (Allies/Enemies)**
* `ally_slain.wav` / `enemy_slain.wav`
* `executed_ally.wav` / `executed_enemy.wav`
* `ally_rampage.wav` / `enemy_rampage.wav`
* `ally_godlike.wav` / `enemy_godlike.wav`
* `ally_legendary.wav` / `enemy_legendary.wav`
* `shutdown_ally.wav` (Ally lost streak)
* `shutdown_enemy.wav` (We shut down an enemy)

**Objectives (Taken/Lost)**
* `turret_destroy.wav` / `turret_lost.wav`
* `inhib_destroy.wav` / `inhib_lost.wav`
* `grubs_taken.wav` / `grubs_lost.wav`
* `herald_taken.wav` / `herald_lost.wav`
* `dragon_taken.wav` / `dragon_lost.wav`
* `baron_taken.wav` / `baron_lost.wav`

**Timers & Spawns**
* **Warnings (30s before spawn):**
    * `grubs_spawning.wav`
    * `herald_spawning.wav`
    * `dragon_spawning.wav`
    * `baron_spawning.wav`
    * `inhib_respawning.wav` (15s before respawn)
* **Live Events (Exact spawn time):**
    * `grubs_live.wav`
    * `herald_live.wav`
    * `dragon_live.wav`
    * `baron_live.wav`
    * `inhib_live.wav`

## Troubleshooting

**"Status stays DISCONNECTED"**
* Ensure you are actually *in a game* (Training Tool works best for testing). The API does not run in the client launcher, only in the game window.
* Ensure your firewall is not blocking connections to `127.0.0.1:2999`.

**"Audio is cutting off"**
* Rift Echo uses `pyglet`. If sound drivers are busy, it might lag. Ensure no other exclusive-mode audio apps are interfering.

**"Missing Asset Error"**
* Check the console/terminal window. It will tell you exactly which filename is missing from your pack.

## License
This project is open-source. Feel free to fork, mod, and create your own chaos on the Rift!