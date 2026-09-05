# -*- coding: utf-8 -*-
"""生成 toC 页面水墨山水画背景图（程序化渲染，非第三方素材，无版权风险，断网可跑）。

用法：python backend/scripts/make_ink_backdrops.py
输出：frontend/media/ink-hero.jpg（页头宣纸横幅）+ ink-body.jpg（正文宣纸底纹）+ ink-foot.jpg（页脚墨色横幅）
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "media"
TAU = 2 * math.pi

PAPER = np.asarray((249, 245, 234), np.float32)
MIST = (252, 250, 242)


def noise2d(w: int, h: int, cells: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, int(cells * h / w)), cells)).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    return np.asarray(img, np.float32) / 255.0


def blend(base: np.ndarray, color, alpha: np.ndarray) -> None:
    a = np.clip(alpha, 0, 1)[..., None]
    base[:] = base * (1 - a) + np.asarray(color, np.float32) * a


def streaks2d(w: int, h: int, seed: int) -> np.ndarray:
    """纵向皴笔纹理：小网格纵向拉伸成竖向笔触。"""
    rng = np.random.default_rng(seed)
    small = rng.random((3, 72)).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    return np.asarray(img, np.float32) / 255.0


def ink_layer(base: np.ndarray, w: int, h: int, base_r: float, amp_scale: float,
              color, alpha_peak: float, fade_r: float, seed: int,
              x_shape=None, ink_noise: float = 0.76) -> None:
    """水墨山层：山脊一线浓墨，向下晕染渐淡；噪声调制出干湿浓淡的笔触感。"""
    ys, _ = np.mgrid[0:h, 0:w].astype(np.float32)
    xs = np.arange(w, dtype=np.float32)
    ridge = np.full(w, base_r * h, np.float32)
    for amp, freq, phase in [(30, 1.6, 0.1), (16, 3.4, 0.55), (7, 7.1, 0.3), (4, 12.7, 0.8)]:
        ridge += amp * amp_scale * np.sin(xs / w * TAU * freq + phase)
    d = ys - ridge[None, :]
    edge = np.exp(-np.abs(d) / 3.5) * 0.55                      # 山脊上下一线浓墨
    tail_short = np.where(d > 0, np.exp(-d / (fade_r * h)), 0.0)         # 近脊浓墨带
    tail_long = np.where(d > 0, np.exp(-d / (fade_r * 2.4 * h)), 0.0)    # 远端淡墨余韵
    wash = 0.62 * tail_short + 0.38 * tail_long
    alpha = alpha_peak * np.clip(edge + wash, 0, 1)
    alpha *= (1 - ink_noise) + ink_noise * noise2d(w, h, 10, seed) * 1.5
    alpha *= 0.68 + 0.64 * streaks2d(w, h, seed + 40)           # 纵向皴笔
    if x_shape is not None:
        alpha *= x_shape
    blend(base, color, alpha)


def mist_band(base: np.ndarray, w: int, h: int, center_r: float, height_r: float,
              peak: float, seed: int) -> None:
    """山脚云雾：窄带 + 噪声，只压住山根，不漫全图。"""
    ys, _ = np.mgrid[0:h, 0:w].astype(np.float32)
    band = np.exp(-((ys - center_r * h) ** 2) / (2 * (height_r * h) ** 2))
    n = noise2d(w, h, 6, seed)
    blend(base, MIST, peak * band * (0.4 + 0.6 * n))


def grain(base: np.ndarray, amp: float, seed: int) -> None:
    n = noise2d(base.shape[1], base.shape[0], 240, seed)
    base[:] += ((n - 0.5) * 2 * amp)[..., None]


def paper_base(w: int, h: int) -> np.ndarray:
    base = np.repeat(PAPER[None, None, :], h, axis=0).repeat(w, axis=1)
    grain(base, 2.0, 7)
    return base


def draw_boat(base_img: Image.Image, x: int, y: int, scale: float, color, alpha: int) -> None:
    d = ImageDraw.Draw(base_img, "RGBA")
    s = scale
    c = (*color, alpha)
    d.polygon([(x - 34 * s, y), (x + 34 * s, y), (x + 26 * s, y + 7 * s), (x - 26 * s, y + 7 * s)], fill=c)
    d.arc([x - 14 * s, y - 16 * s, x + 10 * s, y + 2 * s], start=180, end=360, fill=c, width=max(2, int(3 * s)))
    d.line([(x - 30 * s, y + 11 * s), (x + 30 * s, y + 11 * s)], fill=(*color, int(alpha * 0.35)), width=2)


def draw_birds(base_img: Image.Image, spots, color, alpha: int) -> None:
    d = ImageDraw.Draw(base_img, "RGBA")
    for x, y, s in spots:
        c = (*color, alpha)
        d.line([(x - s, y - s * 0.5), (x, y)], fill=c, width=max(2, int(s * 0.28)))
        d.line([(x, y), (x + s, y - s * 0.5)], fill=c, width=max(2, int(s * 0.28)))


def draw_seal(img: Image.Image, x: int, y: int, size: int, alpha: int = 78) -> None:
    """淡朱砂方印：印框 + 内格，仿真篆刻观感。"""
    d = ImageDraw.Draw(img, "RGBA")
    c = (172, 58, 46, alpha)
    d.rounded_rectangle([x, y, x + size, y + size], radius=int(size * 0.12), outline=c, width=max(3, size // 14))
    pad = int(size * 0.16)
    mid = x + size // 2
    midy = y + size // 2
    d.line([(mid, y + pad), (mid, y + size - pad)], fill=c, width=2)
    d.line([(x + pad, midy), (x + size - pad, midy)], fill=c, width=2)


def make_body() -> None:
    """正文底纹 1600x1200：宣纸底，下部三分之一淡墨远山 + 云雾 + 孤舟，上部大面积留白。"""
    w, h = 1600, 1200
    base = paper_base(w, h)
    ink_layer(base, w, h, 0.64, 1.0, (168, 174, 166), 0.5, 0.085, seed=11)
    mist_band(base, w, h, 0.705, 0.022, 0.5, seed=12)
    ink_layer(base, w, h, 0.75, 0.95, (104, 116, 108), 0.62, 0.075, seed=13)
    mist_band(base, w, h, 0.795, 0.02, 0.55, seed=14)
    ink_layer(base, w, h, 0.86, 0.85, (40, 52, 48), 0.78, 0.07, seed=15)
    # 水面一线淡墨 + 孤舟
    ys, _ = np.mgrid[0:h, 0:w].astype(np.float32)
    blend(base, (72, 84, 78), 0.22 * np.exp(-((ys - 0.905 * h) ** 2) / (2 * (2.2) ** 2)))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    draw_boat(img, int(w * 0.30), int(h * 0.885), 0.95, (44, 54, 50), 170)
    draw_birds(img, [(int(w * 0.66), int(h * 0.36), 13), (int(w * 0.72), int(h * 0.31), 9)], (70, 82, 76), 140)
    draw_seal(img, w - 128, 58, 56, alpha=70)
    img.save(OUT / "ink-body.jpg", quality=88)
    print("ink-body.jpg", img.size)


def make_hero() -> None:
    """页头横幅 1920x400：宣纸底 + 底部墨山，标题区（左上）留白，淡金月右上。"""
    w, h = 1920, 400
    base = paper_base(w, h)
    # 淡金圆月（右上，避免压标题）
    my, mx = np.mgrid[0:h, 0:w].astype(np.float32)
    dm = np.sqrt((mx - w * 0.84) ** 2 + (my - h * 0.22) ** 2)
    moon = np.clip(1 - dm / 26.0, 0, 1) * 0.5 + np.exp(-dm / 76.0) * 0.12
    blend(base, (222, 196, 138), moon)
    calm_left = (0.72 + 0.28 * np.linspace(0, 1, w, dtype=np.float32))[None, :]
    ink_layer(base, w, h, 0.60, 0.9, (162, 170, 162), 0.45, 0.10, seed=21, x_shape=calm_left)
    mist_band(base, w, h, 0.665, 0.026, 0.45, seed=22)
    ink_layer(base, w, h, 0.74, 0.85, (96, 110, 102), 0.6, 0.09, seed=23, x_shape=calm_left)
    mist_band(base, w, h, 0.80, 0.022, 0.5, seed=24)
    ink_layer(base, w, h, 0.89, 0.8, (36, 48, 44), 0.78, 0.08, seed=25, x_shape=calm_left)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    draw_birds(img, [(int(w * 0.62), int(h * 0.26), 12), (int(w * 0.67), int(h * 0.21), 8)], (66, 78, 72), 150)
    img.save(OUT / "ink-hero.jpg", quality=88)
    print("ink-hero.jpg", img.size)


def make_foot() -> None:
    """页脚横幅 1920x420：墨色夜山收底——远山雾白、近山浓墨，与宣纸页头呼应。"""
    w, h = 1920, 420
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    top, bottom = np.asarray((36, 62, 56), np.float32), np.asarray((14, 30, 27), np.float32)
    base = top[None, :] * (1 - ys) + bottom[None, :] * ys
    base = np.repeat(base[:, None, :], w, axis=1)
    ink_layer(base, w, h, 0.52, 1.0, (118, 134, 124), 0.55, 0.085, seed=31)
    mist_band(base, w, h, 0.64, 0.025, 0.16, seed=32)
    ink_layer(base, w, h, 0.74, 0.9, (6, 14, 13), 0.9, 0.10, seed=33)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    draw_birds(img, [(int(w * 0.32), int(h * 0.22), 10)], (196, 208, 200), 110)
    img.save(OUT / "ink-foot.jpg", quality=88)
    print("ink-foot.jpg", img.size)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make_body()
    make_hero()
    make_foot()
    print("OK")
