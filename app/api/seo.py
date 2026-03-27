from fastapi import APIRouter, Response
from datetime import datetime
import xml.etree.ElementTree as ET

router = APIRouter()

@router.get("/sitemap.xml")
async def get_sitemap():
    """
    Dynamically generates sitemap.xml for Zara AI.
    In a real-world scenario, this could query the database for blog posts or dynamic pages.
    """
    base_url = "https://zara-ai-assists.netlify.app"
    pages = [
        {"url": "/", "priority": "1.0", "changefreq": "daily"},
        {"url": "/features", "priority": "0.8", "changefreq": "weekly"},
        {"url": "/docs", "priority": "0.7", "changefreq": "weekly"},
        {"url": "/blog", "priority": "0.7", "changefreq": "daily"},
        {"url": "/pricing", "priority": "0.8", "changefreq": "monthly"},
        {"url": "/about", "priority": "0.6", "changefreq": "monthly"},
    ]
    
    # Root element
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    
    for page in pages:
        url_el = ET.SubElement(urlset, "url")
        loc = ET.SubElement(url_el, "loc")
        loc.text = f"{base_url}{page['url']}"
        
        lastmod = ET.SubElement(url_el, "lastmod")
        lastmod.text = datetime.now().strftime("%Y-%m-%d")
        
        changefreq = ET.SubElement(url_el, "changefreq")
        changefreq.text = page["changefreq"]
        
        priority = ET.SubElement(url_el, "priority")
        priority.text = page["priority"]
    
    # Generate XML string
    xml_data = ET.tostring(urlset, encoding='utf-8', method='xml')
    xml_declaration = b'<?xml version="1.0" encoding="UTF-8"?>\n'
    
    return Response(content=xml_declaration + xml_data, media_type="application/xml")

@router.get("/robots.txt")
async def get_robots():
    """
    Serves dynamic robots.txt.
    """
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "Sitemap: https://zara-ai-assists.netlify.app/sitemap.xml"
    )
    return Response(content=content, media_type="text/plain")

@router.get("/status")
async def get_seo_status():
    """
    Returns SEO health status.
    """
    return {
        "status": "healthy",
        "last_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sitemap_status": "synced",
        "indexing": {
            "google": "partial",
            "bing": "partial",
            "duckduckgo": "indexed"
        },
        "crawl_errors": 0,
        "active_pages": 12
    }
