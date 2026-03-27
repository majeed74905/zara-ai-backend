from fastapi import APIRouter, HTTPException, Depends
from app.schemas.image import ImageGenerationRequest, ImageGenerationResponse
from app.core.config import settings
import httpx
import base64
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Stability AI API URL for Stable Diffusion XL
STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

@router.post("/generate-image", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    if not settings.STABILITY_API_KEY:
        raise HTTPException(status_code=500, detail="Stability AI API Key not configured")

    headers = {
        "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Style mapping to prompt enhancements
    enhanced_prompt = request.prompt
    style_preset = None
    
    # Stability AI supports style_preset in some endpoints, or manual prompting
    # We will use manual prompting for better control over the main prompt
    if request.style == "anime":
        enhanced_prompt += ", anime style, vibrant colors, studio ghibli, high quality"
        style_preset = "anime"
    elif request.style == "cyberpunk":
        enhanced_prompt += ", cyberpunk, neon lights, futuristic, high tech"
    elif request.style == "realistic":
        enhanced_prompt += ", photorealistic, 8k, detailed, cinematic lighting"
        style_preset = "photographic"
    elif request.style == "cartoon":
        enhanced_prompt += ", cartoon, flat colors, illustration"
        style_preset = "comic-book"

    # Default negative prompt
    negative_prompt = "blurry, low quality, distorted, watermark, bad anatomy, deformed"

    # Ensure dimensions are allowed by SDXL (must be multiples of 64)
    # Defaulting to 1024x1024 as it's the native resolution for SDXL
    # If user sends 512, we might want to upscale or just request 1024 for better quality
    width = 1024
    height = 1024
    
    if request.width and request.height:
        # Simple logic to match aspect ratio but keep high res
        ratio = request.width / request.height
        if ratio > 1: # Landscape
            width = 1216
            height = 832
        elif ratio < 1: # Portrait
            width = 832
            height = 1216
            
    payload = {
        "text_prompts": [
            {"text": enhanced_prompt, "weight": 1},
            {"text": negative_prompt, "weight": -1}
        ],
        "cfg_scale": 7,
        "height": height,
        "width": width,
        "samples": 1,
        "steps": 30,
    }
    
    if style_preset:
        payload["style_preset"] = style_preset

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(STABILITY_API_URL, headers=headers, json=payload, timeout=45.0)
            
            if response.status_code != 200:
                logger.error(f"Stability API Error: {response.text}")
                error_detail = "Image generation failed"
                try:
                    error_json = response.json()
                    error_detail = error_json.get("message", error_json.get("name", error_detail))
                except:
                    pass
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            data = response.json()
            # Stability AI returns a list of artifacts
            artifacts = data.get("artifacts", [])
            if not artifacts:
                raise HTTPException(status_code=500, detail="No image generated")
            
            # Get the first image
            base64_image = artifacts[0].get("base64")
            image_data_url = f"data:image/png;base64,{base64_image}"

            return ImageGenerationResponse(image_url=image_data_url)

    except httpx.RequestError as exc:
        logger.error(f"Request error: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error during image generation")
