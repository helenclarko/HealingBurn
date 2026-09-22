"""
Procedurally paints every pixel-art asset for RosyFire and saves them as PNGs
into ../assets/. Everything is generated with gradients, ordered dithering,
and hand-placed shapes - no photos, no external images - so the whole scene
shares one palette and reads as one cohesive piece of pixel art.

Run once (or whenever you want to tweak the art):
    python tools/generate_assets.py
"""

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

random.seed(7)

SCENE_W, SCENE_H = 320, 180
HORIZON_Y = 98         # sky / far mountains meet the lake
SHORE_Y = 132          # lake meets the near shore
FIRE_X, FIRE_Y = 172, 150

# ---------------------------------------------------------------------------
# palette
# ---------------------------------------------------------------------------

SKY_STOPS = [
    (0.00, (28, 22, 62)),
    (0.30, (86, 40, 88)),
    (0.60, (196, 88, 78)),
    (1.00, (255, 175, 96)),
]
SUN_COLOR = (255, 226, 150)
SUN_GLOW = (255, 175, 110)
STAR = (255, 255, 240)
CLOUD = (255, 190, 150)

MOUNTAIN = (98, 76, 118)
MOUNTAIN_SNOW = (216, 198, 210)
PINE_FAR = (26, 24, 34)
PINE_NEAR = (14, 15, 20)

LAKE_SHORE = (58, 40, 58)
LAKE_HORIZON = (150, 90, 90)
LAKE_SPARKLE = (255, 200, 150)

GROUND_DARK = (24, 18, 18)
GROUND_MID = (46, 32, 26)
GROUND_WARM = (168, 92, 48)
ROCK = (60, 50, 48)
ROCK_HI = (92, 78, 72)

CABIN_WALL = (74, 54, 48)
CABIN_ROOF = (30, 22, 24)
WINDOW_GLOW = (255, 205, 120)
WINDOW_CORE = (255, 240, 200)

DOCK_WOOD = (74, 50, 36)
DOCK_DARK = (46, 30, 22)
CANOE = (120, 58, 34)

SIGN_WOOD = (96, 63, 40)
SIGN_DARK = (58, 36, 22)
SIGN_TEXT = (240, 228, 200)
POST_WOOD = (70, 46, 30)

LANTERN_METAL = (36, 30, 28)
LANTERN_GLOW = (255, 205, 130)
MUG_BODY = (222, 216, 200)
MUG_SHADE = (170, 160, 145)

FIRE_CORE = (255, 246, 195)
FIRE_INNER = (255, 178, 72)
FIRE_MID = (233, 108, 46)
FIRE_OUTER = (168, 55, 36)

STONE_LIGHT = (132, 118, 106)
STONE_DARK = (70, 60, 54)
LOG_BODY = (112, 68, 40)
LOG_DARK = (66, 38, 22)
LOG_HI = (152, 100, 62)
ASH = (50, 42, 44)

LAP_SHADOW = (16, 13, 16)
LAP_MID = (30, 24, 27)
LAP_RIM = (255, 150, 84)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

BAYER4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def dither_pick(x, y, t):
    threshold = (BAYER4[y % 4][x % 4] + 0.5) / 16.0
    return t > threshold


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))


def multi_lerp(stops, t):
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            local = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return lerp_color(c0, c1, local)
    return stops[-1][1]


def blank(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def save(img, name, scale=1):
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(OUT / name)
    print(f"wrote {name}  {img.width}x{img.height}")


def ridge_line(width, base_y, amplitude, seed, anchors=None):
    rnd = random.Random(seed)
    n = anchors or max(4, width // 26)
    pts = [base_y + rnd.uniform(-amplitude, amplitude) for _ in range(n + 1)]
    heights = []
    for x in range(width):
        t = x / width * n
        i = int(t)
        f = t - i
        f = f * f * (3 - 2 * f)
        a = pts[min(i, n)]
        b = pts[min(i + 1, n)]
        heights.append(lerp(a, b, f))
    return heights


TINY_FONT = ImageFont.load_default()


def draw_sign_text(d, cx, top_y, lines, color=SIGN_TEXT):
    for i, line in enumerate(lines):
        bbox = d.textbbox((0, 0), line, font=TINY_FONT)
        w = bbox[2] - bbox[0]
        d.text((cx - w / 2, top_y + i * 8), line, font=TINY_FONT, fill=(*color, 255))


# ---------------------------------------------------------------------------
# background: sky, sun, mountains, pines, lake, shore, cabin, dock, signs
# ---------------------------------------------------------------------------


def paint_sky(img):
    px = img.load()
    for y in range(HORIZON_Y):
        c = multi_lerp(SKY_STOPS, y / (HORIZON_Y - 1))
        for x in range(SCENE_W):
            px[x, y] = (*c, 255)

    sun_x, sun_y, sun_r = 176, 90, 15
    for y in range(sun_y - sun_r - 10, sun_y + sun_r + 10):
        for x in range(SCENE_W):
            if not (0 <= y < HORIZON_Y):
                continue
            d = math.hypot(x - sun_x, y - sun_y)
            if d <= sun_r:
                px[x, y] = (*SUN_COLOR, 255)
            elif d <= sun_r + 10:
                a = (1 - (d - sun_r) / 10) * 0.8
                base = px[x, y][:3]
                px[x, y] = (*lerp_color(base, SUN_GLOW, a), 255)

    rnd = random.Random(3)
    for _ in range(40):
        x = rnd.randrange(SCENE_W)
        y = rnd.randrange(0, int(HORIZON_Y * 0.35))
        if rnd.random() < 0.55:
            px[x, y] = (*STAR, 255)

    for _ in range(5):
        cy = rnd.randrange(18, 55)
        cx = rnd.randrange(20, SCENE_W - 20)
        cw = rnd.randrange(28, 60)
        for x in range(max(0, cx - cw), min(SCENE_W, cx + cw)):
            dx = abs(x - cx) / cw
            if dx > 1:
                continue
            band = int(3 * (1 - dx))
            for yy in range(cy, cy + max(band, 1)):
                if 0 <= yy < HORIZON_Y and dither_pick(x, yy, 0.5 * (1 - dx)):
                    base = px[x, yy][:3]
                    px[x, yy] = (*lerp_color(base, CLOUD, 0.35 * (1 - dx)), 255)


def paint_mountains(img):
    px = img.load()
    heights = ridge_line(SCENE_W, base_y=72, amplitude=16, seed=11, anchors=7)
    for x in range(SCENE_W):
        top = int(heights[x])
        haze = max(0.0, min(1.0, (top - 50) / 40))
        for y in range(max(top, 0), HORIZON_Y):
            depth = (y - top) / max(HORIZON_Y - top, 1)
            sky_c = multi_lerp(SKY_STOPS, y / (HORIZON_Y - 1))
            base = lerp_color(MOUNTAIN, sky_c, 0.25 + 0.15 * (1 - depth))
            if y - top < 5 and (x * 7 + y * 3) % 11 < 4:
                base = lerp_color(base, MOUNTAIN_SNOW, 0.8)
            px[x, y] = (*base, 255)


def pine_tree(d, x, base_y, height, width, color):
    tiers = 3
    for i in range(tiers):
        t = i / tiers
        tier_w = width * (1 - t * 0.72)
        top = base_y - height * (t * 0.7 + 0.3)
        bot = base_y - height * (t * 0.7)
        d.polygon([(x - tier_w / 2, bot), (x, top - height * 0.22), (x + tier_w / 2, bot)], fill=(*color, 255))
    d.rectangle([x - 1, base_y - 2, x + 1, base_y + 2], fill=(*color, 255))


def paint_treeline(img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(21)
    baseline = HORIZON_Y + 6
    for cluster_x, spread, count, near in ((28, 55, 9, False), (292, 40, 7, True)):
        for _ in range(count):
            x = cluster_x + rnd.uniform(-spread, spread)
            x = max(4, min(SCENE_W - 4, x))
            h = rnd.uniform(26, 46) if near else rnd.uniform(16, 30)
            w = h * rnd.uniform(0.42, 0.55)
            by = baseline + rnd.uniform(-3, 6)
            color = PINE_NEAR if h > 30 else PINE_FAR
            pine_tree(d, x, by, h, w, color)
    for _ in range(4):
        x = rnd.uniform(120, 220)
        h = rnd.uniform(10, 16)
        w = h * 0.5
        pine_tree(d, x, baseline + rnd.uniform(0, 3), h, w, PINE_FAR)


def paint_lake(img):
    px = img.load()
    for y in range(HORIZON_Y, SHORE_Y):
        t = 1 - (y - HORIZON_Y) / (SHORE_Y - HORIZON_Y)
        c = lerp_color(LAKE_SHORE, LAKE_HORIZON, t * 0.8)
        for x in range(SCENE_W):
            px[x, y] = (*c, 255)
    sun_x = 176
    for y in range(HORIZON_Y, SHORE_Y):
        band = 10 + (y - HORIZON_Y) * 0.3
        for x in range(int(sun_x - band), int(sun_x + band)):
            if not (0 <= x < SCENE_W):
                continue
            dx = abs(x - sun_x) / band
            a = (1 - dx) * 0.5
            if dither_pick(x, y, a):
                base = px[x, y][:3]
                px[x, y] = (*lerp_color(base, LAKE_SPARKLE, a), 255)
    rnd = random.Random(5)
    for y in range(HORIZON_Y, SHORE_Y, 2):
        for _ in range(6):
            x = rnd.randrange(SCENE_W)
            base = px[x, y][:3]
            px[x, y] = (*lerp_color(base, (10, 8, 14), 0.25), 255)


def paint_shore(img):
    px = img.load()
    for y in range(SHORE_Y, SCENE_H):
        for x in range(SCENE_W):
            d = math.hypot((x - FIRE_X) / 130.0, (y - (FIRE_Y + 4)) / 34.0)
            warm_t = max(0.0, 1 - d) ** 1.6
            depth_t = (y - SHORE_Y) / (SCENE_H - SHORE_Y)
            base = lerp_color(GROUND_DARK, GROUND_MID, depth_t)
            c = lerp_color(base, GROUND_WARM, warm_t) if dither_pick(x, y, warm_t) else base
            px[x, y] = (*c, 255)
    d = ImageDraw.Draw(img)
    rnd = random.Random(9)
    for _ in range(22):
        x = rnd.randrange(0, SCENE_W)
        y = rnd.randrange(SHORE_Y + 2, SCENE_H - 6)
        if abs(x - FIRE_X) < 30:
            continue
        r = rnd.randrange(2, 5)
        d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(*ROCK, 255))
        d.ellipse([x - r + 1, y - r * 0.7, x + r - 2, y + r * 0.7 - 1], fill=(*ROCK_HI, 255))


def paint_cabin(img):
    px = img.load()
    x0, y0 = 15, HORIZON_Y - 6
    w, h = 50, 32

    window_centers = [(x0 + 12, y0 + 17), (x0 + w - 14, y0 + 17)]
    for wxc, wyc in window_centers:
        for gy in range(wyc - 11, wyc + 11):
            for gx in range(wxc - 11, wxc + 11):
                if 0 <= gx < SCENE_W and 0 <= gy < SCENE_H:
                    dd = math.hypot(gx - wxc, gy - wyc)
                    if dd < 11:
                        a = max(0.0, 1 - dd / 11) * 0.55
                        base = px[gx, gy][:3]
                        px[gx, gy] = (*lerp_color(base, WINDOW_GLOW, a), 255)

    d = ImageDraw.Draw(img)
    d.polygon([(x0 - 6, y0), (x0 + w / 2, y0 - 18), (x0 + w + 6, y0)], fill=(*CABIN_ROOF, 255))
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=(*CABIN_WALL, 255))
    d.rectangle([x0 + w - 10, y0 - 14, x0 + w - 4, y0 - 2], fill=(*CABIN_ROOF, 255))
    for wxc, wyc in window_centers:
        d.rectangle([wxc - 5, wyc - 5, wxc + 5, wyc + 5], fill=(*WINDOW_GLOW, 255))
        d.rectangle([wxc - 3, wyc - 3, wxc + 3, wyc + 3], fill=(*WINDOW_CORE, 255))
    for step in range(3):
        d.rectangle([x0 + 14 - step * 3, y0 + h + step * 3, x0 + 30 + step * 3, y0 + h + step * 3 + 2],
                     fill=(*ROCK, 255))


def paint_dock(img):
    d = ImageDraw.Draw(img)
    base_x, base_y = 214, SHORE_Y - 6
    for i in range(7):
        t = i / 6
        px_ = base_x + t * 46
        py = base_y + t * 20
        plank_w = 4 - t * 1.5
        d.line([(px_, py), (px_ + 6, py - 1)], fill=(*DOCK_DARK, 255), width=int(max(plank_w, 1)))
    d.line([(base_x, base_y - 2), (base_x + 50, base_y + 20)], fill=(*DOCK_WOOD, 255), width=6)
    d.line([(base_x, base_y - 2), (base_x + 50, base_y + 20)], fill=(*DOCK_DARK, 255), width=1)
    for t in (0.15, 0.5, 0.85):
        px_ = base_x + t * 50
        py = base_y - 2 + t * 22
        d.line([(px_, py - 5), (px_, py + 4)], fill=(*DOCK_DARK, 255), width=2)

    cx, cy = base_x + 30, base_y + 14
    d.polygon([(cx - 16, cy), (cx - 10, cy - 5), (cx + 12, cy - 5), (cx + 17, cy)], fill=(*CANOE, 255))
    d.line([(cx - 14, cy - 1), (cx + 14, cy - 1)], fill=(*DOCK_DARK, 255), width=1)


def paint_signs(img):
    d = ImageDraw.Draw(img)

    # hanging sign, upper right corner, on an overhanging branch
    d.rectangle([SCENE_W - 14, 0, SCENE_W - 8, 34], fill=(*PINE_NEAR, 255))
    d.line([(SCENE_W - 30, 6), (SCENE_W - 8, 16)], fill=(*PINE_NEAR, 255), width=5)
    board_x, board_y, bw, bh = SCENE_W - 78, 22, 60, 30
    d.line([(board_x + 10, 16), (board_x + 10, board_y)], fill=(*SIGN_DARK, 255), width=1)
    d.line([(board_x + bw - 10, 16), (board_x + bw - 10, board_y)], fill=(*SIGN_DARK, 255), width=1)
    d.rectangle([board_x, board_y, board_x + bw, board_y + bh], fill=(*SIGN_WOOD, 255))
    d.rectangle([board_x, board_y, board_x + bw, board_y + bh], outline=(*SIGN_DARK, 255), width=2)
    draw_sign_text(d, board_x + bw / 2, board_y + 6, ["BRIGHTER", "YOU"])

    # post sign, bottom-left foreground
    px0, py0 = 112, SCENE_H - 60
    d.rectangle([px0 - 3, py0, px0 + 3, SCENE_H - 8], fill=(*POST_WOOD, 255))
    d.rectangle([px0 - 26, py0 - 26, px0 + 26, py0 + 2], fill=(*SIGN_WOOD, 255))
    d.rectangle([px0 - 26, py0 - 26, px0 + 26, py0 + 2], outline=(*SIGN_DARK, 255), width=2)
    draw_sign_text(d, px0, py0 - 22, ["HEAL", "SLOW"])


def paint_lantern(img):
    d = ImageDraw.Draw(img)
    px = img.load()
    lx, ly = 296, SHORE_Y + 12
    for r, a in ((14, 40), (9, 80), (5, 140)):
        for yy in range(ly - r, ly + r):
            for xx in range(lx - r, lx + r):
                if 0 <= xx < SCENE_W and 0 <= yy < SCENE_H and math.hypot(xx - lx, yy - ly) <= r:
                    base = px[xx, yy][:3]
                    px[xx, yy] = (*lerp_color(base, LANTERN_GLOW, a / 255), 255)
    d.line([(lx, ly - 22), (lx, ly - 10)], fill=(*LANTERN_METAL, 255), width=1)
    d.rectangle([lx - 5, ly - 10, lx + 5, ly + 6], outline=(*LANTERN_METAL, 255), width=1)
    d.rectangle([lx - 3, ly - 8, lx + 3, ly + 4], fill=(*LANTERN_GLOW, 255))
    d.line([(lx - 5, ly + 6), (lx + 5, ly + 6)], fill=(*LANTERN_METAL, 255), width=2)


def paint_mug(img):
    d = ImageDraw.Draw(img)
    mx, my = 66, SCENE_H - 26
    d.ellipse([mx - 9, my - 4, mx + 9, my + 12], fill=(*MUG_BODY, 255))
    d.ellipse([mx - 9, my - 4, mx + 9, my + 2], fill=(*MUG_SHADE, 255))
    d.rectangle([mx - 9, my, mx + 9, my + 12], fill=(*MUG_BODY, 255))
    d.arc([mx + 6, my, mx + 18, my + 12], start=280, end=90, fill=(*MUG_SHADE, 255), width=2)
    d.polygon([(mx - 2, my + 5), (mx, my + 2), (mx + 2, my + 5), (mx, my + 8)], fill=(176, 60, 60, 255))


def make_background():
    img = blank(SCENE_W, SCENE_H)
    paint_sky(img)
    paint_mountains(img)
    paint_lake(img)
    paint_treeline(img)
    paint_cabin(img)
    paint_shore(img)
    paint_dock(img)
    paint_lantern(img)
    paint_mug(img)
    paint_signs(img)
    save(img, "background.png")


# ---------------------------------------------------------------------------
# fire pit
# ---------------------------------------------------------------------------


def make_firepit():
    w, h = 96, 40
    img = blank(w, h)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, h - 12

    d.ellipse([cx - 38, cy - 8, cx + 38, cy + 16], fill=(*ASH, 255))

    stone_positions = [
        (-36, 4), (-26, 12), (-10, 15), (6, 15), (20, 11), (32, 4),
        (37, -5), (26, -13), (10, -17), (-8, -17), (-24, -13), (-35, -5),
    ]
    for i, (ox, oy) in enumerate(stone_positions):
        sx, sy = cx + ox, cy + oy
        r = 6 if i % 2 == 0 else 5
        d.ellipse([sx - r, sy - r * 0.75, sx + r, sy + r * 0.75], fill=(*STONE_DARK, 255))
        d.ellipse([sx - r + 2, sy - r * 0.75, sx + r - 3, sy + r * 0.75 - 2], fill=(*STONE_LIGHT, 255))

    logs = [
        (-30, 0, 26, -4, 5), (-24, -6, 30, -10, 5), (-8, -12, 34, -16, 5),
        (18, -2, -18, -8, 5), (24, -10, -14, -16, 5),
    ]
    for x1, y1, x2, y2, lw in logs:
        d.line([(cx + x1, cy + y1), (cx + x2, cy + y2)], fill=(*LOG_DARK, 255), width=lw + 2)
        d.line([(cx + x1, cy + y1), (cx + x2, cy + y2)], fill=(*LOG_BODY, 255), width=lw)
        d.line([(cx + x1, cy + y1 - 1), (cx + x2, cy + y2 - 1)], fill=(*LOG_HI, 255), width=1)

    save(img, "firepit.png")


# ---------------------------------------------------------------------------
# flame sprite sheet
# ---------------------------------------------------------------------------


def flame_band(height_frac, side_frac):
    metric = height_frac * 0.55 + side_frac * 0.55
    if metric < 0.22:
        return FIRE_CORE
    if metric < 0.48:
        return FIRE_INNER
    if metric < 0.75:
        return FIRE_MID
    return FIRE_OUTER


def make_flames(frames=6, fw=40, fh=58):
    sheet = blank(fw * frames, fh)
    for f in range(frames):
        frame = blank(fw, fh)
        px = frame.load()
        phase = f / frames * math.pi * 2
        base_w = fw * 0.34
        for row in range(fh):
            h = row / (fh - 1)
            height_from_base = 1 - h
            wobble = 1 + 0.22 * math.sin(height_from_base * 7 + phase * 2)
            width = base_w * (height_from_base ** 0.75) * wobble
            width = max(width, 0)
            center = fw / 2 + 3.2 * math.sin(height_from_base * 4 + phase)
            for col in range(fw):
                dx = col - center
                if abs(dx) > width:
                    continue
                side = abs(dx) / max(width, 0.001)
                edge_soft = width - abs(dx)
                color = flame_band(height_from_base, side)
                alpha = 255
                if edge_soft < 1.2:
                    alpha = int(255 * max(edge_soft / 1.2, 0.35))
                px[col, row] = (*color, alpha)
        sheet.paste(frame, (f * fw, 0), frame)
    save(sheet, "flames.png")


# ---------------------------------------------------------------------------
# foreground: viewer's own knees, seen from a first-person seat by the fire
# ---------------------------------------------------------------------------


def make_foreground():
    img = blank(SCENE_W, SCENE_H)
    d = ImageDraw.Draw(img)

    def knee(cx, cy, rx, ry, fold_dx, fold_dy):
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(*LAP_SHADOW, 255))
        fx, fy = cx + fold_dx, cy + fold_dy
        d.ellipse([fx - rx * 0.4, fy - ry * 0.35, fx + rx * 0.4, fy + ry * 0.35], fill=(*LAP_MID, 255))

    knee(58, SCENE_H + 24, 92, 74, -18, -22)
    knee(SCENE_W - 62, SCENE_H + 30, 96, 78, 20, -20)

    d.arc([58 - 92, SCENE_H + 24 - 74, 58 + 92, SCENE_H + 24 + 74], start=250, end=330,
          fill=(*LAP_RIM, 110), width=2)
    d.arc([SCENE_W - 62 - 96, SCENE_H + 30 - 78, SCENE_W - 62 + 96, SCENE_H + 30 + 78], start=200, end=280,
          fill=(*LAP_RIM, 110), width=2)

    save(img, "foreground.png")


# ---------------------------------------------------------------------------
# burnable item icons
# ---------------------------------------------------------------------------


def icon_canvas():
    return blank(24, 24)


def make_hoodie():
    img = icon_canvas()
    d = ImageDraw.Draw(img)
    body = (224, 220, 210)
    shadow = (176, 170, 158)
    hi = (245, 243, 238)
    cord = (140, 132, 120)
    heart = (168, 52, 56)

    d.polygon([(6, 9), (4, 6), (7, 4), (17, 4), (20, 6), (18, 9),
               (18, 20), (6, 20)], fill=(*shadow, 255))
    d.polygon([(7, 9), (6, 7), (8, 5), (16, 5), (18, 7), (17, 9),
               (17, 19), (7, 19)], fill=(*body, 255))
    d.polygon([(8, 6), (12, 4), (16, 6), (14, 10), (10, 10)], fill=(*shadow, 255))
    d.polygon([(9, 7), (12, 5), (15, 7), (13, 9), (11, 9)], fill=(*hi, 255))
    d.line([(11, 10), (10, 15)], fill=(*cord, 255))
    d.line([(13, 10), (14, 15)], fill=(*cord, 255))
    d.rectangle([3, 9, 6, 15], fill=(*shadow, 255))
    d.rectangle([18, 9, 21, 15], fill=(*body, 255))
    d.polygon([(11, 13), (12, 12), (13, 13), (13, 14), (12, 15), (11, 14)], fill=(*heart, 255))
    save(img, "item_hoodie.png", scale=3)


def make_letter():
    img = icon_canvas()
    d = ImageDraw.Draw(img)
    paper = (233, 223, 197)
    line = (150, 138, 116)
    flap = (206, 190, 158)
    seal = (176, 52, 46)

    d.rectangle([3, 6, 21, 19], fill=(*paper, 255))
    d.polygon([(3, 6), (12, 13), (21, 6)], fill=(*flap, 255))
    for ly in (14, 16, 18):
        d.line([(6, ly), (18, ly)], fill=(*line, 255))
    d.ellipse([10, 9, 14, 13], fill=(*seal, 255))
    save(img, "item_letter.png", scale=3)


def make_photo():
    img = icon_canvas()
    d = ImageDraw.Draw(img)
    frame = (240, 235, 222)
    sky = (150, 90, 90)
    ground = (40, 66, 52)
    fig = (28, 22, 24)

    d.rectangle([3, 3, 21, 21], fill=(*frame, 255))
    d.rectangle([5, 5, 19, 16], fill=(*sky, 255))
    d.rectangle([5, 13, 19, 16], fill=(*ground, 255))
    d.ellipse([15, 6, 18, 9], fill=(255, 214, 140, 255))
    d.polygon([(9, 15), (9, 10), (10, 9), (11, 10), (11, 15)], fill=(*fig, 255))
    d.polygon([(12, 15), (12, 10), (13, 9), (14, 10), (14, 15)], fill=(*fig, 255))
    save(img, "item_photo.png", scale=3)


def make_scarf():
    img = icon_canvas()
    d = ImageDraw.Draw(img)
    navy = (52, 66, 92)
    cream = (214, 204, 180)

    pts = [(4, 8), (20, 4), (22, 8), (14, 11), (20, 14), (18, 18), (10, 14), (6, 18), (3, 14)]
    d.polygon(pts, fill=(*navy, 255))
    for y in range(5, 18, 3):
        d.line([(4, y), (21, y - 2)], fill=(*cream, 180))
    d.line([(6, 18), (5, 21)], fill=(*navy, 255), width=2)
    d.line([(10, 14), (9, 21)], fill=(*cream, 255), width=1)
    save(img, "item_scarf.png", scale=3)


def make_trinket():
    img = icon_canvas()
    d = ImageDraw.Draw(img)
    gold = (196, 160, 78)
    gold_hi = (238, 210, 140)
    gem = (188, 56, 68)
    chain = (168, 138, 70)

    for y in range(3, 10):
        d.point((12, y), fill=(*chain, 255))
    d.ellipse([7, 10, 17, 20], outline=(*gold, 255), width=2)
    d.arc([8, 11, 16, 19], start=200, end=340, fill=(*gold_hi, 255), width=1)
    d.ellipse([10, 8, 14, 12], fill=(*gem, 255))
    d.ellipse([11, 9, 12, 10], fill=(255, 200, 200, 255))
    save(img, "item_trinket.png", scale=3)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    make_background()
    make_firepit()
    make_flames()
    make_foreground()
    make_hoodie()
    make_letter()
    make_photo()
    make_scarf()
    make_trinket()
    print("done")
