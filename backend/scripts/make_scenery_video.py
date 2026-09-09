# -*- coding: utf-8 -*-
"""生成登录页山水动态背景视频（程序化渲染，非第三方素材，无版权风险，断网可跑）。

用法：python backend/scripts/make_scenery_video.py
输出：frontend/media/scenery.mp4（12s 无缝循环）+ frontend/media/scenery-poster.jpg
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "frontend-v2" / "public" / "media"
OUT_VIDEO = OUT_DIR / "scenery.mp4"
OUT_POSTER = OUT_DIR / "scenery-poster.jpg"

W, H = 1600, 900
FPS = 24
SECONDS = 12
FRAMES = FPS * SECONDS
WATER_Y = int(0.74 * H)
SUN_X, SUN_Y = int(0.70 * W), int(0.40 * H)

TAU = 2 * math.pi


def ph(k: float, t: float, p: float = 0.0) -> float:
    """整数周期相位：所有随时间变化的量都按整周期运动，保证 t=0 与 t=1 画面一致（无缝循环）。"""
    return TAU * (k * t + p)


def lerp_row_gradient(stops: list[tuple[float, tuple[int, int, int]]]) -> np.ndarray:
    """按 y 位置的多段线性渐变，返回 (H,3) 每行颜色。stops: [(y_ratio, rgb), ...] 升序。"""
    ys = np.arange(H, dtype=np.float32) / H
    rows = np.zeros((H, 3), dtype=np.float32)
    for i in range(len(stops) - 1):
        y0, c0 = stops[i]
        y1, c1 = stops[i + 1]
        seg = (ys >= y0) & (ys <= y1)
        w = np.clip((ys[seg] - y0) / max(y1 - y0, 1e-6), 0, 1)[:, None]
        rows[seg] = np.asarray(c0, np.float32) * (1 - w) + np.asarray(c1, np.float32) * w
    return rows


def sky_gradient() -> np.ndarray:
    rows = lerp_row_gradient(
        [
            (0.00, (24, 42, 66)),
            (0.28, (62, 92, 118)),
            (0.55, (148, 164, 168)),
            (0.72, (232, 192, 140)),
            (0.765, (238, 200, 150)),
            (1.00, (14, 32, 44)),
        ]
    )
    return np.repeat(rows[:, None, :], W, axis=1)


def draw_sun(frame: np.ndarray, t: float) -> None:
    """太阳 + 呼吸光晕（叠加暖色）。"""
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xs - SUN_X) ** 2 + (ys - SUN_Y) ** 2)
    core_r = 44 + 3 * math.sin(ph(1, t))
    glow = np.exp(-np.maximum(d - core_r, 0) / 150.0) * (0.40 + 0.08 * math.sin(ph(1, t)))
    disc = np.clip((core_r - d) / 10.0, 0, 1)  # 实心圆盘 + 软边缘（否则成空心圆环）
    sun_color = np.asarray((255, 224, 168), np.float32)
    strength = np.clip(glow + disc * 0.95, 0, 1)[..., None]
    frame[:] = frame * (1 - strength) + sun_color * strength


MOUNTAIN_LAYERS = [
    # (base_y_ratio, color, alpha, 幅度参数[(amp, freq, phase)], 视差速度)
    (0.52, (112, 132, 156), 0.50, [(38, 2.1, 0.10), (16, 4.7, 0.55), (7, 9.3, 0.20)], 1),
    (0.60, (86, 108, 130), 0.68, [(46, 1.7, 0.45), (20, 3.9, 0.05), (8, 8.1, 0.70)], 2),
    (0.66, (60, 80, 100), 0.85, [(40, 1.4, 0.80), (18, 3.3, 0.30), (7, 6.7, 0.50)], -1),
    (0.695, (38, 56, 72), 0.96, [(26, 1.9, 0.25), (12, 4.3, 0.85), (5, 7.7, 0.40)], 1),
]


def draw_mountains(frame: np.ndarray, t: float) -> None:
    xs = np.arange(W, dtype=np.float32)
    for base_r, color, alpha, waves, drift in MOUNTAIN_LAYERS:
        ridge = np.full(W, base_r * H, np.float32)
        for amp, freq, phase in waves:
            ridge += amp * np.sin(xs / W * TAU * freq + ph(drift * 0.05, t, phase))
        ys = np.arange(H, dtype=np.float32)[:, None]
        below = (ys >= ridge[None, :]).astype(np.float32)
        fade_h = 0.30 * H
        depth = np.clip((ys - ridge[None, :]) / fade_h, 0, 1)
        a = alpha * below * (1 - depth) ** 1.4
        a = a[..., None]
        frame[:] = frame * (1 - a) + np.asarray(color, np.float32) * a


def draw_mist(frame: np.ndarray, t: float) -> None:
    """两带山间流雾（解析软边缘，避免逐帧高斯模糊）。"""
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    for center_r, height, amp, k, phase in [
        (0.62, 0.055, 0.16, 2, 0.0),
        (0.70, 0.045, 0.13, 3, 0.35),
    ]:
        band = np.exp(-((ys - center_r * H) ** 2) / (2 * (height * H) ** 2))
        sway = 0.5 + 0.5 * np.sin(xs / W * TAU * 2 + ph(k, t, phase))
        a = amp * band * (0.45 + 0.55 * sway)
        mist_color = np.asarray((214, 224, 228), np.float32)
        frame[:] = frame * (1 - a[..., None]) + mist_color * a[..., None]


def draw_water(frame: np.ndarray, t: float) -> None:
    """水面基色 + 流动波光 + 日光倒影带。"""
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    water = ys >= WATER_Y
    if not water.any():
        return
    glint = (
        np.sin(xs * 0.028 + ph(2, t))
        * np.sin(xs * 0.007 - ph(3, t, 0.2))
        * np.sin(ys * 0.12 + 0.5)
    )
    streak = np.clip((glint - 0.62) / 0.38, 0, 1) * water
    glint_color = np.asarray((172, 206, 216), np.float32)
    a = (streak * 0.20)[..., None]
    frame[:] = frame * (1 - a) + glint_color * a
    # 日光倒影：太阳正下方竖向光带，随波闪动
    col = np.exp(-((xs - SUN_X) ** 2) / (2 * 55.0**2))
    flicker = 0.5 + 0.5 * np.sin(ys * 0.9 + ph(4, t))
    reflect = np.clip(col[None, :] * (0.12 + 0.25 * flicker), 0, 1) * water
    warm = np.asarray((255, 206, 140), np.float32)
    a = reflect[..., None]
    frame[:] = frame * (1 - a) + warm * a


def draw_vignette(frame: np.ndarray) -> None:
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xs - W / 2) / (W / 2)) ** 2 + ((ys - H / 2) / (H / 2)) ** 2)
    a = np.clip((d - 0.85) / 0.5, 0, 1) * 0.22
    frame[:] = frame * (1 - a[..., None])


BOAT_LAYER = None


def build_boat() -> Image.Image:
    """乌篷船剪影模板（RGBA）。"""
    img = Image.new("RGBA", (150, 74), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    dark = (26, 38, 50, 235)
    d.polygon([(8, 46), (142, 46), (120, 64), (30, 64)], fill=dark)
    d.arc([30, 8, 96, 52], start=180, end=360, fill=dark, width=7)
    d.line([(74, 30), (74, 18)], fill=dark, width=4)
    d.line([(74, 22), (104, 30)], fill=dark, width=3)
    return img


def draw_boat(base: Image.Image, t: float) -> None:
    global BOAT_LAYER
    if BOAT_LAYER is None:
        BOAT_LAYER = build_boat()
    bob = 4 * math.sin(ph(2, t))
    angle = 1.6 * math.sin(ph(2, t, 0.18))
    sway = 14 * math.sin(ph(1, t, 0.1))
    x = int(0.30 * W + sway)
    y = int(0.795 * H + bob)  # 漂在开阔水面，避开山脚
    boat = BOAT_LAYER.rotate(angle, resample=Image.BICUBIC, expand=False)
    base.alpha_composite(boat, (x - 75, y - 40))
    d = ImageDraw.Draw(base)
    d.ellipse([x - 52, y + 22, x + 52, y + 30], fill=(12, 26, 36, 90))


def draw_birds(base: Image.Image, t: float) -> None:
    d = ImageDraw.Draw(base)
    for i, (y0, scale, speed, off) in enumerate(
        [(0.24, 1.0, 1, 0.05), (0.30, 0.8, 1, 0.55), (0.20, 0.65, 2, 0.35)]
    ):
        u = (t * speed + off) % 1.0
        x = -90 + (W + 180) * u
        y = y0 * H + 34 * math.sin(ph(1, t, off))
        flap = math.sin(ph(5, t, off * 3)) * 0.55 + 0.7
        s = 13 * scale
        fade = min(1.0, 4 * min(u, 1 - u))  # 进出画面淡入淡出
        alpha = int(200 * fade)
        color = (34, 50, 64, alpha)
        w = max(2, int(2.4 * scale))
        d.line([(x - s, y - s * flap * 0.9), (x, y)], fill=color, width=w)
        d.line([(x, y), (x + s, y - s * flap * 0.9)], fill=color, width=w)


def render_frame(t: float) -> Image.Image:
    frame = sky_gradient()
    draw_sun(frame, t)
    draw_mountains(frame, t)
    draw_mist(frame, t)
    draw_water(frame, t)
    draw_vignette(frame)
    base = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    draw_boat(base, t)
    draw_birds(base, t)
    return base.convert("RGB")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "26",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-an", str(OUT_VIDEO),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(FRAMES):
        img = render_frame(i / FRAMES)
        if i == int(FRAMES * 0.15):
            img.save(OUT_POSTER, quality=85)
        proc.stdin.write(img.tobytes())
        if i % 48 == 0:
            print(f"frame {i}/{FRAMES}")
    proc.stdin.close()
    proc.wait()
    size_mb = OUT_VIDEO.stat().st_size / 1048576
    print(f"OK {OUT_VIDEO} ({size_mb:.2f} MB) + {OUT_POSTER}")


if __name__ == "__main__":
    main()
