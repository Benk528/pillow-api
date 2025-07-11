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

    # Title
    title_x: int = Query(0),
    title_y: int = Query(0),
    title_size: int = Query(60),
    title_color: str = Query(DEFAULT_COLOR),

    # Content
    content_x: int = Query(0),
    content_y: int = Query(0),
    content_size: int = Query(40),
    content_color: str = Query(DEFAULT_COLOR),

    # Contact
    contact_x: int = Query(0),
    contact_y: int = Query(0),
    contact_size: int = Query(30),
    contact_color: str = Query(DEFAULT_COLOR),

    # Logo
    logo_x: int = Query(0),
    logo_y: int = Query(0),
    logo_width: int = Query(100),
    logo_height: int = Query(100),
):
    print("🔧 RECEIVED PARAMS:")
    print("Title:", title, "| X:", title_x, "| Y:", title_y, "| Size:", title_size, "| Color:", title_color)
    print("Content:", content, "| X:", content_x, "| Y:", content_y, "| Size:", content_size, "| Color:", content_color)
    print("Contact:", contact, "| X:", contact_x, "| Y:", contact_y, "| Size:", contact_size, "| Color:", contact_color)
    print("Logo:", logo_url, "| X:", logo_x, "| Y:", logo_y, "| Width:", logo_width, "| Height:", logo_height)

    # Load base template
    base_template_url = f"{SUPABASE_IMAGE_BASE}{quote(template)}"
    response = requests.get(base_template_url)
    if response.status_code != 200:
        return {"error": "Template image failed to load", "url": base_template_url}

    img = Image.open(BytesIO(response.content)).convert("RGBA")
    img = img.resize((1080, 1080))  # Force canvas to standard size
    print("🖼 Template size:", img.size)
    draw = ImageDraw.Draw(img)

    # Use consistent font sizes
    image_width, image_height = img.size
    title_size = 72
    content_size = 48
    contact_size = 38

    # Load fonts with system fallback and print available font files
    font_path = "fonts/DejaVuSans-Bold.ttf"
    try:
        font_title = ImageFont.truetype(font_path, title_size)
        font_content = ImageFont.truetype(font_path, content_size)
        font_contact = ImageFont.truetype(font_path, contact_size)
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

    # Draw text
    if title:
        draw.text((title_x * 2, title_y * 2), title, font=font_title, fill=safe_color(title_color))
    if content:
        import textwrap
        content_size = 28
        font_content = ImageFont.truetype(font_path, content_size)
        wrapped_lines = textwrap.wrap(content, width=50)
        line_height = font_content.getbbox("A")[3] - font_content.getbbox("A")[1] + 8
        for i, line in enumerate(wrapped_lines):
            draw.text((content_x * 2, content_y * 2 + i * line_height), line, font=font_content, fill=safe_color(content_color))
    if contact:
        draw.text((contact_x * 2, contact_y * 2), contact, font=font_contact, fill=safe_color(contact_color))

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

                logo_img = logo_img.resize((logo_width * 2, logo_height * 2))

                # Ensure main image is RGBA
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                img.paste(logo_img, (logo_x * 2, logo_y * 2), logo_img)
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