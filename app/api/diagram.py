
from fastapi import APIRouter, HTTPException, Response
from app.services.diagram_service import DiagramSchema, render_diagram
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/render")
async def render_png(schema: DiagramSchema):
    if not schema.nodes:
        raise HTTPException(status_code=400, detail="Diagram must have at least one node")
    
    try:
        image_bytes = await render_diagram(schema, format="png")
        return Response(content=image_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"PNG render failure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/render-svg")
async def render_svg(schema: DiagramSchema):
    if not schema.nodes:
        raise HTTPException(status_code=400, detail="Diagram must have at least one node")
    
    try:
        image_bytes = await render_diagram(schema, format="svg")
        return Response(content=image_bytes, media_type="image/svg+xml")
    except Exception as e:
        logger.error(f"SVG render failure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
