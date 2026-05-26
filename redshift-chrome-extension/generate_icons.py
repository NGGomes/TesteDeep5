#!/usr/bin/env python3
"""
Gera os ícones PNG da extensão Chrome a partir de SVG.
Execute: python generate_icons.py
Requer: pip install cairosvg (opcional) ou pillow
"""

import base64
import struct
import zlib

# SVG do ícone RedShift
SVG_ICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="20" fill="#e8192c"/>
  <text x="64" y="85" text-anchor="middle"
        font-family="Arial Black, sans-serif"
        font-size="62" font-weight="900"
        fill="white" letter-spacing="-3">RS</text>
</svg>'''


def create_png(size: int) -> bytes:
    """Cria um PNG mínimo com fundo vermelho e texto RS."""
    # PNG header
    png_header = b'\x89PNG\r\n\x1a\n'

    def chunk(name: bytes, data: bytes) -> bytes:
        c = name + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)

    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    ihdr = chunk(b'IHDR', ihdr_data)

    # Image data — red background
    red  = (232, 25,  44)
    white = (255, 255, 255)

    rows = []
    for y in range(size):
        row = b'\x00'  # filter byte
        for x in range(size):
            # Simple RS text approximation with colored blocks
            cx, cy = x - size//2, y - size//2
            # Rounded rectangle background
            r = min(size * 0.15, 10)
            in_rect = (abs(cx) < size//2 - r and abs(cy) < size//2 - r) or \
                      (abs(cx) < size//2 - r//2 and abs(cy) < size//2) or \
                      (abs(cx) < size//2 and abs(cy) < size//2 - r//2)

            pixel = red if in_rect else (0, 0, 0)

            # Simple "RS" letters in white (rough approximation)
            nx = x / size
            ny = y / size

            # R letter region (left half)
            if 0.2 < nx < 0.48 and 0.25 < ny < 0.75:
                # R stem
                if 0.2 < nx < 0.28:
                    pixel = white
                # R top bowl
                elif ny < 0.5 and nx < 0.44:
                    if 0.28 < ny < 0.32 or 0.46 < ny < 0.50:
                        pixel = white
                    elif 0.28 < nx < 0.44 and (0.28 < ny < 0.50):
                        if nx > 0.38:
                            pixel = white
                # R leg
                elif ny > 0.5 and nx > 0.28 and (ny - 0.5) * 0.8 < (nx - 0.28):
                    pixel = white

            # S letter region (right half)
            if 0.52 < nx < 0.80 and 0.25 < ny < 0.75:
                mid = (0.52 + 0.80) / 2
                if ny < 0.35:
                    if (0.30 < ny < 0.34) or (abs(nx - 0.52) < 0.04 and ny < 0.50):
                        pixel = white
                    if 0.52 < nx < 0.80 and 0.27 < ny < 0.31:
                        pixel = white
                elif 0.48 < ny < 0.52:
                    if 0.52 < nx < 0.80 and 0.48 < ny < 0.52:
                        pixel = white
                elif ny > 0.65:
                    if 0.52 < nx < 0.80 and 0.69 < ny < 0.73:
                        pixel = white
                    if abs(nx - 0.80) < 0.04 and ny > 0.50:
                        pixel = white

            row += bytes(pixel)
        rows.append(row)

    raw = b''.join(rows)
    compressed = zlib.compress(raw, 9)
    idat = chunk(b'IDAT', compressed)
    iend = chunk(b'IEND', b'')

    return png_header + ihdr + idat + iend


if __name__ == "__main__":
    import os
    os.makedirs("src/icons", exist_ok=True)

    for size in [16, 48, 128]:
        data = create_png(size)
        path = f"src/icons/icon{size}.png"
        with open(path, "wb") as f:
            f.write(data)
        print(f"Gerado: {path} ({len(data)} bytes)")

    print("\nÍcones gerados com sucesso!")
    print("Para ícones de maior qualidade, instala cairosvg:")
    print("  pip install cairosvg")
    print("  python -c \"import cairosvg; cairosvg.svg2png(url='icon.svg', write_to='src/icons/icon128.png', output_width=128)\"")
