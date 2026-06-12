import asyncio
import json
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas import SimulatedWellnessSignal
from app.services.rag import (
    get_descriptor_guidance,
    get_persona_metadata,
    get_response_guidance,
)

try:
    from groq import APIConnectionError as GroqAPIConnectionError
    from groq import APIStatusError as GroqAPIStatusError
    from groq import AsyncGroq
    from groq import AuthenticationError as GroqAuthenticationError
    from groq import RateLimitError as GroqRateLimitError
except ImportError:  # pragma: no cover - optional dependency
    AsyncGroq = None
    GroqAPIConnectionError = None
    GroqAPIStatusError = None
    GroqAuthenticationError = None
    GroqRateLimitError = None

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover - optional dependency
    boto3 = None
    BotoCoreError = ClientError = Exception


class LLMServiceError(RuntimeError):
    status_code = 502
    detail = "LLM provider unavailable"


class LLMConfigurationError(LLMServiceError):
    status_code = 503
    detail = "LLM provider not configured"


class LLMAuthenticationError(LLMServiceError):
    status_code = 503
    detail = "LLM provider authentication failed"


class LLMRateLimitError(LLMServiceError):
    status_code = 429
    detail = "LLM provider rate limit exceeded"


DEFAULT_PROMPT_TEMPLATE = """You are Jarvis, a calm and concise AI voice assistant.

Use the context payload when it is relevant. Treat corpus_context.response_contract
as mandatory. Make the selected persona visibly different in structure, pacing,
word choice, and emotional warmth while still speaking as Jarvis.
Be supportive without making medical or mental health diagnoses.

Context:
{{CONTEXT}}

User:
{{USER_MESSAGE}}

Assistant:"""


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bedrock_error: str | None = None
        self.groq_client = (
            AsyncGroq(api_key=settings.groq_api_key)
            if settings.groq_api_key and AsyncGroq is not None
            else None
        )
        self.bedrock_client = self._create_bedrock_client()

    @property
    def provider_status(self) -> str:
        provider = self.settings.llm_provider

        if provider == "groq" and self.groq_client is not None:
            return "configured"
        if provider == "groq" and self.settings.groq_api_key:
            return "missing groq sdk"
        if provider == "groq":
            return "missing groq api key"
        if provider == "bedrock" and self.bedrock_client is not None:
            return f"configured ({self.settings.bedrock_model_id})"
        if provider == "bedrock" and self.bedrock_error is not None:
            return self.bedrock_error
        if provider == "bedrock" and boto3 is None:
            return "missing boto3"
        if provider == "local":
            return "configured (local deterministic)"
        return f"unsupported llm provider: {provider}"

    def _create_bedrock_client(self):
        if self.settings.llm_provider != "bedrock" or boto3 is None:
            return None

        session_kwargs: dict[str, str] = {}
        if self.settings.aws_profile_name:
            session_kwargs["profile_name"] = self.settings.aws_profile_name

        try:
            session = boto3.Session(**session_kwargs)
            return session.client(
                "bedrock-runtime",
                region_name=self.settings.bedrock_region,
            )
        except Exception as exc:  # pragma: no cover - depends on local AWS config
            self.bedrock_error = f"bedrock init failed: {exc}"
            return None

    def _load_prompt_template(self) -> str:
        template_path = Path(self.settings.llm_prompt_template_path)
        try:
            return template_path.read_text(encoding="utf-8")
        except OSError:
            return DEFAULT_PROMPT_TEMPLATE

    def _build_context_payload(
        self,
        *,
        user_message: str,
        emotion: str,
        persona_id: str | None,
        conversation_context: list[dict[str, Any]],
        wellness_signal: SimulatedWellnessSignal | None,
    ) -> dict[str, Any]:
        persona = get_persona_metadata(persona_id)
        resolved_persona_id = str(persona.get("persona_id", persona_id or ""))
        guidance = get_response_guidance(
            resolved_persona_id,
            emotion,
        )
        descriptor_guidance = get_descriptor_guidance(resolved_persona_id, emotion)
        response_contract = persona.get("response_contract", {})
        return {
            "user_text": user_message,
            "emotion": emotion,
            "detected_emotion": emotion,
            "emotion_guidance": guidance,
            "user_profile": persona,
            "corpus_context": {
                "selected_persona_id": resolved_persona_id,
                "response_contract": response_contract,
                "persona_guidance": guidance,
                "descriptor_guidance": descriptor_guidance,
                "persona_source": "corpus/personas.json",
                "persona_guidance_source": "corpus/persona_guidance.json",
                "descriptor_guidance_source": "corpus/descriptors.csv",
            },
            "conversation_history": conversation_context,
            "wellness_signal": wellness_signal.model_dump() if wellness_signal else None,
        }

    def _build_prompt(
        self,
        *,
        user_message: str,
        emotion: str,
        persona_id: str | None,
        conversation_context: list[dict[str, Any]],
        wellness_signal: SimulatedWellnessSignal | None,
    ) -> str:
        context_payload = self._build_context_payload(
            user_message=user_message,
            emotion=emotion,
            persona_id=persona_id,
            conversation_context=conversation_context,
            wellness_signal=wellness_signal,
        )
        context_json = json.dumps(context_payload, indent=2, default=str)
        template = self._load_prompt_template()
        has_context_placeholder = "{{CONTEXT}}" in template or "{{PAYLOAD}}" in template
        has_message_placeholder = "{{USER_MESSAGE}}" in template

        rendered = template.replace("{{CONTEXT}}", context_json)
        rendered = rendered.replace("{{PAYLOAD}}", context_json)
        rendered = rendered.replace("{{USER_MESSAGE}}", user_message)

        if not has_context_placeholder:
            rendered = f"{rendered.rstrip()}\n\nContext:\n{context_json}"
        if not has_message_placeholder:
            rendered = f"{rendered.rstrip()}\n\nUser:\n{user_message}"
        if not rendered.rstrip().endswith("Assistant:"):
            rendered = f"{rendered.rstrip()}\n\nAssistant:"
        return rendered.strip()

    def _extract_bedrock_text(self, response_body: dict[str, Any]) -> str:
        if "content" in response_body and response_body["content"]:
            first_content = response_body["content"][0]
            if isinstance(first_content, dict) and "text" in first_content:
                return str(first_content["text"])

        if "choices" in response_body and response_body["choices"]:
            content = response_body["choices"][0].get("message", {}).get("content", "")
            if isinstance(content, list):
                texts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("text")
                ]
                return "\n".join(texts).strip()
            return str(content)

        if "output" in response_body and isinstance(response_body["output"], dict):
            message = response_body["output"].get("message", {})
            content = message.get("content", [])
            texts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("text")
            ]
            if texts:
                return "\n".join(texts).strip()

        raise ValueError(f"Unsupported Bedrock response format: {response_body}")

    async def _generate_with_groq(self, messages: list[dict[str, str]]) -> str:
        if self.groq_client is None:
            raise LLMConfigurationError(
                "Groq is not configured. Add GROQ_API_KEY and install requirements."
            )

        request_kwargs: dict[str, Any] = {
            "model": self.settings.groq_model,
            "messages": messages,
            "max_tokens": self.settings.llm_max_tokens,
        }
        if self.settings.llm_top_p is not None:
            request_kwargs["top_p"] = self.settings.llm_top_p
        else:
            request_kwargs["temperature"] = self.settings.llm_temperature

        try:
            completion = await self.groq_client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            if GroqAuthenticationError is not None and isinstance(
                exc,
                GroqAuthenticationError,
            ):
                raise LLMAuthenticationError(
                    "Groq rejected GROQ_API_KEY. Replace the placeholder or invalid key "
                    "in .env with a valid Groq key, then restart the server."
                ) from exc
            if GroqRateLimitError is not None and isinstance(exc, GroqRateLimitError):
                raise LLMRateLimitError(
                    "Groq rate limit exceeded. Set a valid GROQ_API_KEY with available "
                    "quota or try again later."
                ) from exc
            if GroqAPIConnectionError is not None and isinstance(
                exc,
                GroqAPIConnectionError,
            ):
                raise LLMServiceError(
                    "Could not reach Groq. Check your network connection and try again."
                ) from exc
            if GroqAPIStatusError is not None and isinstance(exc, GroqAPIStatusError):
                status_code = getattr(exc, "status_code", "unknown")
                raise LLMServiceError(
                    f"Groq request failed with status {status_code}."
                ) from exc
            raise
        return completion.choices[0].message.content or "I could not generate a reply."

    async def _generate_with_bedrock(
        self,
        *,
        prompt: str,
    ) -> str:
        if self.bedrock_client is None:
            raise LLMConfigurationError(
                "Bedrock is not configured. Install boto3 and provide Bedrock settings."
            )

        payload = {
            "max_tokens": self.settings.llm_max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }
        if self.settings.bedrock_model_id.startswith(("anthropic.", "us.anthropic.")):
            payload["anthropic_version"] = "bedrock-2023-05-31"
        if self.settings.llm_top_p is not None:
            payload["top_p"] = self.settings.llm_top_p
        else:
            payload["temperature"] = self.settings.llm_temperature
        if self.settings.llm_top_k is not None:
            payload["top_k"] = self.settings.llm_top_k

        def invoke() -> dict[str, Any]:
            try:
                response = self.bedrock_client.invoke_model(
                    modelId=self.settings.bedrock_model_id,
                    body=json.dumps(payload),
                )
            except (ClientError, BotoCoreError) as exc:
                message = str(exc)
                if isinstance(exc, ClientError):
                    message = exc.response.get("Error", {}).get("Message", str(exc))
                raise LLMServiceError(f"Bedrock invocation failed: {message}") from exc

            return json.loads(response["body"].read())

        response_body = await asyncio.to_thread(invoke)
        text = self._extract_bedrock_text(response_body).strip()
        return text or "I could not generate a reply."

    def _generate_local(
        self,
        *,
        user_message: str,
        emotion: str,
        persona_id: str | None,
    ) -> str:
        persona = get_persona_metadata(persona_id)
        guidance = get_response_guidance(
            str(persona.get("persona_id", persona_id or "")),
            emotion,
        )
        resolved_persona_id = str(persona.get("persona_id", persona_id or ""))
        lowered = user_message.lower()

        if "time" in lowered:
            return (
                "I cannot check the live clock from local test mode, but the Jarvis "
                "pipeline is working."
            )
        persona_responses = {
            "tony_stark": (
                "Lever first: pick the constraint that is actually blocking you. "
                "Then choose one move, run it for 15 minutes, and keep the drama budget at zero."
            ),
            "maya_chen": (
                "That sounds like a lot to hold. It may help to write down what is real, "
                "what is a fear, and one gentle next step you can take."
            ),
            "uncle_ray": (
                "Alright, call it what it is: too many moving parts. Pick the one thing "
                "that matters most today and handle that before you widen the circle."
            ),
            "sam_rivera": (
                "It makes sense that this feels tangled. Try naming the pressure, then "
                "choose one small step that gives you a little room to breathe."
            ),
            "priya_shah": (
                "This is pressure, not a personal failure. Rank the top three tasks, "
                "start a 25-minute timer on number one, and stop there for now."
            ),
        }
        if emotion in {"fear", "sad", "angry"}:
            return persona_responses.get(
                resolved_persona_id,
                (
                    "I hear you. Let's keep this simple: name the one thing you can "
                    "control next, then take that step before widening the plan."
                ),
            )
        if emotion in {"happy", "excited", "surprised"}:
            return (
                "That's good momentum. Capture what worked, then choose one next step "
                "while the energy is fresh."
            )
        if guidance:
            return "Got it. I will keep this clear and practical: what do you want to work on next?"
        return "Got it. What would you like to do next?"

    async def generate_response(
        self,
        *,
        user_message: str,
        emotion: str,
        conversation_context: list[dict[str, Any]],
        persona_id: str | None = None,
        wellness_signal: SimulatedWellnessSignal | None = None,
    ) -> str:
        prompt = self._build_prompt(
            user_message=user_message,
            emotion=emotion,
            persona_id=persona_id,
            conversation_context=conversation_context,
            wellness_signal=wellness_signal,
        )
        messages = [{"role": "user", "content": prompt}]

        if self.settings.llm_provider == "local":
            return self._generate_local(
                user_message=user_message,
                emotion=emotion,
                persona_id=persona_id,
            )
        if self.settings.llm_provider == "groq":
            return await self._generate_with_groq(messages)
        if self.settings.llm_provider == "bedrock":
            return await self._generate_with_bedrock(prompt=prompt)
        raise LLMConfigurationError(
            f"Unsupported llm provider: {self.settings.llm_provider}"
        )
