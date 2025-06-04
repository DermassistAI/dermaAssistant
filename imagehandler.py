# imagehandler.py

import os
import cloudinary
import cloudinary.uploader
import httpx
from fastapi import Request
from agno.app.whatsapp.router import WhatsAppRouter

# Import your derma agent
from dermaAssistant import derma_agent  # Ensure this is correct or refactor to avoid circular imports

# Setup WhatsApp Router
router = WhatsAppRouter(agent=derma_agent)

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# Helper: Get media URL from WhatsApp (requires bearer token)
async def get_media_url(media_id: str, access_token: str) -> str:
    url = f"https://graph.facebook.com/v19.0/{media_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        res.raise_for_status()
        return res.json()["url"]

# Helper: Download image content
async def download_image(url: str, access_token: str) -> bytes:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        res.raise_for_status()
        return res.content

# Helper: Upload to Cloudinary
def upload_to_cloudinary(image_bytes: bytes) -> str:
    uploaded = cloudinary.uploader.upload(image_bytes)
    return uploaded["secure_url"]

# WhatsApp image message handler
@router.on_image()
async def handle_image(agent, wa_id: str, media_id: str, caption: str | None, request: Request):
    token = os.getenv("WHATSAPP_TOKEN")
    try:
        image_url = await get_media_url(media_id, token)
        image_bytes = await download_image(image_url, token)
        cloud_url = upload_to_cloudinary(image_bytes)

        # Send to Derma Agent
        response = await agent.astream(input=cloud_url, user_id=wa_id, metadata={"caption": caption})
        async for chunk in response:
            await router.reply(wa_id, chunk)

    except Exception as e:
        await router.reply(wa_id, f"❌ Error analyzing image: {str(e)}")
