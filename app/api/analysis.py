
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from app.services.file_analysis import analyze_upload
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_FILES = 5
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB

@router.post("/analyze_files")
async def analyze_files_endpoint(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_FILES} files allowed per request."
        )
    
    results = []
    
    for file in files:
        # Check file size before full processing
        content_peek = await file.read()
        if len(content_peek) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File '{file.filename}' exceeds maximum allowed size of 15MB."
            )
        # Reset file pointer for analysis
        await file.seek(0)
        
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
