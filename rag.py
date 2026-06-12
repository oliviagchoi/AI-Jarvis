import csv
import json
import logging
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
DESCRIPTORS_PATH = BASE_DIR / "corpus" / "descriptors.csv"
GUIDANCE_PATH = BASE_DIR / "corpus" / "persona_guidance.json"
PERSONAS_PATH = BASE_DIR / "corpus" / "personas.json"

DEFAULT_PERSONA = "default_danny"
DEFAULT_EMOTION = "neutral"
FALLBACK_GUIDANCE = (
    "Respond warmly, clearly, and helpfully. Keep the answer grounded and concise."
)

logger = logging.getLogger(__name__)


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load %s: %s", path, exc)
        return fallback


def _normalize(value: str | None, default: str) -> str:
    normalized = (value or default).strip().lower()
    return normalized or default


def _load_descriptor_guidance(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = csv.DictReader(handle)
            guidance: dict[str, dict[str, dict[str, str]]] = {}
            for row in rows:
                descriptor_id = _normalize(row.get("descriptor_id"), "")
                emotion = _normalize(row.get("emotion"), DEFAULT_EMOTION)
                if not descriptor_id:
                    continue
                guidance.setdefault(descriptor_id, {})[emotion] = {
                    "guidance": row.get("guidance", "").strip(),
                    "source_short": row.get("source_short", "").strip(),
                }
            return guidance
    except OSError as exc:
        logger.warning("Could not load %s: %s", path, exc)
        return {}


PERSONA_GUIDANCE: dict[str, dict[str, str]] = _load_json(GUIDANCE_PATH, {})
DESCRIPTOR_GUIDANCE = _load_descriptor_guidance(DESCRIPTORS_PATH)
_PERSONA_LIST: list[dict[str, Any]] = _load_json(PERSONAS_PATH, [])
PERSONAS: dict[str, dict[str, Any]] = {
    str(persona["persona_id"]): persona
    for persona in _PERSONA_LIST
    if isinstance(persona, dict) and persona.get("persona_id")
}


def get_response_guidance(persona_id: str | None, emotion: str | None) -> str:
    persona_id = _normalize(persona_id, DEFAULT_PERSONA)
    emotion = _normalize(emotion, DEFAULT_EMOTION)

    guidance = (
        PERSONA_GUIDANCE.get(persona_id, {}).get(emotion)
        or PERSONA_GUIDANCE.get(DEFAULT_PERSONA, {}).get(emotion)
        or PERSONA_GUIDANCE.get(DEFAULT_PERSONA, {}).get(DEFAULT_EMOTION)
    )
    if guidance:
        return guidance

    logger.warning(
        "Missing persona guidance for persona_id=%s emotion=%s",
        persona_id,
        emotion,
    )
    return FALLBACK_GUIDANCE


def get_descriptor_guidance(
    persona_id: str | None,
    emotion: str | None,
) -> list[dict[str, str]]:
    persona = get_persona_metadata(persona_id)
    descriptors = persona.get("descriptors", [])
    if not isinstance(descriptors, list):
        return []

    normalized_emotion = _normalize(emotion, DEFAULT_EMOTION)
    rows = []
    for descriptor in descriptors:
        descriptor_id = _normalize(str(descriptor), "")
        if not descriptor_id:
            continue
        descriptor_rows = DESCRIPTOR_GUIDANCE.get(descriptor_id, {})
        match = (
            descriptor_rows.get(normalized_emotion)
            or descriptor_rows.get(DEFAULT_EMOTION)
        )
        if not match:
            continue
        rows.append(
            {
                "descriptor_id": descriptor_id,
                "emotion": normalized_emotion
                if normalized_emotion in descriptor_rows
                else DEFAULT_EMOTION,
                "guidance": match.get("guidance", ""),
            }
        )
    return rows


def get_persona_metadata(persona_id: str | None) -> dict[str, Any]:
    persona_id = _normalize(persona_id, DEFAULT_PERSONA)
    default_persona = PERSONAS.get(
        DEFAULT_PERSONA,
        {
            "persona_id": DEFAULT_PERSONA,
            "display_name": "Default Danny - The Steady Default",
            "descriptors": [],
            "tone_overlay": "Warm, clear, grounded, and practical.",
        },
    )
    return dict(PERSONAS.get(persona_id, default_persona))


def list_personas() -> list[dict[str, Any]]:
    return [dict(persona) for persona in PERSONAS.values()]
