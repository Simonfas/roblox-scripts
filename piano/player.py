import time
import json
import sys
from pathlib import Path

import win32gui
from pynput.keyboard import Controller, Listener, Key

keyboard = Controller()

TARGET_WINDOW = "Roblox"
stop_script = False

WHITE_KEYS = set("1234567890qwertyuiopasdfghjklzxcvbnm")

SHIFT_SYMBOLS = {
    "!": "1",
    "@": "2",
    "#": "3",  
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",  
    "*": "8",
    "(": "9",
    ")": "0",  
    "?": "/",
}

BLACK_LETTER_KEYS = set("QWET YIOPS DGHJLZCVB".replace(" ", ""))

DEFAULT_SUBDIVISION = 2.0 

KEY_HOLD_RATIO = 0.18
MIN_KEY_HOLD = 0.012
MAX_KEY_HOLD = 0.045


def tempo_from_bpm(bpm: float):
    beat = 60.0 / float(bpm)
    note_delay = beat / DEFAULT_SUBDIVISION
    pause_per_dash = note_delay
    chord_delay = note_delay * 0.72
    return note_delay, pause_per_dash, chord_delay


def normalize_song(song: str) -> str:
    dash_chars = (
        "\u2010",
        "\u2011",
        "\u2012",
        "\u2013",
        "\u2014",
        "\u2015", 
        "\u2212", 
    )

    for dash in dash_chars:
        song = song.replace(dash, "-")

    return song.replace("\t", " ")


def is_target_window_active() -> bool:
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    return TARGET_WINDOW.lower() in (title or "").lower()


def is_piano_key(ch: str) -> bool:
    if len(ch) != 1:
        return False

    if ch in WHITE_KEYS:
        return True

    if ch in SHIFT_SYMBOLS:
        return True

    if ch in BLACK_LETTER_KEYS:
        return True

    return False


def key_needs_shift(ch: str) -> bool:
    return ch in SHIFT_SYMBOLS or ch in BLACK_LETTER_KEYS


def base_key_for(ch: str) -> str:
    if ch in SHIFT_SYMBOLS:
        return SHIFT_SYMBOLS[ch]

    if ch in BLACK_LETTER_KEYS:
        return ch.lower()

    return ch


def safe_press(key):
    try:
        keyboard.press(key)
    except Exception as exc:
        print(f"⚠️ Kunne ikke trykke tast {key!r}: {exc}")


def safe_release(key):
    try:
        keyboard.release(key)
    except Exception:
        pass


def get_single_key_hold(note_delay: float) -> float:
    return max(
        MIN_KEY_HOLD,
        min(MAX_KEY_HOLD, note_delay * KEY_HOLD_RATIO),
    )


def play_key(k: str, note_delay: float):
    if not is_piano_key(k):
        return

    hold_time = min(get_single_key_hold(note_delay), note_delay)
    shifted = key_needs_shift(k)
    base = base_key_for(k)

    start = time.perf_counter()

    if shifted:
        safe_press(Key.shift)
        safe_press(base)
        time.sleep(hold_time)
        safe_release(base)
        safe_release(Key.shift)
    else:
        safe_press(base)
        time.sleep(hold_time)
        safe_release(base)

    elapsed = time.perf_counter() - start
    remaining = note_delay - elapsed

    if remaining > 0:
        time.sleep(remaining)


def play_chord(keys: str, note_delay: float, chord_delay: float):
    valid = [k for k in keys if is_piano_key(k)]

    if not valid:
        return

    normal_keys = []
    shifted_keys = []

    for k in valid:
        base = base_key_for(k)

        if key_needs_shift(k):
            shifted_keys.append(base)
        else:
            normal_keys.append(base)

    start = time.perf_counter()

    for base in normal_keys:
        safe_press(base)

    if shifted_keys:
        safe_press(Key.shift)

        for base in shifted_keys:
            safe_press(base)

    hold_time = min(chord_delay, note_delay)

    if hold_time > 0:
        time.sleep(hold_time)

    for base in reversed(shifted_keys):
        safe_release(base)

    if shifted_keys:
        safe_release(Key.shift)

    for base in reversed(normal_keys):
        safe_release(base)

    elapsed = time.perf_counter() - start
    remaining = note_delay - elapsed

    if remaining > 0:
        time.sleep(remaining)


def play_fast_sequence(keys: str, note_delay: float):
    valid = [k for k in keys if is_piano_key(k)]

    if not valid:
        return

    total_duration = note_delay
    per_note = max(0.018, total_duration / len(valid))

    for k in valid:
        if stop_script:
            break

        hold = min(0.022, per_note * 0.45)
        shifted = key_needs_shift(k)
        base = base_key_for(k)

        start = time.perf_counter()

        if shifted:
            safe_press(Key.shift)
            safe_press(base)
            time.sleep(hold)
            safe_release(base)
            safe_release(Key.shift)
        else:
            safe_press(base)
            time.sleep(hold)
            safe_release(base)

        elapsed = time.perf_counter() - start
        rest = per_note - elapsed

        if rest > 0:
            time.sleep(rest)


def play_song(
    song: str,
    note_delay: float,
    pause_per_dash: float,
    chord_delay: float,
):
    global stop_script

    song = normalize_song(song)
    i = 0

    while i < len(song) and not stop_script:
        ch = song[i]

        if ch == "[":
            end = song.find("]", i + 1)

            if end == -1:
                print(f"⚠️ Manglende ] ved position {i}")
                i += 1
                continue

            chord = "".join(
                c for c in song[i + 1:end]
                if is_piano_key(c)
            )

            if chord:
                play_chord(chord, note_delay, chord_delay)

            i = end + 1
            continue

        if ch == "{":
            end = song.find("}", i + 1)

            if end == -1:
                print(f"⚠️ Manglende }} ved position {i}")
                i += 1
                continue

            seq = "".join(
                c for c in song[i + 1:end]
                if is_piano_key(c)
            )

            if seq:
                play_fast_sequence(seq, note_delay)

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

        if ch.isspace() or ch == "/":
            i += 1
            continue

        if is_piano_key(ch):
            play_key(ch, note_delay)

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
        "bpm": 123,
        "song": "..."
      }

    eller:
      {
        "name": "Titel",
        "tempo": {
          "NOTE_DELAY": 0.1,
          "PAUSE_PER_DASH": 0.1,
          "CHORD_DELAY": 0.07
        },
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

        return (
            name,
            song_text,
            note_delay,
            pause_per_dash,
            chord_delay,
            float(bpm),
        )

    tempo = data.get("tempo", {}) or {}

    note_delay = float(tempo.get("NOTE_DELAY", 0.10))
    pause_per_dash = float(
        tempo.get("PAUSE_PER_DASH", note_delay)
    )
    chord_delay = float(
        tempo.get("CHORD_DELAY", note_delay * 0.72)
    )

    return (
        name,
        song_text,
        note_delay,
        pause_per_dash,
        chord_delay,
        None,
    )


def load_song_any(songs_dir: Path, song_id: str):
    """
    Understøtter:
      - songs/<id>.json
      - songs/<id>.txt + songs/<id>.meta.json
    """
    json_path = songs_dir / f"{song_id}.json"
    txt_path = songs_dir / f"{song_id}.txt"
    meta_path = songs_dir / f"{song_id}.meta.json"

    if json_path.exists():
        return load_song_from_json(songs_dir, song_id)

    if txt_path.exists():
        song_text = txt_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        if not song_text.strip():
            raise ValueError(f"{txt_path} er tom.")

        name = song_id
        bpm = None

        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            name = meta.get("name", song_id)
            bpm = meta.get("bpm", None)

        if bpm is not None:
            note_delay, pause_per_dash, chord_delay = tempo_from_bpm(
                float(bpm)
            )

            return (
                name,
                song_text,
                note_delay,
                pause_per_dash,
                chord_delay,
                float(bpm),
            )

        note_delay = 0.10
        pause_per_dash = note_delay
        chord_delay = note_delay * 0.72

        return (
            name,
            song_text,
            note_delay,
            pause_per_dash,
            chord_delay,
            None,
        )

    raise FileNotFoundError(
        f"Kunne ikke finde {song_id}.json eller {song_id}.txt"
    )


def import_txt_to_json(
    songs_dir: Path,
    input_txt: Path,
    song_id: str,
    name: str,
    bpm: float,
):
    """
    Importér en rå txt til en JSON-sangfil.
    """
    if not input_txt.exists():
        raise FileNotFoundError(f"Input fil findes ikke: {input_txt}")

    song_text = input_txt.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    if not song_text.strip():
        raise ValueError("Input txt er tom.")

    out = {
        "name": name,
        "bpm": float(bpm),
        "song": song_text,
    }

    out_path = songs_dir / f"{song_id}.json"

    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

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
            print(
                'Brug: python player.py import input.txt '
                'songid "Song Name" 123'
            )
            return

        input_txt = Path(sys.argv[2])
        song_id = sys.argv[3]
        song_name = sys.argv[4]
        bpm = float(sys.argv[5])

        import_txt_to_json(
            songs_dir,
            input_txt,
            song_id,
            song_name,
            bpm,
        )
        return

    if len(sys.argv) >= 2 and sys.argv[1].lower() != "bpm":
        song_id = sys.argv[1].strip()

        try:
            (
                name,
                song_text,
                NOTE_DELAY,
                PAUSE_PER_DASH,
                CHORD_DELAY,
                bpm,
            ) = load_song_any(songs_dir, song_id)

            print(f"Valgt sang: {name} ({song_id})")

            if bpm is not None:
                print(
                    f"Tempo fra BPM={bpm:g} -> "
                    f"NOTE_DELAY={NOTE_DELAY:.3f}, "
                    f"PAUSE_PER_DASH={PAUSE_PER_DASH:.3f}, "
                    f"CHORD_DELAY={CHORD_DELAY:.3f}"
                )
            else:
                print(
                    f"Tempo (raw) -> "
                    f"NOTE_DELAY={NOTE_DELAY:.3f}, "
                    f"PAUSE_PER_DASH={PAUSE_PER_DASH:.3f}, "
                    f"CHORD_DELAY={CHORD_DELAY:.3f}"
                )

        except Exception as e:
            print("❌ Kunne ikke loade sang:", e)
            print("Tip: python player.py list")
            return

    else:
        bpm = None

        if len(sys.argv) >= 3 and sys.argv[1].lower() == "bpm":
            try:
                bpm = float(sys.argv[2])
            except Exception:
                bpm = None

        if bpm is None:
            try:
                bpm = float(
                    input("Indtast BPM (fx 123): ").strip()
                )
            except Exception:
                bpm = 60.0

        (
            NOTE_DELAY,
            PAUSE_PER_DASH,
            CHORD_DELAY,
        ) = tempo_from_bpm(bpm)

        print(
            f"Tempo fra BPM={bpm:g} -> "
            f"NOTE_DELAY={NOTE_DELAY:.3f}, "
            f"PAUSE_PER_DASH={PAUSE_PER_DASH:.3f}, "
            f"CHORD_DELAY={CHORD_DELAY:.3f}"
        )

        print(
            "⚠️ BPM mode spiller kun sange fra "
            "songs/<id>.json eller songs/<id>.txt "
            "(kør: python player.py <song_id>)"
        )
        return

    listener = Listener(on_press=on_press)
    listener.start()

    print("Venter på Roblox vindue... (HOME = stop)")

    try:
        while not stop_script:
            if is_target_window_active():
                print("Spiller sang...")

                play_song(
                    song_text,
                    NOTE_DELAY,
                    PAUSE_PER_DASH,
                    CHORD_DELAY,
                )

                stop_script = True
            else:
                time.sleep(0.25)

    except KeyboardInterrupt:
        stop_script = True

    print("Script afsluttet.")


if __name__ == "__main__":
    main()
