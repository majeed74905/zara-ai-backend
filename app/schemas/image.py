from pydantic import BaseModel
from typing import Optional

class ImageGenerationRequest(BaseModel):
    prompt: str
    style: Optional[str] = "realistic"
    width: Optional[int] = 512
    height: Optional[int] = 512

class ImageGenerationResponse(BaseModel):
    image_url: str
