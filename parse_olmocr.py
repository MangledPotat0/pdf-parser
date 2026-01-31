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

def parse_pdf_with_olmocr(pdf_path, output_dir):
    """Parse PDF using olmOCR with multi-GPU support."""
    print(f"Processing: {pdf_path}")
    
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
    for page_num, pil_image in enumerate(images, 1):
        print(f"Processing page {page_num}/{num_pages}...")
        
        # Simple prompt for OCR
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text from this image in markdown format. Preserve the structure, headings, equations (in LaTeX), and tables."
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
        
        markdown_pages.append(text_output)
        print(f"Page {page_num} done ({len(text_output)} chars)")
    
    # Combine all pages
    full_markdown = "\n\n---\n\n".join(markdown_pages)
    
    # Use PDF filename for output
    pdf_name = Path(pdf_path).stem
    output_filename = f"{pdf_name}_olmocr.md"
    
    # Save output
    output_path = Path(output_dir) / output_filename
    output_path.write_text(full_markdown, encoding='utf-8')
    print(f"\nSaved to: {output_path}")
    
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
