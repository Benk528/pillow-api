from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os
from dotenv import load_dotenv
from uuid import uuid4
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
    logo: str = Query(None)
):
    # 1. Load the template image from Supabase public URL
    base_template_url = f"{SUPABASE_IMAGE_BASE}{quote(template)}"
    response = requests.get(base_template_url, headers={"User-Agent": "Mozilla/5.0"})

    if response.status_code != 200:
        return {"error": "Failed to load template image.", "url": base_template_url}

    img = Image.open(BytesIO(response.content)).convert("RGBA")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype(FONT_PATH, 60)
        font_content = ImageFont.truetype(FONT_PATH, 36)
        font_contact = ImageFont.truetype(FONT_PATH, 28)
    except:
        font_title = font_content = font_contact = ImageFont.load_default()

    draw.text((60, 60), title, font=font_title, fill="white")
    draw.text((60, 160), content, font=font_content, fill="white")
    draw.text((60, 360), contact, font=font_contact, fill="white")

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

    # 3. Generate automatic filename
    filename = f"{uuid4()}.png"

    # 4. Save to buffer
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    # 5. Upload to Supabase
    # 1. Generate automatic filename
    filename = f"{uuid4()}.png"

    # 2. Build upload URL with /public/
    upload_url = f"{SUPABASE_PROJECT_URL}/storage/v1/object/public/{SUPABASE_IMAGE_BUCKET}/{quote(filename)}"

    # 3. Set headers with BOTH Authorization and apikey
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "image/png"
    }

    # 4. Debug print — see what's going on
    print("Uploading to:", upload_url)
    print("Headers:", headers)

    # 5. Upload the image buffer
    upload_response = requests.put(upload_url, headers=headers, data=output.getvalue())

    # 6. Print the Supabase response
    print("Upload Status Code:", upload_response.status_code)
    print("Upload Response:", upload_response.text)

    # 7. Error handling
    if upload_response.status_code not in [200, 201]:
        return JSONResponse(status_code=500, content={"error": "Upload failed", "details": upload_response.text})

    # 8. Return the final public URL to Bubble
    public_url = f"{SUPABASE_IMAGE_BASE}{quote(filename)}"
    return JSONResponse(content={"image_url": public_url})