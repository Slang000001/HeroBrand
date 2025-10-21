import json
import argparse
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types as genai_types

# ---------- CONFIGURATION ----------
DATA_PATH = Path("input/heroes.json")
OUTPUT_PATH = Path("output")
OUTPUT_PATH.mkdir(exist_ok=True)

LOGO_PATH = Path("output/hero_circular2.png")

# ---------- RETRIEVAL FUNCTION ----------
def get_hero_data(name: str):
    with open(DATA_PATH, "r") as f:
        heroes = json.load(f)
    return heroes.get(name, {
        "summary": f"No detailed record found for {name}.",
        "quote": f"A blend inspired by {name}.",
        "branch": "Unknown",
        "year": None,
        "color": "#444444"
    })

# ---------- ADD LOGO ----------
def add_logo(image_path: Path, logo_path: Path = LOGO_PATH):
    """Force-overlay the Hero Brand Coffee logo bottom-right."""
    if not logo_path.exists():
        print(f"⚠️ Logo not found at {logo_path}")
        return

    base = Image.open(image_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    target_width = int(base.width * 0.15)
    ratio = logo.height / logo.width
    logo = logo.resize((target_width, int(target_width * ratio)))

    pos = (base.width - logo.width - 20, base.height - logo.height - 20)

    composite = Image.new("RGBA", base.size, (0, 0, 0, 0))
    composite.paste(base, (0, 0))
    composite.paste(logo, pos, mask=logo)

    final = composite.convert("RGB")
    final.save(image_path)
    print(f"🏷️ Added Hero Brand Coffee logo to: {image_path}")

# ---------- PILLOW FALLBACK ----------
def generate_placeholder_images(campaign, suffix="_fallback"):
    """Simulate ad creatives locally (used when Gemini fails)."""
    ratios = {
        "1x1": (1024, 1024),
        "9x16": (1024, 1820),
        "16x9": (1820, 1024)
    }

    text = f"{campaign['product']}\n{campaign['message']}"
    bg_color = campaign.get("color", "#333333")

    for ratio, size in ratios.items():
        out_dir = Path("output") / campaign["product"].replace(" ", "_")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{ratio}{suffix}.png"

        img = Image.new("RGB", size, color=bg_color)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("Arial.ttf", 60)
        except:
            font = ImageFont.load_default()

        bbox = draw.multiline_textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos = ((size[0] - text_w) / 2, (size[1] - text_h) / 2)

        draw.multiline_text(pos, text, fill="white", font=font, align="center")
        img.save(out_path)
        print(f"🖼️ Saved placeholder ad: {out_path}")
        add_logo(out_path)

# ---------- GEMINI IMAGE GENERATION ----------
def generate_images_gemini(campaign):
    client = genai.Client()

    ratios = {
        "1x1": None,
        "9x16": "9:16",
        "16x9": "16:9"
    }

    base_prompt = (
        f"High-quality product photograph of {campaign['product']} coffee. "
        f"Respectful, modern, minimal styling. Color palette inspired by {campaign['color']}. "
        f"Include empty space for text: '{campaign['message']}'. "
        f"Theme: honors Medal of Honor hero {campaign['hero']}."
    )

    out_dir = Path("output") / campaign["product"].replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    for label, aspect in ratios.items():
        print(f"🎨 Generating {label} creative with Gemini...")
        try:
            cfg = genai_types.GenerateContentConfig(
                response_modalities=[genai_types.Modality.IMAGE],
                image_config={"aspect_ratio": aspect} if aspect else None
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[base_prompt],
                config=cfg
            )

            if not response or not response.candidates:
                print(f"⚠️ No Gemini response for {label}, using fallback.")
                generate_placeholder_images(campaign)
                continue

            content = response.candidates[0].content
            if not content or not getattr(content, "parts", None):
                print(f"⚠️ Empty Gemini content for {label}, using fallback.")
                generate_placeholder_images(campaign)
                continue

            image_bytes = None
            for part in content.parts:
                if getattr(part, "inline_data", None):
                    image_bytes = part.inline_data.data
                    break

            if image_bytes:
                out_path = out_dir / f"{label}.png"
                img = Image.open(BytesIO(image_bytes))
                img.save(out_path)
                print(f"✅ Gemini image saved: {out_path}")
                add_logo(out_path)
            else:
                print(f"⚠️ No image data in Gemini response for {label}, using fallback.")
                generate_placeholder_images(campaign)
        except Exception as e:
            print(f"❌ Gemini error for {label}: {e}")
            generate_placeholder_images(campaign)

# ---------- BUILD CAMPAIGN ----------
def build_campaign(hero_name: str, product: str, gen_mode: str = "pillow"):
    hero = get_hero_data(hero_name)

    campaign = {
        "product": f"{hero_name.split()[0]} {product}",
        "hero": hero_name,
        "message": hero["quote"],
        "summary": hero["summary"],
        "branch": hero["branch"],
        "color": hero["color"]
    }

    brief_file = OUTPUT_PATH / f"{hero_name.replace(' ', '_')}_campaign.json"
    with open(brief_file, "w") as f:
        json.dump(campaign, f, indent=2)
    print(f"\n✅ Campaign brief saved: {brief_file}")
    print(json.dumps(campaign, indent=2))

    if gen_mode == "gemini":
        generate_images_gemini(campaign)
    else:
        generate_placeholder_images(campaign)

# ---------- MAIN ----------
def main():
    print("🚀 Running campaign generator...")
    parser = argparse.ArgumentParser(description="Medal of Honor Coffee Campaign Builder")
    parser.add_argument("--hero", required=True, help="Hero name, e.g. 'Roy Benavidez'")
    parser.add_argument("--product", required=True, help="Product name, e.g. 'Espresso'")
    parser.add_argument("--gen", choices=["pillow", "gemini"], default="pillow",
                        help="Choose creative generator")
    args = parser.parse_args()
    build_campaign(args.hero, args.product, gen_mode=args.gen)

if __name__ == "__main__":
    main()
