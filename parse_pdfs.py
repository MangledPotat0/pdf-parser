#!/usr/bin/env python3
"""
Minimal PDF to Markdown converter
Reads PDFs from /pdfs directory and outputs markdown to /output directory
"""

import os
import sys
from pathlib import Path
import pdfplumber

def parse_pdf_to_markdown(pdf_path, output_path):
    """Extract text from PDF and save as markdown"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_content = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text from page
                text = page.extract_text()
                if text:
                    text_content.append(text)
            
            # Join all pages
            full_text = "\n\n".join(text_content)
            
            # Write to markdown file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            print(f"✓ Converted: {pdf_path.name} -> {output_path.name}")
            return True
            
    except Exception as e:
        print(f"✗ Error converting {pdf_path.name}: {str(e)}")
        return False

def main():
    pdf_dir = Path("/pdfs")
    output_dir = Path("/output")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in /pdfs directory")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    print("-" * 50)
    
    success_count = 0
    for pdf_file in pdf_files:
        # Create output filename (replace .pdf with .md)
        output_file = output_dir / f"{pdf_file.stem}.md"
        
        if parse_pdf_to_markdown(pdf_file, output_file):
            success_count += 1
    
    print("-" * 50)
    print(f"Completed: {success_count}/{len(pdf_files)} files converted successfully")

if __name__ == "__main__":
    main()
