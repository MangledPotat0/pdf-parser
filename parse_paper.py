#!/usr/bin/env python3
"""
Research Paper to Markdown Parser
Specialized for academic papers with sections, equations, and references
"""

import re
from pathlib import Path
import pdfplumber

class PaperParser:
    def __init__(self):
        self.sections = []
        self.current_section = None
        
    def extract_text_with_structure(self, pdf_path):
        """Extract text from PDF preserving structure"""
        all_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Use layout mode to better preserve spacing
                text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=3)
                if text:
                    all_text.append(text)
        
        # Join all pages with page breaks
        full_text = "\n\n".join(all_text)
        
        return self.parse_structure(full_text)
    
    def detect_equation(self, line):
        """Detect if a line contains a mathematical equation"""
        # Look for mathematical indicators
        math_indicators = [
            r'=',  # equals sign
            r'\+',  # plus
            r'∑',  # summation
            r'∫',  # integral
            r'∏',  # product
            r'√',  # square root
            r'[A-Z]\(',  # Function calls like Q(, K(
            r'\b(sin|cos|tan|log|exp|max|min|softmax)\b',  # functions
            r'[₀-₉]',  # subscripts
            r'[⁰-⁹]',  # superscripts
            r'\^',  # exponent marker
            r'_',  # subscript marker in plain text
        ]
        
        # Check if line has equation indicators
        has_math = any(re.search(pattern, line) for pattern in math_indicators)
        
        # Check if line is mostly mathematical (less than 20% letters)
        letters = len(re.findall(r'[a-zA-Z]', line))
        total = len(line.replace(' ', ''))
        
        if total > 0 and has_math and letters / total < 0.5:
            return True
        
        # Check for numbered equations like (1), (2), etc at end
        if re.search(r'\(\d+\)\s*$', line.strip()):
            return True
            
        return False
    
    def clean_equation(self, line):
        """Clean and format equation for markdown"""
        line = line.strip()
        
        # Remove equation numbers temporarily
        eq_num_match = re.search(r'\((\d+)\)\s*$', line)
        eq_num = None
        if eq_num_match:
            eq_num = eq_num_match.group(1)
            line = line[:eq_num_match.start()].strip()
        
        # Wrap in display math
        result = f"$$\n{line}\n$$"
        
        if eq_num:
            result += f" (Eq. {eq_num})"
        
        return result
    
    def detect_table(self, lines, start_idx):
        """Detect if lines form a table"""
        # Look for multiple lines with consistent spacing/structure
        # This is a simple heuristic
        if start_idx + 2 >= len(lines):
            return False, 0
        
        # Check for Table keyword
        if 'Table' in lines[start_idx] and ':' in lines[start_idx]:
            return True, min(10, len(lines) - start_idx)
        
        return False, 0
    
    def parse_structure(self, text):
        """Parse text into structured sections"""
        lines = text.split('\n')
        
        result = []
        current_section = []
        in_abstract = False
        in_references = False
        skip_lines = 0
        title_found = False
        
        for i, line in enumerate(lines):
            if skip_lines > 0:
                skip_lines -= 1
                continue
                
            line_stripped = line.strip()
            
            # Skip empty lines but preserve them in content
            if not line_stripped:
                if current_section:
                    current_section.append('')
                continue
            
            # Detect title (usually first substantial line with specific pattern)
            if not title_found and i < 15:
                # Look for title-like patterns: all caps, title case, longer than 10 chars
                if len(line_stripped) > 15 and (
                    line_stripped.istitle() or 
                    (line_stripped[0].isupper() and not line_stripped.isupper())
                ):
                    # Check if it's not an email or institution
                    if '@' not in line_stripped and not any(word in line_stripped.lower() for word in ['university', 'google', 'research', 'brain']):
                        result.append(f"# {line_stripped}\n")
                        title_found = True
                        continue
            
            # Detect authors/affiliations (look for emails, institutions)
            if i < 30 and any(indicator in line_stripped.lower() for indicator in ['@', 'university', 'institute', 'google', 'deepmind', 'research', 'brain']):
                # Skip if it's too long (probably not author info)
                if len(line_stripped) < 100:
                    result.append(f"*{line_stripped}*\n")
                    continue
            
            # Detect Abstract
            if line_stripped.lower() == 'abstract':
                if current_section:
                    result.extend(self.format_paragraph(current_section))
                    current_section = []
                result.append(f"\n## Abstract\n\n")
                in_abstract = True
                continue
            
            # Detect Tables
            is_table, table_lines = self.detect_table(lines, i)
            if is_table:
                if current_section:
                    result.extend(self.format_paragraph(current_section))
                    current_section = []
                result.append(f"\n**{line_stripped}**\n\n")
                skip_lines = table_lines
                continue
            
            # Detect equations
            if self.detect_equation(line_stripped):
                if current_section:
                    result.extend(self.format_paragraph(current_section))
                    current_section = []
                result.append(f"\n{self.clean_equation(line_stripped)}\n\n")
                continue
            
            # Detect major sections (numbered or all caps or numbered+text)
            section_match = re.match(r'^(\d+\.?\s+)?([A-Z][A-Za-z\s&-]+)$', line_stripped)
            if section_match and len(line_stripped) < 80:
                # Check if it looks like a section header
                if (line_stripped.isupper() or 
                    re.match(r'^\d+\s+[A-Z]', line_stripped) or
                    (len(line_stripped) < 50 and line_stripped.istitle())):
                    
                    if current_section:
                        result.extend(self.format_paragraph(current_section))
                        current_section = []
                    
                    # Handle References specially
                    if 'reference' in line_stripped.lower():
                        in_references = True
                        result.append(f"\n## {line_stripped}\n\n")
                    else:
                        result.append(f"\n## {line_stripped}\n\n")
                    continue
            
            # Detect subsections (numbered like 3.1 or 3.1.1)
            subsection_match = re.match(r'^(\d+\.\d+\.?\d*\.?\s+)(.+)$', line_stripped)
            if subsection_match:
                if current_section:
                    result.extend(self.format_paragraph(current_section))
                    current_section = []
                result.append(f"\n### {line_stripped}\n\n")
                continue
            
            # Detect bullet points or list items
            if re.match(r'^[•\-\*]\s+', line_stripped):
                if current_section:
                    result.extend(self.format_paragraph(current_section))
                    current_section = []
                result.append(f"{line_stripped}\n")
                continue
            
            # Regular content
            current_section.append(line_stripped)
        
        # Add remaining content
        if current_section:
            result.extend(self.format_paragraph(current_section))
        
        return '\n'.join(result)
    
    def format_paragraph(self, lines):
        """Format lines into proper paragraphs"""
        if not lines:
            return []
        
        # Join lines that belong together
        paragraph = []
        current = []
        
        for line in lines:
            if not line.strip():
                if current:
                    paragraph.append(' '.join(current))
                    current = []
                paragraph.append('')
            else:
                current.append(line.strip())
        
        if current:
            paragraph.append(' '.join(current))
        
        return [p + '\n' for p in paragraph]
    
def parse_research_paper(pdf_path, output_path):
    """Parse research paper PDF to markdown"""
    try:
        parser = PaperParser()
        
        print(f"Parsing research paper: {pdf_path.name}")
        
        # Extract structured content
        markdown_content = parser.extract_text_with_structure(pdf_path)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✓ Successfully parsed to: {output_path.name}")
        return True
        
    except Exception as e:
        print(f"✗ Error parsing {pdf_path.name}: {str(e)}")
        import traceback
        traceback.print_exc()
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
    
    print(f"Found {len(pdf_files)} PDF file(s) to parse")
    print("=" * 60)
    
    for pdf_file in pdf_files:
        output_file = output_dir / f"{pdf_file.stem}.md"
        parse_research_paper(pdf_file, output_file)
        print()
    
    print("=" * 60)
    print("Paper parsing complete!")

if __name__ == "__main__":
    main()
