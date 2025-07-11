from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from PIL import Image, ImageDraw, ImageFont, ImageColor
import requests
from io import BytesIO
import os
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

app = FastAPI()

SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_IMAGE_BUCKET = os.getenv("SUPABASE_IMAGE_BUCKET")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_IMAGE_BASE = os.getenv("SUPABASE_IMAGE_BASE")
FONT_PATH = "fonts/DejaVuSans-Bold.ttf"
FONT_BOLD_PATH = "fonts/DejaVuSans-Bold.ttf"
DEFAULT_COLOR = "#000000"

def safe_color(value: str, fallback: str = DEFAULT_COLOR) -> str:
    try:
        ImageColor.getrgb(value)
        return value
    except:
        return fallback

@app.get("/")
def root():
    return {"message": "Clean Pillow API is running!"}

@app.get("/generate-and-upload", response_class=JSONResponse)
def generate_and_upload(
    template: str = Query(...),
    title: str = Query(""),
    content: str = Query(""),
    contact: str = Query(""),
    logo_url: str = Query(None),
    filename: str = Query("output.png"),

    title_color: str = Query(DEFAULT_COLOR),
    content_color: str = Query(DEFAULT_COLOR),
    contact_color: str = Query(DEFAULT_COLOR),
):
    print("🔧 RECEIVED PARAMS:")
    print("Title:", title, "| Color:", title_color)
    print("Content:", content, "| Color:", content_color)
    print("Contact:", contact, "| Color:", contact_color)
    print("Logo:", logo_url)

    # Load base template
    base_template_url = f"{SUPABASE_IMAGE_BASE}{quote(template)}"
    response = requests.get(base_template_url)
    if response.status_code != 200:
        return {"error": "Template image failed to load", "url": base_template_url}

    img = Image.open(BytesIO(response.content)).convert("RGBA")
    img = img.resize((1080, 1080))  # Force canvas to standard size
    print("🖼 Template size:", img.size)
    draw = ImageDraw.Draw(img)

    # Load fonts with system fallback and print available font files
    font_path = "fonts/DejaVuSans-Bold.ttf"
    try:
        font_title = ImageFont.truetype(font_path, 60)
        font_content = ImageFont.truetype(font_path, 40)
        font_contact = ImageFont.truetype(font_path, 30)
        print("✅ Fonts loaded from:", font_path)
    except Exception as e:
        print("❌ Failed to load fonts from local path:", font_path, "| Error:", e)
        font_title = ImageFont.load_default()
        font_content = ImageFont.load_default()
        font_contact = ImageFont.load_default()

    try:
        print("📁 Current directory contents:", os.listdir("."))
    except Exception as e:
        print("❌ Directory listing failed:", e)

    # Draw text with bounding box constraints
    def draw_text_within_box(draw, text, font, x, y, max_width, max_height, fill=(0, 0, 0)):
        lines = []
        words = text.split()
        current_line = ''
        for word in words:
            test_line = current_line + ' ' + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]
            if test_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        total_height = 0
        for line in lines:
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_height = line_bbox[3] - line_bbox[1]
            total_height += line_height + 4

        if total_height > max_height:
            print("⚠️ Text exceeds height bounds; may overflow")

        for line in lines:
            draw.text((x, y), line, font=font, fill=fill)
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_height = line_bbox[3] - line_bbox[1]
            y += line_height + 4

    if title:
        draw_text_within_box(draw, title, font_title, 50, 50, 1000, 200, fill=safe_color(title_color))
    if content:
        draw_text_within_box(draw, content, font_content, 50, 400, 500, 300, fill=safe_color(content_color))
    if contact:
        draw_text_within_box(draw, contact, font_contact, 50, 900, 1000, 150, fill=safe_color(contact_color))

    # Add logo
    if logo_url:
        if logo_url.startswith("//"):
            logo_url = "https:" + logo_url
        try:
            logo_response = requests.get(logo_url)
            if logo_response.status_code == 200:
                logo_img = Image.open(BytesIO(logo_response.content))
                print("Logo fetched. Original mode:", logo_img.mode)

                # Ensure RGBA for transparency
                if logo_img.mode != "RGBA":
                    logo_img = logo_img.convert("RGBA")

                logo_img = logo_img.resize((150, 150))

                # Ensure main image is RGBA
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                img.paste(logo_img, (880, 50), logo_img)
            else:
                print(f"Logo fetch failed. Status code: {logo_response.status_code}")
        except Exception as e:
            print("Logo processing error:", str(e))

    # Save to buffer
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    # Upload to Supabase
    upload_url = f"{SUPABASE_PROJECT_URL}/storage/v1/object/{SUPABASE_IMAGE_BUCKET}/{quote(filename)}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "image/png"
    }
    upload_response = requests.put(upload_url, headers=headers, data=output.getvalue())

    if upload_response.status_code not in [200, 201]:
        return {"error": "Upload failed", "details": upload_response.text}

    public_url = f"{SUPABASE_IMAGE_BASE}{quote(filename)}"
    return JSONResponse(content={"image_url": public_url})