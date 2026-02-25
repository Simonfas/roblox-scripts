import time
import json
import sys
from pathlib import Path

import win32gui
from pynput.keyboard import Controller, Listener, Key

keyboard = Controller()

TARGET_WINDOW = "Roblox"
stop_script = False

def tempo_from_bpm(bpm: float):
    """
    Konverter BPM til delays.
    Antagelser:
      - NOTE_DELAY ~ 1/8 node (eighth note)
      - '-' pause ~ 1/4 node (quarter note / beat)
      - CHORD_DELAY ~ 90% af NOTE_DELAY
    """
    beat = 60.0 / float(bpm)      
    note_delay = beat / 2.0         
    pause_per_dash = beat           
    chord_delay = note_delay * 0.90
    return note_delay, pause_per_dash, chord_delay

def is_target_window_active() -> bool:
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    return TARGET_WINDOW.lower() in (title or "").lower()

def play_key(k: str):
    keyboard.press(k)
    keyboard.release(k)


def play_chord(keys: str, chord_delay: float):
    for k in keys:
        keyboard.press(k)
    time.sleep(chord_delay)
    for k in keys:
        keyboard.release(k)


def play_fast_sequence(keys: str, fast_delay: float):
    for k in keys:
        keyboard.press(k)
        keyboard.release(k)
        time.sleep(fast_delay)


def is_note_char(ch: str) -> bool:
    return ch.isalnum()

def play_song(song: str, note_delay: float, pause_per_dash: float, chord_delay: float):
    global stop_script
    i = 0

    fast_sequence_delay = max(0.005, note_delay * 0.35)

    while i < len(song) and not stop_script:
        ch = song[i]

        if ch == "[":
            end = song.find("]", i)
            if end == -1:
                i += 1
                continue

            chord = "".join(c for c in song[i + 1:end] if is_note_char(c))
            if chord:
                play_chord(chord, chord_delay)

            i = end + 1
            continue

        if ch == "{":
            end = song.find("}", i)
            if end == -1:
                i += 1
                continue

            seq = "".join(c for c in song[i + 1:end] if is_note_char(c))
            if seq:
                play_fast_sequence(seq, fast_sequence_delay)

            i = end + 1
            continue

        if ch == "-":
            dash_count = 1
            while i + 1 < len(song) and song[i + 1] == "-":
                dash_count += 1
                i += 1

            time.sleep(pause_per_dash * dash_count)
            i += 1
            continue

        if ch.isspace():
            i += 1
            continue

        if ch == "/":
            i += 1
            continue

        if is_note_char(ch):
            play_key(ch)
            time.sleep(note_delay)

        i += 1

def on_press(key):
    global stop_script
    if key == Key.home:
        print("HOME trykket — afslutter script")
        stop_script = True
        return False

def list_songs(songs_dir: Path):
    ids = set()

    for f in songs_dir.glob("*.json"):
        if f.name.endswith(".meta.json"):
            continue
        ids.add(f.stem)

    for f in songs_dir.glob("*.txt"):
        ids.add(f.stem)

    if not ids:
        print("Ingen sange fundet i:", songs_dir)
        return

    print("Tilgængelige sange:")
    for sid in sorted(ids):
        print(" -", sid)


def load_song_from_json(songs_dir: Path, song_id: str):
    """
    Forventet format:
      {
        "name": "Titel",
        "bpm": 55,
        "song": "..."
      }
    eller:
      {
        "name": "Titel",
        "tempo": { "NOTE_DELAY": 0.1, "PAUSE_PER_DASH": 0.4, "CHORD_DELAY": 0.09 },
        "song": "..."
      }
    """
    path = songs_dir / f"{song_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    name = data.get("name", song_id)
    song_text = data.get("song", "")

    if not str(song_text).strip():
        raise ValueError(f"Sangfilen {path} har ingen 'song' tekst.")

    bpm = data.get("bpm", None)
    if bpm is not None:
        note_delay, pause_per_dash, chord_delay = tempo_from_bpm(float(bpm))
        return name, song_text, note_delay, pause_per_dash, chord_delay, float(bpm)

    tempo = data.get("tempo", {}) or {}
    note_delay = float(tempo.get("NOTE_DELAY", 0.10))
    pause_per_dash = float(tempo.get("PAUSE_PER_DASH", 0.35))
    chord_delay = float(tempo.get("CHORD_DELAY", 0.09))
    return name, song_text, note_delay, pause_per_dash, chord_delay, None


def load_song_any(songs_dir: Path, song_id: str):
    """
    Understøtter:
      - songs/<id>.json  (med bpm eller tempo + song)
      - songs/<id>.txt + songs/<id>.meta.json  (rå tekst + bpm)
    """
    json_path = songs_dir / f"{song_id}.json"
    txt_path = songs_dir / f"{song_id}.txt"
    meta_path = songs_dir / f"{song_id}.meta.json"

    if json_path.exists():
        return load_song_from_json(songs_dir, song_id)

    if txt_path.exists():
        song_text = txt_path.read_text(encoding="utf-8", errors="ignore")
        if not song_text.strip():
            raise ValueError(f"{txt_path} er tom.")

        name = song_id
        bpm = None

        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            name = meta.get("name", song_id)
            bpm = meta.get("bpm", None)

        if bpm is not None:
            note_delay, pause_per_dash, chord_delay = tempo_from_bpm(float(bpm))
            return name, song_text, note_delay, pause_per_dash, chord_delay, float(bpm)

        return name, song_text, 0.10, 0.35, 0.09, None

    raise FileNotFoundError(f"Kunne ikke finde {song_id}.json eller {song_id}.txt")


def import_txt_to_json(songs_dir: Path, input_txt: Path, song_id: str, name: str, bpm: float):
    """
    Importér en rå txt (med linjeskift) til en JSON sangfil.
    Linjeskift bliver automatisk escaped som \\n, så du ikke skal gøre noget manuelt.
    """
    if not input_txt.exists():
        raise FileNotFoundError(f"Input fil findes ikke: {input_txt}")

    song_text = input_txt.read_text(encoding="utf-8", errors="ignore")
    if not song_text.strip():
        raise ValueError("Input txt er tom.")

    out = {
        "name": name,
        "bpm": float(bpm),
        "song": song_text
    }

    out_path = songs_dir / f"{song_id}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Importeret til: {out_path}")

def main():
    global stop_script

    songs_dir = Path(__file__).parent / "songs"
    songs_dir.mkdir(exist_ok=True)

    if len(sys.argv) >= 2 and sys.argv[1].lower() == "list":
        list_songs(songs_dir)
        return

    if len(sys.argv) >= 2 and sys.argv[1].lower() == "import":
        if len(sys.argv) < 6:
            print('Brug: python player.py import input.txt songid "Song Name" 55')
            return
        input_txt = Path(sys.argv[2])
        song_id = sys.argv[3]
        song_name = sys.argv[4]
        bpm = float(sys.argv[5])
        import_txt_to_json(songs_dir, input_txt, song_id, song_name, bpm)
        return

    if len(sys.argv) >= 2 and sys.argv[1].lower() != "bpm":
        song_id = sys.argv[1].strip()
        try:
            name, song_text, NOTE_DELAY, PAUSE_PER_DASH, CHORD_DELAY, bpm = load_song_any(songs_dir, song_id)
            print(f"Valgt sang: {name} ({song_id})")
            if bpm is not None:
                print(f"Tempo fra BPM={bpm:g} -> NOTE_DELAY={NOTE_DELAY:.3f}, PAUSE_PER_DASH={PAUSE_PER_DASH:.3f}, CHORD_DELAY={CHORD_DELAY:.3f}")
            else:
                print(f"Tempo (raw) -> NOTE_DELAY={NOTE_DELAY:.3f}, PAUSE_PER_DASH={PAUSE_PER_DASH:.3f}, CHORD_DELAY={CHORD_DELAY:.3f}")
        except Exception as e:
            print("❌ Kunne ikke loade sang:", e)
            print("Tip: python player.py list")
            return
    else:
        bpm = None
        if len(sys.argv) >= 3 and sys.argv[1].lower() == "bpm":
            try:
                bpm = float(sys.argv[2])
            except:
                bpm = None

        if bpm is None:
            try:
                bpm = float(input("Indtast BPM (fx 55): ").strip())
            except:
                bpm = 60.0

        NOTE_DELAY, PAUSE_PER_DASH, CHORD_DELAY = tempo_from_bpm(bpm)
        song_text = ""
        print(f"Tempo fra BPM={bpm:g} -> NOTE_DELAY={NOTE_DELAY:.3f}, PAUSE_PER_DASH={PAUSE_PER_DASH:.3f}, CHORD_DELAY={CHORD_DELAY:.3f}")
        print("⚠️ BPM mode spiller kun sange fra songs/<id>.json eller songs/<id>.txt (kør: python player.py <song_id>)")
        return

    listener = Listener(on_press=on_press)
    listener.start()

    print("Venter på Roblox vindue... (HOME = stop)")

    try:
        while not stop_script:
            if is_target_window_active():
                print("Spiller sang...")
                play_song(song_text, NOTE_DELAY, PAUSE_PER_DASH, CHORD_DELAY)
                time.sleep(1)
            else:
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    print("Script afsluttet.")


if __name__ == "__main__":
    main()
