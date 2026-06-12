# Jarvis Assistant Starter

Jarvis is a FastAPI-based voice assistant demo. It accepts text or browser microphone input, detects the user's emotional signal, looks up persona-specific response guidance, sends a context-rich prompt to an LLM, stores the conversation turn, and returns text plus a generated audio artifact when TTS is available.

```text
Browser text or microphone
  -> FastAPI endpoint
  -> transcription when needed
  -> emotion detection
  -> persona guidance lookup
  -> prompt template + runtime context
  -> LLM response
  -> TTS or text artifact
  -> browser playback and conversation history
```

## Quick Notes

- Main app entry point: `main.py`
- FastAPI app factory and routes: `app/api.py`
- Browser UI: `app/static/index.html`, `app/static/app.js`, `app/static/styles.css`
- Prompt template: `prompts/jarvis_chat.txt`
- Persona source data: `corpus/personas.json` and `corpus/descriptors.csv`
- Generated persona guidance cache: `corpus/persona_guidance.json`
- Conversation table model: `app/models.py`
- Demo scenarios: `demo/scenarios.json`
- Full smoke test runner: `scripts/run_full_tests.py`

The easiest mode for local testing is:

```env
LLM_PROVIDER=local
```

Local mode avoids Groq and AWS Bedrock. It returns deterministic replies so you can verify the backend, UI, memory, emotion flow, and generated artifacts without an external LLM.

## What The App Does

Jarvis currently supports:

- text chat through `/api/chat`
- voice turns through `/api/voice`
- a browser conversation console at `/ui`
- browser microphone recording
- wake phrase listening in browsers that support the Web Speech API
- emotion-aware response style
- persona-aware guidance using `persona_id + detected_emotion`
- simulated wellness inputs for demo purposes
- recent session history
- TTS playback when Coqui TTS is available
- text artifact fallback when TTS is unavailable
- MySQL storage with SQLite fallback

Current wake phrases:

- `Hey JayJay`
- `Hey Jay Jay`

Current startup behavior:

- the app initializes the database on boot
- all stored conversation turns are cleared every time the app starts

That startup clearing is intentional for demo cleanliness. If you want durable memory across restarts, remove or change the `clear_all_conversation_history()` call in `app/api.py`.

## Stack

- Backend: FastAPI
- Server: Uvicorn
- Validation/settings: Pydantic and `pydantic-settings`
- Database: SQLAlchemy async
- Primary database target: MySQL through `aiomysql`
- Fallback database: SQLite through `aiosqlite`
- LLM providers: Groq, AWS Bedrock, or local deterministic mode
- STT: OpenAI Whisper package
- Optional voice understanding: SenseVoice through FunASR/ModelScope
- Emotion detection: Hugging Face audio classifier plus transcript keyword cues
- TTS: Coqui TTS when installed, text file fallback when unavailable
- Frontend: plain HTML, CSS, and JavaScript

## Project Layout

```text
jarvis-assistant/
├── app/
│   ├── api.py                  # FastAPI app, routes, startup/shutdown behavior
│   ├── config.py               # Environment-backed settings
│   ├── db.py                   # Async database engine/session setup and fallback
│   ├── models.py               # SQLAlchemy conversation table
│   ├── schemas.py              # Pydantic request/response models
│   ├── services/
│   │   ├── emotion.py          # Audio/text emotion detection
│   │   ├── llm.py              # Prompt rendering and LLM provider calls
│   │   ├── memory.py           # Conversation persistence helpers
│   │   ├── orchestrator.py     # Main chat/voice pipeline coordinator
│   │   ├── rag.py              # Persona metadata and guidance lookup
│   │   ├── sensevoice.py       # Optional SenseVoice transcription/emotion path
│   │   ├── stt.py              # Whisper transcription
│   │   └── tts.py              # Coqui TTS or text artifact output
│   └── static/
│       ├── app.js              # Browser behavior, recording, wake phrase, API calls
│       ├── index.html          # Browser console markup
│       └── styles.css          # UI styling and emotion themes
├── corpus/
│   ├── descriptors.csv         # Descriptor-by-emotion source guidance
│   ├── personas.json           # Persona definitions
│   └── persona_guidance.json   # Generated persona-by-emotion runtime cache
├── demo/
│   ├── README.md               # Demo kit notes
│   ├── scenarios.json          # Repeatable demo inputs
│   └── audio/                  # Generated WAV files used with transcript overrides
├── prompts/
│   ├── jarvis_chat.txt         # Main LLM prompt template
│   └── persona_composition.txt # Prompt used for Bedrock-based guidance generation
├── scripts/
│   ├── build_persona_cache.py  # Rebuild corpus/persona_guidance.json
│   ├── generate_demo_assets.py # Create demo WAV clips and scenarios JSON
│   ├── run_demo_scenarios.py   # POST bundled demo scenarios to /api/voice
│   └── run_full_tests.py       # End-to-end smoke checks against a running app
├── wiki/
│   └── Progress-Log.md
├── .env.example
├── main.py
├── requirements.txt
├── requirements-voice.txt
└── ReadMe.md
```

## Setup

Recommended Python version:

- Python `3.11` or `3.12`

Important notes:

- `ffmpeg` is needed for real Whisper transcription.
- Coqui TTS may not install cleanly on newer Python versions.
- If MySQL is unavailable and `ALLOW_SQLITE_FALLBACK=true`, the app falls back to `jarvis.db`.
- Do not set `WHISPER_DEVICE=` or `COQUI_DEVICE=` to a blank value. Leave them commented, or set them to something real such as `cpu` or `cuda`.

Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Optional voice-only install file:

```bash
python3 -m pip install -r requirements-voice.txt
```

Create your environment file:

```bash
cp .env.example .env
```

For offline smoke tests:

```env
LLM_PROVIDER=local
```

For Groq:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

For AWS Bedrock:

```env
LLM_PROVIDER=bedrock
BEDROCK_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
AWS_PROFILE_NAME=your_profile_if_needed
```

## Run The App

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

Open these URLs:

- Browser UI: `http://127.0.0.1:8000/ui`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`
- Root endpoint: `http://127.0.0.1:8000/`

Quick checks:

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

The health response reports provider status for:

- `llm`
- `stt`
- `emotion`
- `tts`
- `database`

## Environment Notes

The settings class is `app/config.py`. Values are read from `.env`.

Common settings:

| Setting | Meaning |
| --- | --- |
| `APP_NAME` | Name shown in health/root metadata |
| `ENVIRONMENT` | Environment label returned by `/health` |
| `DEBUG` | Boolean debug flag; strings like `prod` become `false` |
| `API_PREFIX` | Defaults to `/api` |
| `LLM_PROVIDER` | `local`, `groq`, or `bedrock` |
| `LLM_PROMPT_TEMPLATE_PATH` | Prompt file path, default `prompts/jarvis_chat.txt` |
| `LLM_TEMPERATURE` | Sampling temperature unless `LLM_TOP_P` is set |
| `LLM_MAX_TOKENS` | Max generated response tokens |
| `LLM_TOP_K` | Optional Bedrock top-k setting |
| `LLM_TOP_P` | Optional nucleus sampling setting |
| `DATABASE_URL` | Primary database URL |
| `SQLITE_FALLBACK_URL` | SQLite fallback URL |
| `ALLOW_SQLITE_FALLBACK` | Enables MySQL-to-SQLite fallback |
| `WHISPER_MODEL_SIZE` | Whisper model size, default `base` |
| `WHISPER_LANGUAGE` | Whisper language, default `en` |
| `WHISPER_TASK` | Whisper task, default `transcribe` |
| `VOICE_UNDERSTANDING_PROVIDER` | `legacy` or `sensevoice` |
| `AUDIO_OUTPUT_DIR` | Generated audio/text artifact folder |
| `UPLOAD_DIR` | Uploaded audio folder |

Placeholder API keys such as `your_key_here` are treated as missing, not valid credentials.

## How A Text Turn Works

Text turns go through `/api/chat`.

```text
POST /api/chat
  -> validate ChatRequest
  -> detect emotion from text keywords when no emotion was already supplied
  -> load recent conversation history
  -> load persona metadata and persona/emotion guidance
  -> render prompt template with JSON context
  -> call selected LLM provider
  -> synthesize TTS or write fallback text artifact
  -> store user and assistant turns
  -> return ChatResponse
```

The orchestrator for this flow is `AssistantOrchestrator.handle_chat()` in `app/services/orchestrator.py`.

The text emotion detector is simple by design. It looks for keywords such as `stressed`, `overwhelmed`, `sad`, `excited`, `angry`, and similar terms. If no keyword matches, emotion defaults to `neutral`.

## How A Voice Turn Works

Voice turns go through `/api/voice`.

```text
POST /api/voice
  -> save uploaded audio into uploads/
  -> build optional wellness signal from form fields
  -> if SenseVoice is enabled, try SenseVoice first
  -> otherwise transcribe with Whisper, unless transcript_override is provided
  -> detect emotion from audio + transcript
  -> continue through the same chat pipeline as /api/chat
```

Use `transcript_override` when you want to test voice upload without depending on real speech recognition. The request still includes an audio file, but the transcript comes from your override text.

If Whisper cannot download a model because of local SSL certificate trust, use `Transcript Override` while fixing the Python certificate setup.

## Prompt And Runtime Context

The main prompt template is `prompts/jarvis_chat.txt`.

Jarvis uses this pattern:

```text
prompt template + runtime JSON context + user message -> LLM response
```

Supported placeholders:

- `{{CONTEXT}}`
- `{{PAYLOAD}}`
- `{{USER_MESSAGE}}`

The runtime context includes:

- `user_text`
- `emotion`
- `detected_emotion`
- `emotion_guidance`
- `user_profile`
- `conversation_history`
- `wellness_signal`

If the prompt template does not include a context or user-message placeholder, `LLMService` appends the missing section automatically.

## LLM Provider Notes

The LLM service is `app/services/llm.py`.

Provider behavior:

- `local`: returns deterministic test replies without network calls.
- `groq`: uses `AsyncGroq` chat completions.
- `bedrock`: uses `boto3` and `bedrock-runtime.invoke_model`.

Error handling:

- missing provider setup raises an LLM configuration error
- Groq authentication failures produce a clear invalid-key message
- Groq rate limits return a `429`
- Bedrock invocation errors are converted into LLM service errors

The `/health` endpoint shows whether the selected provider is configured.

## Persona Guidance Notes

Persona guidance is a lightweight lookup, not a vector database.

```text
persona_id + detected_emotion -> guidance string
```

Runtime lookup lives in `app/services/rag.py`.

Source files:

- `corpus/personas.json`: persona profiles and descriptor mixes
- `corpus/descriptors.csv`: descriptor-by-emotion guidance
- `corpus/persona_guidance.json`: generated runtime cache

Current personas:

- `tony_stark`
- `maya_chen`
- `uncle_ray`
- `sam_rivera`
- `priya_shah`
- `default_danny`

Default persona:

- `default_danny`

If a persona or emotion is missing, the lookup falls back to the default persona and then to a generic guidance string.

Rebuild the cache after editing `corpus/descriptors.csv` or `corpus/personas.json`:

```bash
python3 scripts/build_persona_cache.py --force
```

Useful cache builder options:

```bash
python3 scripts/build_persona_cache.py --persona priya_shah
python3 scripts/build_persona_cache.py --emotion fear
python3 scripts/build_persona_cache.py --provider bedrock
```

By default, the builder uses deterministic local composition so demos and tests do not need AWS access.

## Emotion Detection Notes

The emotion service is `app/services/emotion.py`.

For text chat:

- Jarvis checks transcript keywords.
- A keyword match produces emotions such as `happy`, `sad`, `angry`, or `fear`.
- No keyword match becomes `neutral`.

For voice chat:

- Jarvis tries audio classification with the configured Hugging Face model.
- Jarvis also checks transcript keywords.
- Text can override audio when audio confidence is low, audio is neutral, or text confidence is meaningfully stronger.

Returned debug fields:

- `final_emotion`
- `audio_emotion`
- `audio_score`
- `text_emotion`
- `text_score`
- `decision_source`
- optional SenseVoice metadata such as `provider`, `language`, `audio_event`, and `raw_output`

## TTS And Artifacts

The TTS service is `app/services/tts.py`.

When Coqui TTS is available:

- Jarvis writes a `.wav` file into `generated_audio/`.
- The browser loads that artifact through `/generated_audio/...`.

When Coqui TTS is unavailable:

- Jarvis writes a `.txt` file into `generated_audio/`.
- The browser shows the artifact path instead of playing audio.

This fallback is useful for smoke tests and machines where TTS dependencies are difficult to install.

## Database And Memory Notes

Database setup is in `app/db.py`.

Conversation rows are stored in the `conversation_turns` table:

- `id`
- `session_id`
- `role`
- `content`
- `emotion`
- `created_at`

Memory behavior:

- each completed chat turn stores one `user` row and one `assistant` row
- recent history is loaded before each LLM call
- history is grouped by `session_id`
- `/api/history/{session_id}` returns recent turns
- `DELETE /api/history/{session_id}` clears one session
- app startup clears all conversation history

If the configured MySQL database fails during startup and SQLite fallback is allowed, Jarvis creates/uses `jarvis.db`.

## API Notes

### Root

```http
GET /
```

Returns a small app-running message.

### Health

```http
GET /health
```

Returns app metadata and provider statuses.

### Personas

```http
GET /api/personas
```

Returns persona definitions from `corpus/personas.json`.

### Text Chat

```http
POST /api/chat
Content-Type: application/json
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo",
    "persona_id": "default_danny",
    "message": "I am feeling stressed. Help me choose the next step.",
    "wellness_signal": {
      "heart_rate": 108,
      "stress_level": "high",
      "source": "manual_demo"
    }
  }'
```

### Voice Upload

```http
POST /api/voice
Content-Type: multipart/form-data
```

Example with transcript override:

```bash
curl -X POST http://127.0.0.1:8000/api/voice \
  -F "session_id=voice-demo" \
  -F "persona_id=priya_shah" \
  -F "transcript_override=Please remember I like concise answers." \
  -F "wellness_heart_rate=92" \
  -F "wellness_stress_level=moderate" \
  -F "audio=@sample.wav"
```

### History

```bash
curl http://127.0.0.1:8000/api/history/demo
curl -X DELETE http://127.0.0.1:8000/api/history/demo
```

### WebSocket

```text
ws://127.0.0.1:8000/ws/chat
```

The WebSocket path is a lightweight chat endpoint. It sends the incoming text directly to the LLM service with neutral emotion and the default persona. It is useful for connectivity testing, but it does not run the full memory/emotion/TTS pipeline.

## Browser UI Notes

Open:

```text
http://127.0.0.1:8000/ui
```

Main UI areas:

- `Emotion Monitor`: visual state driven by detected emotion
- `Session ID`: groups conversation history
- `Transcript Override`: bypasses STT while still testing voice upload
- `Simulated Heart Rate`: demo-only wellness signal
- `Simulated Stress Level`: demo-only wellness signal
- `Start Voice Turn`: starts browser recording
- `End Voice Turn`: stops recording and uploads the clip
- `Send Text Turn`: sends the text box through `/api/chat`
- `New Conversation`: clears current session history
- `Refresh History`: reloads recent turns for the current session
- `Playback Speed`: changes assistant audio playback speed
- diagnostics panels: transcript, assistant reply, emotion details, output artifact, and raw JSON

The browser UI currently uses the default persona. API callers can pass any supported `persona_id`.

## Manual UI Demo Flow

1. Start the server with `uvicorn main:app --reload`.
2. Open `/ui`.
3. Allow microphone access if the browser asks.
4. Keep the default session ID or type your own.
5. Optionally set heart rate and stress level.
6. Say `Hey JayJay` or click `Start Voice Turn`.
7. Speak your message.
8. Click `End Voice Turn`.
9. Watch the emotion monitor, conversation thread, diagnostics, and assistant output update.

Text-only flow:

1. Open `/ui`.
2. Type a message into `Text Message`.
3. Optionally set wellness inputs.
4. Click `Send Text Turn`.
5. Review the assistant reply, raw JSON, and conversation thread.

Fast voice-pipeline test:

1. Put a sentence in `Transcript Override`.
2. Click `Start Voice Turn`.
3. Record any short clip.
4. Click `End Voice Turn`.
5. Jarvis uses the override text as the transcript.

## Demo Kit

The demo kit gives repeatable API demos without relying on live speech.

Generate or regenerate demo assets:

```bash
python3 scripts/generate_demo_assets.py
```

Run all scenarios against a running server:

```bash
python3 scripts/run_demo_scenarios.py
```

Run one scenario:

```bash
python3 scripts/run_demo_scenarios.py --scenario stressed_focus
```

Bundled scenarios:

- `stressed_focus`: high stress, overwhelmed focus request
- `excited_win`: positive/excited project completion
- `sad_support`: low mood and encouragement request
- `remember_preference`: asks Jarvis to remember concise-answer preference within the current session

The demo audio files are generated tones. They are paired with `transcript_override`, so they test the upload path without requiring spoken recordings.

## Full Smoke Test

Start the server first:

```bash
uvicorn main:app --reload
```

Then run:

```bash
python3 scripts/run_full_tests.py
```

The script checks:

- root endpoint
- health endpoint
- personas endpoint
- chat endpoint
- voice endpoint
- WebSocket endpoint
- generated output artifact
- SQLite persistence when SQLite is the active database

You can target another server URL:

```bash
python3 scripts/run_full_tests.py --base-url http://127.0.0.1:8001
```

## Troubleshooting Notes

### `/health` says the LLM is missing configuration

Use local mode for smoke tests:

```env
LLM_PROVIDER=local
```

For Groq, set a real `GROQ_API_KEY`. Placeholder keys are ignored.

For Bedrock, confirm:

- `boto3` is installed
- AWS credentials are available
- `BEDROCK_REGION` is correct
- `BEDROCK_MODEL_ID` is accessible to your AWS account
- `AWS_PROFILE_NAME` is set if you use a named profile

### MySQL is not running

Set:

```env
ALLOW_SQLITE_FALLBACK=true
```

When MySQL connection setup fails, Jarvis falls back to `sqlite+aiosqlite:///./jarvis.db`.

### Voice transcription fails

Use `Transcript Override` to keep testing the rest of the pipeline.

Also check:

- `ffmpeg` is installed
- `openai-whisper` is installed
- the Whisper model can download
- `WHISPER_DEVICE` is either unset/commented or set to a valid device

### Assistant audio does not play

Check `/health` and the `tts` provider status.

If Coqui is unavailable, Jarvis writes a text artifact instead of a `.wav`. That is expected fallback behavior.

### Wake phrase does not work

Wake listening depends on browser support for the Web Speech API and microphone permission. Manual recording still works through `Start Voice Turn` and `End Voice Turn`.

### Conversation history disappears after restart

This is current app behavior. Startup calls `clear_all_conversation_history()` in `app/api.py`.

## Development Notes

When changing the assistant behavior:

- edit `prompts/jarvis_chat.txt` for response style and prompt rules
- edit `corpus/personas.json` to add or change personas
- edit `corpus/descriptors.csv` to change descriptor/emotion guidance
- regenerate `corpus/persona_guidance.json` after corpus edits
- use `LLM_PROVIDER=local` for fast backend smoke tests
- use `Transcript Override` to test the voice endpoint without real STT

Future expansion ideas already suggested by the structure:

- replace lightweight guidance lookup with true vector RAG
- persist long-term user preferences beyond reboot
- expose persona selection in the browser UI
- add richer wearable integrations in place of simulated wellness fields
- add more robust emotion models or calibration
