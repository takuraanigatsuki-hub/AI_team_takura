"""
Генерирует иконки для PWA и .exe из встроенного SVG.
Запуск: python make_icons.py
Требует: pip install Pillow
"""

import os
import struct
import zlib

ICONS_DIR = os.path.join(os.path.dirname(__file__), "static", "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

# SVG-иконка робота (строка, затем encode — чтобы не было ошибки с кириллицей в bytes)
SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" rx="80" fill="#6c63ff"/>
  <rect x="136" y="120" width="240" height="200" rx="40" fill="#fff" opacity="0.95"/>
  <circle cx="196" cy="210" r="30" fill="#6c63ff"/>
  <circle cx="316" cy="210" r="30" fill="#6c63ff"/>
  <circle cx="196" cy="210" r="14" fill="#fff"/>
  <circle cx="316" cy="210" r="14" fill="#fff"/>
  <rect x="246" y="60" width="20" height="64" rx="10" fill="#fff" opacity="0.9"/>
  <circle cx="256" cy="52" r="20" fill="#ff6b6b"/>
  <rect x="176" y="270" width="160" height="24" rx="12" fill="#6c63ff" opacity="0.7"/>
  <rect x="116" y="344" width="280" height="140" rx="30" fill="#fff" opacity="0.9"/>
  <circle cx="196" cy="410" r="22" fill="#6c63ff" opacity="0.8"/>
  <circle cx="256" cy="410" r="22" fill="#ff6b6b" opacity="0.8"/>
  <circle cx="316" cy="410" r="22" fill="#4ecdc4" opacity="0.8"/>
  <rect x="56" y="344" width="44" height="100" rx="22" fill="#fff" opacity="0.8"/>
  <rect x="412" y="344" width="44" height="100" rx="22" fill="#fff" opacity="0.8"/>
</svg>'''.encode("utf-8")


def make_png_with_pillow(size: int, out_path: str):
    """Генерация PNG через Pillow (если установлен)."""
    try:
        from PIL import Image
        import io
        import cairosvg  # type: ignore
        png_data = cairosvg.svg2png(bytestring=SVG, output_width=size, output_height=size)
        img = Image.open(io.BytesIO(png_data))
        img.save(out_path, "PNG")
        print(f"  ✅ {out_path} ({size}x{size}) — через cairosvg+Pillow")
        return True
    except ImportError:
        pass

    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Фон
        r = int(size * 0.16)
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(108, 99, 255, 255))

        # Голова
        m = size // 512
        head_x, head_y = 136 * m, 120 * m
        head_w, head_h = 240 * m, 200 * m
        draw.rounded_rectangle([head_x, head_y, head_x + head_w, head_y + head_h],
                                radius=40 * m, fill=(255, 255, 255, 242))

        # Глаза
        for ex in [196, 316]:
            draw.ellipse([ex * m - 30 * m, 210 * m - 30 * m,
                          ex * m + 30 * m, 210 * m + 30 * m], fill=(108, 99, 255, 255))
            draw.ellipse([ex * m - 14 * m, 210 * m - 14 * m,
                          ex * m + 14 * m, 210 * m + 14 * m], fill=(255, 255, 255, 255))

        # Антенна
        draw.rounded_rectangle([246 * m, 60 * m, 266 * m, 124 * m],
                                radius=10 * m, fill=(255, 255, 255, 230))
        draw.ellipse([236 * m, 32 * m, 276 * m, 72 * m], fill=(255, 107, 107, 255))

        # Рот
        draw.rounded_rectangle([176 * m, 270 * m, 336 * m, 294 * m],
                                radius=12 * m, fill=(108, 99, 255, 178))

        # Тело
        draw.rounded_rectangle([116 * m, 344 * m, 396 * m, 484 * m],
                                radius=30 * m, fill=(255, 255, 255, 230))

        # Кнопки
        for bx, bc in [(196, (108, 99, 255, 204)),
                       (256, (255, 107, 107, 204)),
                       (316, (78, 205, 196, 204))]:
            draw.ellipse([bx * m - 22 * m, 410 * m - 22 * m,
                          bx * m + 22 * m, 410 * m + 22 * m], fill=bc)

        # Руки
        draw.rounded_rectangle([56 * m, 344 * m, 100 * m, 444 * m],
                                radius=22 * m, fill=(255, 255, 255, 204))
        draw.rounded_rectangle([412 * m, 344 * m, 456 * m, 444 * m],
                                radius=22 * m, fill=(255, 255, 255, 204))

        img.save(out_path, "PNG")
        print(f"  ✅ {out_path} ({size}x{size}) — через Pillow")
        return True
    except ImportError:
        return False


def make_minimal_png(size: int, out_path: str):
    """
    Создаёт минимальный PNG без Pillow —
    просто цветной квадрат с фиолетовым фоном.
    """
    def make_png(w, h, color_rgba):
        def chunk(name, data):
            c = zlib.crc32(name + data) & 0xFFFFFFFF
            return struct.pack('>I', len(data)) + name + data + struct.pack('>I', c)

        r, g, b, a = color_rgba
        raw = b''
        for _ in range(h):
            raw += b'\x00'
            for _ in range(w):
                raw += bytes([r, g, b, a])

        compressed = zlib.compress(raw, 9)
        ihdr_data = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
        png = b'\x89PNG\r\n\x1a\n'
        png += chunk(b'IHDR', ihdr_data)
        png += chunk(b'IDAT', compressed)
        png += chunk(b'IEND', b'')
        return png

    with open(out_path, 'wb') as f:
        f.write(make_png(size, size, (108, 99, 255, 255)))
    print(f"  ⚠️  {out_path} ({size}x{size}) — минимальный PNG (установите Pillow для красивой иконки)")


def make_ico(png_path_192: str, out_path: str):
    """Создаёт .ico из PNG для Windows."""
    try:
        from PIL import Image
        img = Image.open(png_path_192)
        ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(out_path, format='ICO', sizes=ico_sizes)
        print(f"  ✅ {out_path} — ICO для .exe")
    except ImportError:
        # Без Pillow — просто копируем png под именем ico (Windows примет)
        import shutil
        shutil.copy(png_path_192, out_path)
        print(f"  ⚠️  {out_path} — ICO (без Pillow, используется PNG)")


if __name__ == "__main__":
    print("🎨 Генерация иконок AI Team Room…\n")

    png192 = os.path.join(ICONS_DIR, "icon-192.png")
    png512 = os.path.join(ICONS_DIR, "icon-512.png")
    ico    = os.path.join(ICONS_DIR, "icon.ico")

    # Сохраняем SVG
    with open(os.path.join(ICONS_DIR, "icon.svg"), "wb") as f:
        f.write(SVG)
    print(f"  ✅ {os.path.join(ICONS_DIR, 'icon.svg')} — SVG источник")

    if not make_png_with_pillow(192, png192):
        make_minimal_png(192, png192)

    if not make_png_with_pillow(512, png512):
        make_minimal_png(512, png512)

    make_ico(png192, ico)

    print("\n✅ Готово! Иконки сохранены в static/icons/")
    print("   Для красивых иконок: pip install Pillow")
