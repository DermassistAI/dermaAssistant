import cloudinary
import cloudinary.uploader
import os
from typing import Optional

# Configure Cloudinary once (can be in your main app startup or environment setup)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

def upload_to_cloudinary(image_bytes: bytes) -> Optional[str]:
    """
    Upload image bytes to Cloudinary and return the secure URL.

    Args:
        image_bytes (bytes): Raw image content.

    Returns:
        str: Secure URL of the uploaded image, or None if failed.
    """
    try:
        print("[Cloudinary] Starting upload...")
        upload_result = cloudinary.uploader.upload(image_bytes)
        print(f"[Cloudinary] Upload result: {upload_result}")
        secure_url = upload_result.get("secure_url")
        if not secure_url:
            print("[Cloudinary] No secure_url in upload result!")
        return secure_url
    except Exception as e:
        print(f"[Cloudinary] Upload failed: {e}")
        return None
