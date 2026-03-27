
import os
import io
import zipfile
import logging
from typing import List, Dict, Any
from fastapi import UploadFile
import pypdf
import docx
import pandas as pd
from PIL import Image
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini for Image Analysis
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)

async def analyze_upload(file: UploadFile) -> Dict[str, Any]:
    """
    Analyzes a single uploaded file based on its mime type/extension.
    """
    filename = file.filename
    content_type = file.content_type
    
    logger.info(f"Analyzing file: {filename} ({content_type})")
    
    try:
        content = await file.read()
        file_size = len(content)
        
        # 1. ARCHIVES (ZIP)
        if filename.endswith('.zip') or content_type == 'application/zip':
            return await analyze_zip(content)
            
        # 2. PDF
        if filename.endswith('.pdf') or content_type == 'application/pdf':
            return analyze_pdf(content)
            
        # 3. WORD DOCUMENTS
        if filename.endswith('.docx') or content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return analyze_docx(content)
            
        # 4. EXCEL
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            return analyze_excel(content, filename)
            
        # 5. IMAGES
        if content_type.startswith('image/'):
            return await analyze_image(content, content_type)
            
        # 6. TEXT / CODE
        # Fallback for code files, text files, etc.
        try:
            text_content = content.decode('utf-8', errors='ignore')
            # Limit text content to 100kb to prevent massive prompt injection
            summary = text_content[:10000] 
            return {
                "filename": filename,
                "type": "text/code",
                "summary": summary,
                "size": file_size,
                "status": "success"
            }
        except Exception:
            pass

        return {
            "filename": filename,
            "type": "unknown",
            "summary": "Binary or unsupported file type.",
            "status": "skipped"
        }

    except Exception as e:
        logger.error(f"Error analyzing {filename}: {str(e)}")
        return {
            "filename": filename,
            "error": str(e),
            "status": "failed"
        }

async def analyze_zip(content: bytes) -> Dict[str, Any]:
    try:
        results = []
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            for file_info in z.infolist():
                if file_info.is_dir() or file_info.filename.startswith('__MACOSX') or file_info.filename.endswith('.DS_Store'):
                    continue
                
                with z.open(file_info) as f:
                    file_content = f.read()
                    # Recursive analysis restricted to text/small files to avoid infinite loops/complexity
                    # For now, just extract text from internal files
                    try:
                        text = file_content.decode('utf-8', errors='ignore')
                        results.append(f"File: {file_info.filename}\nContent: {text[:2000]}\n---")
                    except:
                        results.append(f"File: {file_info.filename} (Binary/Skipped)")

        return {
            "filename": "archive.zip",
            "type": "archive",
            "summary": "\n".join(results)[:20000], # Cap archive analysis
            "status": "success",
            "file_count": len(results)
        }
    except Exception as e:
        return {"error": f"Zip extraction failed: {str(e)}", "status": "failed"}

def analyze_pdf(content: bytes) -> Dict[str, Any]:
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages[:10]: # Analyze first 10 pages to save time
            text += page.extract_text() + "\n"
        
        return {
            "type": "pdf",
            "summary": text[:10000],
            "page_count": len(reader.pages),
            "status": "success"
        }
    except Exception as e:
        return {"error": f"PDF parsing failed: {str(e)}", "status": "failed"}

def analyze_docx(content: bytes) -> Dict[str, Any]:
    try:
        doc = docx.Document(io.BytesIO(content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return {
            "type": "docx",
            "summary": text[:10000],
            "status": "success"
        }
    except Exception as e:
        return {"error": f"DOCX parsing failed: {str(e)}", "status": "failed"}

def analyze_excel(content: bytes, filename: str) -> Dict[str, Any]:
    try:
        df = pd.read_excel(io.BytesIO(content))
        # Convert first few rows to markdown
        summary = f"Columns: {list(df.columns)}\n\nPreview:\n{df.head(5).to_markdown()}"
        return {
            "type": "excel",
            "summary": summary,
            "status": "success"
        }
    except Exception as e:
        return {"error": f"Excel parsing failed: {str(e)}", "status": "failed"}

async def analyze_image(content: bytes, mime_type: str) -> Dict[str, Any]:
    # Use Gemini Vision if available
    if not settings.GEMINI_API_KEY:
         return {
            "type": "image",
            "summary": "Image analysis requires GEMINI_API_KEY.",
            "status": "skipped"
        }

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        image = Image.open(io.BytesIO(content))
        
        response = await model.generate_content_async([
            "Analyze this image and provide a detailed description of its contents, identifying key elements, text, and context.",
            image
        ])
        
        return {
            "type": "image",
            "summary": response.text,
            "status": "success"
        }
    except Exception as e:
        return {"error": f"Image analysis failed: {str(e)}", "status": "failed"}
