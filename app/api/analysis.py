
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from app.services.file_analysis import analyze_upload
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze_files")
async def analyze_files_endpoint(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    results = []
    
    for file in files:
        result = await analyze_upload(file)
        results.append({
            "filename": file.filename,
            "analysis": result
        })
    
    # Generate a consolidated text summary for the AI context
    context_text = "Analysis of Uploaded Files:\n===========================\n"
    for res in results:
        analysis = res['analysis']
        if analysis.get('status') == 'success':
            context_text += f"\nFile: {res['filename']} ({analysis.get('type')})\n"
            context_text += f"Content Summary:\n{analysis.get('summary')}\n"
            context_text += "---------------------------\n"
        elif analysis.get('status') == 'failed':
             context_text += f"\nFile: {res['filename']} - FAILED: {analysis.get('error')}\n"

    return {
        "results": results,
        "context_text": context_text
    }
