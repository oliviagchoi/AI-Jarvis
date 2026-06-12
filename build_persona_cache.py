import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESCRIPTORS_PATH = ROOT / "corpus" / "descriptors.csv"
DEFAULT_PERSONAS_PATH = ROOT / "corpus" / "personas.json"
DEFAULT_OUTPUT_PATH = ROOT / "corpus" / "persona_guidance.json"
DEFAULT_PROMPT_PATH = ROOT / "prompts" / "persona_composition.txt"
DEFAULT_BEDROCK_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

EMOTIONS = [
    "neutral",
    "calm",
    "happy",
    "excited",
    "surprised",
    "sad",
    "fear",
    "angry",
    "disgust",
]

DESCRIPTOR_LABELS = {
    "direct": "direct communication",
    "indirect": "indirect communication",
    "suppression": "suppression regulation",
    "expressive": "expressive regulation",
    "reappraisal": "cognitive reappraisal",
    "instrumental_support": "instrumental support",
    "emotional_support": "emotional support",
    "mixed_support": "mixed support",
    "avoidant_attachment": "avoidant attachment",
    "anxious_attachment": "anxious attachment",
    "secure_attachment": "secure attachment",
}

EMOTION_LABELS = {
    "neutral": "a neutral state",
    "calm": "calm",
    "happy": "happiness",
    "excited": "excitement",
    "surprised": "surprise",
    "sad": "sadness",
    "fear": "fear",
    "angry": "anger",
    "disgust": "disgust",
}


def load_descriptors(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    descriptors: dict[tuple[str, str], dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            descriptor_id = str(row.get("descriptor_id", "")).strip()
            emotion = str(row.get("emotion", "")).strip().lower()
            if descriptor_id and emotion:
                descriptors[(descriptor_id, emotion)] = {
                    "descriptor_id": descriptor_id,
                    "emotion": emotion,
                    "guidance": str(row.get("guidance", "")).strip(),
                    "source_short": str(row.get("source_short", "")).strip(),
                }
    return descriptors


def load_personas(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_cache(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_sentence(text: str) -> str:
    text = " ".join(text.split()).strip(" .")
    return text


def split_guidance(guidance: str) -> tuple[str, str]:
    marker = " Avoid "
    if marker not in guidance:
        return normalize_sentence(guidance), ""
    do_part, avoid_part = guidance.split(marker, maxsplit=1)
    return normalize_sentence(do_part), normalize_sentence(avoid_part)


def collect_rows(
    *,
    persona: dict[str, Any],
    emotion: str,
    descriptors: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for descriptor_id in persona.get("descriptors", []):
        row = descriptors.get((str(descriptor_id), emotion))
        if row is None:
            raise KeyError(
                f"Missing descriptor row for descriptor_id={descriptor_id} emotion={emotion}"
            )
        rows.append(row)
    return rows


def render_prompt(
    *,
    template: str,
    persona: dict[str, Any],
    emotion: str,
    rows: list[dict[str, str]],
) -> str:
    snippets = "\n\n".join(
        (
            f"- {DESCRIPTOR_LABELS.get(row['descriptor_id'], row['descriptor_id'])}: "
            f"{row['guidance']} Source: {row['source_short']}"
        )
        for row in rows
    )
    rendered = template.replace("{{PERSONA_NAME}}", str(persona["display_name"]))
    rendered = rendered.replace("{{TONE_OVERLAY}}", str(persona["tone_overlay"]))
    rendered = rendered.replace("{{EMOTION}}", emotion)
    return rendered.replace("{{DESCRIPTOR_SNIPPETS}}", snippets)


def compose_local(
    *,
    persona: dict[str, Any],
    emotion: str,
    rows: list[dict[str, str]],
) -> str:
    do_parts: list[str] = []
    avoid_parts: list[str] = []
    for row in rows:
        do_part, avoid_part = split_guidance(row["guidance"])
        label = DESCRIPTOR_LABELS.get(row["descriptor_id"], row["descriptor_id"])
        if do_part:
            do_parts.append(f"{label}: {do_part}")
        if avoid_part:
            avoid_parts.append(avoid_part)

    tone = normalize_sentence(str(persona.get("tone_overlay", "")))
    emotion_label = EMOTION_LABELS.get(emotion, emotion)
    do_sentence = (
        f"For {emotion_label}, combine these profile cues: " + "; ".join(do_parts) + "."
    )
    avoid_sentence = (
        "Avoid " + "; ".join(avoid_parts) + "."
        if avoid_parts
        else "Avoid adding unsupported emotional interpretation."
    )
    return " ".join(part for part in [tone + ".", do_sentence, avoid_sentence] if part)


def extract_bedrock_text(response_body: dict[str, Any]) -> str:
    content = response_body.get("content", [])
    if isinstance(content, list):
        texts = [
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("text")
        ]
        if texts:
            return "\n".join(texts).strip()
    raise ValueError(f"Unsupported Bedrock response format: {response_body}")


def compose_bedrock(
    *,
    prompt: str,
    model_id: str,
    region: str,
    profile_name: str | None,
) -> str:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise RuntimeError("Install boto3 and botocore to use --provider bedrock.") from exc

    session_kwargs: dict[str, str] = {}
    if profile_name:
        session_kwargs["profile_name"] = profile_name
    session = boto3.Session(**session_kwargs)
    client = session.client("bedrock-runtime", region_name=region)
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 220,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"Bedrock composition failed: {exc}") from exc

    guidance = extract_bedrock_text(json.loads(response["body"].read())).strip()
    if not guidance:
        raise RuntimeError("Bedrock returned an empty guidance string.")
    return guidance


def write_cache(path: Path, cache: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the persona-emotion guidance cache for Jarvis."
    )
    parser.add_argument("--descriptors", type=Path, default=DEFAULT_DESCRIPTORS_PATH)
    parser.add_argument("--personas", type=Path, default=DEFAULT_PERSONAS_PATH)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--persona", help="Only build one persona_id.")
    parser.add_argument("--emotion", choices=EMOTIONS, help="Only build one emotion.")
    parser.add_argument("--force", action="store_true", help="Rebuild existing cells.")
    parser.add_argument(
        "--provider",
        choices=["local", "bedrock"],
        default="local",
        help="Use deterministic local composition or Bedrock prompt synthesis.",
    )
    parser.add_argument(
        "--model-id",
        default=os.getenv("BEDROCK_MODEL_ID", DEFAULT_BEDROCK_MODEL_ID),
    )
    parser.add_argument("--region", default=os.getenv("BEDROCK_REGION", "us-west-2"))
    parser.add_argument(
        "--aws-profile",
        default=os.getenv("AWS_PROFILE_NAME") or os.getenv("AWS_PROFILE"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    descriptors = load_descriptors(args.descriptors)
    personas = load_personas(args.personas)
    prompt_template = args.prompt.read_text(encoding="utf-8")
    cache = load_cache(args.output)
    emotions = [args.emotion] if args.emotion else EMOTIONS
    built = 0
    skipped = 0

    for persona in personas:
        persona_id = str(persona["persona_id"])
        if args.persona and persona_id != args.persona:
            continue

        persona_cache = cache.setdefault(persona_id, {})
        for emotion in emotions:
            if persona_cache.get(emotion) and not args.force:
                skipped += 1
                continue

            rows = collect_rows(
                persona=persona,
                emotion=emotion,
                descriptors=descriptors,
            )
            if args.provider == "bedrock":
                prompt = render_prompt(
                    template=prompt_template,
                    persona=persona,
                    emotion=emotion,
                    rows=rows,
                )
                guidance = compose_bedrock(
                    prompt=prompt,
                    model_id=args.model_id,
                    region=args.region,
                    profile_name=args.aws_profile,
                )
            else:
                guidance = compose_local(persona=persona, emotion=emotion, rows=rows)

            persona_cache[emotion] = guidance
            built += 1

    write_cache(args.output, cache)
    print(
        f"Wrote {args.output} with {built} built cell(s) and {skipped} skipped cell(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
