import json
import psycopg2
from psycopg2.extras import execute_values
import openai
import os
from dotenv import load_dotenv
import hashlib
from pathlib import Path
import base64
from typing import List, Dict, Any

load_dotenv()

class DocumentInserter:
    def __init__(self):
        # Database configuration
        self.db_config = {
            'host': 'localhost',
            'database': 'report_agent_11',
            'user': 'postgres',
            'password': os.getenv('PG_PASSWORD', 'your_password'),
            'port': 5432
        }
        
        # OpenAI configuration
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"
        
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text"""
        try:
            # Clean the text
            text = text.replace("\n", " ").strip()
            if not text:
                return None
                
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f" Error getting embedding for text: {str(e)[:100]}...")
            return None
    
    def analyze_image_with_vision(self, base64_image: str, surrounding_text: str = "") -> Dict:
        """
        Analyze image with OpenAI Vision API for comprehensive understanding
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""Analyze this image in detail and provide:
                                1. Detailed description of what you see
                                2. Any text/numbers you can read (OCR)
                                3. Key data points, trends, or insights
                                4. Type of visual (chart, table, diagram, etc.)
                                5. Context: This image appears near: {surrounding_text[:300]}
                                
                                Be very detailed and specific. Extract ALL visible information.
                                
                                Format as JSON:
                                {{
                                    "detailed_description": "comprehensive description",
                                    "ocr_text": "all text found in image",
                                    "key_insights": "important findings and data",
                                    "visual_type": "chart/table/diagram/photo/etc",
                                    "data_extracted": "specific numbers, percentages, values"
                                }}"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": base64_image}
                            }
                        ]
                    }
                ],
                max_tokens=800
            )
            
            # Try to parse JSON response
            content = response.choices[0].message.content
            try:
                result = json.loads(content)
            except:
                # If JSON parsing fails, create structured response
                result = {
                    "detailed_description": content[:500],
                    "ocr_text": "",
                    "key_insights": content[:300],
                    "visual_type": "image",
                    "data_extracted": ""
                }
            
            return result
            
        except Exception as e:
            print(f" Error analyzing image: {e}")
            return {
                "detailed_description": f"Image from document (analysis failed: {str(e)})",
                "ocr_text": "",
                "key_insights": "",
                "visual_type": "unknown",
                "data_extracted": ""
            }
    
    def insert_document(self, filename: str, company_name: str = None, report_year: int = None) -> int:
        """Insert document record and return doc_id"""
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO documents (company_name, report_year, file_path)
                    VALUES (%s, %s, %s) RETURNING doc_id
                """, (company_name, report_year, filename))
                
                doc_id = cur.fetchone()[0]
                conn.commit()
        
        print(f" Document inserted with doc_id: {doc_id}")
        return doc_id
    
    def process_and_insert_chunks(self, doc_id: int, db_ready_data: Dict):
        """
        Process text chunks from db_ready_data.json with advanced chunking strategy
        """
        pages = db_ready_data.get('pages', [])
        total_chunks = 0
        
        print(f" Processing {len(pages)} pages for text chunks...")
        
        for page_num, page_data in enumerate(pages, 1):
            paragraphs = page_data.get('paragraphs', [])
            
            if not paragraphs:
                continue
            
            # Strategy 1: Individual paragraphs (for specific content)
            paragraph_chunks = []
            for i, paragraph in enumerate(paragraphs):
                if len(paragraph.strip()) > 20:  # Skip very short paragraphs
                    embedding = self.get_embedding(paragraph)
                    if embedding:
                        paragraph_chunks.append((
                            doc_id, page_num, paragraph, embedding
                        ))
            
            # Strategy 2: Combined context chunks (for broader understanding)
            if len(paragraphs) > 1:
                # Combine 2-3 paragraphs for context
                for i in range(0, len(paragraphs), 2):
                    combined_text = " ".join(paragraphs[i:i+3])  # Take 2-3 paragraphs
                    if len(combined_text.strip()) > 50:
                        embedding = self.get_embedding(combined_text)
                        if embedding:
                            paragraph_chunks.append((
                                doc_id, page_num, combined_text, embedding
                            ))
            
            # Strategy 3: Full page context (for page-level queries)
            full_page_text = " ".join(paragraphs)
            if len(full_page_text.strip()) > 100:
                # Split into chunks if too long (max ~400 words)
                words = full_page_text.split()
                if len(words) > 400:
                    # Split into overlapping chunks
                    chunk_size = 300
                    overlap = 50
                    for i in range(0, len(words), chunk_size - overlap):
                        chunk_words = words[i:i + chunk_size]
                        chunk_text = " ".join(chunk_words)
                        if len(chunk_text.strip()) > 100:
                            embedding = self.get_embedding(chunk_text)
                            if embedding:
                                paragraph_chunks.append((
                                    doc_id, page_num, chunk_text, embedding
                                ))
                else:
                    embedding = self.get_embedding(full_page_text)
                    if embedding:
                        paragraph_chunks.append((
                            doc_id, page_num, full_page_text, embedding
                        ))
            
            # Bulk insert chunks for this page
            if paragraph_chunks:
                with psycopg2.connect(**self.db_config) as conn:
                    with conn.cursor() as cur:
                        execute_values(cur, """
                            INSERT INTO document_chunks (doc_id, page_number, chunk_text, embedding)
                            VALUES %s
                        """, paragraph_chunks)
                    conn.commit()
                
                total_chunks += len(paragraph_chunks)
                print(f"   Page {page_num}: {len(paragraph_chunks)} chunks inserted")
        
        print(f"🎉 Total text chunks inserted: {total_chunks}")
    
    def process_and_insert_tables(self, doc_id: int, db_ready_data: Dict):
        """
        Process tables with multiple representation strategies
        """
        pages = db_ready_data.get('pages', [])
        total_tables = 0
        
        print(f"Processing tables from {len(pages)} pages...")
        
        for page_num, page_data in enumerate(pages, 1):
            tables = page_data.get('tables', [])
            
            for table_idx, table in enumerate(tables):
                headers = table.get('headers', [])
                rows = table.get('rows', [])
                
                if not headers and not rows:
                    continue
                
                # Strategy 1: Natural language description
                table_description = f"Table from page {page_num} with columns: {', '.join(headers)}. "
                
                # Strategy 2: Row-by-row natural language
                table_text_parts = []
                for row_idx, row in enumerate(rows):
                    row_text = []
                    for col_idx, cell in enumerate(row):
                        if col_idx < len(headers) and cell:
                            row_text.append(f"{headers[col_idx]}: {cell}")
                    
                    if row_text:
                        table_text_parts.append(f"Row {row_idx + 1} - {', '.join(row_text)}")
                
                # Strategy 3: Key-value format
                key_value_text = []
                if headers and rows:
                    for row in rows:
                        for col_idx, cell in enumerate(row):
                            if col_idx < len(headers) and cell:
                                key_value_text.append(f"{headers[col_idx]} is {cell}")
                
                # Combine all strategies
                comprehensive_text = table_description
                if table_text_parts:
                    comprehensive_text += " " + ". ".join(table_text_parts)
                if key_value_text:
                    comprehensive_text += " Additional details: " + ". ".join(key_value_text[:10])  # Limit for length
                
                # Get embedding
                embedding = self.get_embedding(comprehensive_text)
                
                if embedding:
                    with psycopg2.connect(**self.db_config) as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO extracted_tables 
                                (doc_id, page_number, table_data_json, table_as_text, embedding)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                doc_id,
                                page_num,
                                json.dumps(table),
                                comprehensive_text,
                                embedding
                            ))
                        conn.commit()
                    
                    total_tables += 1
                    print(f"   Page {page_num}, Table {table_idx + 1}: Inserted with comprehensive text")
        
        print(f"🎉 Total tables inserted: {total_tables}")
    
    def process_and_insert_images(self, doc_id: int, extracted_data: Dict):
        """
        Process images with AI analysis for comprehensive search capability
        """
        pages = extracted_data.get('pages', [])
        total_images = 0
        
        print(f" Processing images with AI analysis...")
        
        for page_num, page_data in enumerate(pages, 1):
            images = page_data.get('images', [])
            paragraphs = page_data.get('paragraphs', [])
            
            # Get surrounding text context
            surrounding_text = " ".join(paragraphs[:3]) if paragraphs else ""
            
            for image in images:
                base64_data = image.get('base64_data', '')
                if not base64_data:
                    continue
                
                print(f"   Analyzing image {image.get('image_id', 'unknown')} from page {page_num}...")
                
                # Analyze image with Vision API
                ai_analysis = self.analyze_image_with_vision(base64_data, surrounding_text)
                
                # Create comprehensive searchable text
                searchable_content = []
                
                # Add all analysis components
                if ai_analysis.get('detailed_description'):
                    searchable_content.append(f"Image description: {ai_analysis['detailed_description']}")
                
                if ai_analysis.get('ocr_text'):
                    searchable_content.append(f"Text in image: {ai_analysis['ocr_text']}")
                
                if ai_analysis.get('key_insights'):
                    searchable_content.append(f"Key insights: {ai_analysis['key_insights']}")
                
                if ai_analysis.get('data_extracted'):
                    searchable_content.append(f"Data found: {ai_analysis['data_extracted']}")
                
                # Add context
                searchable_content.append(f"Page {page_num} context: {surrounding_text[:200]}")
                
                # Combine all searchable content
                full_searchable_text = ". ".join(searchable_content)
                
                # Save image file
                image_filename = image.get('filename', f'page_{page_num:03d}_image_{total_images + 1:03d}.png')
                image_path = f"images/{image_filename}"
                
                # Create images directory if it doesn't exist
                os.makedirs('images', exist_ok=True)
                
                # Save base64 as file
                try:
                    image_bytes = base64.b64decode(base64_data.split(',')[1])
                    with open(image_path, 'wb') as f:
                        f.write(image_bytes)
                except Exception as e:
                    print(f"   Could not save image file: {e}")
                    image_path = ""
                
                # Insert into database
                with psycopg2.connect(**self.db_config) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO extracted_images 
                            (doc_id, page_number, image_filename, image_path)
                            VALUES (%s, %s, %s, %s)
                        """, (doc_id, page_num, image_filename, image_path))
                    conn.commit()
                
                # ALSO insert image analysis as text chunks for searchability
                embedding = self.get_embedding(full_searchable_text)
                if embedding:
                    with psycopg2.connect(**self.db_config) as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO document_chunks (doc_id, page_number, chunk_text, embedding)
                                VALUES (%s, %s, %s, %s)
                            """, (
                                doc_id, 
                                page_num, 
                                f"[IMAGE CONTENT] {full_searchable_text}", 
                                embedding
                            ))
                        conn.commit()
                
                total_images += 1
                print(f"   Image processed and made searchable: {image_filename}")
        
        print(f" Total images processed: {total_images}")
    
    def insert_complete_document(self, 
                                filename: str,
                                db_ready_path: str,
                                extracted_data_path: str,
                                company_name: str = None,
                                report_year: int = None):
        """
        Complete document insertion with optimal search capability
        """
        print(f" Starting complete document insertion for: {filename}")
        
        # Load both JSON files
        with open(db_ready_path, 'r', encoding='utf-8') as f:
            db_ready_data = json.load(f)
        
        with open(extracted_data_path, 'r', encoding='utf-8') as f:
            extracted_data = json.load(f)
        
        # Insert document record
        doc_id = self.insert_document(filename, company_name, report_year)
        
        # Process all content types
        print("\n Processing text chunks...")
        self.process_and_insert_chunks(doc_id, db_ready_data)
        
        print("\n Processing tables...")
        self.process_and_insert_tables(doc_id, db_ready_data)
        
        print("\n Processing images...")
        self.process_and_insert_images(doc_id, extracted_data)
        
        print(f"\n Complete document insertion finished for doc_id: {doc_id}")
        
        # Print summary
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM document_chunks WHERE doc_id = %s", (doc_id,))
                chunk_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM extracted_tables WHERE doc_id = %s", (doc_id,))
                table_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM extracted_images WHERE doc_id = %s", (doc_id,))
                image_count = cur.fetchone()[0]
        
        print(f"""
 INSERTION SUMMARY:
   Document ID: {doc_id}
   Text Chunks: {chunk_count}
   Tables: {table_count}
   Images: {image_count}
   
 Ready for 100% query coverage!
        """)
        
        return doc_id

def main():
    """
    Main execution function
    """
    inserter = DocumentInserter()
    
    # Configuration
    pdf_filename = "../pdf_holder/test3.pdf"  # Change this
    db_ready_json = "output/db_ready_data.json"    # Path to your db_ready JSON
    extracted_json = "output/extracted_data.json"  # Path to your extracted JSON
    
    company_name = "Example Corp"  # Optional
    report_year = 2023            # Optional
    
    try:
        # Insert complete document
        doc_id = inserter.insert_complete_document(
            filename=pdf_filename,
            db_ready_path=db_ready_json,
            extracted_data_path=extracted_json,
            company_name=company_name,
            report_year=report_year
        )
        
        print(f" SUCCESS! Document inserted with ID: {doc_id}")
        print("🔍 Your database is now ready for ANY query type!")
        
    except Exception as e:
        print(f" ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()