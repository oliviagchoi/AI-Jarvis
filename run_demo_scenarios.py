import argparse
import json
import mimetypes
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "demo" / "scenarios.json"


def load_scenarios() -> list[dict]:
    payload = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    return list(payload.get("scenarios", []))


def encode_multipart(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = "jarvis-demo-boundary"
    parts: list[bytes] = []

    for name, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                f"{value}\r\n".encode(),
            ]
        )

    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="audio"; filename="{file_path.name}"\r\n'
            ).encode(),
            f"Content-Type: {mime_type}\r\n\r\n".encode(),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )

    return b"".join(parts), boundary


def post_voice(base_url: str, scenario: dict) -> dict:
    audio_path = ROOT / "demo" / "audio" / str(scenario["audio_file"])
    fields = {
        "session_id": f"demo-{scenario['id']}",
        "transcript_override": str(scenario["transcript_override"]),
    }

    if scenario.get("heart_rate"):
        fields["wellness_heart_rate"] = str(scenario["heart_rate"])
    if scenario.get("stress_level"):
        fields["wellness_stress_level"] = str(scenario["stress_level"])

    body, boundary = encode_multipart(fields, audio_path)
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/voice",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bundled Jarvis demo scenarios.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for the running Jarvis app.",
    )
    parser.add_argument(
        "--scenario",
        default="all",
        help="Scenario id to run, or 'all' to run every demo scenario.",
    )
    args = parser.parse_args()

    scenarios = load_scenarios()
    selected = (
        scenarios
        if args.scenario == "all"
        else [scenario for scenario in scenarios if scenario["id"] == args.scenario]
    )

    if not selected:
        print(f"No scenario found for '{args.scenario}'.")
        return 1

    for scenario in selected:
        print(f"\n=== {scenario['label']} ({scenario['id']}) ===")
        print(f"Heart rate: {scenario['heart_rate']}")
        print(f"Stress level: {scenario['stress_level'] or 'off'}")
        print(f"Transcript: {scenario['transcript_override']}")
        try:
            payload = post_voice(args.base_url, scenario)
        except urllib.error.URLError as exc:
            print(f"Request failed: {exc}")
            return 1

        print(f"Detected emotion: {payload.get('detected_emotion')}")
        print(f"Assistant reply: {payload.get('assistant_message')}")
        print(f"Artifact: {payload.get('audio_path')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
