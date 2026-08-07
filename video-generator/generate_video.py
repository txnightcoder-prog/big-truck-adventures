"""
BIG TRUCK ADVENTURES — AI Video Generator
==========================================
Generates a full kids cartoon episode as an MP4 video.

Uses:
  - Your Gemini character images (from Downloads/BigTruckAdventures/)
  - gTTS for text-to-speech narration
  - Pillow for scene composition / image manipulation
  - MoviePy for video assembly and export
  - Google Gemini API for AI scene description enhancement

Usage:
  python generate_video.py --episode 1

Requirements:
  pip install -r requirements.txt
"""

import os
import sys
import json
import argparse
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

# ── Try importing optional heavy libs ─────────────────────────────────────────
try:
    from moviepy.editor import (
        ImageClip, AudioFileClip, CompositeVideoClip,
        concatenate_videoclips, TextClip, ColorClip
    )
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False
    print("[WARN] moviepy not installed. Run: pip install moviepy")

try:
    from gtts import gTTS
    GTTS_OK = True
except ImportError:
    GTTS_OK = False
    print("[WARN] gTTS not installed. Run: pip install gTTS")

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
ASSETS_DIR   = BASE_DIR / "assets"
OUTPUT_DIR   = BASE_DIR / "output"
AUDIO_DIR    = BASE_DIR / "temp_audio"

# Where the user saved their Gemini images
DOWNLOADS    = Path.home() / "Downloads" / "BigTruckAdventures"

# Fallback character image folders
CHAR_DIR     = DOWNLOADS / "characters"
TRUCK_DIR    = DOWNLOADS / "trucks"

for d in [ASSETS_DIR, OUTPUT_DIR, AUDIO_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── COLORS ────────────────────────────────────────────────────────────────────
SKY_BLUE    = (100, 180, 255)
GRASS_GREEN = (80,  180,  80)
DIRT_ORANGE = (210, 140,  60)
ROAD_GREY   = (130, 130, 130)
WHITE       = (255, 255, 255)
BLACK       = (0,   0,   0)
YELLOW      = (255, 210,  0)
WARM_YELLOW = (255, 230, 100)
BRIGHT_RED  = (220,  50,  50)

# ── EPISODE DATA ──────────────────────────────────────────────────────────────
EPISODES = {
    1: {
        "title": "Jensen's First Day Countdown",
        "subtitle": "Letters, Numbers & Colors",
        "scenes": [
            {
                "id": "intro",
                "duration": 5,
                "bg": "sky",
                "characters": ["jensen", "bentley", "russell", "emery"],
                "trucks": ["max", "charlie", "remy", "bella"],
                "text_overlay": "BIG TRUCK ADVENTURES",
                "text_color": YELLOW,
                "narration": "Big Truck Adventures! Join Jensen, Bentley, Russell, and baby Emery!",
                "edu_overlay": None,
            },
            {
                "id": "kitchen",
                "duration": 8,
                "bg": "kitchen",
                "characters": ["jensen", "bentley", "russell", "emery"],
                "trucks": [],
                "text_overlay": "Jensen's First Day Countdown!",
                "text_color": YELLOW,
                "narration": "Jensen is SO excited! Only TEN more days until kindergarten!",
                "edu_overlay": {"text": "10", "color": BRIGHT_RED, "label": "TEN days!"},
            },
            {
                "id": "truck_yard",
                "duration": 7,
                "bg": "truck_yard",
                "characters": ["jensen"],
                "trucks": ["max", "charlie", "remy", "bella"],
                "text_overlay": "The Truck Yard",
                "text_color": WHITE,
                "narration": "Jensen counts his school supply list with Charlie the Crane Truck. One, two, three, four, five, six, seven, eight, nine, TEN!",
                "edu_overlay": {"text": "1 2 3 4 5\n6 7 8 9 10", "color": YELLOW, "label": "Count to TEN!"},
            },
            {
                "id": "pencil_shop",
                "duration": 7,
                "bg": "town",
                "characters": ["jensen", "bentley"],
                "trucks": ["max"],
                "text_overlay": "The Pencil Shop",
                "text_color": WHITE,
                "narration": "P is for Pencil! P makes the puh sound. Puh-Puh-Pencil!",
                "edu_overlay": {"text": "P", "color": BRIGHT_RED, "label": "P is for Pencil!"},
            },
            {
                "id": "crayon_factory",
                "duration": 7,
                "bg": "factory",
                "characters": ["jensen", "russell", "emery"],
                "trucks": [],
                "text_overlay": "The Crayon Factory",
                "text_color": WHITE,
                "narration": "Red, blue, yellow, and green! That is FOUR colors!",
                "edu_overlay": {"text": "RED  BLUE\nYELLOW  GREEN", "color": YELLOW, "label": "4 Colors!"},
            },
            {
                "id": "backpack_bridge",
                "duration": 6,
                "bg": "town",
                "characters": ["jensen"],
                "trucks": ["charlie"],
                "text_overlay": "The Backpack Bridge",
                "text_color": WHITE,
                "narration": "Jensen counts the backpacks. One, two, three, four, FIVE! Backpack number five!",
                "edu_overlay": {"text": "5", "color": BRIGHT_RED, "label": "Number FIVE!"},
            },
            {
                "id": "alphabet_road",
                "duration": 8,
                "bg": "road",
                "characters": ["jensen", "bentley", "russell", "emery"],
                "trucks": ["remy"],
                "text_overlay": "The Alphabet Road",
                "text_color": WHITE,
                "narration": "A B C D E F G! H I J K L M N O P! Q R S T U V! W X Y and Z!",
                "edu_overlay": {"text": "A B C D E F G\nH I J K L M N O P\nQ R S T U V W X Y Z", "color": YELLOW, "label": "The Alphabet!"},
            },
            {
                "id": "emery_saves_day",
                "duration": 6,
                "bg": "town",
                "characters": ["emery", "jensen", "bentley", "russell"],
                "trucks": ["bella"],
                "text_overlay": "Emery Saves the Day!",
                "text_color": YELLOW,
                "narration": "Baby Emery found the missing name tag in Bella's loader bucket! Emery saves the day!",
                "edu_overlay": {"text": "J", "color": BRIGHT_RED, "label": "J is for Jensen!"},
            },
            {
                "id": "recap",
                "duration": 8,
                "bg": "sky",
                "characters": ["jensen"],
                "trucks": [],
                "text_overlay": "I learned that for kindergarten!",
                "text_color": YELLOW,
                "narration": "I learned that P is for Pencil! J is for Jensen! Red, blue, yellow, green are four colors! And I can count all the way to TEN! I learned that for kindergarten!",
                "edu_overlay": {"text": "P  J\n1 2 3 4 5 6 7 8 9 10", "color": YELLOW, "label": "I learned that for kindergarten!"},
            },
            {
                "id": "outro",
                "duration": 5,
                "bg": "sunset",
                "characters": ["jensen", "bentley", "russell", "emery"],
                "trucks": ["max", "charlie", "remy", "bella"],
                "text_overlay": "See you next time on\nBig Truck Adventures!",
                "text_color": YELLOW,
                "narration": "See you next time on Big Truck Adventures! Don't forget to subscribe!",
                "edu_overlay": None,
            },
        ]
    }
}

# ── BACKGROUND GENERATOR ─────────────────────────────────────────────────────

def make_background(bg_type: str, width=1280, height=720) -> Image.Image:
    """Generate a colorful background for a scene."""
    img = Image.new("RGB", (width, height), SKY_BLUE)
    draw = ImageDraw.Draw(img)

    if bg_type in ("sky", "truck_yard", "road", "town", "factory"):
        # Sky gradient
        for y in range(height // 2):
            ratio = y / (height // 2)
            r = int(SKY_BLUE[0] * (1 - ratio * 0.3))
            g = int(SKY_BLUE[1] * (1 - ratio * 0.1))
            b = int(min(255, SKY_BLUE[2] * (1 + ratio * 0.1)))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Ground
        draw.rectangle([(0, height//2), (width, height)], fill=GRASS_GREEN)

        # Dirt path
        draw.rectangle([(0, int(height*0.55)), (width, int(height*0.75))], fill=DIRT_ORANGE)

        # Road
        draw.rectangle([(0, int(height*0.62)), (width, int(height*0.72))], fill=ROAD_GREY)

        # Road dashes
        for x in range(0, width, 120):
            draw.rectangle([(x, int(height*0.665)), (x+60, int(height*0.675))], fill=YELLOW)

        # Sun
        draw.ellipse([(width-140, 30), (width-30, 140)], fill=(255, 220, 50))

        # Clouds
        for cx, cy in [(150, 60), (400, 40), (700, 80)]:
            draw.ellipse([(cx-60, cy-20), (cx+60, cy+20)], fill=(240, 245, 255))
            draw.ellipse([(cx-30, cy-35), (cx+30, cy+5)],  fill=(240, 245, 255))

    elif bg_type == "kitchen":
        # Warm kitchen
        draw.rectangle([(0, 0), (width, height)], fill=(255, 240, 200))
        # Floor
        draw.rectangle([(0, int(height*0.7)), (width, height)], fill=(200, 170, 120))
        # Window
        draw.rectangle([(width-200, 50), (width-50, 200)], fill=(180, 220, 255))
        draw.line([(width-125, 50), (width-125, 200)], fill=(150, 120, 80), width=4)
        draw.line([(width-200, 125), (width-50, 125)], fill=(150, 120, 80), width=4)
        # Counter
        draw.rectangle([(0, int(height*0.55)), (width//3, int(height*0.7))], fill=(180, 150, 100))

    elif bg_type == "sunset":
        # Warm sunset
        for y in range(height):
            ratio = y / height
            r = int(255 * (1 - ratio * 0.3))
            g = int(160 * (1 - ratio * 0.5))
            b = int(80  * (1 - ratio * 0.6))
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        draw.rectangle([(0, int(height*0.65)), (width, height)], fill=(60, 120, 60))

    return img


# ── CHARACTER PLACER ─────────────────────────────────────────────────────────

def load_character(name: str, height_px: int = 280) -> Image.Image | None:
    """Load a character image, resize proportionally."""
    # Search paths
    search_paths = [
        CHAR_DIR / f"{name}.png",
        CHAR_DIR / f"{name}.jpg",
        CHAR_DIR / f"{name}.jpeg",
        TRUCK_DIR / f"{name}.png",
        TRUCK_DIR / f"{name}.jpg",
        DOWNLOADS / f"{name}.png",
        DOWNLOADS / f"{name}.jpg",
        ASSETS_DIR / f"{name}.png",
    ]
    for p in search_paths:
        if p.exists():
            img = Image.open(p).convert("RGBA")
            ratio = height_px / img.height
            new_w = int(img.width * ratio)
            return img.resize((new_w, height_px), Image.LANCZOS)

    # Fallback: colored placeholder rectangle with name
    placeholder = Image.new("RGBA", (int(height_px * 0.6), height_px), (200, 200, 200, 200))
    draw = ImageDraw.Draw(placeholder)
    draw.rectangle([(2, 2), (placeholder.width-2, placeholder.height-2)], outline=BLACK, width=3)
    # Draw initials
    initial = name[0].upper()
    draw.text((placeholder.width//2 - 15, placeholder.height//2 - 20), initial, fill=BLACK)
    return placeholder


def place_characters(bg: Image.Image, char_names: list, truck_names: list) -> Image.Image:
    """Place character and truck images onto the background."""
    scene = bg.copy().convert("RGBA")
    w, h = scene.size

    # Ground level Y positions
    char_ground_y = int(h * 0.58)
    truck_ground_y = int(h * 0.52)

    # Place trucks in background (larger, spaced)
    truck_height = int(h * 0.30)
    if truck_names:
        spacing = w // (len(truck_names) + 1)
        for i, name in enumerate(truck_names):
            img = load_character(name, height_px=truck_height)
            if img:
                x = spacing * (i + 1) - img.width // 2
                y = truck_ground_y - img.height
                scene.paste(img, (x, y), img if img.mode == "RGBA" else None)

    # Place characters in foreground
    char_height = int(h * 0.38)
    if char_names:
        spacing = w // (len(char_names) + 1)
        for i, name in enumerate(char_names):
            img = load_character(name, height_px=char_height)
            if img:
                x = spacing * (i + 1) - img.width // 2
                y = char_ground_y - img.height
                scene.paste(img, (x, y), img if img.mode == "RGBA" else None)

    return scene.convert("RGB")


# ── TEXT OVERLAY ─────────────────────────────────────────────────────────────

def add_text_overlays(scene: Image.Image, scene_data: dict) -> Image.Image:
    """Add title text and educational overlays to a scene image."""
    img = scene.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # Try to load a bold font, fall back to default
    font_large = ImageFont.load_default()
    font_edu   = ImageFont.load_default()
    font_small = ImageFont.load_default()

    # Try system fonts
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            try:
                font_large = ImageFont.truetype(fp, 52)
                font_edu   = ImageFont.truetype(fp, 80)
                font_small = ImageFont.truetype(fp, 32)
                break
            except Exception:
                pass

    # ── Title bar at top ──────────────────────────────────────────────────────
    title = scene_data.get("text_overlay", "")
    if title:
        bar_h = 80
        bar = Image.new("RGBA", (w, bar_h), (0, 0, 0, 160))
        img.paste(bar, (0, 0), bar)
        draw = ImageDraw.Draw(img)
        color = scene_data.get("text_color", YELLOW)
        # Shadow
        draw.text((w//2 - 1 + 2, 14 + 2), title, font=font_large, fill=BLACK, anchor="mt")
        draw.text((w//2 - 1, 14), title, font=font_large, fill=color, anchor="mt")

    # ── Educational overlay (big letter / number) ─────────────────────────────
    edu = scene_data.get("edu_overlay")
    if edu:
        edu_text  = edu.get("text", "")
        edu_color = edu.get("color", YELLOW)
        edu_label = edu.get("label", "")

        # Background bubble
        bubble_w, bubble_h = 320, 200
        bx = w - bubble_w - 30
        by = h - bubble_h - 80

        bubble = Image.new("RGBA", (bubble_w, bubble_h), (255, 255, 255, 220))
        bubble_draw = ImageDraw.Draw(bubble)
        bubble_draw.rounded_rectangle([(0,0),(bubble_w-1, bubble_h-1)], radius=20,
                                       outline=edu_color, width=5)

        # Big text
        lines = edu_text.split("\n")
        line_h = bubble_h // (len(lines) + 1)
        for li, line in enumerate(lines):
            bubble_draw.text((bubble_w//2, line_h * (li + 1) - 10),
                             line, font=font_edu, fill=edu_color, anchor="mm")

        img.paste(bubble, (bx, by), bubble)
        draw = ImageDraw.Draw(img)

        # Label below bubble
        if edu_label:
            draw.text((bx + bubble_w//2, by + bubble_h + 10),
                      edu_label, font=font_small, fill=WHITE, anchor="mt")

    # ── Bottom show name bar ──────────────────────────────────────────────────
    bar2 = Image.new("RGBA", (w, 50), (0, 0, 0, 140))
    img.paste(bar2, (0, h - 50), bar2)
    draw = ImageDraw.Draw(img)
    draw.text((w//2, h - 25), "BIG TRUCK ADVENTURES  |  @BigTruckVideosforKids",
              font=font_small, fill=WARM_YELLOW, anchor="mm")

    return img


# ── NARRATION GENERATOR ───────────────────────────────────────────────────────

def generate_narration(text: str, filepath: Path, lang="en", slow=False) -> bool:
    """Generate TTS audio for a scene using gTTS."""
    if not GTTS_OK:
        return False
    try:
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(str(filepath))
        return True
    except Exception as e:
        print(f"[WARN] TTS failed for '{text[:30]}...': {e}")
        return False


# ── SCENE BUILDER ─────────────────────────────────────────────────────────────

def build_scene(scene_data: dict, scene_index: int) -> str | None:
    """Build a single scene as a video clip file. Returns path to temp file."""
    if not MOVIEPY_OK:
        print("[ERROR] moviepy required to build scenes")
        return None

    sid = scene_data["id"]
    duration = scene_data["duration"]
    print(f"  Building scene {scene_index+1}: {sid} ({duration}s)...")

    # 1. Generate background
    bg = make_background(scene_data["bg"])

    # 2. Place characters
    frame = place_characters(bg, scene_data["characters"], scene_data["trucks"])

    # 3. Add text overlays
    frame = add_text_overlays(frame, scene_data)

    # 4. Save frame as temp image
    frame_path = AUDIO_DIR / f"scene_{scene_index:02d}_{sid}.png"
    frame.save(str(frame_path))

    # 5. Generate narration audio
    narration = scene_data.get("narration", "")
    audio_path = AUDIO_DIR / f"scene_{scene_index:02d}_{sid}.mp3"
    has_audio = generate_narration(narration, audio_path) if narration else False

    # 6. Build video clip
    clip = ImageClip(str(frame_path)).set_duration(duration)

    if has_audio and audio_path.exists():
        try:
            audio = AudioFileClip(str(audio_path))
            # Trim audio if longer than scene duration
            if audio.duration > duration:
                audio = audio.subclip(0, duration)
            clip = clip.set_audio(audio)
        except Exception as e:
            print(f"  [WARN] Could not attach audio: {e}")

    # 7. Add simple fade in/out
    clip = clip.fadein(0.3).fadeout(0.3)

    # Save clip
    temp_clip_path = str(AUDIO_DIR / f"clip_{scene_index:02d}_{sid}.mp4")
    clip.write_videofile(temp_clip_path, fps=24, codec="libx264",
                         audio_codec="aac", logger=None, verbose=False)
    return temp_clip_path


# ── EPISODE ASSEMBLER ─────────────────────────────────────────────────────────

def generate_episode(episode_num: int):
    """Generate a full episode video."""
    if episode_num not in EPISODES:
        print(f"[ERROR] Episode {episode_num} not found.")
        return

    ep = EPISODES[episode_num]
    print(f"\n{'='*60}")
    print(f"  GENERATING: Episode {episode_num} — {ep['title']}")
    print(f"{'='*60}\n")

    if not MOVIEPY_OK:
        print("[ERROR] moviepy is required. Run:\n  pip install moviepy")
        return

    # Build each scene
    clip_paths = []
    for i, scene in enumerate(ep["scenes"]):
        path = build_scene(scene, i)
        if path:
            clip_paths.append(path)

    if not clip_paths:
        print("[ERROR] No scenes were generated.")
        return

    # Concatenate all scenes
    print(f"\nAssembling {len(clip_paths)} scenes...")
    clips = [VideoFileClip(p) for p in clip_paths]  # noqa

    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        clips = [VideoFileClip(p) for p in clip_paths]
        final = concatenate_videoclips(clips, method="compose")

        output_path = OUTPUT_DIR / f"E{episode_num:02d}-{ep['title'].replace(' ', '-')}.mp4"
        print(f"Exporting to: {output_path}")
        final.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(AUDIO_DIR / "temp_audio.m4a"),
            remove_temp=True,
        )
        print(f"\n{'='*60}")
        print(f"  ✓ DONE! Video saved to:")
        print(f"  {output_path}")
        print(f"{'='*60}\n")
        print("Next step: Upload this file to YouTube Studio!")

    except Exception as e:
        print(f"[ERROR] Assembly failed: {e}")
    finally:
        # Cleanup temp files
        for p in clip_paths:
            try:
                Path(p).unlink()
            except Exception:
                pass


# ── QUICK PREVIEW (no moviepy needed) ────────────────────────────────────────

def generate_preview(episode_num: int):
    """Generate still images for each scene — quick preview without moviepy."""
    if episode_num not in EPISODES:
        print(f"[ERROR] Episode {episode_num} not found.")
        return

    ep = EPISODES[episode_num]
    preview_dir = OUTPUT_DIR / f"E{episode_num:02d}_preview"
    preview_dir.mkdir(exist_ok=True)

    print(f"\nGenerating preview frames for: {ep['title']}")
    print(f"Output: {preview_dir}\n")

    for i, scene in enumerate(ep["scenes"]):
        bg = make_background(scene["bg"])
        frame = place_characters(bg, scene["characters"], scene["trucks"])
        frame = add_text_overlays(frame, scene)
        out = preview_dir / f"scene_{i+1:02d}_{scene['id']}.png"
        frame.save(str(out))
        print(f"  ✓ Scene {i+1}: {scene['id']} → {out.name}")

    print(f"\nPreview complete! Open {preview_dir} to review all scenes.")
    print("If scenes look good, run without --preview to generate the full video.")


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Big Truck Adventures Video Generator")
    parser.add_argument("--episode", type=int, default=1, help="Episode number to generate (default: 1)")
    parser.add_argument("--preview", action="store_true", help="Generate preview images only (no video, much faster)")
    parser.add_argument("--list", action="store_true", help="List all available episodes")
    args = parser.parse_args()

    if args.list:
        print("\nAvailable episodes:")
        for num, ep in EPISODES.items():
            scene_count = len(ep["scenes"])
            total_dur   = sum(s["duration"] for s in ep["scenes"])
            print(f"  Episode {num}: {ep['title']} ({scene_count} scenes, ~{total_dur}s)")
        sys.exit(0)

    if args.preview:
        generate_preview(args.episode)
    else:
        generate_episode(args.episode)
