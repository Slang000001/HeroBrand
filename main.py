import json
import argparse
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types as genai_types

# ---------- CONFIG ----------
DATA_PATH = Path("input/heroes.json")
CATALOG_PATH = Path("input/product_catalog.json")
OUTPUT_PATH = Path("output")
LOGO_PATH = Path("input/hero_circular2.png")
ASSET_PATH = Path("assets")  # <-- mock storage for existing assets
OUTPUT_PATH.mkdir(exist_ok=True)
ASSET_PATH.mkdir(exist_ok=True)

# ---------- CONFIG ----------
DATA_PATH = Path("input/heroes.json")
CATALOG_PATH = Path("input/product_catalog.json")
OUTPUT_PATH = Path("output")
LOGO_PATH = Path("input/hero_circular2.png")
ASSET_PATH = Path("assets")  # mock storage for existing assets
OUTPUT_PATH.mkdir(exist_ok=True)
ASSET_PATH.mkdir(exist_ok=True)

# ---------- LOAD DATA ----------
def load_json(path: Path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {path}: {e}")
        return {}


HEROES = load_json(DATA_PATH)
PRODUCT_CATALOG = load_json(CATALOG_PATH)
print(f"📖 Loaded {len(HEROES)} heroes and {len(PRODUCT_CATALOG)} products.")


# ---------- HELPERS ----------
def spelled_name(name: str) -> str:
    letters_only = [ch for ch in name if ch.isalpha()]
    return " ".join(ch.upper() for ch in letters_only)


def product_visual_brief(product_id: str) -> dict:
    mapping = {
        "bagged_coffee": {
            "object": "a matte stand-up coffee bag with a front label, vertically oriented",
            "label_instruction": "Print the product name clearly on the bag’s front label area.",
            "supporting_text_instruction": "Below the label, include the hero tag text in smaller type.",
            "tagline_instruction": "Place the campaign tagline near the lower third of the bag."
        },
        "large_bag": {
            "object": "a large matte stand-up coffee bag with a front label, vertically oriented",
            "label_instruction": "Print the product name centered on the bag’s front label.",
            "supporting_text_instruction": "Include the hero tag text below the name in smaller type.",
            "tagline_instruction": "Place the campaign tagline near the bottom edge of the label."
        },
        "k_cup_pods": {
            "object": "a retail box of K-Cup pods with a large front face label",
            "label_instruction": "Print the product name on the box’s front label.",
            "supporting_text_instruction": "Add the hero tag text under the name in smaller type.",
            "tagline_instruction": "Place the campaign tagline along the bottom of the box front."
        },
        "gift_card": {
            "object": "a premium gift card and sleeve, angled slightly on a table",
            "label_instruction": "Print the product name on the gift card’s face, $20 value visible.",
            "supporting_text_instruction": "Include the hero tag text beneath the name in smaller type.",
            "tagline_instruction": "Place the campaign tagline along the bottom margin of the card."
        },
    }
    return mapping.get(product_id, mapping["bagged_coffee"])


# ---------- ASSET REUSE ----------
def find_existing_asset(hero_name: str, product_name: str) -> Path | None:
    """Check for an existing image asset in local mock storage."""
    safe_hero = hero_name.replace(" ", "_")
    safe_product = product_name.replace(" ", "_")
    possible_path = ASSET_PATH / f"{safe_hero}_{safe_product}.png"
    if possible_path.exists():
        print(f"📦 Found existing asset: {possible_path}")
        return possible_path
    else:
        print(f"🔍 No existing asset found for {safe_hero}_{safe_product}.png")
    return None

# ---------- LOGO ----------
def add_logo(image_path: Path):
    if not LOGO_PATH.exists():
        print(f"⚠️ Logo not found at {LOGO_PATH}")
        return
    try:
        base = Image.open(image_path).convert("RGBA")
        logo = Image.open(LOGO_PATH).convert("RGBA")

        target_width = int(base.width * 0.15)
        ratio = logo.height / logo.width
        logo = logo.resize((target_width, int(target_width * ratio)))

        pos = (base.width - logo.width - 20, base.height - logo.height - 20)
        base.paste(logo, pos, mask=logo)
        base.convert("RGB").save(image_path)
        print(f"🏷️ Logo added: {image_path}")
    except Exception as e:
        print(f"❌ Error adding logo: {e}")


# ---------- TEXT OVERLAY ----------
def add_text_overlay(image_path: Path, slogan: str):
    """Overlay slogan at the top with translucent banner."""
    try:
        img = Image.open(image_path).convert("RGBA")
        w, h = img.size
        draw = ImageDraw.Draw(img)

        base_size = int(h * 0.05)
        try:
            font = ImageFont.truetype("Arial.ttf", base_size)
        except:
            font = ImageFont.load_default()

        def text_size(f):
            bbox = draw.textbbox((0, 0), slogan, font=f)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]

        text_w, text_h = text_size(font)
        while text_w > w * 0.9 and base_size > 10:
            base_size -= 2
            try:
                font = ImageFont.truetype("Arial.ttf", base_size)
            except:
                font = ImageFont.load_default()
            text_w, text_h = text_size(font)

        padding = int(base_size * 0.6)
        banner_h = text_h + padding * 2

        # Translucent banner
        banner = Image.new("RGBA", (w, banner_h), (0, 0, 0, 120))
        img.alpha_composite(banner, (0, 0))

        # Center text horizontally in banner
        text_x = (w - text_w) / 2
        text_y = padding // 2

        shadow_offset = int(base_size * 0.05)
        draw.text((text_x + shadow_offset, text_y + shadow_offset), slogan, fill="black", font=font)
        draw.text((text_x, text_y), slogan, fill="white", font=font)

        img.convert("RGB").save(image_path)
        print(f"📝 Slogan overlay added: {image_path}")

    except Exception as e:
        print(f"❌ Error adding slogan overlay: {e}")


# ---------- IMAGE RESIZING ----------
def generate_aspect_renditions(base_path):
    try:
        img = Image.open(base_path)
        w, h = img.size
        targets = {"1x1": (1024, 1024), "9x16": (1024, 1820), "16x9": (1820, 1024)}

        for label, (tw, th) in targets.items():
            scale = max(tw / w, th / h)
            new_w, new_h = int(w * scale), int(h * scale)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left, top = (new_w - tw) / 2, (new_h - th) / 2
            cropped = resized.crop((left, top, left + tw, top + th))
            out_path = base_path.parent / f"{label}.png"
            cropped.save(out_path)
            print(f"✅ Generated rendition: {out_path}")
    except Exception as e:
        print(f"❌ Error resizing/cropping image: {e}")


# ---------- GEMINI ----------
def generate_base_image_gemini(campaign):
    print("🎨 Generating base creative with Gemini...")
    client = genai.Client()
    base_path = None

    pv = product_visual_brief(campaign["product_id"])
    hero_spelled = spelled_name(campaign["hero"])

    prompt = (
        f"Create a high-quality photo of {pv['object']} for Hero Brand Coffee. "
        f"The product is called '{campaign['hero']} Coffee' and should clearly appear on the label. "
        f"This is a {campaign['product']} designed for retail marketing. "
        f"{pv['label_instruction']} For name spelling, the correct letters are: {hero_spelled}. "
        f"{pv['supporting_text_instruction']} Use this hero tag text verbatim: '{campaign['summary']}'. "
        f"{pv['tagline_instruction']} Use this tagline verbatim: '{campaign['message']}'. "
        f"Include a small, respectful portrait of {campaign['hero']} near the label area, without obscuring text. "
        f"Show the product laying flat on a table with natural light, modern, premium styling, minimal background. "
        f"Brand colors: {campaign['color']}. No floating text or watermarks. Brand: Hero Brand Coffee."
    )

    try:
        cfg = genai_types.GenerateContentConfig(
            response_modalities=[genai_types.Modality.IMAGE],
            image_config={"aspect_ratio": "1:1"}
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
            config=cfg
        )

        if not response or not response.candidates:
            raise ValueError("Gemini returned no candidates")

        content = response.candidates[0].content
        image_bytes = None
        for part in getattr(content, "parts", []):
            if getattr(part, "inline_data", None):
                image_bytes = part.inline_data.data
                break
        if not image_bytes:
            raise ValueError("Gemini returned no image bytes")

        safe_hero = campaign["hero"].replace(" ", "_")
        safe_product = campaign["product"].replace(" ", "_")
        out_dir = OUTPUT_PATH / f"{safe_hero}_{safe_product}"
        out_dir.mkdir(parents=True, exist_ok=True)
        base_path = out_dir / f"{safe_hero}_{safe_product}_base.png"

        img = Image.open(BytesIO(image_bytes))
        img.save(base_path)
        print(f"✅ Base image saved: {base_path}")
        return base_path

    except Exception as e:
        print(f"⚠️ Gemini image generation failed: {e}")
        return None


# ---------- BUILD CAMPAIGN ----------
def build_campaign(hero_name: str, product_id: str, gen_mode: str = "gemini", slogan: str | None = None, input_asset: str | None = None):
    print(f"🚀 Building campaign for {hero_name} / {product_id}")
    hero = HEROES.get(hero_name, {})
    product = PRODUCT_CATALOG.get(product_id, {"name": product_id})

    campaign = {
        "product_id": product_id,
        "product": product["name"],
        "hero": hero_name,
        "message": hero.get("quote", "Fueling courage, one cup at a time."),
        "summary": hero.get("summary", "A hero whose valor inspires every blend."),
        "branch": hero.get("branch", "Unknown"),
        "color": hero.get("color", "#333333"),
        "slogan": slogan,
        "target_region": hero.get("region", "United States"),
        "target_audience": hero.get("audience", "Veterans of all eras (WWII, Vietnam, Korean War, Gulf War, GWOT)")
        }


    brief_file = OUTPUT_PATH / f"{hero_name.replace(' ', '_')}_{product_id}_campaign.json"
    with open(brief_file, "w") as f:
        json.dump(campaign, f, indent=2)
    print(f"✅ Campaign brief saved: {brief_file}")

    # Try CLI asset first, then assets folder, then Gemini
    base_path = None
    if input_asset and Path(input_asset).exists():
        print(f"📁 Using provided input asset: {input_asset}")
        safe_hero = hero_name.replace(" ", "_")
        safe_product = product["name"].replace(" ", "_")
        out_dir = OUTPUT_PATH / f"{safe_hero}_{safe_product}"
        out_dir.mkdir(parents=True, exist_ok=True)
        new_base = out_dir / f"{safe_hero}_{safe_product}_base.png"
        if str(Path(input_asset).resolve()) != str(new_base.resolve()):
            import shutil
            shutil.copy(Path(input_asset), new_base)
            print(f"♻️ Copied input asset to {new_base}")
        base_path = new_base
    else:
        existing = find_existing_asset(hero_name, f"{product['name'].replace(' ', '_')}_base")
        if existing:
            safe_hero = hero_name.replace(" ", "_")
            safe_product = product["name"].replace(" ", "_")
            out_dir = OUTPUT_PATH / f"{safe_hero}_{safe_product}"
            out_dir.mkdir(parents=True, exist_ok=True)
            new_base = out_dir / f"{safe_hero}_{safe_product}_base.png"
            if str(existing.resolve()) != str(new_base.resolve()):
                import shutil
                shutil.copy(existing, new_base)
                print(f"♻️ Reused base asset → copied to {new_base}")
            base_path = new_base
        elif gen_mode == "gemini":
            base_path = generate_base_image_gemini(campaign)

        if base_path:
            generate_aspect_renditions(base_path)
            for label in ["1x1", "9x16", "16x9"]:
                out_path = base_path.parent / f"{label}.png"
                if out_path.exists():
                    if campaign.get("slogan"):
                        add_text_overlay(out_path, campaign["slogan"])
                    add_logo(out_path)
                else:
                    print(f"⚠️ Missing resized file: {out_path}")
        else:
            print("❌ No base image available. Skipping output generation.")


# ---------- MAIN ----------
def main():
    parser = argparse.ArgumentParser(description="Hero Brand Coffee Campaign Builder")
    parser.add_argument("--hero", required=True, help="Hero name (e.g. 'Roy Benavidez')")
    parser.add_argument("--product", required=True, help="Product ID (e.g. 'bagged_coffee')")
    parser.add_argument("--slogan", help="Campaign slogan text (optional)")
    parser.add_argument("--gen", choices=["gemini"], default="gemini")
    parser.add_argument("--input_asset", help="Path to an existing image asset to reuse")
    args = parser.parse_args()

    slogan = args.slogan
    if not slogan:
        try:
            slogan = input("Enter campaign slogan (or leave blank to skip overlay): ").strip()
        except EOFError:
            slogan = None

    build_campaign(args.hero, args.product, gen_mode=args.gen, slogan=slogan if slogan else None, input_asset=args.input_asset)


if __name__ == "__main__":
    main()