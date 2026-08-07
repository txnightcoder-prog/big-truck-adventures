"""
Big Truck Adventures – Video Editor
====================================
Full-featured desktop video editor built with PyQt6 + MoviePy.
100 % free, no watermarks, runs locally on Windows.

Author : built for John Kirshy / Big Truck Adventures
"""

# ──────────────────────────────────────────────────────────────────────────────
#  IMPORTS
# ──────────────────────────────────────────────────────────────────────────────
import sys, os, json, sqlite3, threading, time, math, random, shutil, tempfile
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
import urllib.request, urllib.parse, urllib.error
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

# ── PyQt6 ─────────────────────────────────────────────────────────────────────
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QSlider, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QScrollArea, QFrame,
    QTabWidget, QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QProgressBar, QColorDialog, QDialog, QDialogButtonBox, QGroupBox,
    QToolBar, QStatusBar, QSizePolicy, QMenu, QInputDialog, QTreeWidget,
    QTreeWidgetItem, QAbstractItemView, QRubberBand, QScrollBar,
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QPixmap, QImage,
    QIcon, QAction, QDrag, QPalette, QLinearGradient, QPainterPath,
    QKeySequence, QCursor, QTransform, QPolygon,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QRect, QPoint, QSize, QRectF,
    QPointF, QMimeData, QByteArray, QPropertyAnimation, QEasingCurve,
    QRunnable, QThreadPool, QObject, QUrl, pyqtSlot,
)

# ── Optional heavy deps (graceful degradation if missing) ─────────────────────
try:
    from moviepy.editor import (
        VideoFileClip, ImageClip, AudioFileClip, ColorClip, TextClip,
        CompositeVideoClip, concatenate_videoclips, CompositeAudioClip,
    )
    MOVIEPY_OK = True
except Exception:
    MOVIEPY_OK = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PILLOW_OK = True
except Exception:
    PILLOW_OK = False

try:
    from gtts import gTTS
    GTTS_OK = True
except Exception:
    GTTS_OK = False

# ──────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
APP_NAME        = "Big Truck Adventures – Video Editor"
APP_VERSION     = "1.0.0"
ASSETS_ROOT     = Path(r"C:\Users\JohnKirshy\Downloads\BigTruckAdventures")
EDITOR_ROOT     = Path(r"C:\Users\JohnKirshy\Desktop\big-truck-adventures\video-editor")
PROJECTS_DIR    = EDITOR_ROOT / "projects"
EXPORTS_DIR     = EDITOR_ROOT / "exports"
CACHE_DIR       = EDITOR_ROOT / ".cache"
DB_PATH         = EDITOR_ROOT / "editor.db"

for _d in (PROJECTS_DIR, EXPORTS_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

FPS             = 24
CANVAS_W        = 1920
CANVAS_H        = 1080
TIMELINE_PX_PER_SEC = 80     # pixels per second in timeline at zoom=1
THUMB_W, THUMB_H    = 120, 68

# Colour palette (kids cartoon – bright but not harsh)
C_BG        = "#1e1e2e"
C_SURFACE   = "#2a2a3e"
C_PANEL     = "#252535"
C_ACCENT    = "#f9a825"   # amber/gold
C_ACCENT2   = "#42a5f5"  # sky blue
C_RED       = "#ef5350"
C_GREEN     = "#66bb6a"
C_TEXT      = "#e8eaf6"
C_MUTED     = "#9e9eb8"
C_TIMELINE  = "#181828"
C_CLIP_VID  = "#1565c0"
C_CLIP_AUD  = "#2e7d32"
C_CLIP_IMG  = "#6a1b9a"
C_CLIP_TXT  = "#e65100"
C_CLIP_OVLY = "#ad1457"

TRACK_HEIGHT    = 56
TRACK_HEADER_W  = 120
MIN_CLIP_W      = 8

CHAR_NAMES  = ["Jensen", "Bentley", "Russell", "Emery"]
TRUCK_NAMES = ["Max", "Charlie", "Remi", "Bella"]

# ──────────────────────────────────────────────────────────────────────────────
#  DATA MODELS
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Clip:
    """A single clip on the timeline."""
    id:          str   = field(default_factory=lambda: f"clip_{random.randint(100000,999999)}")
    track:       int   = 0         # track index (0 = top)
    start_time:  float = 0.0       # seconds from project start
    duration:    float = 5.0       # seconds
    clip_type:   str   = "video"   # video | audio | image | text | overlay
    source_path: str   = ""
    label:       str   = ""
    # trim
    trim_in:     float = 0.0       # trim from start of source
    trim_out:    float = 0.0       # trim from end of source (0 = no trim)
    # display
    color:       str   = C_CLIP_VID
    volume:      float = 1.0
    # text-specific
    text:        str   = ""
    font_size:   int   = 72
    font_color:  str   = "#ffffff"
    bg_color:    str   = "#00000000"
    animation:   str   = "none"    # none | bounce | pop | slide_left | slide_right | rainbow | fade_in
    pos_x:       int   = 50        # percent from left
    pos_y:       int   = 80        # percent from top
    # overlay-specific
    overlay_type: str  = ""        # letter_card | number_card | color_card | title_card
    overlay_data: str  = ""        # the letter/number/color value

    @property
    def end_time(self) -> float:
        return self.start_time + self.duration

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Clip":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Track:
    id:     str  = field(default_factory=lambda: f"trk_{random.randint(100000,999999)}")
    name:   str  = "Track"
    kind:   str  = "video"   # video | audio | text | overlay
    muted:  bool = False
    locked: bool = False
    height: int  = TRACK_HEIGHT

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Track":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Project:
    name:       str        = "Untitled Episode"
    path:       str        = ""
    fps:        int        = FPS
    width:      int        = CANVAS_W
    height:     int        = CANVAS_H
    duration:   float      = 60.0
    tracks:     List[Track] = field(default_factory=list)
    clips:      List[Clip]  = field(default_factory=list)
    bg_color:   str         = "#0a0a1a"
    music_path: str         = ""
    music_vol:  float       = 0.6

    def save(self, path: str):
        d = {
            "name": self.name, "fps": self.fps,
            "width": self.width, "height": self.height,
            "duration": self.duration,
            "tracks": [t.to_dict() for t in self.tracks],
            "clips":  [c.to_dict() for c in self.clips],
            "bg_color": self.bg_color,
            "music_path": self.music_path,
            "music_vol": self.music_vol,
        }
        with open(path, "w") as f:
            json.dump(d, f, indent=2)
        self.path = path

    @classmethod
    def load(cls, path: str) -> "Project":
        with open(path) as f:
            d = json.load(f)
        p = cls(
            name=d.get("name","Untitled"),
            path=path,
            fps=d.get("fps", FPS),
            width=d.get("width", CANVAS_W),
            height=d.get("height", CANVAS_H),
            duration=d.get("duration", 60.0),
            bg_color=d.get("bg_color","#0a0a1a"),
            music_path=d.get("music_path",""),
            music_vol=d.get("music_vol", 0.6),
        )
        p.tracks = [Track.from_dict(t) for t in d.get("tracks", [])]
        p.clips  = [Clip.from_dict(c) for c in d.get("clips", [])]
        return p

    def default_tracks(self):
        self.tracks = [
            Track(name="Video 1",   kind="video"),
            Track(name="Video 2",   kind="video"),
            Track(name="Characters",kind="image"),
            Track(name="Overlays",  kind="overlay"),
            Track(name="Text",      kind="text"),
            Track(name="Music",     kind="audio"),
            Track(name="SFX",       kind="audio"),
        ]


# ──────────────────────────────────────────────────────────────────────────────
#  DATABASE  (asset library, recent projects)
# ──────────────────────────────────────────────────────────────────────────────
class AssetDB:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self._init()

    def _init(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            kind        TEXT NOT NULL,
            name        TEXT NOT NULL,
            path        TEXT UNIQUE,
            source_url  TEXT,
            preview_url TEXT,
            tags        TEXT,
            added_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS projects (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT,
            path     TEXT UNIQUE,
            opened   TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets(kind);
        """)
        self.conn.commit()

    def add_asset(self, kind: str, name: str, path: str = "", url: str = "",
                  preview: str = "", tags: str = "") -> int:
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO assets(kind,name,path,source_url,preview_url,tags) "
            "VALUES(?,?,?,?,?,?)",
            (kind, name, path, url, preview, tags)
        )
        self.conn.commit()
        return c.lastrowid

    def get_assets(self, kind: str = "") -> List[Dict]:
        c = self.conn.cursor()
        if kind:
            c.execute("SELECT * FROM assets WHERE kind=? ORDER BY name", (kind,))
        else:
            c.execute("SELECT * FROM assets ORDER BY kind,name")
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, row)) for row in c.fetchall()]

    def delete_asset(self, asset_id: int):
        self.conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))
        self.conn.commit()

    def touch_project(self, name: str, path: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO projects(name,path,opened) VALUES(?,?,datetime('now'))",
            (name, path)
        )
        self.conn.commit()

    def recent_projects(self) -> List[Dict]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM projects ORDER BY opened DESC LIMIT 10")
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, row)) for row in c.fetchall()]

    def close(self):
        self.conn.close()


DB: Optional[AssetDB] = None

def get_db() -> AssetDB:
    global DB
    if DB is None:
        DB = AssetDB(DB_PATH)
    return DB


# ──────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def secs_to_tc(secs: float) -> str:
    """Convert float seconds → HH:MM:SS:FF timecode."""
    s = int(secs)
    h, rem = divmod(s, 3600)
    m, s2  = divmod(rem, 60)
    ff     = int((secs - int(secs)) * FPS)
    return f"{h:02d}:{m:02d}:{s2:02d}:{ff:02d}"


def tc_to_secs(tc: str) -> float:
    parts = tc.split(":")
    try:
        h, m, s, f = [int(p) for p in parts]
        return h * 3600 + m * 60 + s + f / FPS
    except Exception:
        return 0.0


def color_blend(c1: str, c2: str, t: float) -> str:
    """Lerp between two hex colours."""
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    r = int(r1 + (r2-r1)*t)
    g = int(g1 + (g2-g1)*t)
    b = int(b1 + (b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"


def make_thumbnail(path: str, w: int = THUMB_W, h: int = THUMB_H) -> QPixmap:
    """Return a QPixmap thumbnail for a file path (image or colour placeholder)."""
    if not path:
        pm = QPixmap(w, h)
        pm.fill(QColor(C_MUTED))
        return pm
    ext = Path(path).suffix.lower()
    if ext in (".png",".jpg",".jpeg",".bmp",".gif",".webp"):
        pm = QPixmap(path)
        if pm.isNull():
            pm = QPixmap(w, h); pm.fill(QColor(C_MUTED))
        return pm.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    else:
        pm = QPixmap(w, h)
        pm.fill(QColor("#1a1a2e"))
        p = QPainter(pm)
        p.setPen(QColor(C_TEXT))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter,
                   Path(path).suffix.upper()[1:] or "FILE")
        p.end()
        return pm


def run_in_thread(fn, *args, **kwargs):
    """Fire-and-forget background thread."""
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


# ──────────────────────────────────────────────────────────────────────────────
#  STYLE  (dark kids-studio theme)
# ──────────────────────────────────────────────────────────────────────────────
QSS = f"""
QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}
QSplitter::handle {{ background: #3a3a5a; width: 3px; height: 3px; }}
QScrollBar:vertical {{
    background: {C_SURFACE}; width: 10px; border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #4a4a6a; border-radius: 5px; min-height: 20px;
}}
QScrollBar:horizontal {{
    background: {C_SURFACE}; height: 10px; border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: #4a4a6a; border-radius: 5px; min-width: 20px;
}}
QPushButton {{
    background-color: {C_SURFACE};
    border: 1px solid #3a3a5a;
    border-radius: 6px;
    padding: 5px 14px;
    color: {C_TEXT};
}}
QPushButton:hover {{ background-color: #3a3a5a; }}
QPushButton:pressed {{ background-color: #4a4a6a; }}
QPushButton#accent {{
    background-color: {C_ACCENT};
    color: #1a1000;
    font-weight: bold;
    border: none;
}}
QPushButton#accent:hover {{ background-color: #ffb300; }}
QPushButton#danger {{
    background-color: {C_RED};
    color: #fff;
    border: none;
}}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {C_SURFACE};
    border: 1px solid #3a3a5a;
    border-radius: 4px;
    padding: 4px 8px;
    color: {C_TEXT};
}}
QTabWidget::pane {{ border: 1px solid #3a3a5a; }}
QTabBar::tab {{
    background: {C_PANEL};
    padding: 6px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {C_MUTED};
}}
QTabBar::tab:selected {{ background: {C_SURFACE}; color: {C_TEXT}; }}
QLabel#heading {{
    font-size: 15px;
    font-weight: bold;
    color: {C_ACCENT};
}}
QLabel#section {{
    font-size: 12px;
    font-weight: bold;
    color: {C_MUTED};
    padding-top: 6px;
}}
QGroupBox {{
    border: 1px solid #3a3a5a;
    border-radius: 6px;
    margin-top: 12px;
    padding: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    color: {C_ACCENT};
    font-weight: bold;
}}
QToolBar {{
    background: {C_PANEL};
    border-bottom: 1px solid #3a3a5a;
    spacing: 6px;
    padding: 4px;
}}
QStatusBar {{ background: {C_PANEL}; border-top: 1px solid #3a3a5a; }}
QListWidget {{
    background: {C_SURFACE};
    border: 1px solid #3a3a5a;
    border-radius: 4px;
}}
QListWidget::item:selected {{ background: {C_ACCENT2}; color: #000; }}
QProgressBar {{
    background: {C_SURFACE};
    border: 1px solid #3a3a5a;
    border-radius: 4px;
    text-align: center;
    height: 16px;
}}
QProgressBar::chunk {{ background: {C_ACCENT}; border-radius: 4px; }}
"""


# ──────────────────────────────────────────────────────────────────────────────
#  ASSET PANEL  (left panel)
# ──────────────────────────────────────────────────────────────────────────────
class AssetThumbnailWidget(QFrame):
    """A single draggable asset card."""
    double_clicked = pyqtSignal(dict)

    def __init__(self, asset: dict, parent=None):
        super().__init__(parent)
        self.asset = asset
        self.setFixedSize(THUMB_W + 10, THUMB_H + 30)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._thumb = make_thumbnail(asset.get("path",""), THUMB_W, THUMB_H)
        self._label = asset.get("name","?")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # background
        p.fillRect(self.rect(), QColor(C_SURFACE))
        # thumb
        px_x = (self.width() - self._thumb.width()) // 2
        p.drawPixmap(px_x, 2, self._thumb)
        # label
        p.setPen(QColor(C_TEXT))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(QRect(2, THUMB_H+4, self.width()-4, 22),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   self._label[:16])
        p.end()

    def mouseDoubleClickEvent(self, e):
        self.double_clicked.emit(self.asset)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.pos()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            delta = (e.pos() - self._drag_start).manhattanLength()
            if delta > 6:
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(json.dumps(self.asset))
                drag.setMimeData(mime)
                drag.setPixmap(self._thumb)
                drag.exec(Qt.DropAction.CopyAction)


class AssetPanel(QWidget):
    """Left panel: Characters, Trucks, My Media, Search."""
    asset_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(280)
        self._setup_ui()
        self._load_builtin_assets()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        title = QLabel("🎬 Asset Library")
        title.setObjectName("heading")
        lay.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        lay.addWidget(self.tabs)

        # Characters tab
        self.char_grid = self._make_grid_tab()
        self.tabs.addTab(self.char_grid, "Characters")

        # Trucks tab
        self.truck_grid = self._make_grid_tab()
        self.tabs.addTab(self.truck_grid, "Trucks")

        # My Media tab
        my_media_w = QWidget()
        my_lay = QVBoxLayout(my_media_w)
        my_lay.setContentsMargins(4,4,4,4)
        add_btn = QPushButton("+ Import Media…")
        add_btn.clicked.connect(self._import_media)
        my_lay.addWidget(add_btn)
        self.media_grid = self._make_grid_tab()
        my_lay.addWidget(self.media_grid)
        self.tabs.addTab(my_media_w, "My Media")

        # Overlays tab
        overlay_w = QWidget()
        ov_lay = QVBoxLayout(overlay_w)
        ov_lay.setContentsMargins(4,4,4,4)
        self._build_overlay_buttons(ov_lay)
        ov_lay.addStretch()
        self.tabs.addTab(overlay_w, "Overlays")

    def _make_grid_tab(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setLayout(QGridLayout())
        inner.layout().setSpacing(4)
        scroll.setWidget(inner)
        scroll._inner = inner
        return scroll

    def _add_thumb(self, scroll: QScrollArea, asset: dict):
        grid = scroll._inner.layout()
        count = grid.count()
        row, col = divmod(count, 2)
        w = AssetThumbnailWidget(asset)
        w.double_clicked.connect(self.asset_double_clicked)
        grid.addWidget(w, row, col)

    def _build_overlay_buttons(self, lay):
        heading = QLabel("Educational Overlays")
        heading.setObjectName("section")
        lay.addWidget(heading)

        items = [
            ("🔤 Letter Card",  {"kind":"overlay","overlay_type":"letter_card","name":"Letter Card","overlay_data":"A"}),
            ("🔢 Number Card",  {"kind":"overlay","overlay_type":"number_card","name":"Number Card","overlay_data":"1"}),
            ("🎨 Color Card",   {"kind":"overlay","overlay_type":"color_card", "name":"Color Card", "overlay_data":"red"}),
            ("🏷️ Title Card",   {"kind":"overlay","overlay_type":"title_card", "name":"Title Card", "overlay_data":"Big Truck Adventures"}),
            ("📣 Caption Bar",  {"kind":"overlay","overlay_type":"caption_bar","name":"Caption Bar","overlay_data":"Jensen says..."}),
        ]
        for label, asset in items:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.clicked.connect(lambda _, a=asset: self.asset_double_clicked.emit(a))
            lay.addWidget(btn)

        heading2 = QLabel("Text Animations")
        heading2.setObjectName("section")
        lay.addWidget(heading2)

        anims = [
            ("↕ Bounce Text",       {"kind":"text","animation":"bounce","name":"Bounce Text","text":"Hello!"}),
            ("💥 Pop Text",         {"kind":"text","animation":"pop","name":"Pop Text","text":"WOW!"}),
            ("→ Slide-In Text",     {"kind":"text","animation":"slide_right","name":"Slide-In Text","text":"..."}),
            ("🌈 Rainbow Text",     {"kind":"text","animation":"rainbow","name":"Rainbow Text","text":"ABC!"}),
            ("✨ Fade-In Text",     {"kind":"text","animation":"fade_in","name":"Fade-In Text","text":"..."}),
        ]
        for label, asset in anims:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.clicked.connect(lambda _, a=asset: self.asset_double_clicked.emit(a))
            lay.addWidget(btn)

    def _load_builtin_assets(self):
        """Scan the BigTruckAdventures asset folder and load into panels."""
        chars_dir  = ASSETS_ROOT / "Characters"
        trucks_dir = ASSETS_ROOT / "Trucks"

        for img in sorted(chars_dir.glob("*.png")):
            asset = {"kind":"image","name":img.stem,"path":str(img),
                     "clip_type":"image","color":C_CLIP_IMG}
            get_db().add_asset("image", img.stem, str(img), tags="character")
            self._add_thumb(self.char_grid, asset)

        for img in sorted(trucks_dir.glob("*.png")):
            asset = {"kind":"image","name":img.stem,"path":str(img),
                     "clip_type":"image","color":C_CLIP_IMG}
            get_db().add_asset("image", img.stem, str(img), tags="truck")
            self._add_thumb(self.truck_grid, asset)

    def _import_media(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import Media",
            str(Path.home()),
            "Media (*.mp4 *.mov *.avi *.mkv *.png *.jpg *.jpeg *.gif *.mp3 *.wav *.ogg *.m4a)"
        )
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in (".mp4",".mov",".avi",".mkv"):
                kind = "video"
                color = C_CLIP_VID
            elif ext in (".mp3",".wav",".ogg",".m4a"):
                kind = "audio"
                color = C_CLIP_AUD
            else:
                kind = "image"
                color = C_CLIP_IMG
            asset = {"kind":kind,"name":Path(f).stem,"path":f,
                     "clip_type":kind,"color":color}
            get_db().add_asset(kind, Path(f).stem, f)
            self._add_thumb(self.media_grid, asset)
        if files:
            self.tabs.setCurrentIndex(2)

    def refresh_media(self):
        """Reload media assets from DB."""
        grid = self.media_grid._inner.layout()
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for row in get_db().get_assets():
            if row["tags"] not in ("character","truck"):
                asset = {"kind":row["kind"],"name":row["name"],
                         "path":row.get("path",""),"clip_type":row["kind"],
                         "color":C_CLIP_VID if row["kind"]=="video" else
                                 C_CLIP_AUD if row["kind"]=="audio" else C_CLIP_IMG}
                self._add_thumb(self.media_grid, asset)


# ──────────────────────────────────────────────────────────────────────────────
#  TIMELINE RULER
# ──────────────────────────────────────────────────────────────────────────────
class TimelineRuler(QWidget):
    seek_changed = pyqtSignal(float)   # seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self._duration = 60.0
        self._zoom     = 1.0
        self._offset   = 0    # horizontal scroll px
        self._playhead = 0.0

    def set_state(self, duration: float, zoom: float, offset: int, playhead: float):
        self._duration = duration
        self._zoom     = zoom
        self._offset   = offset
        self._playhead = playhead
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(C_TIMELINE))
        pps = TIMELINE_PX_PER_SEC * self._zoom

        # tick marks
        step = 1.0
        if pps < 20:   step = 5.0
        if pps < 8:    step = 10.0
        if pps > 150:  step = 0.5

        t = 0.0
        while t <= self._duration + step:
            x = int(TRACK_HEADER_W + t * pps - self._offset)
            if 0 <= x <= w:
                is_sec = abs(t - round(t)) < 0.01
                tick_h = 12 if is_sec else 6
                p.setPen(QPen(QColor(C_MUTED), 1))
                p.drawLine(x, h - tick_h, x, h)
                if is_sec and pps > 10:
                    p.setPen(QColor(C_TEXT))
                    p.setFont(QFont("Segoe UI", 8))
                    p.drawText(x + 3, h - 14, secs_to_tc(t))
            t += step

        # playhead
        ph_x = int(TRACK_HEADER_W + self._playhead * pps - self._offset)
        p.setPen(QPen(QColor(C_ACCENT), 2))
        p.drawLine(ph_x, 0, ph_x, h)
        p.end()

    def mousePressEvent(self, e):
        self._seek(e.pos().x())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._seek(e.pos().x())

    def _seek(self, px: int):
        pps = TIMELINE_PX_PER_SEC * self._zoom
        t = (px - TRACK_HEADER_W + self._offset) / pps
        self.seek_changed.emit(max(0.0, t))


# ──────────────────────────────────────────────────────────────────────────────
#  TIMELINE CLIP ITEM  (drawn on the track canvas)
# ──────────────────────────────────────────────────────────────────────────────
class ClipItem:
    HANDLE_W = 7

    def __init__(self, clip: Clip):
        self.clip    = clip
        self.rect    = QRect()
        self.selected = False
        self._drag_mode = None    # None | "move" | "trim_left" | "trim_right"
        self._drag_start_x = 0
        self._orig_start   = 0.0
        self._orig_dur     = 0.0
        self._orig_trim_in = 0.0

    def hit_test(self, px: int) -> str:
        """Return 'trim_left','trim_right', or 'move'."""
        if abs(px - self.rect.left()) <= self.HANDLE_W:
            return "trim_left"
        if abs(px - self.rect.right()) <= self.HANDLE_W:
            return "trim_right"
        return "move"

    def color(self) -> QColor:
        return QColor(self.clip.color or C_CLIP_VID)


# ──────────────────────────────────────────────────────────────────────────────
#  TIMELINE CANVAS  (scrollable canvas with all tracks + clips)
# ──────────────────────────────────────────────────────────────────────────────
class TimelineCanvas(QWidget):
    """The scrollable canvas that holds all track lanes and clip items."""
    selection_changed = pyqtSignal(object)   # Clip or None
    playhead_changed  = pyqtSignal(float)
    project_changed   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setMinimumHeight(200)

        self.project: Optional[Project] = None
        self._items:  List[ClipItem]    = []
        self._zoom    = 1.0
        self._offset  = 0     # horizontal scroll in px
        self._playhead = 0.0

        self._drag_item: Optional[ClipItem] = None
        self._hover_item: Optional[ClipItem] = None
        self._sel_item:   Optional[ClipItem] = None

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(16)
        self._scroll_timer.timeout.connect(self._auto_scroll)
        self._auto_scroll_dir = 0

    # ── public API ─────────────────────────────────────────────────────────────
    def load_project(self, project: Project):
        self.project = project
        self._rebuild_items()
        self.update()

    def set_zoom(self, zoom: float):
        self._zoom = max(0.1, min(10.0, zoom))
        self.setMinimumWidth(self._canvas_width())
        self.update()

    def set_offset(self, px: int):
        self._offset = px
        self.update()

    def set_playhead(self, t: float):
        self._playhead = t
        self.update()

    def get_selected_clip(self) -> Optional[Clip]:
        return self._sel_item.clip if self._sel_item else None

    def delete_selected(self):
        if self._sel_item and self.project:
            self.project.clips.remove(self._sel_item.clip)
            self._rebuild_items()
            self._sel_item = None
            self.selection_changed.emit(None)
            self.project_changed.emit()
            self.update()

    def split_at_playhead(self):
        if not self._sel_item or not self.project:
            return
        clip = self._sel_item.clip
        t    = self._playhead
        if clip.start_time < t < clip.end_time:
            # left piece
            left = Clip.from_dict(clip.to_dict())
            left.id       = f"clip_{random.randint(100000,999999)}"
            left.duration = t - clip.start_time
            # right piece
            right = clip
            split_offset  = t - right.start_time
            right.trim_in += split_offset
            right.duration -= split_offset
            right.start_time = t
            # insert left
            self.project.clips.append(left)
            self._rebuild_items()
            self.project_changed.emit()
            self.update()

    def add_clip_from_asset(self, asset: dict, track_idx: int = 0, start: float = 0.0):
        """Create a Clip from an asset dict and add to the project."""
        if not self.project:
            return
        ct = asset.get("clip_type", asset.get("kind","video"))
        c  = Clip(
            track      = track_idx,
            start_time = start,
            duration   = 5.0 if ct != "audio" else 30.0,
            clip_type  = ct,
            source_path= asset.get("path",""),
            label      = asset.get("name",""),
            color      = asset.get("color", C_CLIP_VID),
            text       = asset.get("text",""),
            animation  = asset.get("animation","none"),
            overlay_type= asset.get("overlay_type",""),
            overlay_data= asset.get("overlay_data",""),
        )
        self.project.clips.append(c)
        self._rebuild_items()
        self.project_changed.emit()
        self.update()

    # ── internals ──────────────────────────────────────────────────────────────
    def _canvas_width(self) -> int:
        dur = self.project.duration if self.project else 60.0
        return TRACK_HEADER_W + int(dur * TIMELINE_PX_PER_SEC * self._zoom) + 200

    def _track_y(self, track_idx: int) -> int:
        if not self.project:
            return 0
        y = 0
        for i, t in enumerate(self.project.tracks):
            if i == track_idx:
                return y
            y += t.height
        return y

    def _track_at_y(self, y: int) -> int:
        if not self.project:
            return 0
        cy = 0
        for i, t in enumerate(self.project.tracks):
            if cy <= y < cy + t.height:
                return i
            cy += t.height
        return len(self.project.tracks) - 1

    def _time_to_px(self, t: float) -> int:
        return TRACK_HEADER_W + int(t * TIMELINE_PX_PER_SEC * self._zoom) - self._offset

    def _px_to_time(self, px: int) -> float:
        return (px + self._offset - TRACK_HEADER_W) / (TIMELINE_PX_PER_SEC * self._zoom)

    def _rebuild_items(self):
        if not self.project:
            self._items = []
            return
        self._items = []
        for clip in self.project.clips:
            item = ClipItem(clip)
            self._items.append(item)
        self._update_rects()

    def _update_rects(self):
        if not self.project:
            return
        for item in self._items:
            x = self._time_to_px(item.clip.start_time)
            w = max(MIN_CLIP_W, int(item.clip.duration * TIMELINE_PX_PER_SEC * self._zoom))
            y = self._track_y(item.clip.track)
            h = (self.project.tracks[item.clip.track].height
                 if item.clip.track < len(self.project.tracks) else TRACK_HEIGHT)
            item.rect = QRect(x, y, w, h - 2)

    def sizeHint(self) -> QSize:
        h = sum(t.height for t in self.project.tracks) if self.project else 200
        return QSize(self._canvas_width(), h)

    # ── painting ───────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        self._update_rects()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(C_TIMELINE))

        if not self.project:
            p.setPen(QColor(C_MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No project loaded.")
            p.end(); return

        # Track lanes
        y = 0
        for i, track in enumerate(self.project.tracks):
            lane_h = track.height
            # header
            hdr_color = QColor("#2a2a3e") if i % 2 == 0 else QColor("#252535")
            p.fillRect(0, y, TRACK_HEADER_W, lane_h, hdr_color)
            icon = {"video":"🎬","audio":"🎵","image":"🖼","text":"📝","overlay":"✨"}.get(track.kind,"▶")
            p.setPen(QColor(C_TEXT))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(QRect(4, y+2, TRACK_HEADER_W-8, lane_h-4),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       f"{icon} {track.name[:10]}")
            # mute indicator
            if track.muted:
                p.setPen(QColor(C_RED))
                p.drawText(QRect(TRACK_HEADER_W-18, y+2, 14, lane_h-4),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter, "M")
            # lane bg (alternating)
            lane_bg = QColor("#1a1a2a") if i % 2 == 0 else QColor("#1e1e30")
            p.fillRect(TRACK_HEADER_W, y, w - TRACK_HEADER_W, lane_h, lane_bg)
            p.setPen(QPen(QColor("#2a2a40"), 1))
            p.drawLine(0, y + lane_h - 1, w, y + lane_h - 1)
            y += lane_h

        # Clip items
        for item in self._items:
            r    = item.rect
            col  = item.color()
            if not r.isValid() or r.right() < TRACK_HEADER_W or r.left() > w:
                continue
            # body
            grad = QLinearGradient(r.topLeft(), r.bottomLeft())
            grad.setColorAt(0, col.lighter(130))
            grad.setColorAt(1, col)
            p.setBrush(QBrush(grad))
            if item.selected:
                p.setPen(QPen(QColor(C_ACCENT), 2))
            else:
                p.setPen(QPen(col.darker(160), 1))
            p.drawRoundedRect(r, 4, 4)

            # label
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold if item.selected else QFont.Weight.Normal))
            label = item.clip.label or item.clip.text or item.clip.clip_type
            p.setClipRect(r.adjusted(4,0,-4,0))
            p.drawText(r.adjusted(6, 0, -6, 0),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       label[:40])
            p.setClipping(False)

            # trim handles
            p.setBrush(QBrush(QColor(255,255,255,60)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(QRect(r.left(), r.top(), ClipItem.HANDLE_W, r.height()))
            p.drawRect(QRect(r.right()-ClipItem.HANDLE_W, r.top(), ClipItem.HANDLE_W, r.height()))

        # Playhead
        ph_x = self._time_to_px(self._playhead)
        p.setPen(QPen(QColor(C_ACCENT), 2))
        p.drawLine(ph_x, 0, ph_x, h)
        # playhead cap
        cap = QPolygon([QPoint(ph_x-6,0), QPoint(ph_x+6,0), QPoint(ph_x,10)])
        p.setBrush(QBrush(QColor(C_ACCENT)))
        p.drawPolygon(cap)

        p.end()

    # ── mouse events ───────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        px, py = e.pos().x(), e.pos().y()

        # click on track header → mute toggle
        if px < TRACK_HEADER_W and self.project:
            ti = self._track_at_y(py)
            if ti < len(self.project.tracks):
                self.project.tracks[ti].muted ^= True
                self.update()
                return

        clicked = None
        for item in reversed(self._items):
            if item.rect.contains(QPoint(px, py)):
                clicked = item
                break

        # deselect old
        if self._sel_item:
            self._sel_item.selected = False
        self._sel_item = clicked

        if clicked:
            clicked.selected = True
            clicked._drag_mode   = clicked.hit_test(px)
            clicked._drag_start_x= px
            clicked._orig_start  = clicked.clip.start_time
            clicked._orig_dur    = clicked.clip.duration
            clicked._orig_trim_in= clicked.clip.trim_in
            self.setCursor(Qt.CursorShape.SizeHorCursor
                           if clicked._drag_mode != "move"
                           else Qt.CursorShape.ClosedHandCursor)
            self.selection_changed.emit(clicked.clip)
        else:
            # seek
            t = self._px_to_time(px)
            if t >= 0:
                self._playhead = t
                self.playhead_changed.emit(t)
            self.selection_changed.emit(None)

        self.update()

    def mouseMoveEvent(self, e):
        px, py = e.pos().x(), e.pos().y()
        if self._drag_item:
            self._do_drag(px)
        elif e.buttons() & Qt.MouseButton.LeftButton and self._sel_item:
            self._sel_item.clip  # already handled below
            self._do_drag_sel(px)
        else:
            # hover cursor
            for item in reversed(self._items):
                if item.rect.contains(QPoint(px,py)):
                    mode = item.hit_test(px)
                    self.setCursor(Qt.CursorShape.SizeHorCursor
                                   if mode != "move"
                                   else Qt.CursorShape.OpenHandCursor)
                    return
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _do_drag_sel(self, px: int):
        item = self._sel_item
        if not item or not self.project:
            return
        pps  = TIMELINE_PX_PER_SEC * self._zoom
        delta_t = (px - item._drag_start_x) / pps
        if item._drag_mode == "move":
            new_start = max(0.0, item._orig_start + delta_t)
            item.clip.start_time = round(new_start, 3)
        elif item._drag_mode == "trim_left":
            new_start  = max(0.0, item._orig_start + delta_t)
            new_dur    = item._orig_dur - (new_start - item._orig_start)
            if new_dur > 0.1:
                item.clip.start_time = new_start
                item.clip.duration   = round(new_dur, 3)
                item.clip.trim_in    = item._orig_trim_in + (new_start - item._orig_start)
        elif item._drag_mode == "trim_right":
            new_dur = max(0.1, item._orig_dur + delta_t)
            item.clip.duration = round(new_dur, 3)

        self.project_changed.emit()
        self.update()

    def mouseReleaseEvent(self, e):
        self._drag_item = None
        self._auto_scroll_dir = 0
        self._scroll_timer.stop()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = e.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            self.set_zoom(self._zoom * factor)
        else:
            self._offset = max(0, self._offset - e.angleDelta().y() // 2)
            self.update()

    # ── drag-drop from asset panel ─────────────────────────────────────────────
    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        try:
            asset = json.loads(e.mimeData().text())
        except Exception:
            return
        px = e.position().x()
        py = e.position().y()
        t  = max(0.0, self._px_to_time(px))
        ti = self._track_at_y(int(py))
        self.add_clip_from_asset(asset, track_idx=ti, start=t)
        e.acceptProposedAction()

    def _auto_scroll(self):
        self._offset = max(0, self._offset + self._auto_scroll_dir * 20)
        self.update()


# ──────────────────────────────────────────────────────────────────────────────
#  TIMELINE WIDGET  (ruler + canvas + h-scrollbar together)
# ──────────────────────────────────────────────────────────────────────────────
class TimelineWidget(QWidget):
    selection_changed = pyqtSignal(object)
    playhead_changed  = pyqtSignal(float)
    project_changed   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)

        self.ruler  = TimelineRuler()
        lay.addWidget(self.ruler)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.hbar = scroll_area.horizontalScrollBar()

        self.canvas = TimelineCanvas()
        self.canvas.selection_changed.connect(self.selection_changed)
        self.canvas.playhead_changed.connect(self._on_canvas_playhead)
        self.canvas.project_changed.connect(self.project_changed)
        scroll_area.setWidget(self.canvas)
        lay.addWidget(scroll_area)

        self.hbar.valueChanged.connect(self._on_scroll)

        # zoom controls
        zoom_bar = QWidget()
        zb_lay = QHBoxLayout(zoom_bar)
        zb_lay.setContentsMargins(4,2,4,2)
        zb_lay.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(1, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(self._on_zoom)
        zb_lay.addWidget(self.zoom_slider)
        zb_lay.addStretch()
        lay.addWidget(zoom_bar)

    def load_project(self, p: Project):
        self.canvas.load_project(p)
        self._refresh_ruler()

    def set_playhead(self, t: float):
        self.canvas.set_playhead(t)
        self._refresh_ruler()

    def _on_scroll(self, v: int):
        self.canvas.set_offset(v)
        self._refresh_ruler()

    def _on_zoom(self, v: int):
        zoom = v / 100.0
        self.canvas.set_zoom(zoom)
        self._refresh_ruler()

    def _on_canvas_playhead(self, t: float):
        self.playhead_changed.emit(t)
        self._refresh_ruler()

    def _refresh_ruler(self):
        dur = self.canvas.project.duration if self.canvas.project else 60.0
        self.ruler.set_state(dur, self.canvas._zoom, self.canvas._offset,
                             self.canvas._playhead)


# ──────────────────────────────────────────────────────────────────────────────
#  PREVIEW WINDOW
# ──────────────────────────────────────────────────────────────────────────────
class PreviewWindow(QWidget):
    """Centre preview: renders a composite frame from the project state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 270)
        self._project: Optional[Project]  = None
        self._playhead: float             = 0.0
        self._playing:  bool              = False
        self._play_start_real:  float     = 0.0
        self._play_start_proj:  float     = 0.0
        self._current_pixmap: Optional[QPixmap] = None
        self._anim_tick = 0

        self._timer = QTimer(self)
        self._timer.setInterval(1000 // FPS)
        self._timer.timeout.connect(self._on_tick)

        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(4)

        self._canvas = _PreviewCanvas(self)
        lay.addWidget(self._canvas, 1)

        ctrl = QWidget()
        c_lay = QHBoxLayout(ctrl)
        c_lay.setContentsMargins(4,2,4,2)

        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setObjectName("accent")
        self.btn_play.setFixedWidth(90)
        self.btn_play.clicked.connect(self.toggle_play)
        c_lay.addWidget(self.btn_play)

        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setFixedWidth(80)
        self.btn_stop.clicked.connect(self.stop)
        c_lay.addWidget(self.btn_stop)

        self.tc_label = QLabel("00:00:00:00")
        self.tc_label.setFont(QFont("Courier New", 11))
        c_lay.addWidget(self.tc_label)

        c_lay.addStretch()

        self.res_label = QLabel("1920×1080")
        self.res_label.setStyleSheet(f"color:{C_MUTED};font-size:11px;")
        c_lay.addWidget(self.res_label)

        lay.addWidget(ctrl)

    def load_project(self, p: Project):
        self._project = p
        self.res_label.setText(f"{p.width}×{p.height}")
        self._render_frame(self._playhead)

    def set_playhead(self, t: float):
        self._playhead = t
        self.tc_label.setText(secs_to_tc(t))
        self._render_frame(t)

    def toggle_play(self):
        if self._playing:
            self.pause()
        else:
            self.play()

    def play(self):
        self._playing = True
        self._play_start_real  = time.time()
        self._play_start_proj  = self._playhead
        self.btn_play.setText("⏸ Pause")
        self._timer.start()

    def pause(self):
        self._playing = False
        self._timer.stop()
        self.btn_play.setText("▶ Play")

    def stop(self):
        self.pause()
        self.set_playhead(0.0)

    def _on_tick(self):
        if not self._project:
            return
        elapsed = time.time() - self._play_start_real
        t = self._play_start_proj + elapsed
        if t >= self._project.duration:
            self.stop()
            return
        self._playhead = t
        self._anim_tick += 1
        self.tc_label.setText(secs_to_tc(t))
        self._render_frame(t)

    def _render_frame(self, t: float):
        """Compose a preview frame at time t (pure Python/Qt, fast)."""
        if not self._project:
            return
        w, h = self._canvas.width(), self._canvas.height()
        if w <= 0 or h <= 0:
            return

        pm = QPixmap(w, h)
        pm.fill(QColor(self._project.bg_color or "#0a0a1a"))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        scale_x = w / CANVAS_W
        scale_y = h / CANVAS_H

        if not self._project.clips:
            painter.setPen(QColor(C_MUTED))
            painter.setFont(QFont("Segoe UI", 14))
            painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter,
                             "Add clips to the timeline to preview")

        # render clips in track order (lower track index = behind)
        sorted_clips = sorted(self._project.clips,
                              key=lambda c: (c.track, c.start_time))
        for clip in sorted_clips:
            if clip.start_time <= t < clip.end_time:
                local_t = t - clip.start_time
                self._draw_clip(painter, clip, local_t, scale_x, scale_y, w, h)

        painter.end()
        self._canvas.set_pixmap(pm)
        self._current_pixmap = pm

    def _draw_clip(self, p: QPainter, clip: Clip,
                   local_t: float, sx: float, sy: float,
                   cw: int, ch: int):
        """Draw a single clip at local_t onto the painter."""
        ct = clip.clip_type

        if ct == "image" and clip.source_path:
            src_pm = QPixmap(clip.source_path)
            if not src_pm.isNull():
                # scale to fit canvas
                scaled = src_pm.scaled(
                    int(cw * 0.5), int(ch * 0.9),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                # position: centre-bottom by default
                x = (cw - scaled.width()) // 2
                y = ch - scaled.height() - int(20 * sy)
                p.drawPixmap(x, y, scaled)

        elif ct in ("text", "overlay"):
            self._draw_text_overlay(p, clip, local_t, sx, sy, cw, ch)

    def _draw_text_overlay(self, p: QPainter, clip: Clip,
                           local_t: float, sx: float, sy: float,
                           cw: int, ch: int):
        prog = local_t / max(clip.duration, 0.01)  # 0→1 through clip

        if clip.overlay_type == "letter_card":
            self._draw_letter_card(p, clip.overlay_data or "A", prog, cw, ch)
        elif clip.overlay_type == "number_card":
            self._draw_number_card(p, clip.overlay_data or "1", prog, cw, ch)
        elif clip.overlay_type == "color_card":
            self._draw_color_card(p, clip.overlay_data or "red", prog, cw, ch)
        elif clip.overlay_type == "title_card":
            self._draw_title_card(p, clip.overlay_data or clip.text, prog, cw, ch)
        elif clip.overlay_type == "caption_bar":
            self._draw_caption_bar(p, clip.overlay_data or clip.text, prog, cw, ch)
        else:
            # plain animated text
            self._draw_animated_text(p, clip, local_t, prog, sx, sy, cw, ch)

    def _draw_animated_text(self, p: QPainter, clip: Clip,
                             local_t: float, prog: float,
                             sx: float, sy: float, cw: int, ch: int):
        txt  = clip.text or ""
        if not txt:
            return
        fsz  = max(12, int(clip.font_size * min(sx, sy)))
        col  = QColor(clip.font_color or "#ffffff")
        font = QFont("Arial Rounded MT Bold" if "Arial Rounded" in QFont().family()
                     else "Segoe UI", fsz, QFont.Weight.Bold)
        p.setFont(font)

        px_x = int(clip.pos_x * cw / 100)
        px_y = int(clip.pos_y * ch / 100)
        anim = clip.animation

        ox, oy = 0, 0
        alpha  = 255

        if anim == "bounce":
            oy = int(math.sin(local_t * 6) * 14 * min(sx, sy))
        elif anim == "pop":
            scale = 1.0 + 0.3 * math.sin(prog * math.pi)
            fsz   = int(fsz * scale)
            font.setPointSize(fsz)
            p.setFont(font)
        elif anim == "slide_right":
            if prog < 0.25:
                ox = int(-cw * (1 - prog / 0.25))
        elif anim == "slide_left":
            if prog < 0.25:
                ox = int(cw * (1 - prog / 0.25))
        elif anim == "fade_in":
            alpha = min(255, int(255 * prog * 4))
            col.setAlpha(alpha)
        elif anim == "rainbow":
            hue = int((local_t * 60) % 360)
            col = QColor.fromHsv(hue, 255, 255)

        # shadow
        p.setPen(QColor(0, 0, 0, 120))
        p.drawText(QPoint(px_x + ox + 3, px_y + oy + 3), txt)
        p.setPen(col)
        p.drawText(QPoint(px_x + ox, px_y + oy), txt)

    def _draw_letter_card(self, p: QPainter, letter: str, prog: float, cw: int, ch: int):
        CARD_COLORS = ["#e53935","#1e88e5","#43a047","#fb8c00","#8e24aa","#e91e63"]
        letter = letter.strip().upper()[:1] if letter.strip() else "A"
        idx    = ord(letter) - ord('A')
        bg     = QColor(CARD_COLORS[idx % len(CARD_COLORS)])
        # pop-in
        scale = min(1.0, prog * 4)
        cw2   = int(cw * 0.35 * scale)
        ch2   = int(ch * 0.5  * scale)
        x     = (cw - cw2) // 2
        y     = (ch - ch2) // 2

        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor("#ffffff"), 4))
        p.drawRoundedRect(x, y, cw2, ch2, 16, 16)

        p.setPen(QColor("#ffffff"))
        fsz = max(24, int(ch2 * 0.55))
        p.setFont(QFont("Segoe UI", fsz, QFont.Weight.Bold))
        p.drawText(QRect(x, y, cw2, ch2-int(ch2*0.28)),
                   Qt.AlignmentFlag.AlignCenter, letter)

        p.setFont(QFont("Segoe UI", max(12, int(ch2 * 0.16))))
        p.drawText(QRect(x, y + int(ch2*0.62), cw2, int(ch2*0.28)),
                   Qt.AlignmentFlag.AlignCenter, f"'{letter.lower()}' sound")

    def _draw_number_card(self, p: QPainter, num: str, prog: float, cw: int, ch: int):
        num = num.strip()
        scale = min(1.0, prog * 4)
        cw2   = int(cw * 0.35 * scale)
        ch2   = int(ch * 0.5  * scale)
        x     = (cw - cw2) // 2
        y     = (ch - ch2) // 2

        p.setBrush(QBrush(QColor("#1565c0")))
        p.setPen(QPen(QColor("#ffcc02"), 4))
        p.drawRoundedRect(x, y, cw2, ch2, 16, 16)

        p.setPen(QColor("#ffcc02"))
        fsz = max(24, int(ch2 * 0.55))
        p.setFont(QFont("Segoe UI", fsz, QFont.Weight.Bold))
        p.drawText(QRect(x, y, cw2, ch2-int(ch2*0.28)),
                   Qt.AlignmentFlag.AlignCenter, num)

        p.setFont(QFont("Segoe UI", max(12, int(ch2 * 0.14))))
        p.setPen(QColor("#ffffff"))
        p.drawText(QRect(x, y + int(ch2*0.64), cw2, int(ch2*0.26)),
                   Qt.AlignmentFlag.AlignCenter, "The number " + num)

    def _draw_color_card(self, p: QPainter, color_name: str, prog: float, cw: int, ch: int):
        NAMED = {
            "red":"#e53935","blue":"#1e88e5","yellow":"#fdd835",
            "green":"#43a047","orange":"#fb8c00","purple":"#8e24aa",
            "pink":"#e91e63","white":"#f5f5f5","black":"#212121",
            "brown":"#6d4c41",
        }
        c_hex = NAMED.get(color_name.lower(), "#9e9e9e")
        scale = min(1.0, prog * 4)
        cw2 = int(cw * 0.38 * scale)
        ch2 = int(ch * 0.52 * scale)
        x   = (cw - cw2) // 2
        y   = (ch - ch2) // 2

        p.setBrush(QBrush(QColor(c_hex)))
        p.setPen(QPen(QColor("#ffffff"), 4))
        p.drawRoundedRect(x, y, cw2, ch2, 16, 16)

        text_color = QColor("#212121") if color_name.lower() in ("yellow","white") else QColor("#ffffff")
        p.setPen(text_color)
        p.setFont(QFont("Segoe UI", max(18, int(ch2 * 0.32)), QFont.Weight.Bold))
        p.drawText(QRect(x, y, cw2, ch2),
                   Qt.AlignmentFlag.AlignCenter,
                   color_name.upper())

    def _draw_title_card(self, p: QPainter, text: str, prog: float, cw: int, ch: int):
        if not text:
            text = "Big Truck Adventures"
        # slide down from top
        oy = int(-ch * max(0.0, 1.0 - prog * 5)) if prog < 0.2 else 0
        bar_h = int(ch * 0.22)
        p.fillRect(QRect(0, (ch - bar_h)//2 + oy, cw, bar_h), QColor(0,0,0,180))
        p.setPen(QColor(C_ACCENT))
        fsz = max(16, int(cw * 0.04))
        p.setFont(QFont("Segoe UI", fsz, QFont.Weight.Bold))
        p.drawText(QRect(0, (ch-bar_h)//2 + oy, cw, bar_h),
                   Qt.AlignmentFlag.AlignCenter, text)

    def _draw_caption_bar(self, p: QPainter, text: str, prog: float, cw: int, ch: int):
        if not text:
            return
        bar_h = int(ch * 0.12)
        y     = ch - bar_h - int(ch * 0.04)
        alpha = min(255, int(255 * prog * 8))
        p.fillRect(QRect(0, y, cw, bar_h), QColor(0, 0, 0, int(alpha * 0.75)))
        p.setPen(QColor(255,255,255, alpha))
        p.setFont(QFont("Segoe UI", max(12, int(cw * 0.025))))
        p.drawText(QRect(20, y, cw-40, bar_h),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)


class _PreviewCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pm: Optional[QPixmap] = None
        self.setStyleSheet("background:#000;")

    def set_pixmap(self, pm: QPixmap):
        self._pm = pm
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#000000"))
        if self._pm:
            scaled = self._pm.scaled(
                self.width(), self.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            ox = (self.width()  - scaled.width())  // 2
            oy = (self.height() - scaled.height()) // 2
            p.drawPixmap(ox, oy, scaled)
        p.end()


# ──────────────────────────────────────────────────────────────────────────────
#  PROPERTIES PANEL  (right panel)
# ──────────────────────────────────────────────────────────────────────────────
class PropertiesPanel(QWidget):
    """Right panel: shows properties for the selected clip."""
    clip_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)
        self._clip: Optional[Clip] = None
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6,6,6,6)
        lay.setSpacing(6)

        title = QLabel("⚙️ Properties")
        title.setObjectName("heading")
        lay.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner_lay = QVBoxLayout(self.inner)
        self.inner_lay.setContentsMargins(4,4,4,4)
        self.inner_lay.setSpacing(6)
        self.scroll.setWidget(self.inner)
        lay.addWidget(self.scroll)

        self._no_sel = QLabel("Select a clip on the timeline\nto edit its properties.")
        self._no_sel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_sel.setStyleSheet(f"color:{C_MUTED};font-size:12px;")
        self.inner_lay.addWidget(self._no_sel)
        self.inner_lay.addStretch()

    def load_clip(self, clip: Optional[Clip]):
        self._clip = clip
        # clear
        while self.inner_lay.count():
            item = self.inner_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if clip is None:
            lbl = QLabel("Select a clip on the timeline\nto edit its properties.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{C_MUTED};font-size:12px;")
            self.inner_lay.addWidget(lbl)
            self.inner_lay.addStretch()
            return

        # ── Clip info ──────────────────────────────────────────────────────────
        gb = QGroupBox("Clip")
        gl = QGridLayout(gb)
        gl.setSpacing(4)

        gl.addWidget(QLabel("Label:"), 0, 0)
        lbl_edit = QLineEdit(clip.label)
        lbl_edit.textChanged.connect(lambda v: self._set(clip, "label", v))
        gl.addWidget(lbl_edit, 0, 1)

        gl.addWidget(QLabel("Duration:"), 1, 0)
        dur_spin = QDoubleSpinBox()
        dur_spin.setRange(0.1, 3600)
        dur_spin.setValue(clip.duration)
        dur_spin.setSuffix(" s")
        dur_spin.valueChanged.connect(lambda v: self._set(clip, "duration", v))
        gl.addWidget(dur_spin, 1, 1)

        gl.addWidget(QLabel("Start:"), 2, 0)
        start_spin = QDoubleSpinBox()
        start_spin.setRange(0.0, 3600)
        start_spin.setValue(clip.start_time)
        start_spin.setSuffix(" s")
        start_spin.valueChanged.connect(lambda v: self._set(clip, "start_time", v))
        gl.addWidget(start_spin, 2, 1)

        if clip.clip_type == "audio":
            gl.addWidget(QLabel("Volume:"), 3, 0)
            vol_spin = QDoubleSpinBox()
            vol_spin.setRange(0.0, 2.0)
            vol_spin.setSingleStep(0.05)
            vol_spin.setValue(clip.volume)
            vol_spin.valueChanged.connect(lambda v: self._set(clip, "volume", v))
            gl.addWidget(vol_spin, 3, 1)

        self.inner_lay.addWidget(gb)

        # ── Text / Overlay ─────────────────────────────────────────────────────
        if clip.clip_type in ("text","overlay"):
            gb2 = QGroupBox("Text & Animation")
            gl2 = QGridLayout(gb2)
            gl2.setSpacing(4)

            gl2.addWidget(QLabel("Text:"), 0, 0)
            te = QLineEdit(clip.text)
            te.textChanged.connect(lambda v: self._set(clip, "text", v))
            gl2.addWidget(te, 0, 1)

            gl2.addWidget(QLabel("Font size:"), 1, 0)
            fsz = QSpinBox()
            fsz.setRange(8, 300)
            fsz.setValue(clip.font_size)
            fsz.valueChanged.connect(lambda v: self._set(clip, "font_size", v))
            gl2.addWidget(fsz, 1, 1)

            gl2.addWidget(QLabel("Color:"), 2, 0)
            col_btn = QPushButton("Choose…")
            col_btn.setStyleSheet(f"background:{clip.font_color};color:#fff;")
            def _pick_color(btn=col_btn):
                c = QColorDialog.getColor(QColor(clip.font_color), self)
                if c.isValid():
                    clip.font_color = c.name()
                    btn.setStyleSheet(f"background:{c.name()};color:#fff;")
                    self.clip_changed.emit()
            col_btn.clicked.connect(_pick_color)
            gl2.addWidget(col_btn, 2, 1)

            gl2.addWidget(QLabel("Animation:"), 3, 0)
            anim_combo = QComboBox()
            anims = ["none","bounce","pop","slide_left","slide_right","fade_in","rainbow"]
            anim_combo.addItems(anims)
            anim_combo.setCurrentText(clip.animation)
            anim_combo.currentTextChanged.connect(lambda v: self._set(clip, "animation", v))
            gl2.addWidget(anim_combo, 3, 1)

            gl2.addWidget(QLabel("X pos %:"), 4, 0)
            xsp = QSpinBox(); xsp.setRange(0,100); xsp.setValue(clip.pos_x)
            xsp.valueChanged.connect(lambda v: self._set(clip, "pos_x", v))
            gl2.addWidget(xsp, 4, 1)

            gl2.addWidget(QLabel("Y pos %:"), 5, 0)
            ysp = QSpinBox(); ysp.setRange(0,100); ysp.setValue(clip.pos_y)
            ysp.valueChanged.connect(lambda v: self._set(clip, "pos_y", v))
            gl2.addWidget(ysp, 5, 1)

            self.inner_lay.addWidget(gb2)

            if clip.overlay_type:
                gb3 = QGroupBox("Overlay Data")
                gl3 = QGridLayout(gb3)
                gl3.addWidget(QLabel("Value:"), 0, 0)
                od_edit = QLineEdit(clip.overlay_data)
                od_edit.setPlaceholderText("e.g. A, 5, red…")
                od_edit.textChanged.connect(lambda v: self._set(clip, "overlay_data", v))
                gl3.addWidget(od_edit, 0, 1)
                self.inner_lay.addWidget(gb3)

        # ── Source ─────────────────────────────────────────────────────────────
        if clip.source_path:
            gb4 = QGroupBox("Source")
            gl4 = QGridLayout(gb4)
            sp_lbl = QLabel(Path(clip.source_path).name)
            sp_lbl.setWordWrap(True)
            sp_lbl.setStyleSheet(f"color:{C_MUTED};font-size:10px;")
            gl4.addWidget(sp_lbl, 0, 0)
            chg_btn = QPushButton("Replace…")
            chg_btn.clicked.connect(lambda: self._replace_source(clip))
            gl4.addWidget(chg_btn, 1, 0)
            self.inner_lay.addWidget(gb4)

        self.inner_lay.addStretch()

    def _set(self, clip: Clip, attr: str, val):
        setattr(clip, attr, val)
        self.clip_changed.emit()

    def _replace_source(self, clip: Clip):
        f, _ = QFileDialog.getOpenFileName(self, "Replace Source", str(Path.home()),
               "Media (*.mp4 *.mov *.avi *.png *.jpg *.jpeg *.mp3 *.wav)")
        if f:
            clip.source_path = f
            self.clip_changed.emit()
            self.load_clip(clip)


# ──────────────────────────────────────────────────────────────────────────────
#  MEDIA SEARCH DIALOG  (Pexels + Pixabay + Free Music Archive)
# ──────────────────────────────────────────────────────────────────────────────
class MediaSearchDialog(QDialog):
    """Searchable free media library. Returns chosen file path."""
    file_downloaded = pyqtSignal(str, str)  # (path, kind)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Free Media Library – Pexels / Pixabay / Free Music Archive")
        self.setMinimumSize(780, 520)
        self.setModal(False)
        self._setup_ui()
        self._results: List[dict] = []

    def _setup_ui(self):
        lay = QVBoxLayout(self)

        # top bar
        top = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Pexels Videos","Pexels Photos","Pixabay Videos",
                                    "Pixabay Images","Free Music Archive"])
        self.source_combo.setFixedWidth(200)
        top.addWidget(QLabel("Source:"))
        top.addWidget(self.source_combo)

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Search (e.g. 'construction truck', 'kids music')")
        self.query_edit.returnPressed.connect(self._do_search)
        top.addWidget(self.query_edit, 1)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("API key (optional for Pexels/Pixabay)")
        self.api_key_edit.setFixedWidth(180)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        top.addWidget(self.api_key_edit)

        search_btn = QPushButton("Search")
        search_btn.setObjectName("accent")
        search_btn.clicked.connect(self._do_search)
        top.addWidget(search_btn)
        lay.addLayout(top)

        # api key note
        note = QLabel(
            "Tip: get a FREE Pexels API key at pexels.com/api  •  Pixabay key at pixabay.com/api/docs  "
            "•  Free Music Archive needs no key"
        )
        note.setStyleSheet(f"color:{C_MUTED};font-size:11px;")
        note.setWordWrap(True)
        lay.addWidget(note)

        # results grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_lay    = QGridLayout(self.results_widget)
        self.results_lay.setSpacing(6)
        self.scroll.setWidget(self.results_widget)
        lay.addWidget(self.scroll, 1)

        # status + progress
        bot = QHBoxLayout()
        self.status_lbl = QLabel("Enter a search query above.")
        bot.addWidget(self.status_lbl, 1)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(180)
        self.progress.setVisible(False)
        bot.addWidget(self.progress)
        lay.addLayout(bot)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        lay.addWidget(close_btn)

    # ── search ────────────────────────────────────────────────────────────────
    def _do_search(self):
        q       = self.query_edit.text().strip()
        source  = self.source_combo.currentText()
        api_key = self.api_key_edit.text().strip()
        if not q:
            self.status_lbl.setText("Please enter a search query.")
            return

        # clear old results
        while self.results_lay.count():
            item = self.results_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._results = []

        self.progress.setVisible(True)
        self.progress.setRange(0,0)
        self.status_lbl.setText(f"Searching {source}…")

        run_in_thread(self._fetch, source, q, api_key)

    def _fetch(self, source: str, q: str, api_key: str):
        try:
            if source == "Pexels Videos":
                results = self._search_pexels_videos(q, api_key)
            elif source == "Pexels Photos":
                results = self._search_pexels_photos(q, api_key)
            elif source == "Pixabay Videos":
                results = self._search_pixabay_videos(q, api_key)
            elif source == "Pixabay Images":
                results = self._search_pixabay_images(q, api_key)
            elif source == "Free Music Archive":
                results = self._search_fma(q)
            else:
                results = []
        except Exception as ex:
            results = []
            self._post_status(f"Error: {ex}")

        self._post_results(results)

    def _post_status(self, msg: str):
        QTimer.singleShot(0, lambda: self.status_lbl.setText(msg))

    def _post_results(self, results: list):
        QTimer.singleShot(0, lambda: self._show_results(results))

    def _show_results(self, results: list):
        self._results = results
        self.progress.setVisible(False)
        while self.results_lay.count():
            item = self.results_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not results:
            self.status_lbl.setText("No results found (check API key or try a different query).")
            return

        self.status_lbl.setText(f"Found {len(results)} results — double-click to download & add to project.")
        for i, r in enumerate(results[:24]):
            row, col = divmod(i, 4)
            card = _MediaResultCard(r)
            card.download_clicked.connect(self._on_download)
            self.results_lay.addWidget(card, row, col)

    def _on_download(self, result: dict):
        run_in_thread(self._download_file, result)

    def _download_file(self, result: dict):
        url   = result.get("download_url","")
        kind  = result.get("kind","video")
        fname = result.get("filename", f"{kind}_{random.randint(10000,99999)}.mp4")
        dest  = CACHE_DIR / fname
        if dest.exists():
            self._post_status(f"Already cached: {fname}")
            QTimer.singleShot(0, lambda: self.file_downloaded.emit(str(dest), kind))
            return
        try:
            self._post_status(f"Downloading {fname}…")
            req = urllib.request.Request(url, headers={"User-Agent": "BigTruckEditor/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
                shutil.copyfileobj(resp, f)
            self._post_status(f"Downloaded: {fname}")
            QTimer.singleShot(0, lambda: self.file_downloaded.emit(str(dest), kind))
        except Exception as ex:
            self._post_status(f"Download failed: {ex}")

    # ── API helpers ──────────────────────────────────────────────────────────
    def _search_pexels_videos(self, q: str, key: str) -> list:
        if not key:
            return [{"title":"No API key","desc":"Get a free key at pexels.com/api","preview_url":"","download_url":"","kind":"video","filename":""}]
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(q)}&per_page=20&orientation=landscape"
        req = urllib.request.Request(url, headers={"Authorization": key})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        out = []
        for v in data.get("videos",[]):
            files = v.get("video_files",[])
            hd = next((f for f in files if f.get("quality")=="hd"), files[0] if files else {})
            out.append({
                "title": f"Pexels – {v.get('user',{}).get('name','')}",
                "desc": f"{v.get('duration',0)}s | {v.get('width',0)}×{v.get('height',0)}",
                "preview_url": v.get("image",""),
                "download_url": hd.get("link",""),
                "kind": "video",
                "filename": f"pexels_{v['id']}.mp4",
            })
        return out

    def _search_pexels_photos(self, q: str, key: str) -> list:
        if not key:
            return [{"title":"No API key","desc":"Get a free key at pexels.com/api","preview_url":"","download_url":"","kind":"image","filename":""}]
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(q)}&per_page=20&orientation=landscape"
        req = urllib.request.Request(url, headers={"Authorization": key})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        out = []
        for ph in data.get("photos",[]):
            out.append({
                "title": f"Pexels Photo #{ph['id']}",
                "desc": f"{ph.get('width',0)}×{ph.get('height',0)} – {ph.get('photographer','')}",
                "preview_url": ph.get("src",{}).get("small",""),
                "download_url": ph.get("src",{}).get("original",""),
                "kind": "image",
                "filename": f"pexels_{ph['id']}.jpg",
            })
        return out

    def _search_pixabay_videos(self, q: str, key: str) -> list:
        if not key:
            return [{"title":"No API key","desc":"Get a free key at pixabay.com/api/docs","preview_url":"","download_url":"","kind":"video","filename":""}]
        url = (f"https://pixabay.com/api/videos/?key={key}&q={urllib.parse.quote(q)}"
               f"&per_page=20&video_type=all")
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.load(resp)
        out = []
        for v in data.get("hits",[]):
            vids = v.get("videos",{})
            src  = vids.get("large",{}).get("url") or vids.get("medium",{}).get("url","")
            out.append({
                "title": f"Pixabay – {v.get('user','')}",
                "desc": f"{v.get('duration',0)}s | {v.get('views',0)} views",
                "preview_url": v.get("userImageURL",""),
                "download_url": src,
                "kind": "video",
                "filename": f"pixabay_{v['id']}.mp4",
            })
        return out

    def _search_pixabay_images(self, q: str, key: str) -> list:
        if not key:
            return [{"title":"No API key","desc":"Get a free key at pixabay.com/api/docs","preview_url":"","download_url":"","kind":"image","filename":""}]
        url = (f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(q)}"
               f"&per_page=20&image_type=all&orientation=horizontal")
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.load(resp)
        out = []
        for ph in data.get("hits",[]):
            out.append({
                "title": f"Pixabay – {ph.get('user','')}",
                "desc": f"{ph.get('imageWidth',0)}×{ph.get('imageHeight',0)}",
                "preview_url": ph.get("previewURL",""),
                "download_url": ph.get("largeImageURL",""),
                "kind": "image",
                "filename": f"pixabay_{ph['id']}.jpg",
            })
        return out

    def _search_fma(self, q: str) -> list:
        """Free Music Archive – free, no key needed."""
        url = (f"https://freemusicarchive.org/api/get/tracks.json"
               f"?search={urllib.parse.quote(q)}&limit=20")
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.load(resp)
            out = []
            for t in data.get("dataset",[]):
                out.append({
                    "title": t.get("track_title","Unknown"),
                    "desc": f"{t.get('artist_name','')} – {t.get('album_title','')}",
                    "preview_url": t.get("track_image_file",""),
                    "download_url": t.get("track_file",""),
                    "kind": "audio",
                    "filename": f"fma_{t.get('track_id','0')}.mp3",
                })
            return out
        except Exception:
            # Fallback: curated public domain list
            return [
                {"title":"No results (FMA API may be unavailable)","desc":"Try ccmixter.org or freemusicarchive.org directly","preview_url":"","download_url":"","kind":"audio","filename":""},
            ]


class _MediaResultCard(QFrame):
    download_clicked = pyqtSignal(dict)

    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self._result = result
        self.setFixedSize(170, 140)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4,4,4,4)
        lay.setSpacing(2)

        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(162, 90)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet("background:#1a1a2e;")
        lay.addWidget(self._thumb_label)

        icon = {"video":"🎬","audio":"🎵","image":"🖼"}.get(result.get("kind","video"),"▶")
        title_lbl = QLabel(f"{icon} {result.get('title','')[:24]}")
        title_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        title_lbl.setWordWrap(True)
        lay.addWidget(title_lbl)

        desc_lbl = QLabel(result.get("desc","")[:30])
        desc_lbl.setFont(QFont("Segoe UI", 7))
        desc_lbl.setStyleSheet(f"color:{C_MUTED};")
        lay.addWidget(desc_lbl)

        # async thumb load
        purl = result.get("preview_url","")
        if purl:
            run_in_thread(self._load_thumb, purl)

    def _load_thumb(self, url: str):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"BigTruckEditor/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
            pm = QPixmap()
            pm.loadFromData(data)
            if not pm.isNull():
                pm = pm.scaled(162, 90, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                QTimer.singleShot(0, lambda: self._thumb_label.setPixmap(pm))
        except Exception:
            pass

    def mouseDoubleClickEvent(self, e):
        self.download_clicked.emit(self._result)

    def mousePressEvent(self, e):
        self.setStyleSheet(f"background:{C_ACCENT2};")

    def mouseReleaseEvent(self, e):
        self.setStyleSheet("")


# ──────────────────────────────────────────────────────────────────────────────
#  EXPORT ENGINE
# ──────────────────────────────────────────────────────────────────────────────
class ExportWorker(QThread):
    progress = pyqtSignal(int, str)   # (percent, message)
    finished = pyqtSignal(str)        # output path
    error    = pyqtSignal(str)

    def __init__(self, project: Project, out_path: str, parent=None):
        super().__init__(parent)
        self.project  = project
        self.out_path = out_path

    def run(self):
        if not MOVIEPY_OK:
            self.error.emit(
                "MoviePy is not installed.\n"
                "Run INSTALL.bat or: pip install moviepy imageio[ffmpeg]"
            )
            return
        try:
            self._export()
        except Exception as ex:
            import traceback
            self.error.emit(f"Export failed:\n{traceback.format_exc()}")

    def _export(self):
        p  = self.project
        self.progress.emit(5, "Building clip list…")
        clips_moviepy = []

        # Sort clips by track (lower = behind)
        sorted_clips = sorted(p.clips, key=lambda c: (c.track, c.start_time))
        total = len(sorted_clips)

        for idx, clip in enumerate(sorted_clips):
            pct = 5 + int(80 * idx / max(total, 1))
            self.progress.emit(pct, f"Processing clip {idx+1}/{total}: {clip.label or clip.clip_type}")

            if clip.clip_type == "video" and clip.source_path and Path(clip.source_path).exists():
                vc = VideoFileClip(clip.source_path)
                tin  = clip.trim_in
                tout = vc.duration - clip.trim_out if clip.trim_out > 0 else vc.duration
                vc   = vc.subclip(tin, min(tout, vc.duration))
                vc   = vc.set_start(clip.start_time).set_duration(clip.duration)
                if not clip.track_muted(p):
                    vc = vc.volumex(clip.volume)
                clips_moviepy.append(vc)

            elif clip.clip_type == "image" and clip.source_path and Path(clip.source_path).exists():
                ic = ImageClip(clip.source_path, duration=clip.duration)
                ic = ic.set_start(clip.start_time)
                ic = ic.resize(height=p.height)
                clips_moviepy.append(ic)

            elif clip.clip_type in ("text","overlay"):
                tc = self._make_text_clip(clip)
                if tc:
                    clips_moviepy.append(tc)

            elif clip.clip_type == "audio" and clip.source_path and Path(clip.source_path).exists():
                ac = AudioFileClip(clip.source_path)
                ac = ac.set_start(clip.start_time).set_duration(min(clip.duration, ac.duration))
                ac = ac.volumex(clip.volume)
                clips_moviepy.append(ac)

        self.progress.emit(88, "Compositing…")

        bg = ColorClip(size=(p.width, p.height), color=(10,10,26), duration=p.duration)
        video_clips = [bg] + [c for c in clips_moviepy if hasattr(c, 'size')]
        audio_clips = [c for c in clips_moviepy if not hasattr(c, 'size')]

        final = CompositeVideoClip(video_clips, size=(p.width, p.height))
        final = final.set_duration(p.duration)

        if audio_clips:
            final = final.set_audio(CompositeAudioClip(audio_clips))

        self.progress.emit(92, "Rendering to MP4…")
        final.write_videofile(
            self.out_path,
            fps=p.fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None,
        )
        final.close()
        self.progress.emit(100, "Export complete!")
        self.finished.emit(self.out_path)

    def _make_text_clip(self, clip: Clip):
        txt = clip.text or clip.overlay_data
        if not txt:
            return None
        try:
            tc = TextClip(
                txt,
                fontsize=clip.font_size,
                color=clip.font_color,
                font="Arial-Bold",
                method="label",
            )
            tc = tc.set_start(clip.start_time).set_duration(clip.duration)
            px = int(clip.pos_x * CANVAS_W / 100)
            py = int(clip.pos_y * CANVAS_H / 100)
            tc = tc.set_position((px, py))
            return tc
        except Exception:
            return None


# helper on Clip to check mute
def _clip_track_muted(self, project: Project) -> bool:
    if self.track < len(project.tracks):
        return project.tracks[self.track].muted
    return False

Clip.track_muted = _clip_track_muted


class ExportDialog(QDialog):
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Episode to MP4")
        self.setMinimumWidth(440)
        self.project = project
        self._worker: Optional[ExportWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        # output path
        path_lay = QHBoxLayout()
        self.path_edit = QLineEdit(str(EXPORTS_DIR / (self.project.name + ".mp4")))
        path_lay.addWidget(self.path_edit, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        path_lay.addWidget(browse_btn)
        lay.addLayout(path_lay)

        # settings
        gb = QGroupBox("Settings")
        gl = QGridLayout(gb)
        gl.addWidget(QLabel("Resolution:"), 0, 0)
        self.res_combo = QComboBox()
        self.res_combo.addItems(["1920×1080 (Full HD)","1280×720 (HD)","3840×2160 (4K)"])
        gl.addWidget(self.res_combo, 0, 1)
        gl.addWidget(QLabel("FPS:"), 1, 0)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24","30","60"])
        self.fps_combo.setCurrentText(str(self.project.fps))
        gl.addWidget(self.fps_combo, 1, 1)
        lay.addWidget(gb)

        # moviepy warning
        if not MOVIEPY_OK:
            warn = QLabel("⚠️ MoviePy not installed — run INSTALL.bat first!")
            warn.setStyleSheet("color:#ef5350;font-weight:bold;")
            lay.addWidget(warn)

        # progress
        self.prog = QProgressBar()
        self.prog.setVisible(False)
        lay.addWidget(self.prog)
        self.status_lbl = QLabel("")
        lay.addWidget(self.status_lbl)

        # buttons
        btn_lay = QHBoxLayout()
        self.export_btn = QPushButton("🎬 Export MP4")
        self.export_btn.setObjectName("accent")
        self.export_btn.clicked.connect(self._start_export)
        btn_lay.addWidget(self.export_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        btn_lay.addWidget(cancel_btn)
        lay.addLayout(btn_lay)

    def _browse(self):
        f, _ = QFileDialog.getSaveFileName(
            self, "Save MP4", str(EXPORTS_DIR / (self.project.name+".mp4")),
            "MP4 Video (*.mp4)"
        )
        if f:
            self.path_edit.setText(f)

    def _start_export(self):
        out_path = self.path_edit.text().strip()
        if not out_path:
            QMessageBox.warning(self, "Error", "Choose an output path.")
            return

        res_map = {"1920×1080 (Full HD)":(1920,1080),
                   "1280×720 (HD)":(1280,720),
                   "3840×2160 (4K)":(3840,2160)}
        w, h = res_map.get(self.res_combo.currentText(), (1920,1080))
        self.project.width  = w
        self.project.height = h
        self.project.fps    = int(self.fps_combo.currentText())

        self.export_btn.setEnabled(False)
        self.prog.setVisible(True)
        self.prog.setValue(0)

        self._worker = ExportWorker(self.project, out_path, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.prog.setValue(pct)
        self.status_lbl.setText(msg)

    def _on_done(self, path: str):
        self.export_btn.setEnabled(True)
        self.prog.setValue(100)
        self.status_lbl.setText(f"Saved to: {path}")
        QMessageBox.information(self, "Export Complete",
            f"Your episode has been exported!\n\n{path}")

    def _on_error(self, msg: str):
        self.export_btn.setEnabled(True)
        self.prog.setValue(0)
        self.status_lbl.setText("Export failed.")
        QMessageBox.critical(self, "Export Error", msg)


# ──────────────────────────────────────────────────────────────────────────────
#  EPISODE TEMPLATES  (Big Truck Adventures)
# ──────────────────────────────────────────────────────────────────────────────
def _char_img(name: str) -> str:
    p = ASSETS_ROOT / "Characters" / f"{name}.png"
    return str(p) if p.exists() else ""

def _truck_img(name: str) -> str:
    p = ASSETS_ROOT / "Trucks" / f"{name}.png"
    return str(p) if p.exists() else ""

def _banner_img(name: str) -> str:
    p = ASSETS_ROOT / "Banner" / f"{name}.png"
    return str(p) if p.exists() else ""


EPISODE_TEMPLATES: Dict[str, dict] = {

    "E01 – Jensen's First Day Countdown": {
        "name": "E01 – Jensen's First Day Countdown",
        "duration": 420.0,
        "description": "Numbers 1–10, Letters P & J, Colors red/blue/yellow/green",
        "clips": [
            # INTRO (0–30s)
            {"track":0,"start_time":0,"duration":30,"clip_type":"overlay","overlay_type":"title_card",
             "overlay_data":"Big Truck Adventures","label":"Intro Title","color":C_CLIP_OVLY},
            {"track":4,"start_time":2,"duration":8,"clip_type":"text","text":"Big Truck Adventures",
             "animation":"bounce","font_size":72,"font_color":C_ACCENT,"pos_x":50,"pos_y":40,"label":"Show Title"},
            {"track":4,"start_time":10,"duration":5,"clip_type":"text","text":"Episode 1: Jensen's First Day Countdown",
             "animation":"fade_in","font_size":36,"font_color":"#ffffff","pos_x":50,"pos_y":60,"label":"Ep Title"},
            # Characters
            {"track":2,"start_time":5,"duration":25,"clip_type":"image","source_path":_char_img("Jensen"),
             "label":"Jensen","color":C_CLIP_IMG},
            {"track":2,"start_time":15,"duration":15,"clip_type":"image","source_path":_char_img("Bentley"),
             "label":"Bentley","color":C_CLIP_IMG},
            # Scene 2 – Kitchen (30–75s)
            {"track":4,"start_time":35,"duration":6,"clip_type":"text","text":"Only TEN more days!",
             "animation":"pop","font_size":64,"font_color":C_ACCENT,"pos_x":50,"pos_y":70,"label":"TEN caption"},
            {"track":3,"start_time":38,"duration":8,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"10","label":"Number 10 Card","color":C_CLIP_OVLY},
            # Scene 3 – Truck Yard
            {"track":2,"start_time":75,"duration":40,"clip_type":"image","source_path":_truck_img("Charlie"),
             "label":"Charlie Crane","color":C_CLIP_IMG},
            {"track":2,"start_time":75,"duration":40,"clip_type":"image","source_path":_truck_img("Max"),
             "label":"Max Dump Truck","color":C_CLIP_IMG},
            {"track":4,"start_time":80,"duration":6,"clip_type":"text","text":"Count with us: 1…2…3…",
             "animation":"slide_right","font_size":54,"font_color":"#ffffff","pos_x":50,"pos_y":80,"label":"Count CTA"},
            # Scene 4 – Letters
            {"track":3,"start_time":120,"duration":8,"clip_type":"overlay","overlay_type":"letter_card",
             "overlay_data":"P","label":"Letter P Card","color":C_CLIP_OVLY},
            {"track":4,"start_time":120,"duration":5,"clip_type":"text","text":"P is for Pencil!",
             "animation":"bounce","font_size":60,"font_color":C_ACCENT,"pos_x":50,"pos_y":75,"label":"P word"},
            {"track":3,"start_time":150,"duration":8,"clip_type":"overlay","overlay_type":"letter_card",
             "overlay_data":"J","label":"Letter J Card","color":C_CLIP_OVLY},
            {"track":4,"start_time":150,"duration":5,"clip_type":"text","text":"J is for Jensen!",
             "animation":"bounce","font_size":60,"font_color":C_ACCENT2,"pos_x":50,"pos_y":75,"label":"J word"},
            # Colors
            {"track":3,"start_time":200,"duration":6,"clip_type":"overlay","overlay_type":"color_card",
             "overlay_data":"red","label":"Red Card","color":C_CLIP_OVLY},
            {"track":3,"start_time":208,"duration":6,"clip_type":"overlay","overlay_type":"color_card",
             "overlay_data":"blue","label":"Blue Card","color":C_CLIP_OVLY},
            {"track":3,"start_time":216,"duration":6,"clip_type":"overlay","overlay_type":"color_card",
             "overlay_data":"yellow","label":"Yellow Card","color":C_CLIP_OVLY},
            {"track":3,"start_time":224,"duration":6,"clip_type":"overlay","overlay_type":"color_card",
             "overlay_data":"green","label":"Green Card","color":C_CLIP_OVLY},
            # Count-down review
            {"track":4,"start_time":315,"duration":4,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"1","label":"Count 1","color":C_CLIP_OVLY},
            {"track":4,"start_time":319,"duration":3,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"2","label":"Count 2","color":C_CLIP_OVLY},
            {"track":4,"start_time":322,"duration":3,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"3","label":"Count 3","color":C_CLIP_OVLY},
            {"track":4,"start_time":325,"duration":3,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"4","label":"Count 4","color":C_CLIP_OVLY},
            {"track":4,"start_time":328,"duration":3,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"5","label":"Count 5","color":C_CLIP_OVLY},
            {"track":4,"start_time":331,"duration":3,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"6","label":"Count 6","color":C_CLIP_OVLY},
            {"track":4,"start_time":334,"duration":3,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"7","label":"Count 7","color":C_CLIP_OVLY},
            {"track":4,"start_time":337,"duration":3,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"8","label":"Count 8","color":C_CLIP_OVLY},
            {"track":4,"start_time":340,"duration":3,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"9","label":"Count 9","color":C_CLIP_OVLY},
            {"track":4,"start_time":343,"duration":4,"clip_type":"overlay","overlay_type":"number_card",
             "overlay_data":"10","label":"Count 10","color":C_CLIP_OVLY},
            # Outro
            {"track":4,"start_time":390,"duration":10,"clip_type":"text","text":"See you next time!",
             "animation":"rainbow","font_size":80,"font_color":"#ffffff","pos_x":50,"pos_y":50,"label":"Outro"},
            {"track":3,"start_time":400,"duration":20,"clip_type":"overlay","overlay_type":"title_card",
             "overlay_data":"Subscribe for more Big Truck Adventures!","label":"Subscribe CTA","color":C_CLIP_OVLY},
        ],
    },

    "E02 – The Alphabet Truck Parade": {
        "name": "E02 – The Alphabet Truck Parade",
        "duration": 420.0,
        "description": "Full alphabet A–Z, letter sounds, alphabetical ordering",
        "clips": [
            {"track":0,"start_time":0,"duration":30,"clip_type":"overlay","overlay_type":"title_card",
             "overlay_data":"Big Truck Adventures","label":"Intro Title","color":C_CLIP_OVLY},
            {"track":4,"start_time":2,"duration":8,"clip_type":"text","text":"The Alphabet Truck Parade!",
             "animation":"bounce","font_size":64,"font_color":C_ACCENT,"pos_x":50,"pos_y":40,"label":"Title"},
            # Characters
            {"track":2,"start_time":5,"duration":25,"clip_type":"image","source_path":_char_img("Jensen"),
             "label":"Jensen","color":C_CLIP_IMG},
            {"track":2,"start_time":10,"duration":20,"clip_type":"image","source_path":_char_img("Bentley"),
             "label":"Bentley","color":C_CLIP_IMG},
            {"track":2,"start_time":10,"duration":20,"clip_type":"image","source_path":_char_img("Russell"),
             "label":"Russell","color":C_CLIP_IMG},
            # Trucks
            {"track":1,"start_time":30,"duration":60,"clip_type":"image","source_path":_truck_img("Charlie"),
             "label":"Charlie Crane","color":C_CLIP_IMG},
            # Letter cards A–Z (every 10s)
            *[
                {"track":3,"start_time":75 + i*12,"duration":8,
                 "clip_type":"overlay","overlay_type":"letter_card",
                 "overlay_data":chr(ord('A')+i),"label":f"Letter {chr(ord('A')+i)}","color":C_CLIP_OVLY}
                for i in range(26)
            ],
            # Parade caption
            {"track":4,"start_time":75,"duration":10,"clip_type":"text",
             "text":"26 Alphabet Trucks – A to Z!",
             "animation":"slide_right","font_size":54,"font_color":C_ACCENT2,"pos_x":50,"pos_y":80,"label":"Parade"},
            # Emery saves the day
            {"track":2,"start_time":300,"duration":30,"clip_type":"image","source_path":_char_img("Emery"),
             "label":"Emery finds Z!","color":C_CLIP_IMG},
            {"track":4,"start_time":305,"duration":8,"clip_type":"text","text":"Emery found the Z Truck!",
             "animation":"pop","font_size":60,"font_color":"#ffffff","pos_x":50,"pos_y":70,"label":"Z found"},
            {"track":3,"start_time":305,"duration":6,"clip_type":"overlay","overlay_type":"letter_card",
             "overlay_data":"Z","label":"Letter Z","color":C_CLIP_OVLY},
            # Outro
            {"track":4,"start_time":390,"duration":10,"clip_type":"text",
             "text":"Can YOU sing the alphabet?",
             "animation":"rainbow","font_size":60,"font_color":"#ffffff","pos_x":50,"pos_y":50,"label":"CTA"},
            {"track":3,"start_time":400,"duration":20,"clip_type":"overlay","overlay_type":"title_card",
             "overlay_data":"Big Truck Adventures – Subscribe!","label":"Outro","color":C_CLIP_OVLY},
        ],
    },

    "E03 – Count the Construction Cones": {
        "name": "E03 – Count the Construction Cones",
        "duration": 420.0,
        "description": "Counting 1–20, shapes, construction vocabulary",
        "clips": [
            {"track":0,"start_time":0,"duration":30,"clip_type":"overlay","overlay_type":"title_card",
             "overlay_data":"Big Truck Adventures","label":"Intro","color":C_CLIP_OVLY},
            {"track":4,"start_time":5,"duration":8,"clip_type":"text","text":"Count the Construction Cones!",
             "animation":"bounce","font_size":60,"font_color":C_ACCENT,"pos_x":50,"pos_y":40,"label":"Title"},
            {"track":2,"start_time":10,"duration":30,"clip_type":"image","source_path":_char_img("Russell"),
             "label":"Russell","color":C_CLIP_IMG},
            {"track":1,"start_time":30,"duration":60,"clip_type":"image","source_path":_truck_img("Remi"),
             "label":"Remi Road Roller","color":C_CLIP_IMG},
            *[
                {"track":3,"start_time":75 + i*14,"duration":10,
                 "clip_type":"overlay","overlay_type":"number_card",
                 "overlay_data":str(i+1),"label":f"Number {i+1}","color":C_CLIP_OVLY}
                for i in range(20)
            ],
            {"track":4,"start_time":390,"duration":10,"clip_type":"text","text":"How many cones did we count?",
             "animation":"pop","font_size":54,"font_color":C_ACCENT,"pos_x":50,"pos_y":60,"label":"CTA"},
        ],
    },

    "Blank Episode": {
        "name": "New Big Truck Adventure",
        "duration": 420.0,
        "description": "Start from scratch",
        "clips": [
            {"track":0,"start_time":0,"duration":30,"clip_type":"overlay","overlay_type":"title_card",
             "overlay_data":"Big Truck Adventures","label":"Intro Title","color":C_CLIP_OVLY},
            {"track":4,"start_time":2,"duration":8,"clip_type":"text","text":"Big Truck Adventures",
             "animation":"bounce","font_size":72,"font_color":C_ACCENT,"pos_x":50,"pos_y":40,"label":"Show Title"},
            {"track":4,"start_time":390,"duration":10,"clip_type":"text","text":"See you next time!",
             "animation":"rainbow","font_size":80,"font_color":"#ffffff","pos_x":50,"pos_y":50,"label":"Outro"},
        ],
    },
}


def build_project_from_template(template_key: str) -> Project:
    t = EPISODE_TEMPLATES[template_key]
    p = Project(name=t["name"], duration=t["duration"])
    p.default_tracks()
    for clip_dict in t["clips"]:
        cd = {
            "track":       clip_dict.get("track", 0),
            "start_time":  clip_dict.get("start_time", 0.0),
            "duration":    clip_dict.get("duration", 5.0),
            "clip_type":   clip_dict.get("clip_type","text"),
            "source_path": clip_dict.get("source_path",""),
            "label":       clip_dict.get("label",""),
            "color":       clip_dict.get("color", C_CLIP_TXT),
            "text":        clip_dict.get("text",""),
            "animation":   clip_dict.get("animation","none"),
            "font_size":   clip_dict.get("font_size", 72),
            "font_color":  clip_dict.get("font_color","#ffffff"),
            "overlay_type":clip_dict.get("overlay_type",""),
            "overlay_data":clip_dict.get("overlay_data",""),
            "pos_x":       clip_dict.get("pos_x", 50),
            "pos_y":       clip_dict.get("pos_y", 80),
        }
        p.clips.append(Clip(**cd))
    return p


# ──────────────────────────────────────────────────────────────────────────────
#  TTS NARRATION
# ──────────────────────────────────────────────────────────────────────────────
class TTSDialog(QDialog):
    """Generate a narrator voice-over clip using gTTS."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔊 Generate Narration (Text-to-Speech)")
        self.setMinimumWidth(420)
        self._out_path: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Type the narration text:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "e.g.\nJensen said: I learned that for kindergarten!\n"
            "P makes the 'puh' sound — P for Pencil!"
        )
        self.text_edit.setMinimumHeight(100)
        lay.addWidget(self.text_edit)

        row = QHBoxLayout()
        row.addWidget(QLabel("Voice:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["en (English)","en-us (US)","en-gb (British)","en-au (Australian)"])
        row.addWidget(self.lang_combo)
        row.addWidget(QLabel("Slow:"))
        self.slow_chk = QCheckBox()
        row.addWidget(self.slow_chk)
        lay.addLayout(row)

        if not GTTS_OK:
            warn = QLabel("⚠️ gTTS not installed — run INSTALL.bat first!")
            warn.setStyleSheet("color:#ef5350;font-weight:bold;")
            lay.addWidget(warn)

        self.status_lbl = QLabel("")
        lay.addWidget(self.status_lbl)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._generate)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _generate(self):
        if not GTTS_OK:
            QMessageBox.warning(self, "Not Installed", "Install gTTS: pip install gTTS")
            return
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty", "Enter some text first.")
            return
        lang_raw = self.lang_combo.currentText()
        lang     = lang_raw.split(" ")[0].split("-")[0]   # "en"
        tld      = "com" if "us" in lang_raw else ("co.uk" if "gb" in lang_raw else
                   "com.au" if "au" in lang_raw else "com")
        slow     = self.slow_chk.isChecked()
        out_name = f"narr_{random.randint(10000,99999)}.mp3"
        out_path = str(CACHE_DIR / out_name)
        self.status_lbl.setText("Generating…")
        try:
            tts = gTTS(text=text, lang=lang, tld=tld, slow=slow)
            tts.save(out_path)
            self._out_path = out_path
            self.status_lbl.setText(f"Saved: {out_name}")
            self.accept()
        except Exception as ex:
            QMessageBox.critical(self, "TTS Error", str(ex))

    def out_path(self) -> Optional[str]:
        return self._out_path


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ──────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1280, 800)
        self.resize(1600, 950)

        self._project: Optional[Project] = None
        self._modified = False
        self._media_dialog: Optional[MediaSearchDialog] = None

        self._setup_menus()
        self._setup_toolbar()
        self._setup_ui()
        self._setup_status_bar()

        # new blank project on start
        self._new_project_from_template("Blank Episode")

    # ── menus ─────────────────────────────────────────────────────────────────
    def _setup_menus(self):
        mb = self.menuBar()

        # File
        fm = mb.addMenu("File")
        self._act(fm, "New Project…",      self._new_project,    "Ctrl+N")
        self._act(fm, "Open Project…",     self._open_project,   "Ctrl+O")
        self._act(fm, "Save Project",      self._save_project,   "Ctrl+S")
        self._act(fm, "Save As…",          self._save_project_as,"Ctrl+Shift+S")
        fm.addSeparator()
        self._act(fm, "Import Media…",     self._import_media)
        self._act(fm, "Search Free Media…",self._open_media_search)
        fm.addSeparator()
        self._act(fm, "Export to MP4…",    self._export_mp4,     "Ctrl+E")
        fm.addSeparator()
        self._act(fm, "Exit", self.close, "Alt+F4")

        # Edit
        em = mb.addMenu("Edit")
        self._act(em, "Delete Selected Clip", self._delete_clip, "Delete")
        self._act(em, "Split Clip at Playhead", self._split_clip, "Ctrl+K")
        em.addSeparator()
        self._act(em, "Add Track", self._add_track)

        # Insert
        im = mb.addMenu("Insert")
        self._act(im, "Text Clip…",        self._insert_text_clip)
        self._act(im, "Letter Card…",      self._insert_letter_card)
        self._act(im, "Number Card…",      self._insert_number_card)
        self._act(im, "Color Card…",       self._insert_color_card)
        self._act(im, "Title Card…",       self._insert_title_card)
        self._act(im, "Caption Bar…",      self._insert_caption_bar)
        im.addSeparator()
        self._act(im, "Generate Narration (TTS)…", self._insert_narration)

        # Templates
        tm = mb.addMenu("Templates")
        for key in EPISODE_TEMPLATES:
            self._act(tm, key, lambda checked=False, k=key: self._load_template(k))

        # View
        vm = mb.addMenu("View")
        self._act(vm, "Zoom In",    lambda: self._zoom(1.2), "Ctrl+=")
        self._act(vm, "Zoom Out",   lambda: self._zoom(0.8), "Ctrl+-")
        self._act(vm, "Fit to Window", lambda: self._zoom_fit(), "Ctrl+0")

        # Help
        hm = mb.addMenu("Help")
        self._act(hm, "About", self._about)
        self._act(hm, "Keyboard Shortcuts", self._show_shortcuts)

    def _act(self, menu, label: str, slot, shortcut: str = ""):
        a = QAction(label, self)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        menu.addAction(a)
        return a

    # ── toolbar ───────────────────────────────────────────────────────────────
    def _setup_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))

        def tbtn(label: str, slot, tip: str = ""):
            btn = QPushButton(label)
            btn.setToolTip(tip or label)
            btn.setFixedHeight(30)
            btn.clicked.connect(slot)
            tb.addWidget(btn)
            return btn

        tbtn("📄 New",       self._new_project,      "New project (Ctrl+N)")
        tbtn("📂 Open",      self._open_project,     "Open project (Ctrl+O)")
        tbtn("💾 Save",      self._save_project,     "Save project (Ctrl+S)")
        tb.addSeparator()
        tbtn("🔍 Free Media",self._open_media_search,"Search Pexels/Pixabay/FMA")
        tbtn("+ Import",     self._import_media,     "Import media files")
        tb.addSeparator()
        tbtn("✂️ Split",     self._split_clip,       "Split clip at playhead (Ctrl+K)")
        tbtn("🗑️ Delete",   self._delete_clip,      "Delete selected clip (Del)")
        tb.addSeparator()

        # Episode name
        tb.addWidget(QLabel("  Episode: "))
        self.ep_name_edit = QLineEdit("New Big Truck Adventure")
        self.ep_name_edit.setFixedWidth(240)
        self.ep_name_edit.textChanged.connect(lambda v: self._project and setattr(self._project,"name",v))
        tb.addWidget(self.ep_name_edit)
        tb.addSeparator()

        export_btn = QPushButton("🎬 Export MP4")
        export_btn.setObjectName("accent")
        export_btn.setFixedHeight(30)
        export_btn.clicked.connect(self._export_mp4)
        tb.addWidget(export_btn)

    # ── central UI ────────────────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0,0,0,0)
        root_lay.setSpacing(0)

        # main H-splitter: [asset panel | preview+props] | timeline below
        main_vsplit = QSplitter(Qt.Orientation.Vertical)
        root_lay.addWidget(main_vsplit, 1)

        # top section
        top_hsplit = QSplitter(Qt.Orientation.Horizontal)
        main_vsplit.addWidget(top_hsplit)

        # left: asset panel
        self.asset_panel = AssetPanel()
        self.asset_panel.asset_double_clicked.connect(self._on_asset_double_clicked)
        top_hsplit.addWidget(self.asset_panel)

        # centre: preview
        self.preview = PreviewWindow()
        top_hsplit.addWidget(self.preview)

        # right: properties
        self.props = PropertiesPanel()
        self.props.clip_changed.connect(self._on_clip_changed)
        top_hsplit.addWidget(self.props)

        top_hsplit.setStretchFactor(0, 1)
        top_hsplit.setStretchFactor(1, 4)
        top_hsplit.setStretchFactor(2, 1)
        top_hsplit.setSizes([220, 900, 260])

        # bottom: timeline
        self.timeline = TimelineWidget()
        self.timeline.selection_changed.connect(self._on_selection_changed)
        self.timeline.playhead_changed.connect(self._on_playhead_changed)
        self.timeline.project_changed.connect(self._on_project_changed)
        main_vsplit.addWidget(self.timeline)

        main_vsplit.setStretchFactor(0, 3)
        main_vsplit.setStretchFactor(1, 2)
        main_vsplit.setSizes([580, 370])

    def _setup_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_lbl = QLabel("Ready – Big Truck Adventures Video Editor")
        sb.addWidget(self._status_lbl, 1)
        self._moviepy_lbl = QLabel("MoviePy ✓" if MOVIEPY_OK else "MoviePy ✗ (run INSTALL.bat)")
        self._moviepy_lbl.setStyleSheet(f"color:{'#66bb6a' if MOVIEPY_OK else '#ef5350'};")
        sb.addPermanentWidget(self._moviepy_lbl)
        self._gtts_lbl = QLabel("gTTS ✓" if GTTS_OK else "gTTS ✗")
        self._gtts_lbl.setStyleSheet(f"color:{'#66bb6a' if GTTS_OK else C_MUTED};")
        sb.addPermanentWidget(self._gtts_lbl)

    # ── project management ────────────────────────────────────────────────────
    def _load_project(self, project: Project):
        self._project = project
        self._modified = False
        self.ep_name_edit.setText(project.name)
        self.setWindowTitle(f"{project.name} – {APP_NAME}")
        self.timeline.load_project(project)
        self.preview.load_project(project)
        self.props.load_clip(None)
        self._status("Project loaded: " + project.name)
        get_db().touch_project(project.name, project.path)

    def _new_project(self):
        if self._modified:
            r = QMessageBox.question(self,"Unsaved Changes",
                "You have unsaved changes. Create new project anyway?")
            if r != QMessageBox.StandardButton.Yes:
                return
        dlg = _TemplateChooserDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._new_project_from_template(dlg.chosen)

    def _new_project_from_template(self, key: str):
        p = build_project_from_template(key)
        self._load_project(p)

    def _open_project(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Open Project", str(PROJECTS_DIR), "BTA Project (*.btap)"
        )
        if f:
            try:
                self._load_project(Project.load(f))
            except Exception as ex:
                QMessageBox.critical(self, "Error", str(ex))

    def _save_project(self):
        if not self._project:
            return
        if self._project.path:
            self._project.save(self._project.path)
            self._modified = False
            self._status(f"Saved: {self._project.path}")
        else:
            self._save_project_as()

    def _save_project_as(self):
        if not self._project:
            return
        f, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", str(PROJECTS_DIR / (self._project.name+".btap")),
            "BTA Project (*.btap)"
        )
        if f:
            self._project.save(f)
            self._modified = False
            self._status(f"Saved: {f}")
            get_db().touch_project(self._project.name, f)

    def _load_template(self, key: str):
        if self._modified:
            r = QMessageBox.question(self,"Unsaved Changes",
                "You have unsaved changes. Load template anyway?")
            if r != QMessageBox.StandardButton.Yes:
                return
        self._new_project_from_template(key)

    # ── media ─────────────────────────────────────────────────────────────────
    def _import_media(self):
        self.asset_panel._import_media()

    def _open_media_search(self):
        if not self._media_dialog:
            self._media_dialog = MediaSearchDialog(self)
            self._media_dialog.file_downloaded.connect(self._on_media_downloaded)
        self._media_dialog.show()
        self._media_dialog.raise_()

    def _on_media_downloaded(self, path: str, kind: str):
        col = C_CLIP_VID if kind=="video" else C_CLIP_AUD if kind=="audio" else C_CLIP_IMG
        asset = {"kind":kind,"name":Path(path).stem,"path":path,"clip_type":kind,"color":col}
        get_db().add_asset(kind, Path(path).stem, path)
        self.asset_panel.refresh_media()
        if self._project:
            self.timeline.canvas.add_clip_from_asset(asset)
        self._status(f"Added: {Path(path).name}")

    # ── clip operations ───────────────────────────────────────────────────────
    def _on_asset_double_clicked(self, asset: dict):
        if self._project:
            # add at end of existing clips on appropriate track
            ct    = asset.get("clip_type", asset.get("kind","image"))
            start = max((c.end_time for c in self._project.clips), default=0.0)
            track = 4 if ct in ("text","overlay") else 2 if ct=="image" else \
                    5 if ct=="audio" else 0
            self.timeline.canvas.add_clip_from_asset(asset, track_idx=track, start=start)
            self._status(f"Added {asset.get('name','?')} to timeline")

    def _on_selection_changed(self, clip: Optional[Clip]):
        self.props.load_clip(clip)
        if clip:
            self._status(f"Selected: {clip.label or clip.clip_type}")
        else:
            self._status("Ready")

    def _on_playhead_changed(self, t: float):
        self.preview.set_playhead(t)

    def _on_project_changed(self):
        self._modified = True
        self.preview._render_frame(self.preview._playhead)

    def _on_clip_changed(self):
        self._modified = True
        self.timeline.canvas.update()
        self.preview._render_frame(self.preview._playhead)

    def _delete_clip(self):
        self.timeline.canvas.delete_selected()

    def _split_clip(self):
        self.timeline.canvas.split_at_playhead()

    def _add_track(self):
        if not self._project:
            return
        name, ok = QInputDialog.getText(self, "Add Track", "Track name:")
        if ok and name:
            self._project.tracks.append(Track(name=name, kind="video"))
            self.timeline.canvas._rebuild_items()
            self.timeline.canvas.update()

    # ── insert overlays / text ────────────────────────────────────────────────
    def _insert_text_clip(self):
        if not self._project:
            return
        text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
        if ok and text:
            asset = {"kind":"text","clip_type":"text","name":text,
                     "text":text,"animation":"bounce","color":C_CLIP_TXT}
            start = max((c.end_time for c in self._project.clips), default=0.0)
            self.timeline.canvas.add_clip_from_asset(asset, track_idx=4, start=start)

    def _insert_letter_card(self):
        if not self._project:
            return
        letter, ok = QInputDialog.getText(self, "Letter Card", "Enter a letter (e.g. A):")
        if ok and letter.strip():
            asset = {"kind":"overlay","clip_type":"overlay","name":f"Letter {letter.upper()}",
                     "overlay_type":"letter_card","overlay_data":letter.upper(),"color":C_CLIP_OVLY}
            start = max((c.end_time for c in self._project.clips if c.track==3), default=0.0)
            self.timeline.canvas.add_clip_from_asset(asset, track_idx=3, start=start)

    def _insert_number_card(self):
        if not self._project:
            return
        num, ok = QInputDialog.getText(self, "Number Card", "Enter a number (e.g. 5):")
        if ok and num.strip():
            asset = {"kind":"overlay","clip_type":"overlay","name":f"Number {num}",
                     "overlay_type":"number_card","overlay_data":num,"color":C_CLIP_OVLY}
            start = max((c.end_time for c in self._project.clips if c.track==3), default=0.0)
            self.timeline.canvas.add_clip_from_asset(asset, track_idx=3, start=start)

    def _insert_color_card(self):
        if not self._project:
            return
        colors = ["red","blue","yellow","green","orange","purple","pink","white","black","brown"]
        color, ok = QInputDialog.getItem(self, "Color Card", "Choose a color:", colors, 0, False)
        if ok:
            asset = {"kind":"overlay","clip_type":"overlay","name":f"Color: {color}",
                     "overlay_type":"color_card","overlay_data":color,"color":C_CLIP_OVLY}
            start = max((c.end_time for c in self._project.clips if c.track==3), default=0.0)
            self.timeline.canvas.add_clip_from_asset(asset, track_idx=3, start=start)

    def _insert_title_card(self):
        if not self._project:
            return
        text, ok = QInputDialog.getText(self, "Title Card", "Enter title:",
                                        text="Big Truck Adventures")
        if ok and text:
            asset = {"kind":"overlay","clip_type":"overlay","name":f"Title: {text}",
                     "overlay_type":"title_card","overlay_data":text,"color":C_CLIP_OVLY}
            start = max((c.end_time for c in self._project.clips if c.track==3), default=0.0)
            self.timeline.canvas.add_clip_from_asset(asset, track_idx=3, start=start)

    def _insert_caption_bar(self):
        if not self._project:
            return
        text, ok = QInputDialog.getText(self, "Caption Bar", "Enter caption text:")
        if ok and text:
            asset = {"kind":"overlay","clip_type":"overlay","name":f"Caption: {text[:20]}",
                     "overlay_type":"caption_bar","overlay_data":text,"color":C_CLIP_OVLY}
            start = max((c.end_time for c in self._project.clips if c.track==4), default=0.0)
            self.timeline.canvas.add_clip_from_asset(asset, track_idx=4, start=start)

    def _insert_narration(self):
        dlg = TTSDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.out_path():
            path = dlg.out_path()
            asset = {"kind":"audio","clip_type":"audio","name":"Narration",
                     "path":path,"color":C_CLIP_AUD}
            start = max((c.end_time for c in self._project.clips if c.track==6), default=0.0)
            self.timeline.canvas.add_clip_from_asset(asset, track_idx=6, start=start)
            self._status(f"Added narration: {Path(path).name}")

    # ── export ────────────────────────────────────────────────────────────────
    def _export_mp4(self):
        if not self._project:
            QMessageBox.warning(self, "No Project", "Create a project first.")
            return
        dlg = ExportDialog(self._project, self)
        dlg.exec()

    # ── zoom ──────────────────────────────────────────────────────────────────
    def _zoom(self, factor: float):
        z = self.timeline.canvas._zoom * factor
        self.timeline.canvas.set_zoom(z)
        v = int(z * 100)
        self.timeline.zoom_slider.blockSignals(True)
        self.timeline.zoom_slider.setValue(max(1, min(200, v)))
        self.timeline.zoom_slider.blockSignals(False)

    def _zoom_fit(self):
        self.timeline.zoom_slider.setValue(100)

    # ── misc ──────────────────────────────────────────────────────────────────
    def _status(self, msg: str):
        self._status_lbl.setText(msg)

    def _about(self):
        QMessageBox.about(self, "About", f"""
<b>Big Truck Adventures – Video Editor</b><br>
Version {APP_VERSION}<br><br>
Built for John Kirshy – 100% free, no watermarks, no subscriptions.<br><br>
<b>Characters:</b> Jensen, Bentley, Russell, Emery<br>
<b>Trucks:</b> Max, Charlie, Remi, Bella<br><br>
Tech: PyQt6 · MoviePy · Pillow · gTTS · SQLite<br>
Free media: Pexels · Pixabay · Free Music Archive
""")

    def _show_shortcuts(self):
        QMessageBox.information(self, "Keyboard Shortcuts", """
<b>File</b>
Ctrl+N     New project
Ctrl+O     Open project
Ctrl+S     Save project
Ctrl+E     Export to MP4

<b>Edit</b>
Delete     Delete selected clip
Ctrl+K     Split clip at playhead

<b>Timeline</b>
Click clip then drag    Move clip
Drag left/right edge    Trim clip
Ctrl+scroll             Zoom timeline
Click ruler             Seek playhead

<b>Preview</b>
Space (in preview area) Play / Pause
""")

    def closeEvent(self, event):
        if self._modified:
            r = QMessageBox.question(self,"Unsaved Changes",
                "You have unsaved changes. Exit without saving?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Save:
                self._save_project()
                event.accept()
            elif r == QMessageBox.StandardButton.Cancel:
                event.ignore()
            else:
                event.accept()
        else:
            event.accept()
        get_db().close()


# ──────────────────────────────────────────────────────────────────────────────
#  TEMPLATE CHOOSER DIALOG
# ──────────────────────────────────────────────────────────────────────────────
class _TemplateChooserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project – Choose Template")
        self.setMinimumWidth(500)
        self.chosen = "Blank Episode"
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Choose an episode template to start:"))
        self.list = QListWidget()
        for key, t in EPISODE_TEMPLATES.items():
            item = QListWidgetItem(f"  {key}\n  {t['description']}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.list.addItem(item)
        self.list.setCurrentRow(0)
        lay.addWidget(self.list)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _accept(self):
        items = self.list.selectedItems()
        if items:
            self.chosen = items[0].data(Qt.ItemDataRole.UserRole)
        self.accept()


# ──────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # High-DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Big Truck Adventures")

    # Apply stylesheet
    app.setStyleSheet(QSS)

    # Splash
    splash_pm = QPixmap(600, 200)
    splash_pm.fill(QColor(C_BG))
    sp = QPainter(splash_pm)
    sp.setPen(QColor(C_ACCENT))
    sp.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
    sp.drawText(splash_pm.rect(), Qt.AlignmentFlag.AlignCenter,
                "🚛  Big Truck Adventures\nVideo Editor")
    sp.setPen(QColor(C_MUTED))
    sp.setFont(QFont("Segoe UI", 11))
    sp.drawText(QRect(0, 160, 600, 30), Qt.AlignmentFlag.AlignCenter,
                "100% free • no watermarks • runs locally on Windows")
    sp.end()

    splash = None
    try:
        from PyQt6.QtWidgets import QSplashScreen
        splash = QSplashScreen(splash_pm)
        splash.show()
        app.processEvents()
    except Exception:
        pass

    win = MainWindow()
    win.show()

    if splash:
        splash.finish(win)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
