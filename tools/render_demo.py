"""FormLens demo video v2 — in the app's own theme.

Paper/ink/pine palette and DM Serif Display / Instrument Sans / DM Mono, matching
index.html and about.html. Shows only features the app has: schema discovery,
extraction registry, confidence pills, side-by-side review, CSV export, BYOK.

Layout is designed on a 1280x720 grid and scaled by K for output resolution.
Needs: Python 3 with Pillow (pip install pillow) and ffmpeg on PATH.
Run:  python tools/render_demo.py assets/formlens_demo.mp4   full video
      python tools/render_demo.py --still 20 frame.png         one frame (seconds)
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

# ───────────────────────────── config
K = 1.5                                  # 1280x720 design grid -> 1920x1080 output
W, H, FPS = int(1280 * K), int(720 * K), 30
FONT_DIR = os.environ.get('FL_FONTS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts'))
FONTS = {
    'serif': 'dm-serif-display-latin-400-normal.woff',
    'serif-i': 'dm-serif-display-latin-400-italic.woff',
    'sans': 'instrument-sans-latin-400-normal.woff',
    'sans-m': 'instrument-sans-latin-500-normal.woff',
    'sans-b': 'instrument-sans-latin-600-normal.woff',
    'mono': 'dm-mono-latin-400-normal.woff',
    'mono-m': 'dm-mono-latin-500-normal.woff',
    # "handwriting": a system italic serif if present, else DM Serif italic
    'hand': next((p for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf',
                              'C:/Windows/Fonts/georgiai.ttf', '/Library/Fonts/Georgia Italic.ttf']
                  if os.path.exists(p)), 'dm-serif-display-latin-400-italic.woff'),
}

# app palette (index.html :root)
INK, INK2, INK3, INK4 = (28, 27, 24), (74, 72, 64), (138, 135, 126), (184, 180, 170)
PAPER, PAPER2, PAPER3 = (250, 249, 246), (242, 240, 234), (232, 228, 219)
PINE, PINE_MID, PINE_LIGHT, PINE_PALE = (26, 92, 58), (46, 125, 82), (230, 242, 236), (240, 248, 244)
AMBER, AMBER_LIGHT = (180, 83, 9), (254, 243, 226)
SHEET, PEN = (255, 254, 250), (30, 58, 138)
WHITE = (255, 255, 255)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


BORDER = mix(PAPER, INK, 0.10)
BORDER2 = mix(PAPER, INK, 0.18)
BORDER3 = mix(PAPER, INK, 0.28)

# fictional CRF content
FIELDS = [  # (key, label, type, value)
    ('participant_id', 'Participant ID', 'text', 'GM-0417'),
    ('visit_date', 'Visit date', 'date', '14/03/2026'),
    ('haemoglobin', 'Haemoglobin (g/dL)', 'decimal', '10.8'),
    ('ferritin', 'Ferritin (ng/mL)', 'decimal', '23'),
    ('crp', 'CRP (mg/L)', 'decimal', '4.1'),
    ('temperature', 'Temperature (°C)', 'decimal', '37.2'),
]
MORE_ROWS = [  # later records in the batch; row index 2 is the uncertain one
    ['GM-0418', '14/03/2026', '12.1', '41', '1.2', '36.8'],
    ['GM-0419', '15/03/2026', '9.7', '28', '6.3', '37.9'],   # page says 23
    ['GM-0420', '15/03/2026', '11.4', '35', '0.8', '36.6'],
]
CONF = [('High', 96), ('High', 93), ('Medium', 71), ('High', 95)]
PAGE_0419 = ['GM-0419', '15/03/2026', '9.7', '23', '6.3', '37.9']   # what is actually written
ROW_H = 58

_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        path = FONTS[name]
        if not os.path.isabs(path):
            path = os.path.join(FONT_DIR, path)
        _fc[key] = ImageFont.truetype(path, int(size * K))
    return _fc[key]


# ───────────────────────────── timing helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def prog(t, start, dur):
    return ease((t - start) / dur)


# ───────────────────────────── canvas (design-grid coordinates)
class C:
    def __init__(self, bg=PAPER):
        self.img = Image.new('RGB', (W, H), bg)
        self.d = ImageDraw.Draw(self.img)

    @staticmethod
    def s(v):
        return int(round(v * K))

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1, r=0):
        box = [self.s(x0), self.s(y0), self.s(x1), self.s(y1)]
        if r:
            self.d.rounded_rectangle(box, self.s(r), fill=fill, outline=outline, width=max(1, self.s(width)) if outline else 0)
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=max(1, self.s(width)) if outline else 0)

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        self.d.ellipse([self.s(x0), self.s(y0), self.s(x1), self.s(y1)], fill=fill, outline=outline,
                       width=max(1, self.s(width)) if outline else 0)

    def line(self, pts, fill, width=1):
        self.d.line([self.s(p) for p in pts], fill=fill, width=max(1, self.s(width)))

    def text(self, x, y, s, f, fill, anchor='la'):
        self.d.text((self.s(x), self.s(y)), s, font=f, fill=fill, anchor=anchor)

    def tw(self, s, f):
        return self.d.textlength(s, font=f) / K

    def dashed_rect(self, x0, y0, x1, y1, color, dash=8, gap=6, width=2):
        for (ax, ay, bx, by) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
            length = abs(bx - ax) + abs(by - ay)
            n = int(length // (dash + gap)) + 1
            for i in range(n):
                p0 = i * (dash + gap) / length
                p1 = min(1, (i * (dash + gap) + dash) / length)
                self.line([ax + (bx - ax) * p0, ay + (by - ay) * p0, ax + (bx - ax) * p1, ay + (by - ay) * p1], color, width)


def faded(c, base, a):
    """Blend `c` from base colour by alpha a."""
    return mix(base, c, clamp(a))


# ───────────────────────────── components
def caption(c, t, start, end, s):
    a = min(prog(t, start, 0.4), 1 - prog(t, end - 0.4, 0.4))
    if a <= 0:
        return
    f = font('sans-m', 19)
    w = c.tw(s, f)
    x0, y0 = 640 - w / 2 - 20, 652
    c.rect(x0, y0, x0 + w + 40, y0 + 42, fill=faded(INK, PAPER, a), r=21)
    c.text(640, y0 + 21, s, f, faded(PAPER, PAPER, 0) if a < 0.05 else faded(WHITE, INK, a), anchor='mm')


def app_window(c, x0, y0, x1, y1, step=1):
    """App chrome: ink topbar with brand + breadcrumb, paper body (index.html .topbar)."""
    c.rect(x0 + 4, y0 + 8, x1 + 4, y1 + 10, fill=mix(PAPER, INK, 0.06), r=14)  # soft shadow
    c.rect(x0, y0, x1, y1, fill=PAPER, outline=BORDER2, r=12)
    c.rect(x0, y0, x1, y0 + 40, fill=INK, r=12)
    c.rect(x0, y0 + 26, x1, y0 + 40, fill=INK)
    c.ellipse(x0 + 18, y0 + 17, x0 + 24, y0 + 23, fill=PINE_MID)
    c.text(x0 + 32, y0 + 20, 'FormLens', font('serif', 17), WHITE, anchor='lm')
    labels = ['Discover', 'Refine', 'Confirm', 'Extract']
    fx = x1 - 360
    for i, lab in enumerate(labels, start=1):
        active, done = i == step, i < step
        col = WHITE if active else (mix(INK, WHITE, 0.5) if done else mix(INK, WHITE, 0.3))
        cx, cy = fx, y0 + 20
        if active:
            c.ellipse(cx - 8, cy - 8, cx + 8, cy + 8, fill=PINE_MID)
        else:
            c.ellipse(cx - 8, cy - 8, cx + 8, cy + 8, outline=col, width=1)
        c.text(cx, cy, str(i), font('sans-b', 9), WHITE if active else col, anchor='mm')
        c.text(cx + 13, cy, lab, font('sans', 10.5), col, anchor='lm')
        fx += 13 + c.tw(lab, font('sans', 10.5)) + 24


def form_sheet(c, x, y, sc=1.0, active=-1, values=True, amber=-1, vals=None):
    """Scanned CRF page with handwritten values."""
    fw, fh = 300 * sc, 410 * sc
    c.rect(x + 3, y + 5, x + fw + 3, y + fh + 5, fill=mix(PAPER, INK, 0.08), r=4)
    c.rect(x, y, x + fw, y + fh, fill=SHEET, outline=BORDER2, r=4)
    c.text(x + 18 * sc, y + 18 * sc, 'CASE REPORT FORM', font('sans-b', 12.5 * sc), INK)
    c.text(x + 18 * sc, y + 38 * sc, 'Iron Status Study · Visit 2 · Page 1/5', font('sans', 9.5 * sc), INK3)
    c.line([x + 18 * sc, y + 58 * sc, x + fw - 18 * sc, y + 58 * sc], BORDER3, 1)
    for i, (_, label, _, val) in enumerate(FIELDS):
        if vals:
            val = vals[i]
        fy = y + (72 + i * 52) * sc
        if i == active or i == amber:
            fill, edge = (PINE_LIGHT, PINE) if i == active else (AMBER_LIGHT, AMBER)
            c.rect(x + 10 * sc, fy - 5 * sc, x + fw - 10 * sc, fy + 42 * sc, fill=fill, outline=edge, width=2, r=5)
        c.text(x + 18 * sc, fy, label, font('sans-m', 9.5 * sc), INK3)
        c.line([x + 18 * sc, fy + 36 * sc, x + fw - 18 * sc, fy + 36 * sc], BORDER2, 1)
        if values:
            c.text(x + 26 * sc, fy + 13 * sc, val, font('hand', 18 * sc), PEN)
    c.text(x + 18 * sc, y + fh - 24 * sc, 'Signature: ______________', font('sans', 9 * sc), INK4)
    return fw, fh


def pill(c, x, y, level, pct, a=1.0):
    fg, bg = (PINE, PINE_LIGHT) if level == 'High' else (AMBER, AMBER_LIGHT)
    s = f'{level} · {pct}%'
    f = font('sans-b', 11)
    w = c.tw(s, f) + 16
    c.rect(x, y, x + w, y + 22, fill=faded(bg, PAPER, a), r=4)
    c.text(x + 8, y + 11, s, f, faded(fg, PAPER, a), anchor='lm')
    c.rect(x, y + 26, x + 90, y + 29, fill=faded(PAPER3, PAPER, a), r=1.5)
    c.rect(x, y + 26, x + 90 * pct / 100, y + 29, fill=faded(PINE_MID if level == 'High' else AMBER, PAPER, a), r=1.5)


REG_X, REG_Y = 392, 104
COLS = [('#', 32), ('Participant', 112), ('Visit date', 124), ('Hb', 72), ('Ferritin', 88), ('CRP', 72), ('Temp', 76), ('Confidence', 150)]


def col_x(i):
    return REG_X + 14 + sum(w for _, w in COLS[:i])


def registry(c, rows, conf_shown=0, highlight=-1, conf_override=None, count_label=None):
    """Extraction registry table (index.html .reg-tbl). rows: list of lists of cell strings (may be partial)."""
    c.text(REG_X, REG_Y, 'Extraction Registry', font('serif', 22), INK)
    n = len([r for r in rows if any(r)])
    label = count_label or f'{n} record' + ('' if n == 1 else 's')
    f = font('sans-b', 9.5)
    lw = c.tw(label, f) + 18
    c.rect(REG_X + 214, REG_Y + 5, REG_X + 214 + lw, REG_Y + 25, fill=PINE_LIGHT, r=10)
    c.text(REG_X + 214 + lw / 2, REG_Y + 15, label, f, PINE, anchor='mm')
    tx0, ty0 = REG_X, REG_Y + 44
    tx1 = col_x(len(COLS)) + 8
    c.rect(tx0, ty0, tx1, ty0 + 34 + ROW_H * 4 + 6, fill=PAPER, outline=BORDER, r=10)
    c.rect(tx0 + 1, ty0 + 1, tx1 - 1, ty0 + 34, fill=PAPER2, r=9)
    c.rect(tx0 + 1, ty0 + 20, tx1 - 1, ty0 + 34, fill=PAPER2)
    c.line([tx0, ty0 + 34, tx1, ty0 + 34], BORDER2, 1)
    for i, (h, _) in enumerate(COLS):
        c.text(col_x(i), ty0 + 17, h.upper(), font('sans-b', 10), INK2, anchor='lm')
    for r, cells in enumerate(rows):
        ry = ty0 + 34 + r * ROW_H
        mid = ry + ROW_H / 2
        if r == highlight:
            c.rect(tx0 + 1, ry + 1, tx1 - 1, ry + ROW_H - 1, fill=AMBER_LIGHT)
        if r < 3:
            c.line([tx0 + 8, ry + ROW_H, tx1 - 8, ry + ROW_H], BORDER, 1)
        if any(cells):
            c.text(col_x(0), mid, str(r + 1), font('mono', 12), INK3, anchor='lm')
        for j, v in enumerate(cells):
            if v:
                f = font('mono', 13) if j in (1, 2, 3, 4, 5) else font('sans-m', 13.5)
                c.text(col_x(j + 1), mid, v, f, INK, anchor='lm')
        if r < conf_shown:
            level, pct = (conf_override or {}).get(r, CONF[r])
            pill(c, col_x(7), mid - 15, level, pct)
    return tx0, ty0, tx1


# ───────────────────────────── scenes
def scene_problem(t):  # 6.5 s
    c = C()
    for i in range(12):
        p = ease_out((t - i * 0.1) / 0.6)
        if p <= 0:
            continue
        x = 150 + (i % 3) * 5 - (i % 2) * 4
        y = 120 + (1 - p) * -380 + (11 - i) * 7
        c.rect(x, y, x + 250, y + 330, fill=mix(SHEET, PAPER3, (i % 4) / 6), outline=BORDER2, r=3)
        if i == 11:
            for k in range(9):
                c.line([x + 24, y + 44 + k * 30, x + 226 - (k % 3) * 30, y + 44 + k * 30], PAPER3, 2)
    lines = [('40,000 paper CRF pages.', 0.9, INK, 'serif'),
             ('Entered by hand. Then entered again.', 2.3, INK, 'serif'),
             ('Months before analysis can start.', 3.7, AMBER, 'serif-i')]
    for k, (s, st, col, fn) in enumerate(lines):
        a = prog(t, st, 0.6)
        if a > 0:
            c.text(500, 236 + k * 74 + (1 - a) * 12, s, font(fn, 40), faded(col, PAPER, a))
    return c.img


def scene_discover(t):  # 6.5 s
    c = C()
    app_window(c, 40, 30, 1240, 630, step=1 if t < 3.2 else 2)
    p = ease_out((t - 0.3) / 1.0)
    form_sheet(c, -320 + p * 400, 92, 1.0, values=True)
    # drop zone -> schema list
    za = prog(t, 0.2, 0.5) * (1 - prog(t, 1.6, 0.4))
    if za > 0:
        c.dashed_rect(470, 170, 1180, 440, faded(BORDER3, PAPER, za))
        c.text(825, 280, 'Drop your sample PDF here', font('serif', 24), faded(INK, PAPER, za), anchor='mm')
        c.text(825, 316, 'one sample form · AI proposes the schema', font('sans', 13), faded(INK3, PAPER, za), anchor='mm')
    if t > 1.8:
        c.text(470, 100, 'Schema Editor', font('serif', 20), INK)
        c.rect(470, 132, 1180, 160, fill=PAPER2)
        for x, h in [(486, 'FIELD PATH'), (700, 'DISPLAY LABEL'), (940, 'TYPE'), (1070, 'REQUIRED')]:
            c.text(x, 146, h, font('sans-b', 8.5), INK3, anchor='lm')
        for i, (key, label, typ, _) in enumerate(FIELDS):
            a = prog(t, 2.0 + i * 0.32, 0.35)
            if a <= 0:
                continue
            ry = 160 + i * 44
            c.line([470, ry + 44, 1180, ry + 44], faded(BORDER, PAPER, a), 1)
            c.text(486, ry + 22, key, font('mono', 12), faded(INK, PAPER, a), anchor='lm')
            c.text(700, ry + 22, label, font('sans', 12.5), faded(INK, PAPER, a), anchor='lm')
            c.text(940, ry + 22, typ, font('sans', 12.5), faded(INK2, PAPER, a), anchor='lm')
            cx, cy = 1084, ry + 22
            c.rect(cx - 6, cy - 6, cx + 6, cy + 6, fill=faded(PINE, PAPER, a), r=2)
        if t > 4.4:
            a = prog(t, 4.4, 0.4)
            c.rect(1040, 446, 1180, 478, fill=faded(PINE, PAPER, a), r=7)
            c.text(1110, 462, 'Looks Good', font('sans-b', 12.5), faded(WHITE, PAPER, a), anchor='mm')
    caption(c, t, 0.3, 6.5, 'Upload one sample form. FormLens proposes the schema.')
    return c.img


def scene_extract(t):  # 10 s
    c = C()
    app_window(c, 40, 30, 1240, 630, step=4)
    per = 1.05
    idx = int((t - 0.5) // per) if t >= 0.5 else -1
    done_first = t >= 0.5 + per * len(FIELDS)
    local = (t - 0.5) - idx * per if idx >= 0 else 0
    form_sheet(c, 66, 92, 0.8, active=idx if (0 <= idx < len(FIELDS) and not done_first) else -1)
    first = [''] * 6
    filled = len(FIELDS) if done_first else (idx if local < 0.6 else idx + 1)
    for j in range(max(0, filled)):
        first[j] = FIELDS[j][3]
    rows = [first]
    if done_first:
        for k, r in enumerate(MORE_ROWS):
            if t > 0.5 + per * len(FIELDS) + 0.25 + k * 0.45:
                rows.append(r)
    registry(c, rows)
    if 0 <= idx < len(FIELDS) and not done_first and local < 0.6:  # value chip flying to its cell
        p = ease(local / 0.6)
        sx, sy = 66 + 26 * 0.8, 92 + (72 + idx * 52 + 13) * 0.8
        ex, ey = col_x(idx + 1), REG_Y + 44 + 34 + ROW_H / 2 - 7
        x = sx + (ex - sx) * p
        y = sy + (ey - sy) * p - (1 - (2 * p - 1) ** 2) * 50
        s = FIELDS[idx][3]
        f = font('mono-m', 13)
        w = c.tw(s, f)
        c.rect(x - 7, y - 5, x + w + 7, y + 19, fill=PINE, r=5)
        c.text(x, y + 7, s, f, WHITE, anchor='lm')
    caption(c, t, 0.3, 10.0, 'Upload PDFs in bulk. Each handwritten field becomes a record.')
    return c.img


def scene_review(t):  # 9 s
    c = C()
    app_window(c, 40, 30, 1240, 630, step=4)
    rows = [[f[3] for f in FIELDS]] + [list(r) for r in MORE_ROWS]
    shown = int(clamp((t - 0.3) / 0.35, 0, 4))
    fixed = t > 6.6
    override = {2: ('High', 98)} if fixed else None
    if fixed:
        rows[2][3] = '23'
    hl = 2 if (2.0 < t < 6.9) else -1
    form_sheet(c, 66, 92, 0.8, values=True)
    registry(c, rows, conf_shown=shown, highlight=hl, conf_override=override, count_label='4 records')
    if 1.9 < t < 2.9:  # tooltip on the uncertain pill
        a = prog(t, 1.9, 0.2) * (1 - prog(t, 2.7, 0.2))
        tx, ty = col_x(7) - 10, REG_Y + 44 + 34 + 3 * ROW_H + 2
        c.rect(tx, ty, tx + 160, ty + 24, fill=faded(INK, PAPER, a), r=5)
        c.text(tx + 80, ty + 12, 'Uncertain: Ferritin', font('sans-m', 11), faded(WHITE, INK, a), anchor='mm')
    # edit modal (index.html .modal-box with split PDF/fields panes)
    m = prog(t, 2.9, 0.4) * (1 - prog(t, 6.6, 0.35))
    if m > 0:
        ov = Image.new('RGB', (W, H), (0, 0, 0))
        c.img.paste(Image.blend(c.img, ov, 0.35 * m))
        c.d = ImageDraw.Draw(c.img)
        dy = (1 - m) * 24
        x0, y0, x1, y1 = 170, 70 + dy, 1110, 610 + dy
        c.rect(x0, y0, x1, y1, fill=PAPER, outline=BORDER, r=16)
        c.text(x0 + 20, y0 + 24, 'Edit Record — GM-0419', font('serif', 17), INK, anchor='lm')
        c.line([x0, y0 + 48, x1, y0 + 48], BORDER, 1)
        c.rect(x0 + 1, y0 + 49, x0 + 470, y1 - 52, fill=(82, 86, 89))
        c.text(x0 + 14, y0 + 64, 'GM-0419_visit2.pdf', font('mono', 9.5), (200, 202, 204), anchor='lm')
        form_sheet(c, x0 + 90, y0 + 80, 0.95, amber=3, vals=PAGE_0419)
        fx = x0 + 500
        rec = dict(zip([f[0] for f in FIELDS], MORE_ROWS[1]))
        typed = t > 4.6
        for i, (key, label, _, _) in enumerate(FIELDS):
            fy = y0 + 70 + i * 58
            c.text(fx, fy, label.upper(), font('sans-b', 8.5), INK3)
            val = rec[key]
            box_edge = BORDER2
            if key == 'ferritin':
                box_edge = PINE if typed else AMBER
                if t > 3.6 and not typed:
                    val = rec[key]
                if typed:
                    val = '2' if t < 4.85 else '23'
            c.rect(fx, fy + 16, fx + 400, fy + 46, fill=PAPER, outline=box_edge, width=1.5 if key == 'ferritin' else 1, r=7)
            c.text(fx + 12, fy + 31, val, font('sans', 13), INK, anchor='lm')
            if key == 'ferritin' and not typed:
                tag, col, bg = ('Uncertain', AMBER, AMBER_LIGHT)
                tw = c.tw(tag, font('sans-b', 9)) + 14
                c.rect(fx + 400 - tw - 8, fy + 22, fx + 400 - 8, fy + 40, fill=bg, r=4)
                c.text(fx + 400 - tw / 2 - 8, fy + 31, tag, font('sans-b', 9), col, anchor='mm')
        c.line([x0, y1 - 52, x1, y1 - 52], BORDER, 1)
        press = 5.6 < t < 6.0
        c.rect(x1 - 150, y1 - 40, x1 - 20, y1 - 12, fill=PINE_MID if press else PINE, r=7)
        c.text(x1 - 85, y1 - 26, 'Save Changes', font('sans-b', 12), WHITE, anchor='mm')
    caption(c, t, 0.3, 9.0, 'Uncertain fields are flagged. Check them beside the original page.')
    return c.img


def scene_export(t):  # 6.5 s
    c = C()
    a1 = prog(t, 0.2, 0.6)
    x, y = 250, 210 + (1 - a1) * 16
    c.rect(x, y, x + 150, y + 190, fill=faded(SHEET, PAPER, a1), outline=faded(BORDER2, PAPER, a1), r=6)
    for k in range(6):
        c.line([x + 20, y + 30 + k * 18, x + 130 - (k % 2) * 30, y + 30 + k * 18], faded(PAPER3, PAPER, a1), 2)
    c.rect(x + 22, y + 140, x + 128, y + 172, fill=faded(PINE, PAPER, a1), r=6)
    c.text(x + 75, y + 156, 'CSV', font('sans-b', 16), faded(WHITE, PAPER, a1), anchor='mm')
    c.text(x + 75, y + 222, 'Export to CSV', font('serif', 20), faded(INK, PAPER, a1), anchor='mm')
    c.text(x + 75, y + 250, 'with confidence and source file', font('sans', 12), faded(INK3, PAPER, a1), anchor='mm')
    a2 = prog(t, 1.4, 0.6)
    if a2 > 0:
        x0, y0 = 560, 180 + (1 - a2) * 16
        c.rect(x0, y0, x0 + 470, y0 + 280, fill=faded(PINE_PALE, PAPER, a2), outline=faded(PINE_MID, PAPER, a2), width=1.5, r=16)
        lx, ly = x0 + 34, y0 + 42  # lock
        c.d.arc([c.s(lx + 2), c.s(ly - 16), c.s(lx + 26), c.s(ly + 10)], 180, 360, fill=faded(PINE, PAPER, a2), width=c.s(4))
        c.rect(lx - 4, ly, lx + 32, ly + 28, fill=faded(PINE, PAPER, a2), r=5)
        c.text(x0 + 84, y0 + 50, 'Your key, your data path', font('serif', 24), faded(INK, PAPER, a2), anchor='lm')
        items = ['Runs on your own OpenRouter key', 'Forms go only to the AI provider you choose',
                 'Identifiable data: zero-retention providers only']
        for k, s in enumerate(items):
            a = prog(t, 2.0 + k * 0.35, 0.4)
            iy = y0 + 112 + k * 46
            c.line([x0 + 38, iy, x0 + 44, iy + 6, x0 + 56, iy - 6], faded(PINE_MID, PAPER, a), 2.5)
            c.text(x0 + 72, iy, s, font('sans', 15), faded(INK2, PAPER, a), anchor='lm')
    caption(c, t, 0.3, 6.5, 'Export clean data. Your key and your data path stay yours.')
    return c.img


def scene_end(t):  # 7.5 s
    c = C()
    a = prog(t, 0.2, 0.7)
    c.text(640, 150, 'ADAPTIVE FORM INTELLIGENCE', font('mono', 12), faded(PINE, PAPER, a), anchor='mm')
    c.text(640, 222, 'Extract any form,', font('serif', 58), faded(INK, PAPER, a), anchor='mm')
    a2 = prog(t, 0.6, 0.7)
    c.text(640, 292, 'on your terms.', font('serif-i', 58), faded(PINE, PAPER, a2), anchor='mm')
    a3 = prog(t, 1.2, 0.6)
    c.text(640, 366, 'First entry by AI. Verified by your team.', font('sans', 20), faded(INK2, PAPER, a3), anchor='mm')
    a4 = prog(t, 1.9, 0.6)
    if a4 > 0:
        s = 'Free pilot on 100 of your own pages'
        f = font('sans-b', 18)
        w = c.tw(s, f)
        c.rect(640 - w / 2 - 28, 422, 640 + w / 2 + 28, 474, fill=faded(PINE, PAPER, a4), r=10)
        c.text(640, 448, s, f, faded(WHITE, PAPER, a4), anchor='mm')
    a5 = prog(t, 2.6, 0.6)
    f1, f2 = font('serif', 20), font('sans', 13)
    w1, w2 = c.tw('FormLens', f1), c.tw('by A.M. Labs', f2)
    x = 640 - (16 + w1 + 8 + w2) / 2
    c.ellipse(x, 545, x + 8, 553, fill=faded(PINE_MID, PAPER, a5))
    c.text(x + 16, 549, 'FormLens', f1, faded(INK, PAPER, a5), anchor='lm')
    c.text(x + 16 + w1 + 8, 550, 'by A.M. Labs', f2, faded(INK3, PAPER, a5), anchor='lm')
    return c.img


TIMELINE = [(scene_problem, 6.5), (scene_discover, 6.5), (scene_extract, 10.0),
            (scene_review, 9.0), (scene_export, 6.5), (scene_end, 7.5)]
XFADE = 0.35
TOTAL = sum(d for _, d in TIMELINE)


def frame_at(t):
    start = 0.0
    for i, (fn, dur) in enumerate(TIMELINE):
        last = i == len(TIMELINE) - 1
        if t < start + dur or last:
            lt = t - start
            img = fn(lt)
            fade_in = 1.0 if i == 0 else lt / XFADE
            fade_out = (dur - lt) / (0.9 if last else XFADE)
            e = clamp(min(fade_in, fade_out))
            if e < 1:
                img = Image.blend(Image.new('RGB', (W, H), PAPER), img, ease(e))
            return img
        start += dur


def render(out):
    n = int(TOTAL * FPS)
    proc = subprocess.Popen(
        ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
         '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
         '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for k in range(n):
        proc.stdin.write(frame_at(k / FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    print(f'wrote {out}: {n} frames, {TOTAL:.1f}s, {W}x{H}')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--still':
        frame_at(float(sys.argv[2])).save(sys.argv[3] if len(sys.argv) > 3 else 'still.png')
    else:
        render(sys.argv[1] if len(sys.argv) > 1 else 'formlens_demo.mp4')
