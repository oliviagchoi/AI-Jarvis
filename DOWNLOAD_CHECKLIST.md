# Demo Audio Download Checklist

Use this checklist to build a stronger demo audio library for Jarvis.

## Target Folder Layout

Store downloaded files here:

```text
demo/
├── audio/
│   ├── generated/
│   ├── emotion/
│   │   ├── ravdess/
│   │   └── crema_d/
│   ├── accent/
│   └── fallback/
```

Suggested meanings:

- `generated/`: synthetic clips already bundled in this repo
- `emotion/ravdess/`: acted emotional speech clips
- `emotion/crema_d/`: additional emotional speech clips with more speaker variety
- `accent/`: real accent and STT stress-test clips
- `fallback/`: any extra clips you want available offline during demo day

## Recommended Downloads

### 1. RAVDESS

Primary source:

- https://zenodo.org/records/1188976

Easy mirror:

- https://www.kaggle.com/datasets/uwrfkaggler/ravdess-emotional-speech-audio/data

Put these in:

- `demo/audio/emotion/ravdess/`

Recommended files:

- `03-01-01-01-01-01-01.wav`
- `03-01-01-01-01-01-02.wav`
- `03-01-02-01-01-01-03.wav`
- `03-01-02-01-01-01-04.wav`
- `03-01-03-02-01-01-05.wav`
- `03-01-03-02-01-01-06.wav`
- `03-01-04-02-01-01-07.wav`
- `03-01-04-02-01-01-08.wav`
- `03-01-05-02-01-01-09.wav`
- `03-01-05-02-01-01-10.wav`
- `03-01-06-02-01-01-11.wav`
- `03-01-06-02-01-01-12.wav`
- `03-01-08-02-01-01-13.wav`
- `03-01-08-02-01-01-14.wav`

These cover:

- neutral
- calm
- happy
- sad
- angry
- fearful
- surprised
- both male and female voices

### 2. CREMA-D

Source:

- https://www.kaggle.com/datasets/ejlok1/cremad/data

Put these in:

- `demo/audio/emotion/crema_d/`

Download a few examples for each:

- `NEU`
- `HAP`
- `SAD`
- `ANG`

Suggested goal:

- 2 to 3 speakers per emotion

Reason:

- more natural variation than using only RAVDESS

### 3. Speech Accent Archive

Source:

- https://accent.gmu.edu/
- browse: https://accent.gmu.edu/browse.php

Put these in:

- `demo/audio/accent/`

Recommended types of samples:

- native US English
- Indian English
- Chinese L1 speaker
- Spanish L1 speaker
- Arabic L1 speaker

Reason:

- useful for testing STT robustness
- useful for showing that Jarvis can still handle different accents

## Best Minimal Download Set

If you only want a small pack, download:

- 8 to 10 RAVDESS clips
- 4 accent clips from Speech Accent Archive
- 4 CREMA-D clips

That is enough for:

- emotional demo scenes
- realistic speech tests
- accent robustness checks

## Suggested Naming After Download

Rename copies of the files like this if you want a cleaner demo folder:

- `neutral_male_ravdess.wav`
- `neutral_female_ravdess.wav`
- `happy_male_ravdess.wav`
- `sad_female_ravdess.wav`
- `angry_male_ravdess.wav`
- `fearful_female_ravdess.wav`
- `accent_indian_english_01.wav`
- `accent_spanish_l1_01.wav`

Keep the originals too if you want traceability.

## Presentation-Day Tips

- Keep a few clips under 5 to 10 seconds.
- Prefer `.wav` files when available.
- Keep one clip per emotion ready in a quick-access folder.
- Keep 2 backup clips in `fallback/` in case one file is noisy or too quiet.
- Test every downloaded file once before demo day.

## Source Notes

- RAVDESS naming convention and dataset details: https://zenodo.org/records/1188976
- RAVDESS Kaggle mirror: https://www.kaggle.com/datasets/uwrfkaggler/ravdess-emotional-speech-audio/data
- CREMA-D: https://www.kaggle.com/datasets/ejlok1/cremad/data
- Speech Accent Archive: https://accent.gmu.edu/
