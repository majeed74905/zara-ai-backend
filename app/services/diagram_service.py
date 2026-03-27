
import os
import uuid
import logging
import subprocess
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class DiagramNode(BaseModel):
    id: str
    label: str
    shape: Optional[str] = "box"

class DiagramEdge(BaseModel):
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    label: Optional[str] = None

    class Config:
        populate_by_name = True

class DiagramSchema(BaseModel):
    type: str = "flowchart"
    direction: str = "top-down"
    nodes: List[DiagramNode]
    edges: List[DiagramEdge]

def json_to_dot(schema: DiagramSchema) -> str:
    """
    Converts Normalized JSON schema to Graphviz DOT syntax.
    """
    direction = "TB" if schema.direction == "top-down" else "LR"
    
    dot = [
        "digraph G {",
        f'  rankdir={direction};',
        '  bgcolor="#FFFFFF";',
        '  node [fontname="Arial", fontsize=12, style=filled, fillcolor="#f8fafc", color="#cbd5e1"];',
        '  edge [fontname="Arial", fontsize=10, color="#64748b"];',
    ]
    
    # Map shapes
    # AI uses: oval, box, diamond
    # Graphviz uses: ellipse, box, diamond
    shape_map = {
        "oval": "ellipse",
        "box": "box",
        "diamond": "diamond"
    }
    
    for node in schema.nodes:
        shape = shape_map.get(node.shape, "box")
        label = node.label.replace('"', '\\"') # Escape quotes in labels
        dot.append(f'  "{node.id}" [label="{label}", shape={shape}];')
        
    for edge in schema.edges:
        label_part = f', label="{edge.label}"' if edge.label else ""
        dot.append(f'  "{edge.from_node}" -> "{edge.to_node}" [color="#64748b"{label_part}];')
        
    dot.append("}")
    return "\n".join(dot)

async def render_diagram(schema: DiagramSchema, format: str = "png") -> bytes:
    """
    Renders diagram using the 'dot' command line tool.
    """
    dot_content = json_to_dot(schema)
    temp_id = str(uuid.uuid4())
    dot_file = f"temp_{temp_id}.dot"
    out_file = f"temp_{temp_id}.{format}"
    
    try:
        with open(dot_file, "w", encoding="utf-8") as f:
            f.write(dot_content)
            
        # Try to find dot path if not in global path
        dot_path = "dot"
        if os.name == 'nt': # Windows
            common_paths = [
                "C:\\Program Files\\Graphviz\\bin\\dot.exe",
                "C:\\Program Files (x86)\\Graphviz\\bin\\dot.exe"
            ]
            for p in common_paths:
                if os.path.exists(p):
                    dot_path = p
                    break

        # Run Graphviz
        process = subprocess.run(
            [dot_path, f"-T{format}", dot_file, "-o", out_file],
            capture_output=True,
            text=True,
            check=True
        )
        
        with open(out_file, "rb") as f:
            image_data = f.read()
            
        return image_data
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Graphviz render error: {e.stderr}")
        raise Exception(f"Graphviz render failed: {e.stderr}")
    except Exception as e:
        logger.error(f"General render error: {str(e)}")
        raise e
    finally:
        # Cleanup
        if os.path.exists(dot_file): os.remove(dot_file)
        if os.path.exists(out_file): os.remove(out_file)
