"""
图形验证码生成与校验
用 pillow 生成随机字母数字组合的 PNG 图片，内存字典存储（5 分钟过期）
"""
import random
import string
import io
import time
import uuid
from typing import Tuple

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    Image = None

# 内存存储：{captcha_id: {"code": "AB3X", "expires_at": timestamp}}
_store: dict = {}

CAPTCHA_TTL = 300  # 验证码有效期 5 分钟


def _random_color(min_val=0, max_val=128) -> Tuple[int, int, int]:
    return (
        random.randint(min_val, max_val),
        random.randint(min_val, max_val),
        random.randint(min_val, max_val),
    )


def _random_char() -> str:
    """生成随机字符（排除易混淆的 0OIl1）"""
    chars = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return random.choice(chars)


def generate_captcha(length: int = 4) -> Tuple[str, str]:
    """
    生成验证码图片
    :param length: 验证码字符数
    :return: (captcha_id, png_bytes_base64)
    """
    if Image is None:
        raise RuntimeError("pillow 未安装，请运行: pip install pillow")

    code = "".join(_random_char() for _ in range(length))
    captcha_id = uuid.uuid4().hex

    # 存到内存
    _store[captcha_id] = {
        "code": code,
        "expires_at": time.time() + CAPTCHA_TTL,
    }
    # 清理过期
    _clean_expired()

    # 生成图片
    width, height = 120, 44
    image = Image.new("RGB", (width, height), color=(240, 245, 250))
    draw = ImageDraw.Draw(image)

    # 干扰线
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=_random_color(100, 180), width=1)

    # 噪点
    for _ in range(30):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point((x, y), fill=_random_color(80, 180))

    # 写文字（用默认字体，每个字符独立绘制以增加不规则感）
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
        except (OSError, IOError):
            font = ImageFont.load_default()

    for i, ch in enumerate(code):
        x = 10 + i * 26 + random.randint(-4, 4)
        y = random.randint(4, 12)
        color = _random_color(0, 80)
        draw.text((x, y), ch, font=font, fill=color)

    # 轻微模糊使 OCR 更难
    image = image.filter(ImageFilter.GaussianBlur(radius=0.3))

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)

    import base64
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return captcha_id, f"data:image/png;base64,{b64}"


def verify_captcha(captcha_id: str, code: str) -> bool:
    """
    校验验证码，验证通过后立即删除（一次性）
    """
    if not captcha_id or not code:
        return False

    entry = _store.pop(captcha_id, None)
    if entry is None:
        return False

    if time.time() > entry["expires_at"]:
        return False

    return code.upper().strip() == entry["code"].upper()


def _clean_expired():
    """清理过期的验证码"""
    now = time.time()
    expired = [k for k, v in _store.items() if now > v["expires_at"]]
    for k in expired:
        _store.pop(k, None)
