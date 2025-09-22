import psycopg2
import openai
import os
from dotenv import load_dotenv
import json
import re
from typing import List, Dict, Any, Tuple
import numpy as np

load_dotenv()

class EnhancedRAG:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'report_agent_11',
            'user': 'postgres',
            'password': os.getenv('PG_PASSWORD'),
            'port': 5432
        }
        
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text with error handling"""
        try:
            if not text or not text.strip():
                return None
            
            # Clean text
            text = text.replace('\n', ' ').strip()
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return None
    
    def preprocess_query(self, query: str) -> Dict[str, Any]:
        """Analyze and preprocess the query to determine search strategy"""
        query = query.lower().strip()
        
        # Detect query patterns
        patterns = {
            'table_query': any(word in query for word in [
                'table', 'performance', 'measure', 'indicator', 'result', 'target',
                'actual', 'percentage', '%', 'score', 'rate', 'level', 'coverage'
            ]),
            'numerical_query': bool(re.search(r'\d+|number|count|amount|total|sum', query)),
            'comparison_query': any(word in query for word in [
                'compare', 'vs', 'versus', 'difference', 'change', 'increase', 'decrease',
                'better', 'worse', 'higher', 'lower'
            ]),
            'temporal_query': any(word in query for word in [
                '2020', '2021', '2022', '2023', '2024', 'year', 'fy', 'fiscal'
            ]),
            'specific_metric': any(word in query for word in [
                'service', 'accuracy', 'timeliness', 'satisfaction', 'inventory',
                'collection', 'compliance', 'resolution'
            ])
        }
        
        return {
            'original': query,
            'patterns': patterns,
            'is_complex': sum(patterns.values()) >= 2
        }
    
    def expand_query(self, query: str) -> List[str]:
        """Generate query variations for better recall"""
        variations = [query]
        
        # Add synonyms and related terms
        replacements = {
            'performance': ['result', 'outcome', 'achievement', 'metric'],
            'target': ['goal', 'objective', 'aim'],
            'actual': ['result', 'achieved', 'real'],
            'measure': ['metric', 'indicator', 'kpi'],
            'service': ['assistance', 'support', 'help'],
            'accuracy': ['correctness', 'precision'],
            'customer': ['taxpayer', 'caller', 'client']
        }
        
        for original, synonyms in replacements.items():
            if original in query.lower():
                for synonym in synonyms:
                    variations.append(query.lower().replace(original, synonym))
        
        return list(set(variations))[:5]  # Limit to 5 variations
    
    def hybrid_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Enhanced hybrid search combining semantic and keyword matching"""
        query_analysis = self.preprocess_query(query)
        query_variations = self.expand_query(query)
        
        all_results = []
        
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    # 1. Semantic search with multiple query variations
                    for q_variant in query_variations:
                        query_embedding = self.get_embedding(q_variant)
                        if not query_embedding:
                            continue
                        
                        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                        
                        # Search text chunks
                        cur.execute("""
                            SELECT chunk_text, page_number, doc_id,
                                   (embedding <-> %s::vector) as distance,
                                   'text' as content_type
                            FROM document_chunks
                            WHERE doc_id IS NOT NULL
                            ORDER BY distance
                            LIMIT %s
                        """, (embedding_str, limit))
                        
                        results = cur.fetchall()
                        for row in results:
                            all_results.append({
                                'content': row[0],
                                'page': row[1],
                                'doc_id': row[2],
                                'distance': row[3],
                                'type': 'text',
                                'score': 1 / (1 + row[3]),  # Convert distance to similarity score
                                'query_variant': q_variant
                            })
                    
                    # 2. Table-focused search (especially important for your data)
                    for q_variant in query_variations:
                        query_embedding = self.get_embedding(q_variant)
                        if not query_embedding:
                            continue
                        
                        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                        
                        cur.execute("""
                            SELECT table_as_text, page_number, doc_id, table_data_json,
                                   (embedding <-> %s::vector) as distance,
                                   'table' as content_type
                            FROM extracted_tables
                            WHERE doc_id IS NOT NULL
                            ORDER BY distance
                            LIMIT %s
                        """, (embedding_str, limit))
                        
                        table_results = cur.fetchall()
                        for row in table_results:
                            # Parse table JSON for structured data
                            table_json = {}
                            try:
                                table_json = json.loads(row[3]) if row[3] else {}
                            except:
                                pass
                            
                            all_results.append({
                                'content': row[0],
                                'page': row[1],
                                'doc_id': row[2],
                                'distance': row[4],
                                'type': 'table',
                                'score': 1 / (1 + row[4]),
                                'table_data': table_json,
                                'query_variant': q_variant
                            })
                    
                    # 3. Keyword-based fallback search
                    keywords = query.lower().split()
                    for keyword in keywords:
                        if len(keyword) > 3:  # Skip short words
                            cur.execute("""
                                SELECT chunk_text, page_number, doc_id,
                                       'keyword_text' as content_type
                                FROM document_chunks
                                WHERE LOWER(chunk_text) LIKE %s
                                LIMIT 5
                            """, (f'%{keyword}%',))
                            
                            keyword_results = cur.fetchall()
                            for row in keyword_results:
                                all_results.append({
                                    'content': row[0],
                                    'page': row[1],
                                    'doc_id': row[2],
                                    'distance': 0.5,  # Fixed distance for keyword matches
                                    'type': 'keyword_text',
                                    'score': 0.7,
                                    'matched_keyword': keyword
                                })
        
        except Exception as e:
            print(f"Search error: {e}")
            return []
        
        # Remove duplicates and rank results
        unique_results = self.deduplicate_and_rank(all_results, query_analysis)
        
        return unique_results[:limit]
    
    def deduplicate_and_rank(self, results: List[Dict], query_analysis: Dict) -> List[Dict]:
        """Remove duplicates and rank results by relevance"""
        seen = set()
        unique_results = []
        
        for result in results:
            # Create a hash based on content and page
            content_hash = hash(result['content'][:100] + str(result['page']))
            if content_hash not in seen:
                seen.add(content_hash)
                
                # Boost score based on query patterns
                boost_factor = 1.0
                
                if query_analysis['patterns']['table_query'] and result['type'] == 'table':
                    boost_factor = 1.5
                elif query_analysis['patterns']['numerical_query'] and any(c.isdigit() or c == '%' for c in result['content']):
                    boost_factor = 1.3
                
                result['final_score'] = result['score'] * boost_factor
                unique_results.append(result)
        
        # Sort by final score (descending)
        return sorted(unique_results, key=lambda x: x['final_score'], reverse=True)
    
    def format_context_for_llm(self, results: List[Dict], query: str) -> str:
        """Format search results into optimal context for LLM"""
        if not results:
            return "No relevant information found."
        
        context_parts = []
        table_count = 0
        text_count = 0
        
        for i, result in enumerate(results):
            if result['type'] == 'table':
                table_count += 1
                # Format table data specially
                table_info = f"\n--- TABLE {table_count} (Page {result['page']}) ---\n"
                table_info += result['content']
                
                # If we have structured table data, add it
                if 'table_data' in result and result['table_data']:
                    table_data = result['table_data']
                    if 'headers' in table_data and 'rows' in table_data:
                        table_info += "\n\nStructured Data:\n"
                        headers = table_data['headers']
                        for row_idx, row in enumerate(table_data['rows']):
                            row_info = []
                            for col_idx, cell in enumerate(row):
                                if col_idx < len(headers) and cell:
                                    row_info.append(f"{headers[col_idx]}: {cell}")
                            if row_info:
                                table_info += f"• {' | '.join(row_info)}\n"
                
                context_parts.append(table_info)
            
            else:
                text_count += 1
                context_parts.append(f"\n--- TEXT {text_count} (Page {result['page']}) ---\n{result['content']}")
        
        return "\n".join(context_parts)
    
    def generate_enhanced_answer(self, query: str, results: List[Dict]) -> str:
        """Generate comprehensive answer with enhanced prompting"""
        if not results:
            return "I couldn't find any relevant information in the documents to answer your question. Please try rephrasing your query or asking about different topics."
        
        context = self.format_context_for_llm(results, query)
        query_analysis = self.preprocess_query(query)
        
        # Determine response style based on query type
        if query_analysis['patterns']['table_query']:
            response_instruction = """Focus on extracting specific data points, numbers, percentages, and performance metrics. 
            Present the information in a clear, structured way. If comparing values, highlight the differences clearly."""
        
        elif query_analysis['patterns']['comparison_query']:
            response_instruction = """Compare the relevant data points clearly. Show changes over time, 
            highlight improvements or declines, and provide context for the changes."""
        
        else:
            response_instruction = """Provide a comprehensive answer that directly addresses the question. 
            Include specific details and explain their significance."""
        
        prompt = f"""You are a document analyst. Answer the question directly and concisely.

QUESTION: {query}

RELEVANT INFORMATION:
{context}

INSTRUCTIONS:
- Give a direct, concise answer (1-3 sentences maximum)
- Include specific numbers/data if relevant
- No extra explanations unless specifically asked
- No formatting like bullet points or headers

ANSWER:"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Using more capable model for better accuracy
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.1  # Low temperature for factual accuracy
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I found relevant information but encountered an error generating the response: {e}"
    
    def ask(self, question: str) -> str:
        """Main function to ask a question and get a direct answer"""
        # Search for relevant documents
        results = self.hybrid_search(question, limit=8)
        
        # Generate answer
        answer = self.generate_enhanced_answer(question, results)
        
        print(f"\n**Question:** {question}")
        print(f"**Answer:** {answer}")
        
        return answer
    
def main():
    """Simple Q&A loop"""
    rag = EnhancedRAG()
    
    print("RAG System Ready. Ask your questions:")
    
    while True:
        question = input("\nQuestion: ").strip()
        if not question:
            continue
        
        try:
            rag.ask(question)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()