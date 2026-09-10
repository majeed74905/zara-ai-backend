
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
from google import genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configuration happens on client instantiation now
# if settings.GOOGLE_API_KEY:

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
            return await analyze_pdf(content)
            
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

async def analyze_pdf(content: bytes) -> Dict[str, Any]:
    """
    Extract content from a PDF.
    Fast path: pypdf text extraction (digital PDFs).
    Fallback: if little/no text is found (scanned or image-based PDF / forms),
    use Gemini's native PDF understanding (OCR + visual reading) for an accurate result.
    """
    extracted_text = ""
    page_count = 0
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        page_count = len(reader.pages)
        for page in reader.pages[:15]:  # first 15 pages to keep it fast
            extracted_text += (page.extract_text() or "") + "\n"
    except Exception as e:
        logger.warning(f"pypdf extraction failed: {e}")

    cleaned = extracted_text.strip()

    # Fast path: real text was extracted (digital PDF)
    if len(cleaned) >= 120:
        return {
            "type": "pdf",
            "summary": cleaned[:12000],
            "page_count": page_count,
            "status": "success",
            "extraction": "text",
        }

    # Fallback: scanned/image-based PDF → read it with Gemini (handles OCR + layout)
    if settings.GEMINI_API_KEY:
        try:
            from google.genai import types
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            pdf_part = types.Part.from_bytes(data=content, mime_type="application/pdf")
            response = await client.aio.models.generate_content(
                model="gemini-1.5-flash",
                contents=[
                    (
                        "Read this PDF carefully — it may be scanned, handwritten, or a filled form. "
                        "Extract and clearly lay out ALL meaningful content: document type and purpose, "
                        "every field with its value, names, dates, ID numbers, tables, and any notable details. "
                        "Preserve the document's structure. Be thorough and accurate; do not invent anything."
                    ),
                    pdf_part,
                ],
            )
            vision_text = (response.text or "").strip()
            if vision_text:
                return {
                    "type": "pdf",
                    "summary": vision_text[:12000],
                    "page_count": page_count,
                    "status": "success",
                    "extraction": "vision",
                }
        except Exception as e:
            logger.error(f"Gemini PDF vision analysis failed: {e}")

    # Last resort
    return {
        "type": "pdf",
        "summary": cleaned or "No extractable text found (likely a scanned PDF without OCR support).",
        "page_count": page_count,
        "status": "success" if cleaned else "partial",
        "extraction": "none",
    }

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
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        image = Image.open(io.BytesIO(content))
        
        response = await client.aio.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                "Analyze this image and provide a detailed description of its contents, identifying key elements, text, and context.",
                image
            ]
        )
        
        return {
            "type": "image",
            "summary": response.text,
            "status": "success"
        }
    except Exception as e:
        return {"error": f"Image analysis failed: {str(e)}", "status": "failed"}
