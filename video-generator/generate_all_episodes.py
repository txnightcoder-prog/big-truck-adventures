# -*- coding: utf-8 -*-
"""
BIG TRUCK ADVENTURES — Automated Episode Generator
====================================================
Generates all 7 Season 1 episodes as MP4 videos automatically.
Uses your Gemini character images + the episode scripts.

Usage:
  python generate_all_episodes.py           # Generate all 7 episodes
  python generate_all_episodes.py --ep 1    # Generate just episode 1
  python generate_all_episodes.py --preview # Preview frames only (fast)

Output: exports\ folder — one MP4 per episode, ready to upload to YouTube
"""

import sys, os, json, math, textwrap, argparse, shutil
from pathlib import Path
from typing import Optional

# Force UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('PYTHONUTF8', '1')

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
EXPORTS_DIR  = BASE_DIR / "exports"
TEMP_DIR     = BASE_DIR / ".tmp_gen"
DOWNLOADS    = Path.home() / "Downloads" / "BigTruckAdventures"
CHAR_DIR     = DOWNLOADS / "characters"
TRUCK_DIR    = DOWNLOADS / "trucks"
EXPORTS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# ── DEPS ──────────────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("[ERROR] Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

try:
    from moviepy.editor import (
        ImageClip, AudioFileClip, concatenate_videoclips,
        CompositeVideoClip, TextClip, ColorClip, VideoFileClip
    )
    import moviepy.config as mpy_cfg
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False
    print("[ERROR] moviepy not installed. Run: pip install moviepy")
    sys.exit(1)

try:
    from gtts import gTTS
    GTTS_OK = True
except ImportError:
    GTTS_OK = False
    print("[WARN] gTTS not installed — no narration audio. Run: pip install gTTS")

# ── COLORS ────────────────────────────────────────────────────────────────────
W, H = 1280, 720

SKY_TOP    = (80,  160, 240)
SKY_BOT    = (140, 210, 255)
GRASS      = (60,  160,  60)
DIRT       = (180, 120,  50)
ROAD_COL   = (100, 100, 110)
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
YELLOW     = (255, 210,   0)
ORANGE     = (255, 140,   0)
RED        = (220,  50,  50)
BLUE       = (30,  100, 220)
GREEN      = (30,  160,  60)
PINK       = (220,  80, 160)
PURPLE     = (140,  60, 200)
AMBER      = (255, 180,   0)
DARK_BLUE  = (20,  40,  100)

# ── FONTS ─────────────────────────────────────────────────────────────────────
FONT_PATHS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]

def get_font(size: int) -> ImageFont.FreeTypeFont:
    for fp in FONT_PATHS:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()

# ── BACKGROUND BUILDER ────────────────────────────────────────────────────────

def make_bg(bg_type: str) -> Image.Image:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Sky gradient
    for y in range(H):
        t = y / H
        r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
        g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
        b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
        if y > H * 0.55:
            # Ground fade
            gf = min(1.0, (y - H * 0.55) / (H * 0.15))
            r = int(r + (GRASS[0] - r) * gf)
            g = int(g + (GRASS[1] - g) * gf)
            b = int(b + (GRASS[2] - b) * gf)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Road
    ry1, ry2 = int(H * 0.60), int(H * 0.75)
    draw.rectangle([(0, ry1), (W, ry2)], fill=ROAD_COL)
    # Road markings
    for x in range(0, W, 120):
        draw.rectangle([(x+10, H//2 + 85), (x+80, H//2 + 92)], fill=YELLOW)

    # Sun
    draw.ellipse([(W-130, 20), (W-20, 130)], fill=(255, 220, 50))
    draw.ellipse([(W-120, 30), (W-30, 120)], fill=(255, 240, 100))

    # Clouds
    for cx, cy, sz in [(120,55,50), (380,35,40), (680,65,45), (950,40,38)]:
        draw.ellipse([(cx-sz, cy-sz//2), (cx+sz, cy+sz//2)], fill=(240, 245, 255))
        draw.ellipse([(cx-sz//2, cy-sz), (cx+sz//2, cy)], fill=(240, 245, 255))
        draw.ellipse([(cx, cy-sz//2), (cx+sz*1.2, cy+sz//2)], fill=(240, 245, 255))

    # Buildings (town background)
    if bg_type in ("town", "factory", "kitchen"):
        for bx, bw, bh, bc in [
            (50,  80, 120, (180,140,100)),
            (160, 60, 100, (140,170,200)),
            (250, 90, 140, (200,160,120)),
            (900, 70, 110, (160,190,160)),
            (1000,80, 130, (190,150,130)),
            (1110,65,  95, (170,180,210)),
        ]:
            by = int(H * 0.55) - bh
            draw.rectangle([(bx, by), (bx+bw, int(H*0.55))], fill=bc)
            # Windows
            for wy in range(by+10, by+bh-20, 25):
                for wx in range(bx+10, bx+bw-10, 20):
                    draw.rectangle([(wx, wy), (wx+10, wy+12)],
                                   fill=(220,240,255), outline=(150,170,200))

    if bg_type == "kitchen":
        # Warm kitchen overlay
        overlay = Image.new("RGBA", (W, H), (255, 240, 200, 80))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)

    if bg_type == "sunset":
        for y in range(H):
            t = y / H
            r = int(255 * (1 - t * 0.3))
            g = int(180 * (1 - t * 0.5))
            b = int(100 * (1 - t * 0.5))
            if y > H * 0.65:
                gf = min(1.0, (y - H * 0.65) / 0.1 / H)
                r = int(r + (40 - r) * gf)
                g = int(g + (100 - g) * gf)
                b = int(b + (40 - b) * gf)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

    return img


# ── CHARACTER LOADER ──────────────────────────────────────────────────────────

def load_char(name: str, height: int, fallback_color=(200,200,200)) -> Image.Image:
    for d in [CHAR_DIR, TRUCK_DIR, DOWNLOADS]:
        for ext in [".png", ".jpg", ".jpeg", ".PNG", ".JPG"]:
            p = d / f"{name}{ext}"
            if p.exists():
                img = Image.open(p).convert("RGBA")
                ratio = height / img.height
                return img.resize((int(img.width * ratio), height), Image.LANCZOS)

    # Colored placeholder
    pw = int(height * 0.65)
    ph = height
    pl = Image.new("RGBA", (pw, ph), (*fallback_color, 200))
    d = ImageDraw.Draw(pl)
    d.rectangle([(2,2),(pw-2,ph-2)], outline=BLACK, width=3)
    font = get_font(max(20, height//6))
    initial = name[0].upper()
    d.text((pw//2, ph//2), initial, fill=BLACK, font=font, anchor="mm")
    d.text((pw//2, ph//2 + height//5), name[:6], fill=(80,80,80),
           font=get_font(max(12, height//10)), anchor="mm")
    return pl


# ── SCENE COMPOSITOR ──────────────────────────────────────────────────────────

CHAR_COLORS = {
    "jensen": (255, 200, 50),
    "bentley": (50, 130, 255),
    "russell": (50, 200, 80),
    "emery": (255, 100, 180),
    "max": (40, 100, 220),
    "charlie": (220, 160, 30),
    "remy": (50, 180, 70),
    "bella": (220, 100, 160),
}

def compose_scene(
    bg_type: str,
    chars: list,
    trucks: list,
    title: str,
    title_color: tuple,
    edu: Optional[dict],
    ep_num: int,
) -> Image.Image:
    bg = make_bg(bg_type)
    draw = ImageDraw.Draw(bg)
    w, h = W, H

    # Trucks (background, larger)
    truck_h = int(h * 0.28)
    truck_y_base = int(h * 0.62)
    if trucks:
        spacing = w // (len(trucks) + 1)
        for i, name in enumerate(trucks):
            color = CHAR_COLORS.get(name, (180, 180, 180))
            img = load_char(name, truck_h, color)
            x = spacing * (i + 1) - img.width // 2
            y = truck_y_base - img.height
            bg.paste(img, (x, y), img)

    # Characters (foreground)
    char_h = int(h * 0.36)
    char_y_base = int(h * 0.70)
    if chars:
        # Space chars across center of screen
        total_w = len(chars) * int(char_h * 0.65)
        start_x = w // 2 - total_w // 2
        for i, name in enumerate(chars):
            color = CHAR_COLORS.get(name, (200, 200, 200))
            img = load_char(name, char_h, color)
            x = start_x + i * int(char_h * 0.7) + img.width // 4
            y = char_y_base - img.height
            bg.paste(img, (x, y), img)

    draw = ImageDraw.Draw(bg)

    # ── Top title bar ─────────────────────────────────────────────────────────
    bar = Image.new("RGBA", (w, 80), (0, 0, 0, 170))
    bg = bg.convert("RGBA")
    bg.paste(bar, (0, 0), bar)
    bg = bg.convert("RGB")
    draw = ImageDraw.Draw(bg)

    font_title = get_font(44)
    # Shadow
    draw.text((w//2 + 2, 40 + 2), title, font=font_title, fill=BLACK, anchor="mm")
    draw.text((w//2, 40), title, font=font_title, fill=title_color, anchor="mm")

    # ── Educational overlay bubble ────────────────────────────────────────────
    if edu:
        bw, bh = 280, 200
        bx = w - bw - 25
        by = h - bh - 60

        bubble = Image.new("RGBA", (bw, bh), (255, 255, 255, 235))
        bd = ImageDraw.Draw(bubble)
        border_color = edu.get("color", YELLOW)
        # Rounded rect via multiple rects
        bd.rectangle([(8,0),(bw-8,bh)], fill=(255,255,255,235))
        bd.rectangle([(0,8),(bw,bh-8)], fill=(255,255,255,235))
        bd.rectangle([(4,4),(bw-4,bh-4)], outline=border_color, width=5)

        # Big educational text
        edu_text = edu.get("text", "")
        lines = edu_text.split("\n")
        line_h = (bh - 30) // max(len(lines), 1)
        font_size = min(90, max(28, line_h - 10))
        edu_font = get_font(font_size)
        for li, line in enumerate(lines):
            ty = 20 + line_h * li + line_h // 2
            # Shadow
            bd.text((bw//2 + 2, ty + 2), line, font=edu_font,
                    fill=(0,0,0,120), anchor="mm")
            bd.text((bw//2, ty), line, font=edu_font,
                    fill=border_color, anchor="mm")

        bg = bg.convert("RGBA")
        bg.paste(bubble, (bx, by), bubble)
        bg = bg.convert("RGB")
        draw = ImageDraw.Draw(bg)

        # Label below bubble
        label = edu.get("label", "")
        if label:
            lf = get_font(22)
            draw.text((bx + bw//2 + 2, by + bh + 14), label,
                      font=lf, fill=BLACK, anchor="mt")
            draw.text((bx + bw//2, by + bh + 12), label,
                      font=lf, fill=WHITE, anchor="mt")

    # ── Bottom show bar ───────────────────────────────────────────────────────
    bot = Image.new("RGBA", (w, 42), (0, 0, 0, 160))
    bg = bg.convert("RGBA")
    bg.paste(bot, (0, h - 42), bot)
    bg = bg.convert("RGB")
    draw = ImageDraw.Draw(bg)
    sm_font = get_font(20)
    draw.text((w//2, h - 21),
              f"BIG TRUCK ADVENTURES  |  Episode {ep_num}  |  @BigTruckVideosforKids",
              font=sm_font, fill=AMBER, anchor="mm")

    return bg.convert("RGB")


# ── TTS NARRATION ─────────────────────────────────────────────────────────────

def make_audio(text: str, path: Path) -> bool:
    if not GTTS_OK or not text:
        return False
    try:
        gTTS(text=text, lang="en", slow=False).save(str(path))
        return path.exists()
    except Exception as e:
        print(f"    [audio] TTS failed: {e}")
        return False


# ── SCENE → VIDEO CLIP ────────────────────────────────────────────────────────

def scene_to_clip(scene: dict, idx: int, ep_num: int):
    sid = scene["id"]
    dur = scene["duration"]
    print(f"    Scene {idx+1}/{scene.get('_total','-')}: {sid} ({dur}s)")

    # Compose frame
    frame = compose_scene(
        bg_type    = scene.get("bg", "sky"),
        chars      = scene.get("characters", []),
        trucks     = scene.get("trucks", []),
        title      = scene.get("text_overlay", ""),
        title_color= scene.get("text_color", YELLOW),
        edu        = scene.get("edu_overlay"),
        ep_num     = ep_num,
    )

    # Save frame image
    frame_path = TEMP_DIR / f"ep{ep_num:02d}_s{idx:02d}_{sid}.png"
    frame.save(str(frame_path))

    # Build clip
    clip = ImageClip(str(frame_path)).set_duration(dur)
    clip = clip.fadein(0.25).fadeout(0.25)

    # Narration
    narr = scene.get("narration", "")
    audio_path = TEMP_DIR / f"ep{ep_num:02d}_s{idx:02d}_{sid}.mp3"
    if make_audio(narr, audio_path):
        try:
            audio = AudioFileClip(str(audio_path))
            if audio.duration > dur:
                audio = audio.subclip(0, dur)
            clip = clip.set_audio(audio)
        except Exception as e:
            print(f"      [audio] attach failed: {e}")

    return clip


# ── ALL EPISODE DATA ──────────────────────────────────────────────────────────

SEASON_1 = {
    1: {
        "title": "Jensen's First Day Countdown",
        "skills": "Letters P & J, Numbers 1-10, Colors",
        "scenes": [
            {"id":"intro","duration":5,"bg":"sky",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"BIG TRUCK ADVENTURES","text_color":YELLOW,
             "narration":"Big Truck Adventures! Join Jensen, Bentley, Russell, and baby Emery on their very first adventure!",
             "edu_overlay":None},
            {"id":"kitchen","duration":8,"bg":"kitchen",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":[],
             "text_overlay":"Jensen's First Day Countdown!","text_color":YELLOW,
             "narration":"Jensen is SO excited! Only TEN more days until kindergarten! The whole family is helping him get ready!",
             "edu_overlay":{"text":"10","color":RED,"label":"TEN days to go!"}},
            {"id":"truck_yard","duration":7,"bg":"sky",
             "characters":["jensen"],"trucks":["max","charlie","remy","bella"],
             "text_overlay":"The Truck Yard","text_color":WHITE,
             "narration":"Jensen counts his school supply list with Charlie the Crane Truck. One, two, three, four, five, six, seven, eight, nine, TEN!",
             "edu_overlay":{"text":"1 2 3 4 5\n6 7 8 9 10","color":YELLOW,"label":"Count to TEN!"}},
            {"id":"pencil_shop","duration":7,"bg":"town",
             "characters":["jensen","bentley"],"trucks":["max"],
             "text_overlay":"The Pencil Shop — Letter P!","text_color":WHITE,
             "narration":"Look at the door! The letter P! P makes the puh sound. Puh-Puh-Pencil! P is for Pencil!",
             "edu_overlay":{"text":"P","color":RED,"label":"P is for Pencil!"}},
            {"id":"crayon_factory","duration":7,"bg":"factory",
             "characters":["jensen","russell","emery"],"trucks":[],
             "text_overlay":"The Crayon Factory","text_color":WHITE,
             "narration":"Red, blue, yellow, and green! Those are FOUR colors! Can you say them with me? Red! Blue! Yellow! Green!",
             "edu_overlay":{"text":"RED  BLUE\nYELLOW GREEN","color":ORANGE,"label":"4 Colors!"}},
            {"id":"backpack_bridge","duration":6,"bg":"town",
             "characters":["jensen"],"trucks":["charlie"],
             "text_overlay":"Count to Find Backpack 5!","text_color":WHITE,
             "narration":"Jensen counts the backpacks. One, two, three, four, FIVE! Backpack number five is the one!",
             "edu_overlay":{"text":"5","color":BLUE,"label":"Number FIVE!"}},
            {"id":"alphabet_road","duration":8,"bg":"road",
             "characters":["jensen","bentley","russell","emery"],"trucks":["remy"],
             "text_overlay":"The Alphabet Road — A to Z!","text_color":WHITE,
             "narration":"A B C D E F G! H I J K L M N O P! Q R S T U V! W X Y and Z! Now I know my ABCs!",
             "edu_overlay":{"text":"A B C D E F G\nH I J K L M N O P\nQ R S T U V W X Y Z","color":PURPLE,"label":"The Alphabet!"}},
            {"id":"emery_saves","duration":6,"bg":"town",
             "characters":["emery","jensen","bentley","russell"],"trucks":["bella"],
             "text_overlay":"Emery Saves the Day!","text_color":YELLOW,
             "narration":"Baby Emery found the missing name tag in Bella's loader bucket! J is for Jensen! Emery saves the day!",
             "edu_overlay":{"text":"J","color":RED,"label":"J is for Jensen!"}},
            {"id":"recap","duration":8,"bg":"sky",
             "characters":["jensen"],"trucks":[],
             "text_overlay":"I Learned That for Kindergarten!","text_color":YELLOW,
             "narration":"P is for Pencil! J is for Jensen! Red, blue, yellow, green are four colors! And I can count all the way to TEN! I learned that for kindergarten!",
             "edu_overlay":{"text":"P  J\n1 2 3 4 5\n6 7 8 9 10","color":YELLOW,"label":"I learned that for kindergarten!"}},
            {"id":"outro","duration":5,"bg":"sunset",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"See You Next Time!","text_color":YELLOW,
             "narration":"See you next time on Big Truck Adventures! Don't forget to subscribe!",
             "edu_overlay":None},
        ]
    },
    2: {
        "title": "The Alphabet Truck Parade",
        "skills": "Full Alphabet A-Z, Letter Sounds, Ordering",
        "scenes": [
            {"id":"intro","duration":5,"bg":"sky",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"BIG TRUCK ADVENTURES","text_color":YELLOW,
             "narration":"Big Truck Adventures! Today it's the Annual Alphabet Truck Parade!",
             "edu_overlay":None},
            {"id":"parade_day","duration":7,"bg":"town",
             "characters":["jensen","bentley","russell","emery"],"trucks":["charlie"],
             "text_overlay":"Parade Day! 26 Trucks — A to Z!","text_color":YELLOW,
             "narration":"The 26 Alphabet Trucks are here but they're all mixed up! Jensen must put them in order from A to Z to unlock the big surprise!",
             "edu_overlay":{"text":"A → Z","color":BLUE,"label":"26 Alphabet Trucks!"}},
            {"id":"trucks_a_to_f","duration":8,"bg":"town",
             "characters":["jensen"],"trucks":["charlie","max"],
             "text_overlay":"A B C D E F","text_color":WHITE,
             "narration":"A is for Adventure! B is for Bentley! C is for Charlie! D is for Determined! E is for Emery! F is for Friends!",
             "edu_overlay":{"text":"A B C\nD E F","color":RED,"label":"Letters A through F!"}},
            {"id":"trucks_g_to_m","duration":8,"bg":"town",
             "characters":["jensen","russell"],"trucks":["remy"],
             "text_overlay":"G H I J K L M","text_color":WHITE,
             "narration":"G is for Go! H is for Helpers! I is for Incredible! J is for Jensen! K is for Kind! L is for Learn! M is for Max!",
             "edu_overlay":{"text":"G H I J\nK L M","color":ORANGE,"label":"Letters G through M!"}},
            {"id":"trucks_n_to_r","duration":7,"bg":"road",
             "characters":["jensen","bentley"],"trucks":["max","charlie"],
             "text_overlay":"N O P Q R","text_color":WHITE,
             "narration":"N is for nine! O is for oval! P is for pencil! Q is for quiet! R is for road roller!",
             "edu_overlay":{"text":"N O P\nQ R","color":GREEN,"label":"Letters N through R!"}},
            {"id":"russell_ice_cream","duration":6,"bg":"town",
             "characters":["russell","bentley","jensen"],"trucks":[],
             "text_overlay":"Russell Found the Y Truck!","text_color":YELLOW,
             "narration":"Russell found the Y truck! He was eating ice cream behind the ice cream shop! Y is for Yummy!",
             "edu_overlay":{"text":"Y","color":PINK,"label":"Y is for Yummy!"}},
            {"id":"emery_z_truck","duration":6,"bg":"town",
             "characters":["emery","jensen","bentley","russell"],"trucks":["bella"],
             "text_overlay":"Emery Found the Z Truck!","text_color":YELLOW,
             "narration":"Baby Emery found the Z truck hiding under a bench! A zebra striped street sweeper! Z is the last letter!",
             "edu_overlay":{"text":"Z","color":PURPLE,"label":"Z is LAST!"}},
            {"id":"parade","duration":8,"bg":"town",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"A to Z — Perfect Order!","text_color":YELLOW,
             "narration":"All 26 trucks march in perfect order! A B C D all the way to Z! The whole alphabet in one amazing parade!",
             "edu_overlay":{"text":"A...Z","color":YELLOW,"label":"All 26 Letters!"}},
            {"id":"recap","duration":7,"bg":"sky",
             "characters":["jensen"],"trucks":[],
             "text_overlay":"I Learned That for Kindergarten!","text_color":YELLOW,
             "narration":"The alphabet goes from A all the way to Z — twenty-six letters! Every letter makes a special sound! I learned that for kindergarten!",
             "edu_overlay":{"text":"26\nLetters!","color":BLUE,"label":"I learned that for kindergarten!"}},
            {"id":"outro","duration":5,"bg":"sunset",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"See You Next Thursday!","text_color":YELLOW,
             "narration":"See you next time on Big Truck Adventures! Subscribe so you never miss an adventure!",
             "edu_overlay":None},
        ]
    },
    3: {
        "title": "Count the Construction Cones",
        "skills": "Counting 1-20, Left and Right, Following Directions",
        "scenes": [
            {"id":"intro","duration":5,"bg":"sky",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"BIG TRUCK ADVENTURES","text_color":YELLOW,
             "narration":"Big Truck Adventures! Today Remy the Road Roller hits a cone before the theme song even starts!",
             "edu_overlay":None},
            {"id":"blocked_road","duration":7,"bg":"road",
             "characters":["jensen","bentley","russell"],"trucks":["remy"],
             "text_overlay":"The Road is Blocked!","text_color":RED,
             "narration":"A work zone blocks the whole road! There are orange construction cones everywhere! Jensen must count them all to find the safe path!",
             "edu_overlay":{"text":"20\nCones!","color":ORANGE,"label":"Count them all!"}},
            {"id":"cones_1_to_5","duration":7,"bg":"road",
             "characters":["jensen"],"trucks":["charlie"],
             "text_overlay":"Cones 1 through 5!","text_color":WHITE,
             "narration":"One! Two! Three! Four! FIVE! Jensen steps forward counting each cone. Numbers one through five!",
             "edu_overlay":{"text":"1  2  3\n4  5","color":RED,"label":"Count 1 to 5!"}},
            {"id":"left_right","duration":7,"bg":"road",
             "characters":["jensen","bentley"],"trucks":["max"],
             "text_overlay":"Left or Right?","text_color":WHITE,
             "narration":"The path splits! Cone seven is to the LEFT! Jensen points left! Left! Bentley turns left! Right means the other way!",
             "edu_overlay":{"text":"LEFT\nor\nRIGHT","color":BLUE,"label":"Which way to go?"}},
            {"id":"cones_6_to_10","duration":6,"bg":"road",
             "characters":["jensen","russell"],"trucks":["remy"],
             "text_overlay":"Cones 6 through 10!","text_color":WHITE,
             "narration":"Six! Seven! Eight! Nine! TEN! Russell turns counting into a dance! Left right left right — it is like a dance!",
             "edu_overlay":{"text":"6  7  8\n9  10","color":ORANGE,"label":"Count to 10!"}},
            {"id":"cones_11_to_15","duration":6,"bg":"road",
             "characters":["jensen"],"trucks":["charlie","remy"],
             "text_overlay":"Cones 11 through 15!","text_color":WHITE,
             "narration":"Eleven! Twelve! Cone thirteen rolled away! Remy finds it and rolls it back! Thirteen! Fourteen! FIFTEEN! Halfway there!",
             "edu_overlay":{"text":"11 12 13\n14  15","color":GREEN,"label":"Halfway there!"}},
            {"id":"emery_cone_19","duration":6,"bg":"road",
             "characters":["emery","jensen","bentley","russell"],"trucks":["bella"],
             "text_overlay":"Emery Spots Cone 19!","text_color":YELLOW,
             "narration":"Where is cone nineteen? Emery points at a bush! Cone nineteen is hiding in the bush! Emery saves the day again!",
             "edu_overlay":{"text":"19","color":RED,"label":"Emery found it!"}},
            {"id":"cone_20","duration":6,"bg":"road",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"TWENTY! The Road is Open!","text_color":YELLOW,
             "narration":"Nineteen! And now... TWENTY! The safe path lights up green! The road is open! Jensen counted all the way to twenty!",
             "edu_overlay":{"text":"20","color":GREEN,"label":"Count to TWENTY!"}},
            {"id":"recap","duration":8,"bg":"sky",
             "characters":["jensen"],"trucks":[],
             "text_overlay":"I Learned That for Kindergarten!","text_color":YELLOW,
             "narration":"Counting goes all the way to twenty! One two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen TWENTY! I learned that for kindergarten!",
             "edu_overlay":{"text":"1→20","color":YELLOW,"label":"I learned that for kindergarten!"}},
            {"id":"outro","duration":5,"bg":"sunset",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"See You Next Thursday!","text_color":YELLOW,
             "narration":"Count to twenty with us! See you next time on Big Truck Adventures!",
             "edu_overlay":None},
        ]
    },
    4: {
        "title": "Bentley's Big Game Road Trip",
        "skills": "Shapes, Road Signs, Left and Right Directions",
        "scenes": [
            {"id":"intro","duration":5,"bg":"sky",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"BIG TRUCK ADVENTURES","text_color":YELLOW,
             "narration":"Big Truck Adventures! Today it is game day for Bentley!",
             "edu_overlay":None},
            {"id":"game_day","duration":7,"bg":"kitchen",
             "characters":["bentley","jensen","russell","emery"],"trucks":[],
             "text_overlay":"Game Day! Championship Trophy!","text_color":YELLOW,
             "narration":"It is Bentley's big championship baseball game today! But the road is full of detours! Jensen will use road sign shapes to navigate!",
             "edu_overlay":{"text":"SHAPES!","color":BLUE,"label":"Read the road signs!"}},
            {"id":"triangle_sign","duration":7,"bg":"road",
             "characters":["jensen","bentley"],"trucks":["max"],
             "text_overlay":"Triangle Sign — WARNING!","text_color":ORANGE,
             "narration":"A yellow triangle sign! A triangle has THREE sides! One two three! Triangle signs mean WARNING — look out ahead! A muddy puddle!",
             "edu_overlay":{"text":"3\nsides","color":ORANGE,"label":"TRIANGLE = Warning!"}},
            {"id":"square_sign","duration":6,"bg":"road",
             "characters":["jensen"],"trucks":["max","charlie"],
             "text_overlay":"Square Sign — Turn RIGHT!","text_color":BLUE,
             "narration":"A blue square sign! A square has FOUR equal sides! One two three four! The square sign says turn RIGHT! Max turns right!",
             "edu_overlay":{"text":"4\nsides","color":BLUE,"label":"SQUARE = Information!"}},
            {"id":"circle_sign","duration":6,"bg":"road",
             "characters":["jensen","russell","emery"],"trucks":["remy","bella"],
             "text_overlay":"Circle Sign — STOP!","text_color":RED,
             "narration":"A red circle sign! A circle has NO sides — it is perfectly round! Red circle means STOP! A family of ducks is crossing the road!",
             "edu_overlay":{"text":"0\nsides","color":RED,"label":"CIRCLE = Stop!"}},
            {"id":"rectangle_sign","duration":6,"bg":"road",
             "characters":["jensen","bentley"],"trucks":["max"],
             "text_overlay":"Rectangle Sign — Almost There!","text_color":GREEN,
             "narration":"A green rectangle sign! A rectangle has four sides — two long and two short! Green means GO! Championship Field — turn LEFT!",
             "edu_overlay":{"text":"4 sides\n2 long\n2 short","color":GREEN,"label":"RECTANGLE = Go!"}},
            {"id":"diamond_sign","duration":6,"bg":"road",
             "characters":["jensen"],"trucks":["max","charlie"],
             "text_overlay":"Diamond Sign — Exit 2!","text_color":YELLOW,
             "narration":"A diamond sign in the roundabout! A diamond is like a square tilted on its corner! Count the exits — one, TWO! Take exit two!",
             "edu_overlay":{"text":"Diamond\n= Tilted\nSquare","color":YELLOW,"label":"Exit TWO!"}},
            {"id":"the_game","duration":7,"bg":"sky",
             "characters":["bentley","jensen","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"BENTLEY WINS THE CHAMPIONSHIP!","text_color":YELLOW,
             "narration":"Bentley hits the ball! CRACK! The whole team cheers! Bentley wins the championship trophy! They made it thanks to Jensen and the shape road signs!",
             "edu_overlay":{"text":"WIN!","color":YELLOW,"label":"Bentley's the champion!"}},
            {"id":"recap","duration":8,"bg":"sky",
             "characters":["jensen"],"trucks":[],
             "text_overlay":"I Learned That for Kindergarten!","text_color":YELLOW,
             "narration":"Triangle has three sides and means warning! Square has four equal sides! Circle has no sides and means stop! Rectangle has four sides — two long two short! Diamond is a tilted square! I learned that for kindergarten!",
             "edu_overlay":{"text":"Shapes\nHelp Us\nRead Signs!","color":BLUE,"label":"I learned that for kindergarten!"}},
            {"id":"outro","duration":5,"bg":"sunset",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"See You Next Thursday!","text_color":YELLOW,
             "narration":"Name the shapes you see today! See you next time on Big Truck Adventures!",
             "edu_overlay":None},
        ]
    },
    5: {
        "title": "Russell's Mystery Truck",
        "skills": "Colors, Shapes, Process of Elimination",
        "scenes": [
            {"id":"intro","duration":5,"bg":"sky",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"BIG TRUCK ADVENTURES","text_color":YELLOW,
             "narration":"Big Truck Adventures! Today Russell gets to solve a mystery truck!",
             "edu_overlay":None},
            {"id":"mystery_arrives","duration":7,"bg":"sky",
             "characters":["russell","bentley","jensen","emery"],
             "trucks":["remy","bella"],
             "text_overlay":"A Mystery Truck Arrives!","text_color":YELLOW,
             "narration":"A new truck arrives covered in a tarp! Foreman Bear says Russell must figure out what kind of truck it is using clues! Russell is ready!",
             "edu_overlay":{"text":"?","color":ORANGE,"label":"Mystery Truck!"}},
            {"id":"clue_color","duration":7,"bg":"sky",
             "characters":["russell","jensen"],"trucks":[],
             "text_overlay":"Clue 1 — The Color!","text_color":YELLOW,
             "narration":"Clue number one! The mystery truck is YELLOW! Yellow like the sun! Yellow like Charlie! So many yellow trucks! Russell needs more clues!",
             "edu_overlay":{"text":"YELLOW","color":(220,200,0),"label":"Clue 1: Color!"}},
            {"id":"clue_shape","duration":7,"bg":"sky",
             "characters":["russell","jensen","bentley"],"trucks":[],
             "text_overlay":"Clue 2 — The Shape!","text_color":BLUE,
             "narration":"Clue number two! The truck has a long RECTANGLE arm that reaches up HIGH! A rectangle — four sides, two long and two short! Russell is getting closer!",
             "edu_overlay":{"text":"Rectangle\nArm","color":BLUE,"label":"Clue 2: Shape!"}},
            {"id":"clue_function","duration":7,"bg":"sky",
             "characters":["russell"],"trucks":[],
             "text_overlay":"Clue 3 — What It Does!","text_color":GREEN,
             "narration":"Clue number three! The truck DIGS into the ground! Its arm goes down AND up! And it has a big C-shaped scoop at the end!",
             "edu_overlay":{"text":"C shape\nDigs!","color":GREEN,"label":"Clue 3: What it does!"}},
            {"id":"russell_knows","duration":7,"bg":"sky",
             "characters":["russell","jensen","bentley","emery"],
             "trucks":["remy","bella"],
             "text_overlay":"Russell Knows! It's an EXCAVATOR!","text_color":YELLOW,
             "narration":"Yellow! Rectangle arm! C-shaped bucket! Digs into the ground! Russell knows! It is an EXCAVATOR! A yellow excavator! Russell was right!",
             "edu_overlay":{"text":"EXCAVATOR!","color":YELLOW,"label":"Russell solved it!"}},
            {"id":"meet_dig","duration":6,"bg":"sky",
             "characters":["russell","jensen","bentley","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"Meet DIG the New Crew Member!","text_color":YELLOW,
             "narration":"The tarp comes off! It IS a yellow excavator! His name is Dig! Welcome to the Big Truck Adventures crew Dig!",
             "edu_overlay":{"text":"DIG","color":ORANGE,"label":"New crew member!"}},
            {"id":"recap","duration":7,"bg":"sky",
             "characters":["jensen","russell"],"trucks":[],
             "text_overlay":"I Learned That for Kindergarten!","text_color":YELLOW,
             "narration":"When you do not know something use CLUES! Color — yellow! Shape — rectangle arm! What it does — digs with a C-shaped scoop! Put the clues together and you can figure out ANYTHING! I learned that for kindergarten!",
             "edu_overlay":{"text":"Use\nCLUES!","color":ORANGE,"label":"I learned that for kindergarten!"}},
            {"id":"outro","duration":5,"bg":"sunset",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"See You Next Thursday!","text_color":YELLOW,
             "narration":"What color was the mystery truck? YELLOW! See you next time on Big Truck Adventures!",
             "edu_overlay":None},
        ]
    },
    6: {
        "title": "The Days of the Week Delivery",
        "skills": "Days of the Week Monday-Sunday, Sequencing",
        "scenes": [
            {"id":"intro","duration":5,"bg":"sky",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"BIG TRUCK ADVENTURES","text_color":YELLOW,
             "narration":"Big Truck Adventures! Today the weekly delivery boxes are all mixed up!",
             "edu_overlay":None},
            {"id":"mixed_boxes","duration":7,"bg":"town",
             "characters":["jensen","bentley","russell"],"trucks":["charlie"],
             "text_overlay":"7 Delivery Boxes — All Mixed Up!","text_color":RED,
             "narration":"Seven delivery boxes — one for each day of the week — are all in the wrong order! Jensen must sort them Monday through Sunday!",
             "edu_overlay":{"text":"7 Days\nin a\nWeek!","color":BLUE,"label":"Days of the week!"}},
            {"id":"mon_tue_wed","duration":8,"bg":"town",
             "characters":["jensen","russell"],"trucks":["max","charlie"],
             "text_overlay":"Monday! Tuesday! Wednesday!","text_color":YELLOW,
             "narration":"Monday is day ONE! Tuesday is day TWO! Wednesday is day THREE! W-W-Wednesday starts with W like WHOOSH!",
             "edu_overlay":{"text":"Mon  Tue\nWed","color":RED,"label":"Days 1, 2, and 3!"}},
            {"id":"thu_fri","duration":7,"bg":"town",
             "characters":["jensen","russell","bentley"],"trucks":["remy"],
             "text_overlay":"Thursday! FRIDAY — Party Day!","text_color":YELLOW,
             "narration":"Thursday is day FOUR! Friday is day FIVE! The Friday box has party horns inside! Russell blows a party horn! Friday is Russell's favorite day!",
             "edu_overlay":{"text":"Thu  Fri","color":ORANGE,"label":"Days 4 and 5!"}},
            {"id":"sat_sun","duration":6,"bg":"sky",
             "characters":["jensen","bentley"],"trucks":["max"],
             "text_overlay":"Saturday! Sunday! — The Weekend!","text_color":BLUE,
             "narration":"Saturday is day SIX — game day for Bentley! Sunday is day SEVEN — the last day of the week! Then it starts over with Monday again!",
             "edu_overlay":{"text":"Sat  Sun\nDay 6  7","color":BLUE,"label":"The Weekend!"}},
            {"id":"emery_horn","duration":5,"bg":"town",
             "characters":["emery","jensen","bentley","russell"],"trucks":["bella"],
             "text_overlay":"Emery Has a Party Horn!","text_color":PINK,
             "narration":"Emery somehow has a party horn! Nobody knows where she got it! She honks it and everyone jumps! Then everyone laughs!",
             "edu_overlay":{"text":"Ba-ba\nBRRM!","color":PINK,"label":"Emery surprises everyone!"}},
            {"id":"delivery_parade","duration":7,"bg":"town",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"Deliveries Monday through Sunday!","text_color":YELLOW,
             "narration":"All seven boxes delivered in order! Monday through Sunday! Every day of the week has something special!",
             "edu_overlay":{"text":"Mon→Sun\nAll 7!","color":GREEN,"label":"All 7 days delivered!"}},
            {"id":"recap","duration":8,"bg":"sky",
             "characters":["jensen"],"trucks":[],
             "text_overlay":"I Learned That for Kindergarten!","text_color":YELLOW,
             "narration":"There are SEVEN days in a week and they always go in the same order! Monday Tuesday Wednesday Thursday Friday Saturday Sunday! Then Monday again! I learned that for kindergarten!",
             "edu_overlay":{"text":"7 Days\nMon Tue Wed\nThu Fri Sat Sun","color":YELLOW,"label":"I learned that for kindergarten!"}},
            {"id":"outro","duration":5,"bg":"sunset",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"See You Next Thursday!","text_color":YELLOW,
             "narration":"Say all seven days with us! Monday Tuesday Wednesday Thursday Friday Saturday Sunday! See you next time on Big Truck Adventures!",
             "edu_overlay":None},
        ]
    },
    7: {
        "title": "Emery's Big Surprise",
        "skills": "Rainbow Colors, Feelings and Emotions, Family Love",
        "scenes": [
            {"id":"intro","duration":5,"bg":"sky",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"BIG TRUCK ADVENTURES","text_color":YELLOW,
             "narration":"Big Truck Adventures! Today the brothers plan the best surprise ever for Mom and baby Emery!",
             "edu_overlay":None},
            {"id":"the_plan","duration":7,"bg":"kitchen",
             "characters":["bentley","jensen","russell","emery"],"trucks":[],
             "text_overlay":"The Secret Surprise Plan!","text_color":YELLOW,
             "narration":"The brothers whisper their plan! Decorations, flowers, and a banner that says we love Mom! But Emery keeps rolling her walker right into everything!",
             "edu_overlay":{"text":"Surprise!","color":PINK,"label":"For Mom and Emery!"}},
            {"id":"rainbow_flowers","duration":7,"bg":"sky",
             "characters":["jensen","emery"],"trucks":["bella"],
             "text_overlay":"Rainbow Flowers!","text_color":YELLOW,
             "narration":"Jensen sorts flowers by color — red, yellow, pink, and purple! Emery grabs all four colors at once and drops them in one pot! A rainbow bouquet!",
             "edu_overlay":{"text":"RED\nYELLOW\nPINK  PURPLE","color":PINK,"label":"Rainbow flowers!"}},
            {"id":"rainbow_path","duration":7,"bg":"sky",
             "characters":["russell","jensen","emery"],"trucks":[],
             "text_overlay":"Rainbow Stepping Stones!","text_color":YELLOW,
             "narration":"Emery rearranges Russell's stepping stones into rainbow order! Red orange yellow green blue purple! A perfect rainbow path!",
             "edu_overlay":{"text":"Red Orange\nYellow Green\nBlue Purple","color":ORANGE,"label":"Rainbow order!"}},
            {"id":"mom_arrives","duration":7,"bg":"sky",
             "characters":["bentley","jensen","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"MOM SEES THE SURPRISE!","text_color":YELLOW,
             "narration":"Mom opens the back door and sees everything! The rainbow flowers! The beautiful banner! The rainbow path! She hugs all three boys and picks up baby Emery!",
             "edu_overlay":{"text":"We Love\nYou Mom!","color":PINK,"label":"The best surprise ever!"}},
            {"id":"celebration","duration":6,"bg":"sunset",
             "characters":["bentley","jensen","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"Family Celebration!","text_color":YELLOW,
             "narration":"The whole family celebrates together! The trucks circle around like part of the family! Emery puts a yellow flower in Mom's hair!",
             "edu_overlay":{"text":"FAMILY","color":PINK,"label":"Together is best!"}},
            {"id":"recap","duration":8,"bg":"sunset",
             "characters":["jensen"],"trucks":[],
             "text_overlay":"I Learned That for Kindergarten!","text_color":YELLOW,
             "narration":"When you love someone you SHOW them! Use colors to make things beautiful — red orange yellow green blue purple! Use your words — we love you! And sometimes your baby sister makes everything even better just by being there! I learned that for life!",
             "edu_overlay":{"text":"Red Orange\nYellow Green\nBlue Purple","color":ORANGE,"label":"Rainbow colors!"}},
            {"id":"outro","duration":5,"bg":"sunset",
             "characters":["jensen","bentley","russell","emery"],
             "trucks":["max","charlie","remy","bella"],
             "text_overlay":"END OF SEASON 1 — Thank You!","text_color":YELLOW,
             "narration":"That is the end of Season 1 of Big Truck Adventures! Thank you so much for watching! Subscribe for Season 2 coming soon!",
             "edu_overlay":None},
        ]
    },
}


# ── EPISODE GENERATOR ─────────────────────────────────────────────────────────

def generate_episode(ep_num: int, preview_only: bool = False):
    if ep_num not in SEASON_1:
        print(f"[ERROR] Episode {ep_num} not found.")
        return

    ep = SEASON_1[ep_num]
    total = len(ep["scenes"])
    print(f"\n{'='*65}")
    print(f"  Episode {ep_num}: {ep['title']}")
    print(f"  Skills: {ep['skills']}")
    print(f"  Scenes: {total}")
    print(f"{'='*65}")

    if preview_only:
        # Just render frames
        prev_dir = EXPORTS_DIR / f"E{ep_num:02d}_preview"
        prev_dir.mkdir(exist_ok=True)
        for i, scene in enumerate(ep["scenes"]):
            scene["_total"] = total
            frame = compose_scene(
                bg_type     = scene.get("bg","sky"),
                chars       = scene.get("characters",[]),
                trucks      = scene.get("trucks",[]),
                title       = scene.get("text_overlay",""),
                title_color = scene.get("text_color", YELLOW),
                edu         = scene.get("edu_overlay"),
                ep_num      = ep_num,
            )
            out = prev_dir / f"s{i+1:02d}_{scene['id']}.png"
            frame.save(str(out))
            print(f"  Scene {i+1}/{total}: {scene['id']} -> {out.name}")
        print(f"\nPreview saved to: {prev_dir}")
        return

    # Build video
    clips = []
    for i, scene in enumerate(ep["scenes"]):
        scene["_total"] = total
        clip = scene_to_clip(scene, i, ep_num)
        clips.append(clip)

    print(f"\nAssembling {len(clips)} scenes...")
    final = concatenate_videoclips(clips, method="compose")

    out_path = EXPORTS_DIR / f"E{ep_num:02d}-{ep['title'].replace(' ','-').replace('/','-')}.mp4"
    print(f"Exporting to: {out_path}")
    final.write_videofile(
        str(out_path), fps=24, codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(TEMP_DIR / f"ep{ep_num}_temp.m4a"),
        remove_temp=True, logger="bar",
    )
    print(f"\n  Video saved: {out_path}")

    # Cleanup temp files for this episode
    for f in TEMP_DIR.glob(f"ep{ep_num:02d}_*"):
        try: f.unlink()
        except: pass

    return out_path


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Big Truck Adventures — Automated Episode Generator"
    )
    parser.add_argument("--ep", type=int, default=0,
                        help="Episode number to generate (1-7). 0 = all episodes.")
    parser.add_argument("--preview", action="store_true",
                        help="Generate preview images only (fast, no moviepy)")
    args = parser.parse_args()

    episodes = [args.ep] if args.ep > 0 else list(SEASON_1.keys())

    print(f"\nBIG TRUCK ADVENTURES — Season 1 Generator")
    print(f"Episodes to generate: {episodes}")
    print(f"Mode: {'PREVIEW' if args.preview else 'FULL VIDEO'}")
    print(f"Output: {EXPORTS_DIR}")

    # Check character images
    print(f"\nCharacter image check:")
    for name in ["jensen","bentley","russell","emery","max","charlie","remy","bella"]:
        found = any(
            (d / f"{name}{ext}").exists()
            for d in [CHAR_DIR, TRUCK_DIR, DOWNLOADS]
            for ext in [".png",".jpg",".jpeg",".PNG",".JPG"]
        )
        status = "FOUND" if found else "NOT FOUND (placeholder will be used)"
        print(f"  {name:12s}: {status}")

    print()

    for ep_num in episodes:
        generate_episode(ep_num, preview_only=args.preview)

    print(f"\n{'='*65}")
    print(f"  ALL DONE!")
    print(f"  Videos saved to: {EXPORTS_DIR}")
    print(f"  Upload each MP4 to YouTube Studio @BigTruckVideosforKids")
    print(f"  Schedule for Thursday release!")
    print(f"{'='*65}\n")
