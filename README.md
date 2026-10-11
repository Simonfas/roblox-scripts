# Roblox Scripts

A collection of simple Python scripts for Roblox on **Windows**.

## How the scripts interact with Roblox

These are **external Windows keyboard-automation scripts**, not Roblox exploits or modifications. They simulate ordinary key presses using Python's `pynput` library and check the active window title before sending input.

They **do not inject code into Roblox, modify Roblox files, edit game memory, or call internal Roblox functions**. They also do not change game scripts or server data directly. Roblox receives the simulated keyboard input and may react to it in the same way as regular player input.

- **AFK:** Holds A and D alternately to simulate movement.
- **Hold E:** Repeatedly holds and releases E.
- **Piano:** Reads locally saved piano sheets and plays them as simulated keyboard notes.

**Important:** This is still gameplay automation. Not modifying Roblox does **not** mean that automated input is undetectable or allowed in every Roblox experience. Check the applicable rules and use these scripts responsibly.

## Scripts

- **`afk.py`** — Alternates between holding A and D while Roblox is the active window.
- **`hold_e_loop.py`** — Repeatedly presses and releases E while Roblox is active.
- **`piano/player.py`** — Plays Roblox piano sheets from the `piano/songs` folder.

## Recommended: Python Executor (easy method)

**[Get Python Executor here](https://github.com/Simonfas/python-executor)** — a Windows app that makes running these scripts easier, without using a terminal for every run.

1. Download Python Executor from its GitHub repository and launch **`run.bat`**.
2. Let it check Python and prepare the required libraries. It attempts to install or update Python when needed; Windows permissions may require manual installation.
3. Select the script you want to run (`afk.py`, `hold_e_loop.py`, or `piano/player.py`).
4. Select your Roblox window and start the script.
5. For the piano player, enter a song ID when prompted (for example, `damned`). The Executor can also show script `input()` prompts in a popup.

Python Executor automatically detects imports, installs missing packages, and reuses installed libraries between scripts. It also displays live logs and checks scripts for suspicious patterns before running them. **Its security scan cannot guarantee safety.**

**Stopping:** Use the Executor's Stop control or **Ctrl+C**. The piano player also supports **Home** to stop.

## Manual method (optional)

Install Python on Windows, then run these commands from the repository folder:

```powershell
python -m pip install pyautogui pygetwindow psutil pynput pywin32
python afk.py
```

Other scripts:

```powershell
python hold_e_loop.py
python piano/player.py list
python piano/player.py damned
```

The piano player's song IDs are filenames inside `piano/songs`, without `.txt` or `.json`. Songs can use `.txt` with optional `.meta.json` metadata, or a `.json` song file.

## Notes

- **Windows only.** Keep Roblox focused while the scripts are running.
- Close Roblox chat before using keyboard automation.
- Only use automation where permitted by the game or experience rules.
