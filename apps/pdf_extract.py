#working pdf_exttract.py
import os
from dotenv import load_dotenv
from mistralai import Mistral
import base64
import time
import re
import json
from pathlib import Path
from extract_data_to_json import process_pdf_to_json  # Import the new JSON processor

load_dotenv()
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))


def clean_ocr_text(text: str) -> str:
    """
    Remove LaTeX-style escapes from OCR text.
    """
    text = text.replace(r'\%', '%')
    text = text.replace(r'\$', '$')
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    return text


class EnhancedOCRProcessor:
    def __init__(self, client):
        self.client = client
 
    def process_with_retry(self, file_path, max_retries=3, delay=2):
        """Process PDF with retry mechanism"""
        for attempt in range(max_retries):
            try:
                uploaded_file = self.client.files.upload(
                    file={
                        "file_name": f"document_attempt_{attempt}.pdf",
                        "content": open(file_path, "rb")
                    },
                    purpose="ocr"
                )
                
                file_url = self.client.files.get_signed_url(file_id=uploaded_file.id)
                
                # Try different processing parameters
                response = self.client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url",
                        "document_url": file_url.url
                    },
                    include_image_base64=True,
                )
                
                return response
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    raise

    def process_page_by_page(self, file_path):
        """Process individual pages if full document processing fails"""
        # You'd need to split PDF into individual pages first
       
        pass
    
    def validate_extraction(self, response):
        """Validate and analyze extraction completeness"""
        total_chars = 0
        pages_with_content = 0
        pages_without_content = 0
        
        for i, page in enumerate(response.pages):
            char_count = len(page.markdown.strip())
            total_chars += char_count
            
            if char_count > 10:  # Threshold for meaningful content
                pages_with_content += 1
            else:
                pages_without_content += 1
                print(f"Warning: Page {i+1} has minimal content ({char_count} chars)")
        
        print(f"Total pages: {len(response.pages)}")
        print(f"Pages with content: {pages_with_content}")
        print(f"Pages with minimal content: {pages_without_content}")
        print(f"Total characters extracted: {total_chars}")
        
        return {
            'total_pages': len(response.pages),
            'content_pages': pages_with_content,
            'empty_pages': pages_without_content,
            'total_chars': total_chars
        }



    def enhanced_export(self, response, output_dir="output"):
        """Enhanced export with better organization and validation"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Export markdown with page separators
        with open(output_path / 'complete_output.md', 'w', encoding='utf-8') as f:
            for i, page in enumerate(response.pages):
                f.write(f"\n\n--- PAGE {i+1} ---\n\n")
                f.write(clean_ocr_text(page.markdown))
                # f.write(page.markdown)

                if len(page.markdown.strip()) < 10:
                    f.write(f"\n[WARNING: This page has minimal content]\n")
        
        # Export individual pages
        pages_dir = output_path / "pages"
        pages_dir.mkdir(exist_ok=True)
        
        for i, page in enumerate(response.pages):
            with open(pages_dir / f'page_{i+1:03d}.md', 'w', encoding='utf-8') as f:
                f.write(page.markdown)
        
        # Export images
        images_dir = output_path / "images"
        images_dir.mkdir(exist_ok=True)
        
        image_count = 0
        for i, page in enumerate(response.pages):
            for j, image in enumerate(page.images):
                try:
                    parsed_image = self.data_uri_to_bytes(image.image_base64)
                    image_filename = f"page_{i+1:03d}_image_{j+1:03d}.png"
                    with open(images_dir / image_filename, 'wb') as f:
                        f.write(parsed_image)
                    image_count += 1
                except Exception as e:
                    print(f"Failed to export image {j+1} from page {i+1}: {e}")
        
        print(f"Exported {image_count} images to {images_dir}")
        
 
        print("/n Converting to JSON format...")
        document_data = process_pdf_to_json(response, output_dir)
        
        return output_path, document_data
    
    def data_uri_to_bytes(self, data_uri):
        """Convert data URI to bytes"""
        _, encoded = data_uri.split(',', 1)
        return base64.b64decode(encoded)

# Alternative approach using multiple processing strategies
def multi_strategy_processing(file_path):
    """Try multiple processing strategies to maximize extraction"""
    processor = EnhancedOCRProcessor(client)
    
    strategies = [
        # Strategy 1: Standard processing with retry
        lambda: processor.process_with_retry(file_path),
        
        # Strategy 2: Process with different file names (sometimes helps)
        lambda: processor.process_with_retry(file_path, max_retries=2),
    ]
    
    best_result = None
    best_char_count = 0
    
    for i, strategy in enumerate(strategies):
        try:
            print(f"Trying strategy {i+1}...")
            result = strategy()
            
            # Count total characters to determine best result
            total_chars = sum(len(page.markdown) for page in result.pages)
            
            if total_chars > best_char_count:
                best_result = result
                best_char_count = total_chars
                print(f"Strategy {i+1} extracted {total_chars} characters")
            
        except Exception as e:
            print(f"Strategy {i+1} failed: {e}")
    
    return best_result

# Usage example
def main():
    file_path = "../pdf_holder/test3.pdf"
    
    # Try enhanced processing
    processor = EnhancedOCRProcessor(client)
    
    try:

        print("=== Enhanced Single Processing ===")
        response = processor.process_with_retry(file_path)
        stats = processor.validate_extraction(response)
        
        # Export with validation AND JSON conversion
        output_dir, document_data = processor.enhanced_export(response)
        print(f"Results exported to: {output_dir}")
        

        if stats['empty_pages'] > stats['content_pages'] * 0.2:  # If >20% pages are empty
            print("\n=== Trying Multi-Strategy Processing ===")
            better_response = multi_strategy_processing(file_path)
            if better_response:
                better_stats = processor.validate_extraction(better_response)
                if better_stats['total_chars'] > stats['total_chars']:
                    print("Multi-strategy processing found more content!")
                    output_dir_enhanced, document_data_enhanced = processor.enhanced_export(better_response, "output_enhanced")
        
        if document_data:
            print(f"Document has {len(document_data['pages'])} pages")
            
       
            if document_data['pages']:
                first_page = document_data['pages'][0]
                print(f"Page 1 structure:")
                print(f"  - Paragraphs: {len(first_page['paragraphs'])}")
                print(f"  - Tables: {len(first_page['tables'])}")
                print(f"  - Images: {len(first_page['images'])}")
                
         
                if first_page['paragraphs']:
                    snippet = first_page['paragraphs'][0][:100] + "..." if len(first_page['paragraphs'][0]) > 100 else first_page['paragraphs'][0]
                    print(f"  - First paragraph: '{snippet}'")
        
    except Exception as e:
        print(f"Processing failed: {e}")

if __name__ == "__main__":
    main()