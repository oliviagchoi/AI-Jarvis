import json
import math
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"
AUDIO_DIR = DEMO_DIR / "audio"
SCENARIOS_PATH = DEMO_DIR / "scenarios.json"
SAMPLE_RATE = 16000
AMPLITUDE = 12000


SCENARIOS = [
    {
        "id": "stressed_focus",
        "label": "Stressed Focus",
        "heart_rate": 108,
        "stress_level": "high",
        "transcript_override": "I have too much to do and I cannot focus right now.",
        "audio_file": "stressed_focus.wav",
        "tone_hz": 330,
        "duration_seconds": 1.8,
        "notes": "Use this to demo a calming, grounded response.",
    },
    {
        "id": "excited_win",
        "label": "Excited Win",
        "heart_rate": 96,
        "stress_level": "low",
        "transcript_override": "I just finished my project and I am really excited about it.",
        "audio_file": "excited_win.wav",
        "tone_hz": 520,
        "duration_seconds": 1.6,
        "notes": "Use this to show an upbeat response style.",
    },
    {
        "id": "sad_support",
        "label": "Sad Support",
        "heart_rate": 74,
        "stress_level": "moderate",
        "transcript_override": "I have been feeling down today and I could use encouragement.",
        "audio_file": "sad_support.wav",
        "tone_hz": 220,
        "duration_seconds": 2.0,
        "notes": "Use this to show warm, supportive behavior.",
    },
    {
        "id": "remember_preference",
        "label": "Remember Preference",
        "heart_rate": 72,
        "stress_level": "",
        "transcript_override": "Please remember that I like short answers.",
        "audio_file": "remember_preference.wav",
        "tone_hz": 410,
        "duration_seconds": 1.5,
        "notes": "Use this before a follow-up prompt to demo preference memory.",
    },
]


def ensure_dirs() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def build_tone_frames(frequency_hz: int, duration_seconds: float) -> bytes:
    total_frames = int(SAMPLE_RATE * duration_seconds)
    frames = bytearray()

    for index in range(total_frames):
        fade = min(1.0, index / 800, (total_frames - index) / 800)
        sample = int(
            AMPLITUDE
            * fade
            * math.sin((2.0 * math.pi * frequency_hz * index) / SAMPLE_RATE)
        )
        frames.extend(sample.to_bytes(2, byteorder="little", signed=True))

    return bytes(frames)


def write_wave(path: Path, *, frequency_hz: int, duration_seconds: float) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(
            build_tone_frames(
                frequency_hz=frequency_hz,
                duration_seconds=duration_seconds,
            )
        )


def write_scenarios_json() -> None:
    payload = {"generated_by": "scripts/generate_demo_assets.py", "scenarios": SCENARIOS}
    SCENARIOS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    ensure_dirs()
    write_scenarios_json()

    for scenario in SCENARIOS:
        write_wave(
            AUDIO_DIR / scenario["audio_file"],
            frequency_hz=int(scenario["tone_hz"]),
            duration_seconds=float(scenario["duration_seconds"]),
        )

    print(f"Wrote {len(SCENARIOS)} demo scenarios to {SCENARIOS_PATH}")
    print(f"Wrote audio clips to {AUDIO_DIR}")


if __name__ == "__main__":
    main()
