import json
import re
import base64
from pathlib import Path
from typing import Dict, List, Any
import hashlib

class PDFDataExtractor:
    def __init__(self):
        self.table_patterns = [
            r'\|.*?\|',  # Markdown table pattern
            r'\+[-=]+\+',  # ASCII table borders
            r'(?:(?:\S+\s*){2,}(?:\n|$)){3,}',  # Columnar data pattern
        ]
        
    def extract_tables_from_text(self, text: str) -> List[Dict]:
        """Extract tables from markdown text"""
        tables = []
        lines = text.split('\n')
        
        # Look for markdown tables
        table_start = None
        current_table_lines = []
        
        for i, line in enumerate(lines):
            # Check if line contains table markers
            if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
                if table_start is None:
                    table_start = i
                    current_table_lines = [line]
                else:
                    current_table_lines.append(line)
            else:
                # End of table or no table
                if table_start is not None and len(current_table_lines) >= 2:
                    # Process the table
                    table_data = self.parse_markdown_table(current_table_lines)
                    if table_data:
                        tables.append({
                            'table_id': f'table_{len(tables) + 1}',
                            'type': 'markdown_table',
                            'headers': table_data.get('headers', []),
                            'rows': table_data.get('rows', []),
                            'raw_text': '\n'.join(current_table_lines)
                        })
                
                # Reset table tracking
                table_start = None
                current_table_lines = []
        
        # Handle last table if exists
        if table_start is not None and len(current_table_lines) >= 2:
            table_data = self.parse_markdown_table(current_table_lines)
            if table_data:
                tables.append({
                    'table_id': f'table_{len(tables) + 1}',
                    'type': 'markdown_table',
                    'headers': table_data.get('headers', []),
                    'rows': table_data.get('rows', []),
                    'raw_text': '\n'.join(current_table_lines)
                })
        
        return tables
    
    def parse_markdown_table(self, table_lines: List[str]) -> Dict:
        """Parse markdown table into structured format"""
        if len(table_lines) < 2:
            return {}
        
        # Remove leading/trailing pipes and split
        def clean_row(line):
            return [cell.strip() for cell in line.strip('|').split('|')]
        
        # Parse headers (first line)
        headers = clean_row(table_lines[0])
        
        # Skip separator line (second line with dashes)
        data_rows = []
        for line in table_lines[2:]:  # Skip header and separator
            if line.strip() and '|' in line:
                row = clean_row(line)
                # Ensure row has same number of columns as headers
                while len(row) < len(headers):
                    row.append('')
                data_rows.append(row[:len(headers)])  # Truncate if too many columns
        
        return {
            'headers': headers,
            'rows': data_rows
        }
    
    def extract_paragraphs(self, text: str, tables: List[Dict]) -> List[str]:
        """Extract paragraphs, excluding table content"""
        # Remove table content from text
        clean_text = text
        for table in tables:
            clean_text = clean_text.replace(table['raw_text'], '')
        
        # Split into paragraphs
        paragraphs = []
        for para in clean_text.split('\n\n'):
            para = para.strip()
            if para and len(para) > 10:  # Filter out very short content
                # Clean up the paragraph
                para = re.sub(r'\n+', ' ', para)  # Replace multiple newlines with space
                para = re.sub(r'\s+', ' ', para)  # Replace multiple spaces with single space
                paragraphs.append(para)
        
        return paragraphs
    
    def process_images(self, images: List, page_num: int) -> List[Dict]:
        """Process images from a page"""
        processed_images = []
        
        for i, image in enumerate(images):
            try:
                # Generate image hash for unique identification
                image_data = base64.b64decode(image.image_base64.split(',')[1])
                image_hash = hashlib.md5(image_data).hexdigest()
                
                image_info = {
                    'image_id': f'page_{page_num}_image_{i + 1}',
                    'image_hash': image_hash,
                    'filename': f'page_{page_num:03d}_image_{i + 1:03d}.png',
                    'size_bytes': len(image_data),
                    'base64_data': image.image_base64,  # Keep full base64 for storage
                    'position': {
                        'page': page_num,
                        'image_index': i
                    }
                }
                
                # Add bounding box if available
                if hasattr(image, 'bbox') and image.bbox:
                    image_info['bbox'] = image.bbox
                
                processed_images.append(image_info)
                
            except Exception as e:
                print(f"Error processing image {i + 1} on page {page_num}: {e}")
        
        return processed_images
    
    def extract_page_data(self, page, page_num: int) -> Dict:
        """Extract structured data from a single page"""
        # Get raw text
        raw_text = page.markdown
        
        # Extract tables
        tables = self.extract_tables_from_text(raw_text)
        
        # Extract paragraphs (excluding table content)
        paragraphs = self.extract_paragraphs(raw_text, tables)
        
        # Process images
        images = self.process_images(page.images, page_num)
        
        # Create page data structure
        page_data = {
            'page_number': page_num,
            'paragraphs': paragraphs,
            'tables': tables,
            'images': images,
            'metadata': {
                'paragraph_count': len(paragraphs),
                'table_count': len(tables),
                'image_count': len(images),
                'total_characters': len(raw_text),
                'has_content': len(paragraphs) > 0 or len(tables) > 0 or len(images) > 0
            },
            'raw_markdown': raw_text  # Keep original for reference
        }
        
        return page_data
    
    def extract_full_document(self, response) -> Dict:
        """Extract data from entire document"""
        document_data = {
            'document_metadata': {
                'total_pages': len(response.pages),
                'extraction_timestamp': None,
                'total_paragraphs': 0,
                'total_tables': 0,
                'total_images': 0
            },
            'pages': []
        }
        
        # Process each page
        for i, page in enumerate(response.pages):
            page_num = i + 1
            page_data = self.extract_page_data(page, page_num)
            document_data['pages'].append(page_data)
            
            # Update document metadata
            document_data['document_metadata']['total_paragraphs'] += page_data['metadata']['paragraph_count']
            document_data['document_metadata']['total_tables'] += page_data['metadata']['table_count']
            document_data['document_metadata']['total_images'] += page_data['metadata']['image_count']
        
        # Add timestamp
        from datetime import datetime
        document_data['document_metadata']['extraction_timestamp'] = datetime.now().isoformat()
        
        return document_data
    
    def save_to_json(self, document_data: Dict, output_path: str = "extracted_data.json"):
        """Save extracted data to JSON file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, indent=2, ensure_ascii=False)
            print(f" Data saved to {output_path}")
            return True
        except Exception as e:
            print(f"Error saving JSON: {e}")
            return False
    
    def create_database_ready_json(self, document_data: Dict, output_path: str = "db_ready_data.json"):
        """Create a database-ready version with optimized structure"""
        db_ready_data = []
        
        for page in document_data['pages']:
            page_record = {
                'page_number': page['page_number'],
                'paragraphs': page['paragraphs'],
                'tables': page['tables'],
                'images': [
                    {
                        'image_id': img['image_id'],
                        'filename': img['filename'],
                        'size_bytes': img['size_bytes'],
                        'image_hash': img['image_hash']
                        # Note: base64_data removed for DB efficiency - store separately if needed
                    } for img in page['images']
                ],
                'metadata': page['metadata']
            }
            db_ready_data.append(page_record)
        
        # Save database-ready version
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'document_metadata': document_data['document_metadata'],
                    'pages': db_ready_data
                }, f, indent=2, ensure_ascii=False)
            print(f" Database-ready data saved to {output_path}")
            return True
        except Exception as e:
            print(f" Error saving database-ready JSON: {e}")
            return False

def process_pdf_to_json(response, output_dir="output"):
    """Main function to process PDF response and create JSON files"""
    extractor = PDFDataExtractor()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print(" Starting JSON extraction...")
    
    # Extract all data
    document_data = extractor.extract_full_document(response)
    
    # Save complete JSON
    complete_json_path = output_path / "extracted_data.json"
    extractor.save_to_json(document_data, str(complete_json_path))
    
    # Save database-ready JSON
    db_json_path = output_path / "db_ready_data.json"
    extractor.create_database_ready_json(document_data, str(db_json_path))
    
    # Print summary
    print("\n Extraction Summary:")
    print(f"Total Pages: {document_data['document_metadata']['total_pages']}")
    print(f"Total Paragraphs: {document_data['document_metadata']['total_paragraphs']}")
    print(f"Total Tables: {document_data['document_metadata']['total_tables']}")
    print(f"Total Images: {document_data['document_metadata']['total_images']}")
    
    return document_data

# Example usage function
def main():
    # This would be called from your main OCR script
    # Example: process_pdf_to_json(ocr_response)
    pass

if __name__ == "__main__":
    main()