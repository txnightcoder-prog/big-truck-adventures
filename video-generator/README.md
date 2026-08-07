# Big Truck Adventures — Video Generator

Free, no-subscription Python video generator for the Big Truck Adventures kids cartoon.

## What it does
- Takes your Gemini character images
- Composes them onto colorful cartoon backgrounds
- Adds educational text overlays (letters, numbers, colors)
- Generates text-to-speech narration for each scene
- Exports a complete MP4 video ready to upload to YouTube

## Setup (one time)

1. Make sure Python is installed: https://python.org
2. Double-click `INSTALL_AND_RUN.bat`
   - This installs all dependencies and runs a preview automatically

OR manually:
```
pip install -r requirements.txt
python generate_video.py --episode 1 --preview
```

## Where to put your character images

```
Downloads/
└── BigTruckAdventures/
    ├── characters/
    │   ├── jensen.png
    │   ├── bentley.png
    │   ├── russell.png
    │   └── emery.png
    └── trucks/
        ├── max.png
        ├── charlie.png
        ├── remy.png
        └── bella.png
```

## Usage

```bash
# Preview all scenes as still images (fast, no moviepy needed)
python generate_video.py --episode 1 --preview

# Generate full MP4 video
python generate_video.py --episode 1

# List all available episodes
python generate_video.py --list
```

## Output

Videos are saved to the `output/` folder:
```
output/
└── E01-Jensen's-First-Day-Countdown.mp4
```

Upload this file directly to YouTube Studio.

## Adding more episodes

Edit `generate_video.py` and add to the `EPISODES` dictionary.
Each episode has scenes with:
- `bg` — background type (sky, kitchen, town, factory, road, sunset)
- `characters` — list of character names to show
- `trucks` — list of truck names to show
- `text_overlay` — title text at top of scene
- `narration` — what the AI voice says
- `edu_overlay` — educational content bubble (letter, number, etc.)
- `duration` — how many seconds the scene lasts

## Dependencies (all free, open source)
- `moviepy` — video assembly and export
- `Pillow` — image composition and text rendering
- `gTTS` — Google Text-to-Speech (free, uses Google's TTS)
- `numpy` — image processing
