from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont
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
FONT_PATH = os.getenv("FONT_PATH", "arial.ttf")

@app.get("/")
def root():
    return {"message": "Pillow Image API with Supabase upload is running!"}

@app.get("/generate-and-upload", response_class=JSONResponse)
def generate_and_upload(
    template: str = Query(...),
    title: str = Query(""),
    content: str = Query(""),
    contact: str = Query(""),
    logo: str = Query(None),
    filename: str = Query("output.png")
):
    # 1. Load the template image from Supabase public URL
    base_template_url = f"{SUPABASE_IMAGE_BASE}{quote(template)}"
    response = requests.get(base_template_url, headers={"User-Agent": "Mozilla/5.0"})

    if response.status_code != 200:
        return {"error": "Failed to load template image.", "url": base_template_url}

    img = Image.open(BytesIO(response.content)).convert("RGBA")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype(FONT_PATH, 110)      # Was 60 → now bigger + bolder
        font_content = ImageFont.truetype(FONT_PATH, 72)     # Was 36 → clearer body text
        font_contact = ImageFont.truetype(FONT_PATH, 48)     # Was 28 → readable contact
    except:
        font_title = font_content = font_contact = ImageFont.load_default()

    brand_color = "#2A2E74"  # Your Falstaff deep blue

    draw.text((60, 60), title, font=font_title, fill=brand_color)
    draw.text((60, 220), content, font=font_content, fill=brand_color)
    draw.text((60, 380), contact, font=font_contact, fill=brand_color)

    # 2. Add logo (if provided)
    if logo:
        try:
            logo_response = requests.get(logo)
            if logo_response.status_code == 200:
                logo_img = Image.open(BytesIO(logo_response.content)).convert("RGBA")
                logo_img = logo_img.resize((100, 100))
                img.paste(logo_img, (img.width - 160, 60), logo_img)
        except Exception as e:
            print("Logo load error:", e)

    # 3. Save to buffer
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    # 4. Upload to Supabase
    upload_url = f"{SUPABASE_PROJECT_URL}/storage/v1/object/{SUPABASE_IMAGE_BUCKET}/{quote(filename)}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "image/png"
    }
    upload_response = requests.put(upload_url, headers=headers, data=output.getvalue())

    if upload_response.status_code not in [200, 201]:
        return {"error": "Upload failed", "details": upload_response.text}

   # 5. Return public URL in JSON format
    public_url = f"{SUPABASE_IMAGE_BASE}{quote(filename)}"
    return JSONResponse(content={"image_url": public_url})