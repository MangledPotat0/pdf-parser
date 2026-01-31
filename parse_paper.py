#!/usr/bin/env python3
"""
Research Paper to Markdown Parser
Specialized for academic papers with sections, equations, and references
"""

import re
from pathlib import Path
import pdfplumber
from datetime import datetime

class PaperParser:
    def __init__(self):
        self.sections = []
        self.current_section = None
        self.metadata = {
            'title': None,
            'authors': [],
            'year': None,
            'venue': None,
            'abstract': None,
            'keywords': []
        }
        
    def extract_text_with_structure(self, pdf_path):
        """Extract text from PDF preserving structure"""
        all_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            # Extract PDF metadata if available
            if pdf.metadata:
                if pdf.metadata.get('Title'):
                    self.metadata['title'] = pdf.metadata['Title']
                if pdf.metadata.get('Author'):
                    self.metadata['authors'] = [pdf.metadata['Author']]
                if pdf.metadata.get('CreationDate'):
                    # Try to extract year from creation date
                    try:
                        date_str = pdf.metadata['CreationDate']
                        year_match = re.search(r'(\d{4})', str(date_str))
                        if year_match:
                            self.metadata['year'] = year_match.group(1)
                    except:
                        pass
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Use layout mode to better preserve spacing
                text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=3)
                if text:
                    all_text.append(text)
        
        # Join all pages with page breaks
        full_text = "\n\n".join(all_text)
        
        # Extract metadata from text and return cleaned content
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
        metadata_section = True  # First 30 lines are typically metadata
        
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
                    if '@' not in line_stripped and not any(word in line_stripped.lower() for word in ['university', 'google', 'research', 'brain', 'department']):
                        # Store title in metadata
                        if not self.metadata['title']:
                            self.metadata['title'] = line_stripped
                        title_found = True
                        # Don't add to result - metadata only
                        continue
            
            # Detect authors/affiliations (look for emails, institutions)
            if i < 40 and metadata_section:
                # Detect author names (usually after title, before institutions)
                # Skip if it contains typical institution keywords
                is_institution = any(indicator in line_stripped.lower() for indicator in 
                                    ['@', 'university', 'institute', 'google', 'deepmind', 
                                     'research', 'brain', 'department', 'college', '.com', '.edu'])
                
                # Skip lines that look like abstract or paper body
                is_content = any(keyword in line_stripped.lower() for keyword in 
                                ['abstract', 'introduction', 'recurrent', 'neural network', 
                                 'the ', 'based on', 'we propose'])
                
                if title_found and not is_institution and not is_content:
                    # Likely author names - but check it's not too long
                    if 5 < len(line_stripped) < 150:
                        # Split by common delimiters for multiple authors
                        # Look for patterns like "Name1, Name2" or "Name1    Name2"
                        if ',' in line_stripped or re.search(r'  +', line_stripped):
                            # Multiple authors on one line
                            author_list = re.split(r'[,]|  +', line_stripped)
                            # Clean and filter authors
                            for author in author_list:
                                author = author.strip()
                                # Only add if it looks like a name (has letters, not too many special chars)
                                if author and len(author) > 3 and author.replace(' ', '').replace('.', '').replace('-', '').isalpha():
                                    # Avoid duplicates
                                    if author not in self.metadata['authors']:
                                        self.metadata['authors'].append(author)
                        else:
                            # Single author or needs better parsing
                            if line_stripped.replace(' ', '').replace('.', '').replace('-', '').isalpha():
                                if line_stripped not in self.metadata['authors']:
                                    self.metadata['authors'].append(line_stripped)
                        continue
                
                # Detect affiliations/institutions
                if is_institution and not is_content:
                    # Store as venue if we don't have one yet and it's not an email
                    if not self.metadata['venue'] and '@' not in line_stripped:
                        self.metadata['venue'] = line_stripped
                    # Don't add to result - metadata only
                    if len(line_stripped) < 200:
                        continue
            
            # Detect Abstract
            if line_stripped.lower() == 'abstract':
                metadata_section = False  # After abstract, no more metadata
                if current_section:
                    result.extend(self.format_paragraph(current_section))
                    current_section = []
                result.append(f"\n## Abstract\n\n")
                in_abstract = True
                continue
            
            # Collect abstract content for metadata (only first paragraph, up to 500 chars)
            if in_abstract and not line_stripped.lower().startswith(('introduction', '1 ', '2 ')):
                # Check if it's a section header
                if not re.match(r'^(\d+\.?\s+)?([A-Z][A-Za-z\s&-]+)$', line_stripped):
                    if not self.metadata['abstract']:
                        self.metadata['abstract'] = line_stripped
                    elif len(self.metadata['abstract']) < 500 and line_stripped:
                        self.metadata['abstract'] += ' ' + line_stripped
                else:
                    # Hit next section, stop collecting abstract
                    in_abstract = False
            
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
    
    def generate_bibtex(self, cite_key=None):
        """Generate BibTeX entry from metadata"""
        # Create cite key from first author and year
        if not cite_key:
            first_author = self.metadata['authors'][0] if self.metadata['authors'] else 'Unknown'
            # Get last name
            last_name = first_author.split()[-1] if first_author else 'Unknown'
            year = self.metadata['year'] or str(datetime.now().year)
            cite_key = f"{last_name}{year}".replace(' ', '')
        
        # Build BibTeX entry - use @inproceedings for conference papers
        entry_type = 'inproceedings' if self.metadata.get('venue') else 'article'
        bibtex = f"@{entry_type}{{{cite_key},\n"
        
        if self.metadata['title']:
            bibtex += f"  title = {{{self.metadata['title']}}},\n"
        
        if self.metadata['authors']:
            # Limit to first 8 authors for cleaner BibTeX
            authors = self.metadata['authors'][:8]
            authors_str = ' and '.join(authors)
            bibtex += f"  author = {{{authors_str}}},\n"
        
        if self.metadata['year']:
            bibtex += f"  year = {{{self.metadata['year']}}},\n"
        
        if self.metadata['venue']:
            # Use booktitle for conference papers
            if entry_type == 'inproceedings':
                bibtex += f"  booktitle = {{{self.metadata['venue']}}},\n"
            else:
                bibtex += f"  journal = {{{self.metadata['venue']}}},\n"
        
        if self.metadata['abstract']:
            # Clean abstract for BibTeX
            abstract_clean = self.metadata['abstract'].replace('{', '').replace('}', '')
            # Limit to reasonable length
            if len(abstract_clean) > 500:
                abstract_clean = abstract_clean[:497] + '...'
            bibtex += f"  abstract = {{{abstract_clean}}},\n"
        
        bibtex += "}\n"
        
        return bibtex
    
    def sanitize_filename(self, filename):
        """Sanitize filename for filesystem"""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace spaces and other chars with underscores
        filename = re.sub(r'[\s]+', '_', filename)
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        return filename

def parse_research_paper(pdf_path, output_dir):
    """Parse research paper PDF to markdown and generate BibTeX"""
    try:
        parser = PaperParser()
        
        print(f"Parsing research paper: {pdf_path.name}")
        
        # Extract structured content
        markdown_content = parser.extract_text_with_structure(pdf_path)
        
        # Determine output filename from title
        if parser.metadata['title']:
            base_name = parser.sanitize_filename(parser.metadata['title'])
            print(f"  Title: {parser.metadata['title']}")
        else:
            base_name = pdf_path.stem
            print(f"  Warning: Could not extract title, using filename")
        
        if parser.metadata['authors']:
            print(f"  Authors: {', '.join(parser.metadata['authors'][:3])}" + 
                  (f" et al." if len(parser.metadata['authors']) > 3 else ""))
        
        if parser.metadata['year']:
            print(f"  Year: {parser.metadata['year']}")
        
        # Create output paths
        md_output = output_dir / f"{base_name}.md"
        bib_output = output_dir / f"{base_name}.bib"
        
        # Write markdown file
        with open(md_output, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Generate and write BibTeX file
        bibtex_content = parser.generate_bibtex()
        with open(bib_output, 'w', encoding='utf-8') as f:
            f.write(bibtex_content)
        
        print(f"✓ Successfully parsed to: {md_output.name}")
        print(f"✓ BibTeX saved to: {bib_output.name}")
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
        parse_research_paper(pdf_file, output_dir)
        print()
    
    print("=" * 60)
    print("Paper parsing complete!")

if __name__ == "__main__":
    main()
