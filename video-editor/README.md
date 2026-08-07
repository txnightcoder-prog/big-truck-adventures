# 🚛 Big Truck Adventures — Video Editor

**100% free. No watermarks. No subscription. Runs locally on your Windows PC. Forever.**

Built specifically for creating Big Truck Adventures episodes with Jensen, Bentley, Russell, and Emery.

---

## 🚀 Quick Start

1. Double-click **`INSTALL.bat`**
2. Wait ~2 minutes while dependencies are installed automatically
3. The editor opens immediately after install
4. **To launch later**, just double-click `INSTALL.bat` again (it will skip already-installed packages)

> **Requires Python 3.10+** — download free at [python.org](https://www.python.org/downloads/)  
> During install, **check "Add Python to PATH"**

---

## 🖥️ Editor Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Toolbar: New | Open | Save | Free Media | Split | Delete | Export│
├──────────────┬────────────────────────────────┬─────────────────┤
│              │                                │                 │
│  🎬 ASSET    │      👁️ PREVIEW WINDOW         │  ⚙️ PROPERTIES  │
│   LIBRARY    │     (live composite view)      │   (selected     │
│              │                                │    clip editor) │
│  Characters  │   ▶ Play  ■ Stop  00:00:00:00  │                 │
│  Trucks      │                                │  Label, timing, │
│  My Media    │                                │  text, color,   │
│  Overlays    │                                │  animation…     │
│              │                                │                 │
├──────────────┴────────────────────────────────┴─────────────────┤
│  ── TIMELINE ──────────────────────────────────── Zoom: [─────]  │
│  🎬 Video 1  │██████████████████████████████                    │
│  🎬 Video 2  │        ████████                                   │
│  🖼 Characters│ ███████       ████████████                       │
│  ✨ Overlays  │    ████    ███████  ████                          │
│  📝 Text      │  ████   ██████        ████                       │
│  🎵 Music     │██████████████████████████████████                │
│  🎵 SFX       │          █████                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎬 How to Make an Episode

### 1. Start from a Template
- Click **`File → New Project…`** or **`Ctrl+N`**
- Choose from built-in episode templates:
  - **E01 – Jensen's First Day Countdown** (Numbers 1-10, Letters P & J, Colors)
  - **E02 – The Alphabet Truck Parade** (Full A-Z alphabet, letter sounds)
  - **E03 – Count the Construction Cones** (Counting 1-20)
  - **Blank Episode** — start from scratch

### 2. Add Characters to the Timeline
- In the **Asset Library** (left panel), click **Characters** tab
- **Drag** Jensen, Bentley, Russell, or Emery onto the timeline
- Or **double-click** any character to add them at the end of the timeline

### 3. Add Trucks
- Click the **Trucks** tab in the Asset Library
- Drag Max, Charlie, Remi, or Bella onto the timeline

### 4. Add Background Videos/Photos (FREE)
- Click **`🔍 Free Media`** in the toolbar
- Enter a search query like `"construction site"`, `"sunny park"`, `"city street"`
- Select **Pexels Videos**, **Pexels Photos**, **Pixabay Videos**, or **Pixabay Images**
- Enter your free API key (see below)
- **Double-click** any result to download and add to your timeline

### 5. Add Educational Overlays
Click **`Insert`** menu or use the **Overlays** tab:

| Overlay | Description | Example |
|---------|-------------|---------|
| 🔤 Letter Card | Colorful animated letter card | "A" for Apple |
| 🔢 Number Card | Bold number card in blue/gold | "5" the number five |
| 🎨 Color Card | Full-color card showing a named color | RED |
| 🏷️ Title Card | Cinematic title bar overlay | "Big Truck Adventures" |
| 📣 Caption Bar | Subtitle bar at the bottom | "Jensen says…" |

### 6. Add Text Animations
Click **`Insert → Text Clip…`** and pick an animation in the Properties panel:

| Animation | Effect |
|-----------|--------|
| **bounce** | Text bounces up and down |
| **pop** | Text scales in with a pop |
| **slide_right** | Slides in from the left |
| **slide_left** | Slides in from the right |
| **fade_in** | Fades in over the first second |
| **rainbow** | Cycles through rainbow colors |

### 7. Add Free Music
- Click **`🔍 Free Media`** → choose **Free Music Archive** (no API key needed!)
- Search `"kids music"`, `"upbeat"`, `"educational"`, etc.
- Double-click to download and add to the Music track

### 8. Generate Narrator Voice-Over
- Click **`Insert → Generate Narration (TTS)…`**
- Type what Jensen/Bentley should say
- Click OK — an MP3 is generated and added to the SFX track
- Requires internet connection (uses Google Text-to-Speech)

### 9. Preview Your Episode
- Click **`▶ Play`** in the preview window to watch your episode
- Click the timeline ruler to seek to any time
- Preview updates live as you edit clips

### 10. Export to MP4
- Click **`🎬 Export MP4`** in the toolbar or **`Ctrl+E`**
- Choose resolution (1080p HD recommended for YouTube)
- Click **Export** — your episode renders to `exports/` folder
- Export requires MoviePy (installed by INSTALL.bat)

---

## 🔑 Getting Free API Keys

### Pexels (videos + photos)
1. Go to [pexels.com/api](https://www.pexels.com/api/)
2. Create a free account
3. Copy your API key
4. Paste it in the **Free Media** search dialog

### Pixabay (videos + images)  
1. Go to [pixabay.com/api/docs](https://pixabay.com/api/docs/)
2. Create a free account
3. Copy your API key
4. Paste it in the **Free Media** search dialog

### Free Music Archive
- **No key needed!** Just search and download.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New project |
| `Ctrl+O` | Open project |
| `Ctrl+S` | Save project |
| `Ctrl+E` | Export to MP4 |
| `Delete` | Delete selected clip |
| `Ctrl+K` | Split clip at playhead |
| `Ctrl+=` | Zoom in timeline |
| `Ctrl+-` | Zoom out timeline |
| `Ctrl+0` | Fit timeline to window |

---

## 📁 File Locations

| Folder | Contents |
|--------|----------|
| `projects/` | Your saved projects (`.btap` files) |
| `exports/` | Exported MP4 videos |
| `.cache/` | Downloaded media & generated narration |
| `editor.db` | Asset library database |

---

## 🐛 Troubleshooting

**The editor won't open:**
- Run `INSTALL.bat` again as Administrator
- Make sure Python 3.10+ is installed with "Add to PATH" checked

**Export fails / "MoviePy not installed":**
- Run `INSTALL.bat` again
- Or run: `pip install moviepy imageio[ffmpeg]`

**Free Media search returns nothing:**
- For Pexels/Pixabay: make sure you entered your API key in the search dialog
- For FMA: the API may be temporarily unavailable; visit [freemusicarchive.org](https://freemusicarchive.org) directly

**Character images don't appear:**
- Make sure your images are in: `C:\Users\JohnKirshy\Downloads\BigTruckAdventures\Characters\`
- Files must be named: `Jensen.png`, `Bentley.png`, `Russell.png`, `Emery.png`

**Preview is slow:**
- The preview renders in real-time using Python — this is normal for complex scenes
- The exported MP4 will be full quality and smooth

---

## 🎭 Characters

| Character | Role | Truck |
|-----------|------|-------|
| **Jensen** | Main character, kindergarten-age | — |
| **Bentley** | Older brother, team leader | — |
| **Russell** | Youngest brother, comic relief | — |
| **Emery** | Baby sister, always saves the day | — |
| **Max** | Big dump truck, carries supplies | Dump Truck |
| **Charlie** | Crane truck, wise helper | Crane |
| **Remi** | Road roller, alphabet roads | Road Roller |
| **Bella** | Tiny baby loader | Baby Loader |

---

## 📺 Episode Templates Included

| Episode | Educational Focus | Runtime |
|---------|-------------------|---------|
| E01 – Jensen's First Day Countdown | Numbers 1-10, Letters P & J, Colors | ~7 min |
| E02 – The Alphabet Truck Parade | Full A-Z alphabet, letter sounds | ~7 min |
| E03 – Count the Construction Cones | Counting 1-20, construction | ~7 min |

---

## 💻 Tech Stack

- **PyQt6** — desktop GUI framework
- **MoviePy** — video compositing and MP4 export
- **Pillow** — image manipulation
- **gTTS** — Google Text-to-Speech narration
- **SQLite** — local asset database
- **Pexels API** — royalty-free videos and photos
- **Pixabay API** — royalty-free images and videos
- **Free Music Archive** — royalty-free music (no key needed)

---

*Big Truck Adventures Video Editor — built for John Kirshy*  
*100% free, 100% local, 100% yours.*
