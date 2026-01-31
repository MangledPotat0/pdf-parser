# PDF to Markdown Parser

Minimal Docker container for converting PDF files to Markdown format.

## Build the Container

```bash
docker build -t pdf-parser .
```

## Usage

```bash
docker run --rm \
  -v /path/to/your/pdfs:/pdfs \
  -v /path/to/output:/output \
  pdf-parser
```

### Windows PowerShell Example

```powershell
docker run --rm `
  -v C:\path\to\pdfs:/pdfs `
  -v C:\path\to\output:/output `
  pdf-parser
```

## Directory Structure

- `/pdfs` - Mount your PDF files here (input)
- `/output` - Converted markdown files will be saved here (output)

## Notes

- All PDF files in the `/pdfs` directory will be converted
- Output files will have the same name with `.md` extension
- Basic text extraction only (no complex formatting yet)
