# Jarvis Presentation Examples

These examples are slide-ready scenarios for explaining why Jarvis uses
emotion detection, persona guidance, and a lightweight retrieval cache.

## Internet-Backed Framing Examples

### 1. Why Emotion-Aware Support Matters

Research on graduate education reports elevated anxiety and depression signals among
graduate students, which makes MSBA/student stress a realistic target demo context.
Jarvis should not diagnose or act like therapy; it should detect emotional state and
adapt tone, pacing, and next-step support.

Presentation line:

> Graduate students are a high-pressure audience, so Jarvis focuses on practical,
> emotionally aware support rather than generic chatbot replies.

Use with:

- Persona: `priya_shah`
- Emotion: `fear`
- Demo user line: "I have a presentation tomorrow and I cannot focus. I feel like I am going to fail."

Jarvis demo response:

> You are not failing; you are overloaded. Let's shrink this to one controllable move:
> open the deck, fix the weakest slide first, and give it 15 focused minutes.

Source:

- Evans et al., Nature Biotechnology, "Evidence for a mental health crisis in graduate education": https://www.nature.com/articles/nbt.4089
- Evans et al. reply with reported graduate-student anxiety/depression rates in their sample: https://www.nature.com/articles/s41587-019-0181-4

### 2. Emotion-Aware Voice AI Is Already a Product Direction

Hume's Empathic Voice Interface positions voice AI around vocal expression,
prosody, timing, and emotionally attuned responses. Jarvis can frame itself as a
student project version of the same design direction: listen to how the user sounds,
detect emotion, then adapt the response.

Presentation line:

> The broader AI market is moving from "assistant that answers" to "assistant that
> listens, senses context, and responds with the right emotional pacing."

Use with:

- Persona: `sam_rivera`
- Emotion: `sad`
- Demo user line: "I thought I did okay, but the feedback made me feel really small."

Jarvis demo response:

> That kind of feedback can sting, especially when you were trying hard. Let's hold
> both things at once: it hurt, and it may still contain one useful signal you can use.

Source:

- Hume AI EVI docs: https://dev.hume.ai/docs/speech-to-speech-evi/overview

### 3. Empathetic Dialogue Is a Known AI Research Problem

The EmpatheticDialogues benchmark was built around conversations grounded in
emotional situations. That supports the Jarvis design choice: the model needs an
explicit emotional context, not only the user's literal words.

Presentation line:

> Empathetic response generation is a known benchmark problem. Jarvis makes that
> practical by injecting detected emotion and persona-specific guidance into the prompt.

Use with:

- Persona: `maya_chen`
- Emotion: `sad`
- Demo user line: "My group chat went quiet after I sent my idea. I think they all hate it."

Jarvis demo response:

> That silence would make a lot of people spiral. It does not automatically mean they
> hate the idea; it may just mean nobody has responded yet. If you want, send one calm
> follow-up asking whether they want a shorter version or a different direction.

Source:

- Rashkin et al., "Towards Empathetic Open-domain Conversation Models": https://arxiv.org/abs/1811.00207

### 4. Conversational Support Has Been Studied With Young Adults

A randomized Woebot study recruited young adults from a university community and
tested a conversational CBT-style chatbot. Jarvis should not claim therapy outcomes,
but the study is useful evidence that conversational agents can be studied for
student-support contexts.

Presentation line:

> We are not building therapy. We are building a safer assistant pattern: acknowledge
> emotion, avoid diagnosis, and offer one practical next step.

Use with:

- Persona: `default_danny`
- Emotion: `fear`
- Demo user line: "I am stressed and I do not know what to do first."

Jarvis demo response:

> Start with the task that reduces the most pressure. Pick one, set a 15-minute timer,
> and ignore everything else until that timer ends.

Source:

- Fitzpatrick, Darcy, and Vierhile, JMIR Mental Health, Woebot randomized trial: https://mental.jmir.org/2017/2/e19/

### 5. RAG Explains the Long-Term Architecture

AWS frames RAG as retrieving information from data sources to improve relevance and
accuracy. Jarvis currently uses a simple JSON cache instead of vector retrieval:
`persona_id + detected_emotion -> guidance`. This is fast, explainable, and enough
for the presentation demo. Later, uploaded documents can be chunked, embedded, and
retrieved with a vector database.

Presentation line:

> Version one is intentionally not full vector RAG. It is a prebuilt guidance lookup:
> faster at runtime, easier to inspect, and perfect for a 54-cell persona-emotion matrix.

Use with:

- Slide visual:

```text
User input
-> emotion detection
-> persona_id + emotion lookup
-> prompt context
-> LLM response
-> TTS output
```

Source:

- AWS Bedrock Knowledge Bases docs: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html

## Persona Comparison Slide

Use one user message and show how Jarvis adapts across personas.

User message:

> I am overwhelmed. I have three deadlines, and I do not know where to start.

Detected emotion:

`fear`

### Priya Shah - Stressed MSBA Student

Response:

> You are overloaded, not broken. Pick the deadline with the closest consequence,
> write the first deliverable in one sentence, and work on only that for 15 minutes.

Why it works:

Direct, expressive, mixed support, anxious attachment. Acknowledge pressure, reduce
self-blame, then triage.

### Tony Stark - Armored Fixer

Response:

> Triage it. Rank the three deadlines by consequence, pick the highest-impact one,
> and define the next physical action. No emotional autopsy required.

Why it works:

Direct, suppression, instrumental support, avoidant attachment. Keep autonomy and
move quickly to options.

### Maya Chen - Reassurance Texter

Response:

> That sounds like a lot, and it makes sense that your brain is trying to treat all
> three as emergencies. You do not have to solve all of them tonight. Start by naming
> the one that is actually due first.

Why it works:

Indirect, expressive, emotional support, anxious attachment. Validate first, then
separate facts from fear.

### Default Danny - Steady Default

Response:

> Let's make it smaller. Choose the deadline that matters most today, define the next
> 15-minute action, and come back to the full list after that.

Why it works:

Direct, reappraisal, mixed support, secure attachment. Balanced, clear, and practical.

## Demo Flow For Presentation

1. Open the browser UI and show the current default persona.
2. Send a stressed text prompt through `/api/chat`.
3. Show `detected_emotion` in the raw JSON.
4. Show that the response uses guidance from `corpus/persona_guidance.json`.
5. Use `/api/personas` to show the available profiles.
6. Explain the future vector RAG layer:

```text
uploaded docs -> chunk -> embed -> vector DB -> retrieve top chunks -> LLM prompt
```

