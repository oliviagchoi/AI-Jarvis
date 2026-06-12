# Demo Kit

This folder contains reusable demo scenarios for Jarvis.

## What Is Included

- `audio/` generated `.wav` clips for upload-based demos
- `scenarios.json` with transcript override text, heart rate, and stress level
- `DOWNLOAD_CHECKLIST.md` with recommended real audio sources and filenames

The clips are synthetic tones, not spoken recordings. They are meant to be used with
`transcript_override`, so the backend still receives a valid audio file while the spoken
content comes from the scenario text.

## Generate Or Regenerate The Demo Files

From the project root:

```bash
python3 scripts/generate_demo_assets.py
```

## Run All Demo Scenarios Against A Running App

Start the app first, then run:

```bash
python3 scripts/run_demo_scenarios.py
```

Run one scenario only:

```bash
python3 scripts/run_demo_scenarios.py --scenario stressed_focus
```

## Suggested Scenario Order

1. `stressed_focus`
2. `excited_win`
3. `sad_support`
4. `remember_preference`

After `remember_preference`, send a normal follow-up prompt in the UI like:

- `What should I do next?`

## UI Demo Tips

- Use the same `Session ID` while showing a multi-turn flow.
- Match the UI's `Simulated Heart Rate` and `Simulated Stress Level` controls to the scenario.
- For a browser-only demo, you can copy the scenario transcript into `Transcript Override` and use `Start Voice Turn` with any short recording.
