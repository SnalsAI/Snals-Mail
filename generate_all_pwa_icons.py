#!/usr/bin/env python3
"""
Script completo per generare TUTTE le icone PWA richieste dal manifest
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Crea directory icons
icons_dir = "/home/ubuntu/Snals-Mail/frontend/public/icons"
os.makedirs(icons_dir, exist_ok=True)

# Colori SNALS (dal theme)
BG_COLOR = "#0ea5e9"  # Blu theme
TEXT_COLOR = "#ffffff"  # Bianco
EMAIL_COLOR = "#10b981"  # Verde per email
CALENDAR_COLOR = "#f59e0b"  # Arancione per calendario
INTERPELLI_COLOR = "#8b5cf6"  # Viola per interpelli

# Dimensioni icone principali da generare (dal manifest)
MAIN_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def create_icon(size, text="SNALS", bg_color=BG_COLOR):
    """Crea un'icona PWA con testo personalizzato"""
    # Crea immagine con sfondo colorato
    img = Image.new('RGB', (size, size), bg_color)
    draw = ImageDraw.Draw(img)

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

    return img

# 1. Genera tutte le icone principali
print("📱 Generazione icone principali...")
for size in MAIN_SIZES:
    icon = create_icon(size)
    filename = f"{icons_dir}/icon-{size}x{size}.png"
    icon.save(filename, "PNG")
    print(f"  ✅ {size}x{size}")

# 2. Genera icone per shortcuts
print("\n🔗 Generazione icone shortcuts...")

# Email shortcut (96x96)
email_icon = create_icon(96, "📧", EMAIL_COLOR)
email_icon.save(f"{icons_dir}/shortcut-email.png", "PNG")
print("  ✅ shortcut-email.png")

# Calendar shortcut (96x96)
calendar_icon = create_icon(96, "📅", CALENDAR_COLOR)
calendar_icon.save(f"{icons_dir}/shortcut-calendar.png", "PNG")
print("  ✅ shortcut-calendar.png")

# Interpelli shortcut (96x96)
interpelli_icon = create_icon(96, "📋", INTERPELLI_COLOR)
interpelli_icon.save(f"{icons_dir}/shortcut-interpelli.png", "PNG")
print("  ✅ shortcut-interpelli.png")

# 3. Crea anche favicon.ico (16x16 + 32x32 + 48x48)
print("\n🌐 Generazione favicon...")
favicon_sizes = [16, 32, 48]
favicon_images = [create_icon(s) for s in favicon_sizes]
favicon_path = "/home/ubuntu/Snals-Mail/frontend/public/favicon.ico"
favicon_images[0].save(
    favicon_path,
    format='ICO',
    sizes=[(s, s) for s in favicon_sizes],
    append_images=favicon_images[1:]
)
print("  ✅ favicon.ico (multi-size)")

# 4. Crea apple-touch-icon (180x180 per iOS)
print("\n🍎 Generazione Apple Touch Icon...")
apple_icon = create_icon(180)
apple_icon.save("/home/ubuntu/Snals-Mail/frontend/public/apple-touch-icon.png", "PNG")
print("  ✅ apple-touch-icon.png")

print("\n" + "="*50)
print("🎉 TUTTE LE ICONE PWA GENERATE CON SUCCESSO!")
print("="*50)
print(f"\n📁 Directory: {icons_dir}")
print(f"📊 Icone principali: {len(MAIN_SIZES)} dimensioni")
print(f"🔗 Shortcuts: 3 icone")
print(f"🌐 Favicon: Multi-size ICO")
print(f"🍎 Apple: 180x180")
print("\n✅ La PWA è ora pronta per l'installazione!")
