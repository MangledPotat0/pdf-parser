# PDF to Markdown Parser

Docker containers for converting research papers (PDF) to Markdown format with BibTeX metadata extraction.

## Three Parser Options

### 1. Standard Parser (pdfplumber) - Fast, Lightweight
Basic PDF text extraction with structure detection.

**Build:**
```bash
docker build -t pdf-parser .
```

**Features:**
- Fast processing (~1 second per page)
- Small image size (~250MB)
- Basic equation detection
- Structure-aware (sections, subsections)
- Metadata extraction (title, authors, year)
- BibTeX generation
- **No GPU required**

**Limitations:**
- Complex equations lose formatting (subscripts, superscripts)
- Figures show captions only
- Tables may not format perfectly

### 2. olmOCR Parser - High Quality, Multi-GPU
AllenAI's vision-language model (8B parameters) for document OCR with proper LaTeX equations.

**Requirements:**
- **2x GPUs with 16GB+ VRAM each** (or 1x 24GB+ GPU)
- NVIDIA Docker runtime
- Hugging Face token (free account)

**Build:**
```bash
docker build -f Dockerfile.olmocr -t pdf-parser-olmocr .
```

**Run:**
```bash
# Create .env file with your Hugging Face token
echo "HF_TOKEN=hf_your_token_here" > .env

# Run with both GPUs
docker run --rm --gpus all --env-file .env \
  -v /path/to/your/pdfs:/app/data \
  -v /path/to/output:/app/output \
  pdf-parser-olmocr
```

**Features:**
- ✅ Excellent equation handling (proper LaTeX: `\( x^2 \)`, `\[ E = mc^2 \]`)
- ✅ Better structure detection
- ✅ Table formatting preserved
- ✅ Figure recognition
- ✅ Automatic multi-GPU distribution
- First run downloads ~15GB model (cached for future runs)

**Performance:**
- ~2-3 seconds per page (on 2x RTX 4060 Ti)
- Processes full papers in 30-60 seconds

### 3. Nougat Parser - DEPRECATED
Meta's academic PDF parser. **Not recommended** - has compatibility issues with many PDFs.

See NOUGAT_STATUS.md for details on why we don't recommend this approach.

## Usage

### Standard Parser (pdfplumber)
```bash
docker run --rm \
  -v /path/to/your/pdfs:/pdfs \
  -v /path/to/output:/output \
  pdf-parser
```

### olmOCR Parser (Multi-GPU)
```bash
# Windows PowerShell
docker run --rm --gpus all --env-file .env `
  -v C:\path\to\pdfs:/app/data `
  -v C:\path\to\output:/app/output `
  pdf-parser-olmocr

# Linux/Mac
docker run --rm --gpus all --env-file .env \
  -v /path/to/pdfs:/app/data \
  -v /path/to/output:/app/output \
  pdf-parser-olmocr
```

## Output Files

### Standard Parser
For each PDF:
- `{paper_title}.md` - Markdown file with paper content
- `{paper_title}.bib` - BibTeX entry with metadata

### olmOCR Parser
For each PDF:
- `{filename}_olmocr.md` - Markdown file with full LaTeX equations

Example:
- Input: `NIPS-2017-attention-is-all-you-need-Paper.pdf`
- Standard output: 
  - `Attention_is_All_you_Need.md`
  - `Attention_is_All_you_Need.bib`
- olmOCR output:
  - `NIPS-2017-attention-is-all-you-need-Paper_olmocr.md`

## Directory Structure

### Standard Parser
- `/pdfs` - Mount your PDF files here (input)
- `/output` - Converted markdown and BibTeX files saved here

### olmOCR Parser
- `/app/data` - Mount your PDF files here (input)
- `/app/output` - Converted markdown files saved here

## Setup Notes

### Getting a Hugging Face Token (for olmOCR)
1. Create free account at https://huggingface.co
2. Go to https://huggingface.co/settings/tokens
3. Click "Create new token"
4. Select "Read" access
5. Copy token (starts with `hf_...`)
6. Create `.env` file with: `HF_TOKEN=hf_your_token_here`

### GPU Requirements (olmOCR)
- **Minimum:** 2x 16GB GPUs or 1x 24GB GPU
- **Tested on:** 2x RTX 4060 Ti (16GB each)
- Model automatically distributes across available GPUs
- Uses `device_map="auto"` for optimal memory utilization

## Notes

- All PDF files in input directory will be processed
- Standard parser: output filenames based on paper title
- olmOCR parser: preserves original PDF filename with `_olmocr` suffix
- Metadata (title, authors, affiliations) removed from markdown body (standard parser only)
- BibTeX includes: title, authors, year, venue, abstract (standard parser only)
