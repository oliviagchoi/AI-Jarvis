import asyncio
from pathlib import Path

from app.config import Settings

try:
    from transformers import pipeline
except ImportError:  # pragma: no cover - optional dependency
    pipeline = None


class EmotionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.classifier = None
        self.keyword_map = {
            "happy": {
                "happy",
                "excited",
                "great",
                "awesome",
                "good",
                "glad",
                "love",
                "amazing",
                "fantastic",
                "wonderful",
            },
            "sad": {
                "sad",
                "upset",
                "frustrated",
                "depressed",
                "down",
                "tired",
                "hurt",
                "cry",
                "lonely",
                "hopeless",
            },
            "angry": {
                "angry",
                "mad",
                "furious",
                "annoyed",
                "irritated",
                "hate",
            },
            "fear": {
                "afraid",
                "scared",
                "nervous",
                "worried",
                "anxious",
                "panic",
                "overwhelmed",
                "stressed",
                "stress",
                "tense",
            },
        }

    @property
    def provider_status(self) -> str:
        if pipeline is None:
            return "missing transformers dependency"
        return "configured (hybrid audio+text)"

    def _load_classifier(self):
        if pipeline is None:
            raise RuntimeError("Transformers is not installed.")
        if self.classifier is None:
            self.classifier = pipeline(
                task="audio-classification",
                model=self.settings.emotion_model_name,
                device=self.settings.emotion_device,
            )
        return self.classifier

    @staticmethod
    def _normalize_label(label: str) -> str:
        lowered = label.lower().strip()
        mapping = {
            "joy": "happy",
            "happiness": "happy",
            "happy": "happy",
            "sadness": "sad",
            "sad": "sad",
            "anger": "angry",
            "angry": "angry",
            "fear": "fear",
            "fearful": "fear",
            "surprise": "surprised",
            "surprised": "surprised",
            "neutral": "neutral",
            "calm": "calm",
        }
        return mapping.get(lowered, lowered)

    def _classify_sync(self, audio_path: Path) -> tuple[str, float]:
        classifier = self._load_classifier()
        results = classifier(str(audio_path), top_k=3)
        if not results:
            return ("neutral", 0.0)
        top = results[0]
        return (self._normalize_label(str(top["label"])), float(top.get("score", 0.0)))

    def _detect_from_text(self, transcript: str) -> tuple[str, float]:
        lowered = transcript.lower()
        best_emotion = "neutral"
        best_score = 0.0

        for emotion, keywords in self.keyword_map.items():
            hits = sum(1 for keyword in keywords if keyword in lowered)
            if hits > 0:
                score = min(0.95, 0.35 + (hits * 0.2))
                if score > best_score:
                    best_emotion = emotion
                    best_score = score

        return (best_emotion, best_score)

    async def detect_from_text(self, transcript: str) -> dict[str, object]:
        text_emotion, text_score = await asyncio.to_thread(
            self._detect_from_text,
            transcript,
        )
        final_emotion = text_emotion if text_score > 0.0 else "neutral"
        decision_source = "text_keywords" if text_score > 0.0 else "fallback"
        return {
            "final_emotion": final_emotion,
            "audio_emotion": None,
            "audio_score": None,
            "text_emotion": text_emotion,
            "text_score": round(text_score, 3),
            "decision_source": decision_source,
        }

    async def detect_from_audio(self, audio_path: Path) -> tuple[str, float]:
        if pipeline is None:
            raise RuntimeError(
                "Transformers is not installed. Install requirements and try again."
            )
        return await asyncio.to_thread(self._classify_sync, audio_path)

    async def detect_hybrid(self, audio_path: Path, transcript: str) -> dict[str, object]:
        audio_emotion = "neutral"
        audio_score = 0.0

        try:
            audio_emotion, audio_score = await self.detect_from_audio(audio_path)
        except Exception:
            audio_emotion, audio_score = ("neutral", 0.0)

        text_emotion, text_score = self._detect_from_text(transcript)
        final_emotion = audio_emotion
        decision_source = "audio"

        if text_score == 0.0:
            if audio_score == 0.0:
                final_emotion = "neutral"
                decision_source = "fallback"
            return {
                "final_emotion": final_emotion,
                "audio_emotion": audio_emotion,
                "audio_score": round(audio_score, 3),
                "text_emotion": text_emotion,
                "text_score": round(text_score, 3),
                "decision_source": decision_source,
            }

        if audio_score < 0.55:
            final_emotion = text_emotion
            decision_source = "text_low_audio_confidence"
            return {
                "final_emotion": final_emotion,
                "audio_emotion": audio_emotion,
                "audio_score": round(audio_score, 3),
                "text_emotion": text_emotion,
                "text_score": round(text_score, 3),
                "decision_source": decision_source,
            }

        if audio_emotion in {"neutral", "calm"} and text_score >= 0.45:
            final_emotion = text_emotion
            decision_source = "text_overrode_neutral_audio"
            return {
                "final_emotion": final_emotion,
                "audio_emotion": audio_emotion,
                "audio_score": round(audio_score, 3),
                "text_emotion": text_emotion,
                "text_score": round(text_score, 3),
                "decision_source": decision_source,
            }

        if audio_emotion != text_emotion and text_score >= (audio_score + 0.12):
            final_emotion = text_emotion
            decision_source = "text_overrode_audio"
            return {
                "final_emotion": final_emotion,
                "audio_emotion": audio_emotion,
                "audio_score": round(audio_score, 3),
                "text_emotion": text_emotion,
                "text_score": round(text_score, 3),
                "decision_source": decision_source,
            }

        return {
            "final_emotion": final_emotion,
            "audio_emotion": audio_emotion,
            "audio_score": round(audio_score, 3),
            "text_emotion": text_emotion,
            "text_score": round(text_score, 3),
            "decision_source": decision_source,
        }
