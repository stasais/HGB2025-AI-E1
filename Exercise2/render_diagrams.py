#!/usr/bin/env python3
"""
Script to render Mermaid diagrams from markdown and create PDF with images.
"""
import re
import os
from pathlib import Path
from mermaid import Mermaid
from mermaid.graph import Graph

def extract_mermaid_blocks(markdown_content):
    """Extract all mermaid code blocks from markdown."""
    pattern = r'```mermaid\n(.*?)```'
    matches = re.findall(pattern, markdown_content, re.DOTALL)
    return matches

def render_diagram(code, output_path, index):
    """Render a single mermaid diagram to PNG."""
    try:
        graph = Graph(f'diagram_{index}', code.strip())
        m = Mermaid(graph)
        png_path = output_path / f'diagram_{index}.png'
        m.to_png(str(png_path))
        print(f"✅ Rendered diagram {index} -> {png_path}")
        return png_path
    except Exception as e:
        print(f"❌ Failed to render diagram {index}: {e}")
        return None

def replace_mermaid_with_images(markdown_content, image_paths):
    """Replace mermaid blocks with image references."""
    def replacer(match):
        nonlocal image_index
        if image_index < len(image_paths) and image_paths[image_index]:
            img_path = str(image_paths[image_index].absolute())  # Use absolute path
            image_index += 1
            return f'![Diagram]({img_path})'
        image_index += 1
        return match.group(0)  # Keep original if failed
    
    image_index = 0
    pattern = r'```mermaid\n.*?```'
    return re.sub(pattern, replacer, markdown_content, flags=re.DOTALL)

def main():
    # Setup paths
    script_dir = Path(__file__).parent
    md_file = script_dir / 'architecture_diagrams.md'
    diagrams_dir = script_dir / 'diagrams'
    diagrams_dir.mkdir(exist_ok=True)
    
    # Read markdown
    print(f"📖 Reading {md_file}")
    content = md_file.read_text()
    
    # Extract mermaid blocks
    mermaid_blocks = extract_mermaid_blocks(content)
    print(f"📊 Found {len(mermaid_blocks)} Mermaid diagrams")
    
    # Render each diagram
    image_paths = []
    for i, code in enumerate(mermaid_blocks, 1):
        path = render_diagram(code, diagrams_dir, i)
        image_paths.append(path)
    
    # Create new markdown with images
    new_content = replace_mermaid_with_images(content, image_paths)
    
    # Write modified markdown
    output_md = script_dir / 'architecture_diagrams_with_images.md'
    output_md.write_text(new_content)
    print(f"📝 Created {output_md}")
    
    # Convert to PDF from the same directory
    pdf_path = script_dir / 'buinitskii_sbd_architecture.pdf'
    cmd = f'cd "{script_dir}" && pandoc "{output_md.name}" -o "{pdf_path.name}" --pdf-engine=xelatex -V geometry:margin=1cm --resource-path="{script_dir}"'
    os.system(cmd)
    print(f"📄 Created PDF: {pdf_path}")

if __name__ == '__main__':
    main()
