import os
import base64
from pathlib import Path
from io import BytesIO
from PIL import Image
from transformers import AutoProcessor
from transformers import Qwen2_5_VLForConditionalGeneration
from pdf2image import convert_from_path
import torch
import re

# Get Hugging Face token from environment
HF_TOKEN = os.environ.get('HF_TOKEN', None)

def fix_equation_formatting(text):
    """Convert LaTeX equations from \[ \] and \( \) to $$ $$ and $ $ for markdown."""
    # Replace block equations: \[ ... \] -> $$ ... $$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    
    # Replace inline equations: \( ... \) -> $ ... $
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    
    return text

def parse_pdf_with_olmocr(pdf_path, output_dir):
    """Parse PDF using olmOCR with multi-GPU support."""
    print(f"Processing: {pdf_path}")
    
    # Create figures subdirectory
    pdf_name = Path(pdf_path).stem
    figures_dir = Path(output_dir) / f"{pdf_name}_figures"
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
    
    # Save all page images as potential figures
    print(f"Saving page images to {figures_dir}...")
    for page_num, pil_image in enumerate(images, 1):
        figure_path = figures_dir / f"page_{page_num}.png"
        pil_image.save(figure_path, "PNG")
    
    # Process each page
    markdown_pages = []
    figure_references = []
    
    for page_num, pil_image in enumerate(images, 1):
        print(f"Processing page {page_num}/{num_pages}...")
        
        # Enhanced prompt to detect figures
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text from this image in markdown format. Preserve the structure, headings, equations (in LaTeX), and tables. For figures/diagrams, note their location with markdown image syntax: ![Figure caption](path). For tables, use markdown table syntax."
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
        
        # Check if page contains figure references
        if re.search(r'Figure \d+:', text_output, re.IGNORECASE):
            figure_references.append((page_num, text_output))
            # Add reference to saved page image
            figure_path = f"{pdf_name}_figures/page_{page_num}.png"
            text_output += f"\n\n![Page {page_num} - Contains figure]({figure_path})\n"
        
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
    if figure_references:
        print(f"\nFound {len(figure_references)} pages with figures:")
        for page_num, _ in figure_references:
            print(f"  - Page {page_num}: {figures_dir}/page_{page_num}.png")
    
    print(f"All page images saved to: {figures_dir}/")
    
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
