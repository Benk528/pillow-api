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
    filename: str = Query("output.png"),
    title_x: int = Query(60),
    title_y: int = Query(60),
    title_size: int = Query(110),
    title_color: str = Query("#2A2E74"),
    content_x: int = Query(60),
    content_y: int = Query(220),
    content_size: int = Query(72),
    content_color: str = Query("#2A2E74"),
    contact_x: int = Query(60),
    contact_y: int = Query(380),
    contact_size: int = Query(48),
    contact_color: str = Query("#2A2E74"),
    logo_x: int = Query(0),
    logo_y: int = Query(0),
    logo_width: int = Query(100),
    logo_height: int = Query(100),
):
    base_template_url = f"{SUPABASE_IMAGE_BASE}{quote(template)}"
    response = requests.get(base_template_url, headers={"User-Agent": "Mozilla/5.0"})

    if response.status_code != 200:
        return {"error": "Failed to load template image.", "url": base_template_url}

    img = Image.open(BytesIO(response.content)).convert("RGBA")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype(FONT_PATH, title_size)
        font_content = ImageFont.truetype(FONT_PATH, content_size)
        font_contact = ImageFont.truetype(FONT_PATH, contact_size, layout_engine=ImageFont.LAYOUT_BASIC)
    except:
        font_title = font_content = font_contact = ImageFont.load_default()

    draw.text((title_x, title_y), title, font=font_title, fill=title_color)
    draw.text((content_x, content_y), content, font=font_content, fill=content_color)
    draw.text((contact_x, contact_y), contact, font=font_contact, fill=contact_color)

    if logo:
        try:
            logo_response = requests.get(logo)
            if logo_response.status_code == 200:
                logo_img = Image.open(BytesIO(logo_response.content)).convert("RGBA")
                logo_img = logo_img.resize((logo_width, logo_height))
                img.paste(logo_img, (logo_x, logo_y), logo_img)
        except Exception as e:
            print("Logo load error:", e)

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

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