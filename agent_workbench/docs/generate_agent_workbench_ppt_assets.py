from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


W = 1600
H = 900

SCRIPT_DIR = Path(__file__).resolve().parent
WORKBENCH_ROOT = SCRIPT_DIR.parent
ASSET_DIR = SCRIPT_DIR / "ppt_assets" / "agent_workbench_overview"

NAVY = "#0F172A"
SLATE = "#1E293B"
MIST = "#E2E8F0"
WHITE = "#F8FAFC"
INK = "#0B1220"
TEAL = "#14B8A6"
CYAN = "#38BDF8"
BLUE = "#2563EB"
AMBER = "#F59E0B"
ROSE = "#F43F5E"
GREEN = "#22C55E"
RED = "#EF4444"
LIGHT_BG = "#F6F8FC"
CARD = "#FFFFFF"
SOFT = "#D7DFEA"

FONT_REGULAR = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]
FONT_BOLD = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\arialbd.ttf",
]
FONT_MONO = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
]


def rgb(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def lighten(color: str, amount: float) -> tuple[int, int, int, int]:
    base = rgb(color)
    out = tuple(int(base[i] + (255 - base[i]) * amount) for i in range(3))
    return out + (255,)


def tint(color: str, amount: float, alpha: int) -> tuple[int, int, int, int]:
    base = lighten(color, amount)
    return base[:3] + (alpha,)


def find_font(candidates: Iterable[str], size: int) -> ImageFont.FreeTypeFont:
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        return find_font(FONT_MONO, size)
    return find_font(FONT_BOLD if bold else FONT_REGULAR, size)


def new_canvas(dark: bool = False) -> Image.Image:
    img = Image.new("RGBA", (W, H), rgb(NAVY if dark else LIGHT_BG))
    return img


def add_vertical_gradient(img: Image.Image, top: str, bottom: str) -> None:
    draw = ImageDraw.Draw(img)
    tr, tg, tb, _ = rgb(top)
    br, bg, bb, _ = rgb(bottom)
    for y in range(H):
        t = y / max(H - 1, 1)
        fill = (
            int(tr + (br - tr) * t),
            int(tg + (bg - tg) * t),
            int(tb + (bb - tb) * t),
            255,
        )
        draw.line((0, y, W, y), fill=fill)


def add_horizontal_gradient(img: Image.Image, left: str, right: str) -> None:
    draw = ImageDraw.Draw(img)
    lr, lg, lb, _ = rgb(left)
    rr, rg, rb, _ = rgb(right)
    for x in range(W):
        t = x / max(W - 1, 1)
        fill = (
            int(lr + (rr - lr) * t),
            int(lg + (rg - lg) * t),
            int(lb + (rb - lb) * t),
            255,
        )
        draw.line((x, 0, x, H), fill=fill)


def add_glow(img: Image.Image, center: tuple[int, int], radius: int, color: str, alpha: int) -> None:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cx, cy = center
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=rgb(color, alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius // 2))
    img.alpha_composite(overlay)


def add_grid(img: Image.Image, step: int, color: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(img)
    for x in range(0, W, step):
        draw.line((x, 0, x, H), fill=color, width=1)
    for y in range(0, H, step):
        draw.line((0, y, W, y), fill=color, width=1)


def add_noise_dots(img: Image.Image, count: int, color: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(img)
    rnd = random.Random(42)
    for _ in range(count):
        x = rnd.randint(0, W - 1)
        y = rnd.randint(0, H - 1)
        draw.point((x, y), fill=color)


def rounded_card(
    img: Image.Image,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    fill: tuple[int, int, int, int] | str,
    outline: tuple[int, int, int, int] | None = None,
    radius: int = 28,
    shadow: bool = True,
    shadow_alpha: int = 42,
    shadow_blur: int = 18,
) -> None:
    fill_rgba = rgb(fill) if isinstance(fill, str) else fill
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if shadow:
        draw.rounded_rectangle(
            (x, y + 10, x + w, y + h + 10),
            radius=radius,
            fill=(12, 18, 32, shadow_alpha),
        )
        overlay = overlay.filter(ImageFilter.GaussianBlur(shadow_blur))
        img.alpha_composite(overlay)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill_rgba, outline=outline, width=2 if outline else 0)
    img.alpha_composite(overlay)


def measure(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    if not text:
        return 0, 0
    left, top, right, bottom = draw.textbbox((0, 0), text, font=fnt)
    return right - left, bottom - top


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    paragraphs = text.split("\n")
    lines: list[str] = []
    for paragraph in paragraphs:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            trial = current + ch
            if not current or measure(draw, trial, fnt)[0] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def draw_wrapped_text(
    img: Image.Image,
    text: str,
    *,
    x: int,
    y: int,
    width: int,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int] | str,
    line_gap: int = 8,
    max_lines: int | None = None,
) -> int:
    draw = ImageDraw.Draw(img)
    fill_rgba = rgb(fill) if isinstance(fill, str) else fill
    lines = wrap_text(draw, text, fnt, width)
    if max_lines is not None:
        lines = lines[:max_lines]
    cursor = y
    _, line_h = measure(draw, "Ag", fnt)
    for line in lines:
        draw.text((x, cursor), line, font=fnt, fill=fill_rgba)
        cursor += line_h + line_gap
    return cursor


def draw_title(img: Image.Image, title: str, subtitle: str | None = None, *, dark: bool = False) -> None:
    fill = WHITE if dark else INK
    accent = rgb(CYAN if dark else BLUE)
    draw_wrapped_text(img, title, x=100, y=82, width=860, fnt=font(42, bold=True), fill=fill, line_gap=10)
    overlay = ImageDraw.Draw(img)
    overlay.rounded_rectangle((100, 154, 204, 162), radius=4, fill=accent)
    if subtitle:
        draw_wrapped_text(img, subtitle, x=100, y=186, width=930, fnt=font(20), fill=(226, 232, 240, 230) if dark else (71, 85, 105, 255))


def draw_pill(img: Image.Image, text: str, x: int, y: int, *, bg: str, fg: str, size: int = 18) -> int:
    draw = ImageDraw.Draw(img)
    fnt = font(size, bold=True)
    tw, th = measure(draw, text, fnt)
    w = tw + 34
    h = th + 18
    rounded_card(img, x, y, w, h, fill=rgb(bg, 235), radius=18, shadow=False)
    draw.text((x + 17, y + 8), text, font=fnt, fill=rgb(fg))
    return w


def draw_bullets(
    img: Image.Image,
    items: list[str],
    *,
    x: int,
    y: int,
    width: int,
    dark: bool = False,
    bullet_color: str = CYAN,
    text_size: int = 22,
) -> int:
    draw = ImageDraw.Draw(img)
    fill = rgb(WHITE if dark else INK)
    bullet_fill = rgb(bullet_color)
    body = font(text_size)
    cursor = y
    for item in items:
        draw.ellipse((x, cursor + 10, x + 10, cursor + 20), fill=bullet_fill)
        cursor = draw_wrapped_text(img, item, x=x + 24, y=cursor, width=width - 24, fnt=body, fill=fill, line_gap=6)
        cursor += 12
    return cursor


def draw_code_panel(
    img: Image.Image,
    title: str,
    lines: list[str],
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    accent: str = CYAN,
) -> None:
    rounded_card(img, x, y, w, h, fill=rgb(SLATE, 245), outline=tint(accent, 0.2, 120), radius=28)
    draw = ImageDraw.Draw(img)
    draw.text((x + 26, y + 18), title, font=font(18, bold=True), fill=rgb(WHITE))
    for i, dot in enumerate((ROSE, AMBER, GREEN)):
        draw.ellipse((x + w - 92 + i * 22, y + 18, x + w - 78 + i * 22, y + 32), fill=rgb(dot))
    code_font = font(16, mono=True)
    cursor_y = y + 56
    for line in lines:
        draw.text((x + 24, cursor_y), line, font=code_font, fill=rgb(MIST))
        cursor_y += 24


def draw_metric_card(
    img: Image.Image,
    title: str,
    value: str,
    note: str,
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    accent: str,
    dark: bool = False,
) -> None:
    bg = rgb("#111A2D", 232) if dark else rgb(CARD)
    rounded_card(img, x, y, w, h, fill=bg, outline=tint(accent, 0.15, 80), radius=28)
    draw = ImageDraw.Draw(img)
    primary = rgb(WHITE if dark else INK)
    secondary = (203, 213, 225, 255) if dark else (71, 85, 105, 255)
    draw.text((x + 24, y + 24), title, font=font(19, bold=True), fill=primary)
    draw.text((x + 24, y + 68), value, font=font(40, bold=True), fill=rgb(accent))
    draw_wrapped_text(img, note, x=x + 24, y=y + 130, width=w - 48, fnt=font(18), fill=secondary, line_gap=5)


def draw_arrow(img: Image.Image, x1: int, y1: int, x2: int, y2: int, *, color: str, width: int = 6) -> None:
    draw = ImageDraw.Draw(img)
    fill = rgb(color)
    draw.line((x1, y1, x2, y2), fill=fill, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 16
    p1 = (x2, y2)
    p2 = (x2 - head * math.cos(angle - math.pi / 6), y2 - head * math.sin(angle - math.pi / 6))
    p3 = (x2 - head * math.cos(angle + math.pi / 6), y2 - head * math.sin(angle + math.pi / 6))
    draw.polygon((p1, p2, p3), fill=fill)


def draw_outline_box(
    img: Image.Image,
    text: str,
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    accent: str,
    dark: bool = True,
    big: bool = False,
) -> None:
    fill = rgb("#0C1426", 210) if dark else rgb(WHITE)
    rounded_card(img, x, y, w, h, fill=fill, outline=tint(accent, 0.2, 90), radius=26)
    fnt = font(26 if big else 20, bold=True)
    draw_wrapped_text(
        img,
        text,
        x=x + 24,
        y=y + (h // 2 - (34 if big else 26)),
        width=w - 48,
        fnt=fnt,
        fill=WHITE if dark else INK,
        line_gap=6,
    )


def draw_circuit_hero(img: Image.Image, *, x: int, y: int, w: int, h: int) -> None:
    add_glow(img, (x + 180, y + 180), 180, CYAN, 80)
    add_glow(img, (x + 360, y + 90), 140, TEAL, 70)
    add_glow(img, (x + 480, y + 320), 180, BLUE, 60)
    overlay = ImageDraw.Draw(img)
    board = (x + 70, y + 80, x + w - 40, y + h - 70)
    overlay.rounded_rectangle(board, radius=42, outline=rgb(CYAN, 120), width=3, fill=rgb("#10213C", 150))
    overlay.rounded_rectangle((x + 210, y + 150, x + 450, y + 360), radius=32, outline=rgb(WHITE, 80), width=2, fill=rgb("#173156", 190))
    chip = (x + 270, y + 190, x + 390, y + 310)
    overlay.rounded_rectangle(chip, radius=24, fill=rgb("#0B1220"), outline=rgb(TEAL), width=3)
    for i in range(6):
        overlay.line((chip[0] - 30, chip[1] + 12 + i * 18, chip[0], chip[1] + 12 + i * 18), fill=rgb(CYAN, 180), width=3)
        overlay.line((chip[2], chip[1] + 12 + i * 18, chip[2] + 30, chip[1] + 12 + i * 18), fill=rgb(CYAN, 180), width=3)
    for px, py in ((x + 130, y + 210), (x + 150, y + 300), (x + 520, y + 180), (x + 550, y + 290), (x + 440, y + 430)):
        overlay.ellipse((px - 10, py - 10, px + 10, py + 10), fill=rgb(TEAL))
    trace_points = [
        ((x + 150, y + 210), (x + 240, y + 210), (x + 270, y + 220)),
        ((x + 150, y + 300), (x + 220, y + 300), (x + 270, y + 280)),
        ((x + 520, y + 180), (x + 430, y + 180), (x + 390, y + 220)),
        ((x + 550, y + 290), (x + 460, y + 290), (x + 390, y + 280)),
        ((x + 440, y + 430), (x + 440, y + 340), (x + 390, y + 310)),
    ]
    for pts in trace_points:
        overlay.line(pts, fill=rgb(CYAN, 160), width=4)
    draw_outline_box(img, "CONFIG", x=x + 40, y=y + 20, w=168, h=80, accent=TEAL, dark=True)
    draw_outline_box(img, "CLI", x=x + 250, y=y + h - 110, w=140, h=80, accent=CYAN, dark=True)
    draw_outline_box(img, "EVIDENCE", x=x + w - 240, y=y + 30, w=190, h=80, accent=AMBER, dark=True)
    draw_arrow(img, x + 210, y + 60, x + 260, y + 92, color=TEAL, width=4)
    draw_arrow(img, x + 390, y + h - 70, x + 420, y + 340, color=CYAN, width=4)
    draw_arrow(img, x + w - 240, y + 70, x + 500, y + 165, color=AMBER, width=4)


def terminal_excerpt(path: Path, count: int) -> list[str]:
    if not path.exists():
        return ["# missing file"]
    lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return lines[:count]


def slide_01() -> Image.Image:
    img = new_canvas(dark=True)
    add_vertical_gradient(img, "#081120", "#13284A")
    add_glow(img, (1360, 150), 220, CYAN, 80)
    add_glow(img, (1260, 520), 220, TEAL, 70)
    add_glow(img, (1100, 760), 180, BLUE, 55)
    add_noise_dots(img, 420, (255, 255, 255, 18))
    draw = ImageDraw.Draw(img)
    draw_pill(img, "STM32 Engineering Workflow", 100, 84, bg="#12304A", fg=WHITE, size=16)
    draw_wrapped_text(img, "agent_workbench", x=100, y=170, width=640, fnt=font(72, bold=True), fill=WHITE, line_gap=10)
    draw.text((118, 270), "把 STM32 + AI 研发流程", font=font(34, bold=True), fill=rgb("#C9F7FF"))
    draw.text((118, 320), "做成可复用闭环", font=font(34, bold=True), fill=rgb("#C9F7FF"))
    draw_wrapped_text(
        img,
        "面向研发同事的专业介绍版\n统一配置、统一命令、统一证据，降低协作成本和验证不确定性。",
        x=100,
        y=360,
        width=620,
        fnt=font(24),
        fill=(224, 231, 255, 220),
        line_gap=10,
    )
    chip_y = 510
    x = 100
    for label, bg, fg in [
        ("Single Source of Truth", "#10304C", WHITE),
        ("Evidence-first Verification", "#15384F", WHITE),
        ("Low-context Model Ready", "#1B334C", WHITE),
    ]:
        x += draw_pill(img, label, x, chip_y, bg=bg, fg=fg, size=16) + 14
    draw_wrapped_text(
        img,
        "基于 serial 仓库真实命令、任务文件和 session evidence 生成",
        x=100,
        y=780,
        width=600,
        fnt=font(18),
        fill=(186, 199, 215, 210),
    )
    draw_circuit_hero(img, x=880, y=120, w=610, h=600)
    return img


def slide_02() -> Image.Image:
    img = new_canvas()
    add_vertical_gradient(img, "#F8FBFF", "#EEF4FB")
    draw_title(img, "为什么需要 agent_workbench", "不是为了多一层脚本，而是为了把 STM32 + AI 的关键环节做成稳定工作流。")
    pain_cards = [
        ("命令入口分散", "构建、烧录、串口、验证各自分散，迁移机器和换人时容易失真。", CYAN),
        ("硬件参数容易靠猜", "定时器、串口、探针和验证条件容易变成经验口口相传。", TEAL),
        ("结论难复盘", "常见状态是“看起来好了”，但缺少 build / UART / assertion 的证据链。", AMBER),
        ("前端适配重复维护", "更换 OpenCode / Continue 等前端时，项目规则和接入文件容易重复造。", BLUE),
    ]
    positions = [(100, 220), (520, 220), (100, 470), (520, 470)]
    for (title, body, accent), (x, y) in zip(pain_cards, positions):
        rounded_card(img, x, y, 360, 190, fill=rgb(CARD), outline=tint(accent, 0.15, 86), radius=26)
        draw = ImageDraw.Draw(img)
        draw.ellipse((x + 26, y + 26, x + 62, y + 62), fill=rgb(accent))
        draw.text((x + 80, y + 24), title, font=font(24, bold=True), fill=rgb(INK))
        draw_wrapped_text(img, body, x=x + 26, y=y + 78, width=310, fnt=font(19), fill=(71, 85, 105, 255), line_gap=6)

    rounded_card(img, 1040, 220, 460, 440, fill=rgb("#0F1B33"), radius=34)
    draw = ImageDraw.Draw(img)
    draw.text((1074, 246), "没有统一控制平面时", font=font(26, bold=True), fill=rgb(WHITE))
    funnel_boxes = [
        ("分散工具链", 1120, 320, 300, 72, "#173156"),
        ("协作信息失真", 1155, 430, 230, 72, "#1E3A5F"),
        ("验证结果不可信", 1190, 540, 160, 72, "#27496D"),
    ]
    for label, x, y, w, h, fill in funnel_boxes:
        rounded_card(img, x, y, w, h, fill=rgb(fill), outline=rgb(CYAN, 90), radius=22, shadow=False)
        draw_wrapped_text(img, label, x=x + 22, y=y + 20, width=w - 44, fnt=font(22, bold=True), fill=WHITE)
    draw_arrow(img, 1270, 392, 1270, 424, color=CYAN, width=5)
    draw_arrow(img, 1270, 502, 1270, 534, color=CYAN, width=5)
    draw_metric_card(
        img,
        "workbench 的价值",
        "把这些环节拉回统一 CLI",
        "同一份配置、同一份命令入口、同一条 evidence 链，方便重复执行和团队对齐。",
        x=1040,
        y=698,
        w=460,
        h=138,
        accent=TEAL,
    )
    return img


def slide_03() -> Image.Image:
    img = new_canvas()
    add_horizontal_gradient(img, "#F7FAFF", "#EEF4FB")
    draw_title(img, "它到底是什么", "agent_workbench 是面向 STM32 项目的自动化控制平面，而不是某一个 AI 前端的私有脚本。")
    draw_wrapped_text(
        img,
        "它把 构建、烧录、串口、诊断、规划、验证、报告 和 AI/editor 集成收敛到统一 CLI 和统一配置中。",
        x=100,
        y=230,
        width=640,
        fnt=font(30, bold=True),
        fill=INK,
        line_gap=8,
    )
    draw_bullets(
        img,
        [
            "单一事实来源：agent_workbench.yaml",
            "统一入口：agent_workbench.bat / workbench.py",
            "核心能力与前端适配解耦：opencode、continue 只是 integration",
            "输出的不只是命令结果，还有 runtime 与 session evidence",
        ],
        x=100,
        y=330,
        width=600,
        dark=False,
        bullet_color=TEAL,
        text_size=22,
    )
    cards = [
        ("Build & Flash", "build / flash / reset", CYAN),
        ("UART & Diag", "uart / diag / monitor", TEAL),
        ("Plan & Verify", "plan / verify / compare", AMBER),
        ("Integration & Evidence", "integration / context / report", BLUE),
    ]
    positions = [(840, 230), (1170, 230), (840, 470), (1170, 470)]
    for (title, body, accent), (x, y) in zip(cards, positions):
        rounded_card(img, x, y, 260, 190, fill=rgb(CARD), outline=tint(accent, 0.18, 96), radius=24)
        draw = ImageDraw.Draw(img)
        draw.ellipse((x + 24, y + 24, x + 54, y + 54), fill=rgb(accent))
        draw.text((x + 72, y + 20), title, font=font(22, bold=True), fill=rgb(INK))
        draw_wrapped_text(img, body, x=x + 24, y=y + 84, width=210, fnt=font(19), fill=(71, 85, 105, 255))
    draw_code_panel(
        img,
        "Main Commands",
        [
            'cmd /c ".\\agent_workbench.bat doctor --json"',
            'cmd /c ".\\agent_workbench.bat build --json"',
            'cmd /c ".\\agent_workbench.bat plan ""add PWM ..."" --json"',
            'cmd /c ".\\agent_workbench.bat verify current --task ... --json"',
        ],
        x=820,
        y=705,
        w=680,
        h=120,
        accent=TEAL,
    )
    return img


def slide_04() -> Image.Image:
    img = new_canvas(dark=True)
    add_vertical_gradient(img, "#08111F", "#122A49")
    add_grid(img, 80, (255, 255, 255, 12))
    draw_title(img, "核心架构：配置、CLI、集成、证据四层", "前端中立 + 配置集中 + 证据沉淀，是这套工作台稳定性的核心。", dark=True)
    draw_outline_box(img, "agent_workbench.yaml\n单一事实来源", x=610, y=180, w=380, h=120, accent=TEAL, dark=True, big=True)
    draw_outline_box(img, "workbench.py + core/\n统一 CLI 能力", x=560, y=365, w=480, h=150, accent=CYAN, dark=True, big=True)
    draw_outline_box(img, "integrations/\nopencode | continue", x=140, y=590, w=310, h=130, accent=AMBER, dark=True)
    draw_outline_box(img, "runtime/\n当前运行产物", x=565, y=610, w=260, h=130, accent=TEAL, dark=True)
    draw_outline_box(img, "evidence/sessions/\n可复盘会话证据", x=1030, y=590, w=360, h=130, accent=BLUE, dark=True)
    draw_arrow(img, 800, 300, 800, 360, color=CYAN, width=6)
    draw_arrow(img, 620, 515, 310, 590, color=AMBER, width=5)
    draw_arrow(img, 800, 515, 695, 610, color=TEAL, width=5)
    draw_arrow(img, 980, 515, 1205, 590, color=BLUE, width=5)
    draw_metric_card(
        img,
        "Why it matters",
        "新前端只要接 integration",
        "新的 AI 前端通常只需要新增 integration 包；核心流程仍然依赖同一份 CLI 和同一份配置。",
        x=80,
        y=180,
        w=400,
        h=220,
        accent=CYAN,
        dark=True,
    )
    draw_metric_card(
        img,
        "Evidence-first",
        "runtime / sessions 分层沉淀",
        "runtime 关注最近一次执行，evidence/sessions 关注可归档、可复盘、可对比的工程记录。",
        x=1120,
        y=180,
        w=400,
        h=220,
        accent=TEAL,
        dark=True,
    )
    return img


def slide_05() -> Image.Image:
    img = new_canvas()
    add_vertical_gradient(img, "#FBFDFF", "#EEF4FB")
    draw_title(img, "日常最小使用路径", "第一次上手不需要记住所有命令，先记住这 5 个动作。")
    steps = [
        ("1", "doctor", "先确认环境和配置是通的", CYAN),
        ("2", "integration install", "给前端生成项目级接入文件", TEAL),
        ("3", "plan", "把自然语言需求转成可执行 playbook", BLUE),
        ("4", "build", "统一走构建入口", AMBER),
        ("5", "verify current", "一条命令完成验证闭环", GREEN),
    ]
    step_w = 250
    start_x = 70
    y = 330
    for idx, (num, title, body, accent) in enumerate(steps):
        x = start_x + idx * 300
        rounded_card(img, x, y, step_w, 220, fill=rgb(CARD), outline=tint(accent, 0.15, 92), radius=26)
        draw = ImageDraw.Draw(img)
        draw.ellipse((x + 22, y + 18, x + 70, y + 66), fill=rgb(accent))
        draw.text((x + 39, y + 24), num, font=font(22, bold=True), fill=rgb(WHITE))
        draw.text((x + 88, y + 22), title, font=font(22, bold=True), fill=rgb(INK))
        draw_wrapped_text(img, body, x=x + 24, y=y + 92, width=200, fnt=font(18), fill=(71, 85, 105, 255), line_gap=5)
        if idx < len(steps) - 1:
            draw_arrow(img, x + step_w, y + 110, x + 280, y + 110, color=CYAN, width=5)
    draw_code_panel(
        img,
        "Command Path",
        [
            'cmd /c ".\\agent_workbench.bat doctor --json"',
            'cmd /c ".\\agent_workbench.bat integration install opencode --json"',
            'cmd /c ".\\agent_workbench.bat plan ""add PWM output on PA8, 1kHz, 50% duty"" --json"',
            'cmd /c ".\\agent_workbench.bat build --json"',
            'cmd /c ".\\agent_workbench.bat verify current --task agent_workbench/tasks/cli_automation_regression.yaml --json"',
        ],
        x=80,
        y=620,
        w=1440,
        h=190,
        accent=BLUE,
    )
    return img


def slide_06() -> Image.Image:
    img = new_canvas(dark=True)
    add_vertical_gradient(img, "#09111F", "#112644")
    add_glow(img, (260, 220), 180, CYAN, 70)
    add_glow(img, (1260, 620), 210, BLUE, 60)
    draw_title(img, "为什么它对 AI 更友好", "把原来依赖模型记忆的内容，转移到可引用、可约束的 context 产物里。", dark=True)
    stages = [
        ("Analyze", ["*_brief.md", "*_facts.json", "*_constraints.json"]),
        ("Implement", ["*_paste.md", "edit scope", "stable strings"]),
        ("Verify", ["agent_state.json", "resume.md", "next commands"]),
    ]
    x_positions = [110, 450, 790]
    for (title, items), x in zip(stages, x_positions):
        rounded_card(img, x, 310, 260, 280, fill=rgb("#0E1A31", 230), outline=rgb(CYAN, 76), radius=28)
        draw = ImageDraw.Draw(img)
        draw.text((x + 24, 332), title, font=font(28, bold=True), fill=rgb(WHITE))
        draw_bullets(img, items, x=x + 24, y=392, width=200, dark=True, bullet_color=TEAL, text_size=18)
    draw_arrow(img, 370, 450, 438, 450, color=CYAN, width=5)
    draw_arrow(img, 710, 450, 778, 450, color=CYAN, width=5)
    brief_path = WORKBENCH_ROOT / "runtime" / "context_pack_feature_cli_automation_regression_verify_balanced_local_brief.md"
    excerpt = terminal_excerpt(brief_path, 14)
    draw_code_panel(img, "Local Model Brief", excerpt, x=1100, y=260, w=400, h=470, accent=TEAL)
    draw_pill(img, "阶段化", 110, 680, bg="#14304A", fg=WHITE)
    draw_pill(img, "低幻觉", 250, 680, bg="#14304A", fg=WHITE)
    draw_pill(img, "可续接", 390, 680, bg="#14304A", fg=WHITE)
    draw_metric_card(
        img,
        "关键收益",
        "一轮只做一个阶段",
        "例如先 analyze，再 implement，再 verify。上下文不足时直接 resume，而不是重新把整个仓库喂给模型。",
        x=110,
        y=750,
        w=1390,
        h=100,
        accent=CYAN,
        dark=True,
    )
    return img


def slide_07() -> Image.Image:
    img = new_canvas()
    add_vertical_gradient(img, "#F8FBFF", "#EEF4FB")
    draw_title(img, "为什么结果更可信", "最终结论来自 build、UART transcript、assertions 和 session summary，而不是模型口头判断。")
    rounded_card(img, 80, 230, 640, 540, fill=rgb(CARD), outline=tint(CYAN, 0.18, 88), radius=28)
    draw = ImageDraw.Draw(img)
    draw.text((110, 258), "Direct Verify Summary", font=font(26, bold=True), fill=rgb(INK))
    steps = [
        ("doctor", "pass", GREEN),
        ("build", "pass", GREEN),
        ("test_run", "fail", RED),
        ("uart_smoke", "pass", GREEN),
        ("feature_session", "skipped", AMBER),
    ]
    base_y = 328
    for i, (label, status, accent) in enumerate(steps):
        y = base_y + i * 78
        rounded_card(img, 110, y, 580, 56, fill=rgb("#F8FAFC"), outline=tint(accent, 0.18, 90), radius=18, shadow=False)
        draw.text((130, y + 14), label, font=font(21, bold=True), fill=rgb(INK))
        draw_pill(img, status.upper(), 560, y + 10, bg=accent, fg=WHITE, size=15)
    draw_wrapped_text(
        img,
        "价值：失败也会被结构化暴露出来，能够定位到底是 doctor、build、test 还是 uart_smoke 出了问题。",
        x=110,
        y=674,
        width=560,
        fnt=font(18),
        fill=(71, 85, 105, 255),
        line_gap=5,
    )

    rounded_card(img, 760, 230, 760, 540, fill=rgb("#0F1B33"), radius=28)
    draw.text((790, 258), "Session Summary", font=font(26, bold=True), fill=rgb(WHITE))
    draw_metric_card(img, "Verdict", "pass", "CLI probe completed successfully.", x=790, y=320, w=210, h=170, accent=GREEN, dark=True)
    draw_metric_card(img, "Assertions", "10 / 0 / 0", "pass / fail / skip", x=1025, y=320, w=210, h=170, accent=CYAN, dark=True)
    draw_metric_card(img, "Strongest Evidence", "saw_ready=True", "saw_prompt=True", x=1260, y=320, w=230, h=170, accent=AMBER, dark=True)
    draw_code_panel(
        img,
        "CLI Tail",
        [
            "[2026-04-08T13:15:30.654+00:00] < [ok] blue -> toggle",
            "[2026-04-08T13:15:30.655+00:00] < System status:",
            "[2026-04-08T13:15:30.657+00:00] < UART: USART2 @ 115200 8N1",
            "[2026-04-08T13:15:30.663+00:00] < cli>",
        ],
        x=790,
        y=535,
        w=700,
        h=180,
        accent=TEAL,
    )
    draw_pill(img, "可回放", 790, 740, bg="#14304A", fg=WHITE)
    draw_pill(img, "可复盘", 922, 740, bg="#14304A", fg=WHITE)
    draw_pill(img, "可对外说明", 1054, 740, bg="#14304A", fg=WHITE)
    return img


def slide_08() -> Image.Image:
    img = new_canvas(dark=True)
    add_vertical_gradient(img, "#09111F", "#142B4A")
    add_glow(img, (280, 240), 220, CYAN, 80)
    add_glow(img, (1280, 260), 180, AMBER, 70)
    add_glow(img, (1030, 690), 220, TEAL, 60)
    draw = ImageDraw.Draw(img)
    draw_pill(img, "Use Cases", 100, 92, bg="#12304A", fg=WHITE)
    draw_wrapped_text(img, "最后看三个实际使用场景", x=100, y=170, width=700, fnt=font(62, bold=True), fill=WHITE, line_gap=8)
    draw_wrapped_text(
        img,
        "不是抽象概念，而是都能在当前 serial 仓库里找到任务定义、命令路径或 evidence 产物的真实案例。",
        x=100,
        y=290,
        width=760,
        fnt=font(24),
        fill=(214, 225, 238, 230),
        line_gap=8,
    )
    case_cards = [
        ("案例 1", "CLI 自动化回归验证", CYAN, 100),
        ("案例 2", "定时器功能交付任务", TEAL, 470),
        ("案例 3", "低上下文模型协作", AMBER, 840),
    ]
    for label, title, accent, x in case_cards:
        rounded_card(img, x, 510, 320, 200, fill=rgb("#10213C", 220), outline=tint(accent, 0.18, 80), radius=28)
        draw.text((x + 28, 542), label, font=font(18, bold=True), fill=rgb(accent))
        draw_wrapped_text(img, title, x=x + 28, y=580, width=260, fnt=font(30, bold=True), fill=WHITE, line_gap=8)
    draw_circuit_hero(img, x=1020, y=90, w=470, h=340)
    return img


def slide_09() -> Image.Image:
    img = new_canvas()
    add_vertical_gradient(img, "#F9FBFF", "#EEF4FB")
    draw_title(img, "案例 1：CLI 自动化回归验证", "目标是让 USART2 文本 CLI 适合重复运行、可断言、可比较。")
    rounded_card(img, 80, 230, 690, 580, fill=rgb(CARD), outline=tint(CYAN, 0.18, 88), radius=28)
    draw = ImageDraw.Draw(img)
    draw.text((110, 258), "任务文件里的核心定义", font=font(26, bold=True), fill=rgb(INK))
    draw_code_panel(
        img,
        "cli_automation_regression.yaml",
        [
            "goal: Keep the USART2 text CLI command-driven,",
            "      automation-friendly, and safe for repeated debug sessions.",
            "verify.sequence:",
            "  - doctor",
            "  - build",
            "  - test",
            "  - debug",
            'needle: "STM32 UART CLI ready."',
            'needle: "[ok] all -> off"',
        ],
        x=110,
        y=300,
        w=630,
        h=330,
        accent=CYAN,
    )
    draw_bullets(
        img,
        [
            "用 acceptance.blackbox 把 ready banner、prompt、命令响应全部变成可机器判断的标准。",
            "verify.sequence 明确了 doctor -> build -> test -> debug 的执行顺序。",
        ],
        x=110,
        y=662,
        width=620,
        dark=False,
        bullet_color=TEAL,
        text_size=18,
    )

    rounded_card(img, 820, 230, 700, 580, fill=rgb("#0F1B33"), radius=28)
    draw.text((850, 258), "最终结果：session evidence", font=font(26, bold=True), fill=rgb(WHITE))
    draw_metric_card(img, "Verdict", "pass", "CLI probe OK", x=850, y=316, w=190, h=160, accent=GREEN, dark=True)
    draw_metric_card(img, "Assertions", "10 / 0 / 0", "pass / fail / skip", x=1062, y=316, w=190, h=160, accent=CYAN, dark=True)
    draw_metric_card(img, "Signals", "ready + prompt", "machine-readable markers", x=1274, y=316, w=200, h=160, accent=AMBER, dark=True)
    draw_code_panel(
        img,
        "CLI Transcript",
        [
            "> blue toggle",
            "< [ok] blue -> toggle",
            "< System status:",
            "< UART: USART2 @ 115200 8N1",
            "< cli>",
        ],
        x=850,
        y=520,
        w=624,
        h=190,
        accent=TEAL,
    )
    draw_wrapped_text(
        img,
        "结论不再是“看起来没问题”，而是 session_summary.md、cli_transcript.log 和 assertions.jsonl 共同给出的工程证据。",
        x=850,
        y=736,
        width=600,
        fnt=font(18),
        fill=(203, 213, 225, 255),
        line_gap=6,
    )
    return img


def slide_10() -> Image.Image:
    img = new_canvas(dark=True)
    add_vertical_gradient(img, "#08111F", "#122641")
    draw_title(img, "案例 2：定时器功能交付任务", "以 timer_led_blink 为例，看 workbench 如何把“功能需求”收敛成受控改动。", dark=True)
    rounded_card(img, 80, 230, 680, 580, fill=rgb("#0F1B33"), radius=28)
    draw = ImageDraw.Draw(img)
    draw.text((110, 258), "Implementation Brief", font=font(26, bold=True), fill=rgb(WHITE))
    draw_code_panel(
        img,
        "timer_led_blink",
        [
            "goal: Add a hardware timer (TIM3) that blinks",
            "      the RED LED (PB0) at approximately 1 Hz.",
            "include: Core/Src/main.c",
            "         Core/Src/stm32f1xx_it.c",
            "         Core/Inc/main.h",
            "verify: doctor, build, uart_smoke",
            "max_edit_files: 3",
        ],
        x=110,
        y=308,
        w=620,
        h=250,
        accent=CYAN,
    )
    draw_bullets(
        img,
        [
            "先把目标、范围、稳定字符串、可编辑文件列清楚，再进入实现。",
            "这样做的价值是把“功能开发”变成可解释、可审阅、可验证的任务卡。",
        ],
        x=110,
        y=596,
        width=610,
        dark=True,
        bullet_color=TEAL,
        text_size=18,
    )

    rounded_card(img, 810, 230, 710, 580, fill=rgb("#10213C", 232), radius=28)
    draw.text((842, 258), "工作方式从“自由发挥”变成“受控执行”", font=font(26, bold=True), fill=rgb(WHITE))
    draw_outline_box(img, "自然语言需求", x=850, y=330, w=180, h=86, accent=AMBER, dark=True)
    draw_outline_box(img, "plan / brief", x=1075, y=330, w=180, h=86, accent=CYAN, dark=True)
    draw_outline_box(img, "受控编辑范围", x=1300, y=330, w=180, h=86, accent=TEAL, dark=True)
    draw_arrow(img, 1030, 373, 1065, 373, color=CYAN, width=5)
    draw_arrow(img, 1255, 373, 1290, 373, color=CYAN, width=5)
    draw_outline_box(img, "doctor / build / uart_smoke", x=980, y=490, w=370, h=110, accent=GREEN, dark=True)
    draw_arrow(img, 1190, 418, 1190, 482, color=GREEN, width=5)
    draw_wrapped_text(
        img,
        "对研发同事来说，最大的好处不是多一份文档，而是以后别人接手时能明确看到：这次需求允许改哪里、为什么这样验证、最后留下了什么 evidence。",
        x=850,
        y=660,
        width=610,
        fnt=font(18),
        fill=(203, 213, 225, 255),
        line_gap=6,
    )
    return img


def slide_11() -> Image.Image:
    img = new_canvas()
    add_vertical_gradient(img, "#F9FBFF", "#EEF4FB")
    draw_title(img, "案例 3：低上下文模型也能稳定协作", "通过 context pack 把阶段、事实、限制和下一步命令结构化给模型。")
    rounded_card(img, 80, 230, 700, 580, fill=rgb(CARD), outline=tint(TEAL, 0.2, 86), radius=28)
    draw = ImageDraw.Draw(img)
    draw.text((110, 258), "阶段化协作路径", font=font(26, bold=True), fill=rgb(INK))
    draw_outline_box(img, "analyze", x=120, y=340, w=160, h=90, accent=CYAN, dark=False)
    draw_outline_box(img, "implement", x=320, y=340, w=160, h=90, accent=TEAL, dark=False)
    draw_outline_box(img, "verify", x=520, y=340, w=160, h=90, accent=AMBER, dark=False)
    draw_arrow(img, 280, 385, 312, 385, color=CYAN, width=5)
    draw_arrow(img, 480, 385, 512, 385, color=CYAN, width=5)
    draw_bullets(
        img,
        [
            "每一轮都只处理当前阶段，避免“分析、改代码、跑验证”混在一起。",
            "facts / constraints / paste / resume 把上下文预算和行为边界都明示出来。",
            "上下文满了以后直接 resume，而不是重新回顾整个仓库。",
        ],
        x=120,
        y=500,
        width=540,
        dark=False,
        bullet_color=TEAL,
        text_size=18,
    )

    brief_path = WORKBENCH_ROOT / "runtime" / "context_pack_feature_cli_automation_regression_verify_balanced_local_brief.md"
    excerpt = terminal_excerpt(brief_path, 16)
    draw_code_panel(img, "Real Brief Excerpt", excerpt, x=840, y=230, w=680, h=410, accent=CYAN)
    draw_metric_card(
        img,
        "Forbidden Assumptions",
        "不要凭源码印象下结论",
        "brief 会明确写出 allowed reads / edits 与 forbidden assumptions，帮助模型在证据边界内行动。",
        x=840,
        y=670,
        w=680,
        h=140,
        accent=AMBER,
        dark=False,
    )
    return img


def slide_12() -> Image.Image:
    img = new_canvas(dark=True)
    add_vertical_gradient(img, "#08111F", "#142A48")
    add_glow(img, (280, 230), 200, CYAN, 80)
    add_glow(img, (1280, 660), 240, TEAL, 70)
    draw_pill(img, "Takeaways", 100, 92, bg="#12304A", fg=WHITE)
    draw_wrapped_text(img, "如果今天只带走三件事", x=100, y=170, width=720, fnt=font(62, bold=True), fill=WHITE)
    takeaway_cards = [
        ("1", "它不是前端附属脚本", "它是自动化控制平面，前端只是 integration。", CYAN),
        ("2", "第一次上手\n先记住 5 个动作", "doctor -> plan -> build -> verify。", TEAL),
        ("3", "最终结论\n一定要看 evidence", "build、transcript、assertions、summary 才是可复盘依据。", AMBER),
    ]
    for i, (num, title, body, accent) in enumerate(takeaway_cards):
        x = 100 + i * 500
        rounded_card(img, x, 330, 430, 260, fill=rgb("#0F1B33", 232), outline=tint(accent, 0.18, 90), radius=30)
        draw = ImageDraw.Draw(img)
        draw.ellipse((x + 26, 356, x + 82, 412), fill=rgb(accent))
        draw.text((x + 47, 366), num, font=font(24, bold=True), fill=rgb(WHITE))
        draw_wrapped_text(img, title, x=x + 108, y=356, width=290, fnt=font(26, bold=True), fill=WHITE, line_gap=6)
        draw_wrapped_text(img, body, x=x + 26, y=442, width=374, fnt=font(18), fill=(203, 213, 225, 255), line_gap=6)
    draw_metric_card(
        img,
        "Recommended Next Step",
        "把这套 deck 当成团队统一口径",
        "后续如果你愿意，我可以继续把它拆成“演讲稿备注版”或“老板汇报版”，也可以再导出 PDF 预览版。",
        x=100,
        y=670,
        w=1400,
        h=140,
        accent=CYAN,
        dark=True,
    )
    return img


SLIDES = [
    slide_01,
    slide_02,
    slide_03,
    slide_04,
    slide_05,
    slide_06,
    slide_07,
    slide_08,
    slide_09,
    slide_10,
    slide_11,
    slide_12,
]


def save_image(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, format="PNG", optimize=True)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for idx, builder in enumerate(SLIDES, start=1):
        image = builder()
        slide_path = ASSET_DIR / f"slide_{idx:02d}.png"
        save_image(image, slide_path)
        print(slide_path)


if __name__ == "__main__":
    main()
