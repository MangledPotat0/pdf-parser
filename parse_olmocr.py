import os
import base64
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw
from transformers import AutoProcessor
from transformers import Qwen2_5_VLForConditionalGeneration
from pdf2image import convert_from_path
import torch
import re
import numpy as np

# Get Hugging Face token from environment
HF_TOKEN = os.environ.get('HF_TOKEN', None)

def fix_equation_formatting(text):
    """Convert LaTeX equations from \[ \] and \( \) to $$ $$ and $ $ for markdown."""
    # Replace block equations: \[ ... \] -> $$ ... $$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    
    # Replace inline equations: \( ... \) -> $ ... $
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    
    return text

def extract_figure_from_page(pil_image, page_num, figures_dir, pdf_name):
    """
    Extract figure region from a page by detecting non-text areas.
    Returns the figure path if a figure is found, None otherwise.
    """
    # Convert to grayscale
    gray = pil_image.convert('L')
    img_array = np.array(gray)
    
    # Simple heuristic: look for large connected regions of non-white pixels
    # This is a basic approach - figures typically have darker pixels
    threshold = 250  # Nearly white threshold
    binary = img_array < threshold
    
    # Find bounding box of non-white regions
    rows = np.any(binary, axis=1)
    cols = np.any(binary, axis=0)
    
    if not np.any(rows) or not np.any(cols):
        return None
    
    # Get the bounds
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    
    # Calculate dimensions
    height = rmax - rmin
    width = cmax - cmin
    total_pixels = height * width
    image_pixels = img_array.shape[0] * img_array.shape[1]
    
    # If the non-white area is between 10% and 80% of page, likely contains a figure
    # (Too small = just text, too large = full page text)
    ratio = total_pixels / image_pixels
    
    if 0.1 < ratio < 0.8:
        # Crop with some padding
        padding = 20
        crop_box = (
            max(0, cmin - padding),
            max(0, rmin - padding),
            min(img_array.shape[1], cmax + padding),
            min(img_array.shape[0], rmax + padding)
        )
        
        cropped = pil_image.crop(crop_box)
        
        # Save the figure
        figure_filename = f"figure_page_{page_num}.png"
        figure_path = figures_dir / figure_filename
        cropped.save(figure_path, "PNG")
        
        return f"data/{pdf_name}/{figure_filename}"
    
    return None

def parse_pdf_with_olmocr(pdf_path, output_dir):
    """Parse PDF using olmOCR with multi-GPU support."""
    print(f"Processing: {pdf_path}")
    
    # Create figures subdirectory in data/[PAPER_NAME]/
    pdf_name = Path(pdf_path).stem
    # Save figures in data directory, not output
    data_dir = Path("/app/data")
    figures_dir = data_dir / pdf_name
    figures_dir.mkdir(exist_ok=True)
    
    # Load model with automatic device mapping across multiple GPUs
    print("Loading olmOCR model with multi-GPU support...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        "allenai/olmOCR-2-7B-1025",
        torch_dtype=torch.bfloat16,
        device_map="auto",  # Automatically split across available GPUs
        token=HF_TOKEN
    )
    
    processor = AutoProcessor.from_pretrained(
        "Qwen/Qwen2.5-VL-7B-Instruct",
        token=HF_TOKEN
    )
    
    print(f"Model loaded successfully!")
    print(f"Device map: {model.hf_device_map}")
    
    # Convert PDF to images
    print("Converting PDF to images...")
    images = convert_from_path(str(pdf_path), dpi=200)
    num_pages = len(images)
    print(f"Processing {num_pages} pages...")
    
    # Process each page
    markdown_pages = []
    extracted_figures = {}  # page_num -> figure_path
    
    for page_num, pil_image in enumerate(images, 1):
        print(f"Processing page {page_num}/{num_pages}...")
        
        # Enhanced prompt to detect figures
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text from this image in markdown format. Preserve the structure, headings, equations (in LaTeX), and tables. If there are figures or diagrams, describe them briefly with 'Figure N: [description]'. For tables, use markdown table syntax."
                    },
                    {
                        "type": "image",
                        "image": pil_image
                    },
                ],
            }
        ]
        
        # Apply chat template
        text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Process inputs
        inputs = processor(
            text=[text],
            images=[pil_image],
            padding=True,
            return_tensors="pt",
        )
        
        # Move to GPU (model handles multi-GPU distribution)
        inputs = {key: value.to("cuda:0") for (key, value) in inputs.items()}
        
        # Generate output
        with torch.no_grad():
            output = model.generate(
                **inputs,
                temperature=0.1,
                max_new_tokens=4096,
                num_return_sequences=1,
                do_sample=True,
            )
        
        # Decode output
        prompt_length = inputs["input_ids"].shape[1]
        new_tokens = output[:, prompt_length:]
        text_output = processor.tokenizer.batch_decode(
            new_tokens,
            skip_special_tokens=True
        )[0]
        
        # Check if page contains figure references and extract the figure
        if re.search(r'Figure \d+:', text_output, re.IGNORECASE):
            print(f"  -> Figure detected on page {page_num}, extracting...")
            figure_path = extract_figure_from_page(pil_image, page_num, figures_dir, pdf_name)
            if figure_path:
                extracted_figures[page_num] = figure_path
                # Add figure reference in markdown
                text_output += f"\n\n![Figure from page {page_num}]({figure_path})\n"
                print(f"  -> Figure saved to: {figure_path}")
            else:
                # Save full page as fallback
                fallback_path = f"data/{pdf_name}/page_{page_num}.png"
                pil_image.save(figures_dir / f"page_{page_num}.png", "PNG")
                text_output += f"\n\n![Page {page_num}]({fallback_path})\n"
                print(f"  -> Saved full page as fallback")
        
        markdown_pages.append(text_output)
        print(f"Page {page_num} done ({len(text_output)} chars)")
    
    # Combine all pages
    full_markdown = "\n\n---\n\n".join(markdown_pages)
    
    # Fix equation formatting for proper markdown rendering
    print("Converting LaTeX equation syntax...")
    full_markdown = fix_equation_formatting(full_markdown)
    
    # Use PDF filename for output
    output_filename = f"{pdf_name}_olmocr.md"
    
    # Save output
    output_path = Path(output_dir) / output_filename
    output_path.write_text(full_markdown, encoding='utf-8')
    print(f"\nSaved markdown to: {output_path}")
    
    # Print figure summary
    if extracted_figures:
        print(f"\n✓ Extracted {len(extracted_figures)} figures:")
        for page_num, fig_path in extracted_figures.items():
            print(f"  - Page {page_num}: {fig_path}")
    
    print(f"\nFigures saved to: {figures_dir}/")
    
    return output_path

if __name__ == "__main__":
    data_dir = Path("/app/data")
    output_dir = Path("/app/output")
    output_dir.mkdir(exist_ok=True)
    
    # Process all PDFs in data directory
    pdf_files = list(data_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in /app/data")
        exit(1)
    
    for pdf_file in pdf_files:
        try:
            parse_pdf_with_olmocr(pdf_file, output_dir)
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            import traceback
            traceback.print_exc()
