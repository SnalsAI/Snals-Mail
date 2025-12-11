#!/usr/bin/env python3
"""
Script per generare icone PWA per SNALS Mail
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Crea directory icons
icons_dir = "/home/ubuntu/Snals-Mail/frontend/public/icons"
os.makedirs(icons_dir, exist_ok=True)

# Colori SNALS (dal theme)
BG_COLOR = "#0ea5e9"  # Blu theme
TEXT_COLOR = "#ffffff"  # Bianco

# Dimensioni icone da generare
SIZES = [16, 32, 64, 128, 192, 256, 384, 512]

def create_icon(size):
    """Crea un'icona PWA con il logo SNALS"""
    # Crea immagine con sfondo blu
    img = Image.new('RGB', (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Testo "SNALS"
    text = "SNALS"

    # Prova a usare un font, altrimenti usa il default
    try:
        # Font size proporzionale all'icona
        font_size = int(size * 0.25)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        # Fallback al font default
        font = ImageFont.load_default()

    # Calcola posizione centrata del testo
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size - text_width) / 2
    y = (size - text_height) / 2

    # Disegna il testo
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    # Aggiungi un bordo arrotondato (solo per icone grandi)
    if size >= 192:
        # Crea una maschera per gli angoli arrotondati
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        radius = size // 8
        mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=radius, fill=255)

        # Applica la maschera
        output = Image.new('RGB', (size, size), BG_COLOR)
        output.paste(img, (0, 0))
        output.putalpha(mask)
        return output

    return img

# Genera tutte le icone
for size in SIZES:
    icon = create_icon(size)
    filename = f"{icons_dir}/icon-{size}x{size}.png"
    icon.save(filename, "PNG")
    print(f"✅ Creata: {filename}")

# Crea anche favicon.ico (16x16 + 32x32)
favicon_sizes = [(16, 16), (32, 32)]
favicon_images = [create_icon(s) for s, _ in favicon_sizes]
favicon_path = "/home/ubuntu/Snals-Mail/frontend/public/favicon.ico"
favicon_images[0].save(favicon_path, format='ICO', sizes=favicon_sizes)
print(f"✅ Creata: {favicon_path}")

print("\n🎉 Tutte le icone PWA sono state generate con successo!")
print(f"📁 Directory: {icons_dir}")
