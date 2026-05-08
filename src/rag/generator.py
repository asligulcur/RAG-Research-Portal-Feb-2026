"""
Generator Module - RAG System
Generates answers from retrieved chunks using an LLM, with proper citations.
"""

import os
import re
import json
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime

from .llm_guard import call_with_guard

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generates answers from retrieved chunks using an LLM."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.1,
        max_tokens: int = 1000
    ):
        """
        Initialize the generator.
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model name (gpt-4, gpt-3.5-turbo, etc.)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Try to import OpenAI
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            self.provider = "openai"
            logger.info(f"✅ OpenAI client initialized (model: {model})")
        except ImportError:
            logger.warning("OpenAI not installed. Install with: pip install openai")
            self.client = None
            self.provider = None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI: {e}")
            self.client = None
            self.provider = None
    
    def build_prompt(
        self,
        query: str,
        chunks: List[Dict],
        system_prompt: Optional[str] = None
    ) -> tuple:
        """
        Build the prompt for the LLM.
        
        Args:
            query: User query
            chunks: Retrieved chunks with metadata
            system_prompt: Optional custom system prompt
            
        Returns:
            Tuple of (system_message, user_message)
        """
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()
        
        # Format chunks for context
        context = self._format_chunks_for_prompt(chunks)
        
        # Build user message
        user_message = f"""Based on the following research paper excerpts, please answer this question:

**Question**: {query}

**Research Paper Excerpts**:
{context}

**Instructions**:
1. Answer the question based ONLY on the provided excerpts
2. Cite EVERY factual claim using EXACTLY this format: [Source: paper_id, Chunk: chunk_id]
   - ALWAYS use the bracketed format—never use bare "source_id, chunk_id" at the end of a sentence
   - Use the exact Source ID and Chunk ID from each excerpt header
   - Place the citation immediately after the claim it supports
3. CRITICAL—CITE WHEN EVIDENCE EXISTS: If excerpts contain ANY relevant information (tables, numbers, partial facts, methodology), you MUST extract and cite it. Only say "insufficient information" when excerpts are completely unrelated or contain ZERO relevant content.
4. SEARCH ALL excerpts for relevant data—including tables. Benchmark tables (MMLU, RULER, etc.) have model names as column headers and scores in rows. Map each column to the correct model before claiming information is missing.
5. If the excerpts don't contain enough information to answer the question, say so explicitly
6. Do not fabricate or hallucinate information not present in the excerpts
7. If you're uncertain about something, acknowledge the uncertainty

**Example of a well-cited answer**:
Question: "What is Phi-3's performance on MMLU?"
If an excerpt contains "Phi-3-mini achieves 68.8% on MMLU (5-shot)" from Phi3_2024, Phi3_2024_chunk_0014:
Answer: "Phi-3-mini achieves 68.8% on the MMLU benchmark (5-shot) [Source: Phi3_2024, Chunk: Phi3_2024_chunk_0014]."

**Answer**:"""
        
        return system_prompt, user_message
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt based on Phase 1 improved prompts."""
        return """You are an AI research assistant helping analyze academic papers on Small Language Models (SLMs).

Your role is to:
- Answer questions based STRICTLY on provided research paper excerpts
- Provide accurate citations in the format [Source: paper_id, Chunk: chunk_id]
- Acknowledge when information is not present in the excerpts
- Never fabricate or hallucinate information
- Flag ambiguous or contradictory evidence when present

CRITICAL TRUST BEHAVIOR RULES:

1. VERIFICATION REQUIRED:
   - Before answering, verify that the excerpts actually discuss the specific subject in the question
   - If the question asks about "Model X" but excerpts discuss "Model Y", DO NOT use that information
   - If the question asks about "Claude 3" but excerpts only mention it in passing (not describing it), flag missing evidence

2. MISSING EVIDENCE:
   - ALWAYS extract and cite any factual information that IS present in the excerpts, even if it's incomplete
   - If the excerpts contain the answer (even partially), provide it with citations
   - Example: If asked "What is X's parameter count?" and excerpts say "X (3.8B parameters)", answer: "X has 3.8B parameters [Source: X, Chunk: Y]"
   - Only say "insufficient information" if the excerpts are completely unrelated or contain ZERO relevant information
   - When specific numbers, names, or facts are stated in excerpts, cite them directly
   
3. LOW RELEVANCE:
   - If excerpts have low relevance but are somewhat related, provide a brief answer noting the limitation
   - Only refuse to answer if excerpts are completely unrelated to the question
   - When possible, extract and cite any relevant information even if incomplete

4. CONTRADICTIONS:
   - If excerpts contradict each other, use this format: "⚡ Sources disagree: [SourceA] argues X while [SourceB] argues Y."
   - Cite both sources showing the contradiction

5. CITATION REQUIREMENTS:
   - Always cite specific chunks when making claims using [Source: X, Chunk: Y]—never use bare source_id, chunk_id
   - Each factual statement should have a citation immediately after it
   - Use the exact Source ID and Chunk ID from the excerpt headers (e.g. [Source: Phi3_2024, Chunk: Phi3_2024_chunk_0017])
   - Be precise about what you know vs. what you infer

6. ENTITY MATCHING:
   - Verify the entity in the question matches the entity in the excerpt
   - "Phi-3" ≠ "Phi-4", "Llama 2" ≠ "Llama 3", "MiniCPM" ≠ "Mistral"
   - If there's a mismatch, acknowledge it explicitly

7. TABLES AND BENCHMARK DATA (applies to any document):
   - Excerpts often contain tables with column headers and numeric rows. Map each number to its column header before citing
   - Column order matters: the first number in a row corresponds to the first column header, the second to the second, etc.
   - Headers may be compact: "14bPhi-2" or "3.8bPhi-3-small" means the column is for Phi-2 or Phi-3-small—scan for the model name
   - Do NOT conflate columns—if asked about "Model A" and the table has A|B|C with scores 68|75|56, Model A = 68, not 56
   - Do NOT say "information is not provided" if a relevant excerpt contains a table with the data—search all columns before concluding
   - Distinguish different benchmarks (MMLU, RULER, RepoQA, etc.)—scores from different tables must not be mixed

Remember: It's better to say "I don't know based on these excerpts" than to guess or fabricate. Your credibility depends on being honest about limitations."""
    
    def _format_chunks_for_prompt(self, chunks: List[Dict]) -> str:
        """Format chunks for the LLM prompt."""
        formatted = []
        
        for i, chunk in enumerate(chunks, 1):
            paper_title = chunk.get('metadata', {}).get('title', 'Unknown')
            source_id = chunk['source_id']
            chunk_id = chunk['chunk_id']
            section = chunk.get('section', 'Unknown')
            text = chunk['text']
            score = chunk.get('similarity_score', 0.0)
            
            chunk_text = f"""--- Excerpt {i} (Relevance: {score:.3f}) ---
Paper: {paper_title}
Source ID: {source_id}
Chunk ID: {chunk_id}
Section: {section}

{text}

[End of Excerpt {i}]
"""
            formatted.append(chunk_text)
        
        return "\n".join(formatted)
    
    def generate(
        self,
        query: str,
        chunks: List[Dict],
        system_prompt: Optional[str] = None
    ) -> Dict:
        """
        Generate an answer from retrieved chunks.
        
        Args:
            query: User query
            chunks: Retrieved chunks with metadata
            system_prompt: Optional custom system prompt
            
        Returns:
            Dictionary with answer, citations, and metadata
        """
        if self.client is None:
            return {
                'answer': "ERROR: No LLM client initialized. Please set OPENAI_API_KEY or install openai package.",
                'citations': [],
                'metadata': {
                    'error': 'No LLM client'
                }
            }
        
        # Build prompt
        system_msg, user_msg = self.build_prompt(query, chunks, system_prompt)
        
        logger.info(f"Generating answer for query: {query[:100]}...")
        logger.info(f"Using {len(chunks)} chunks as context")

        def _is_connection_error(e: Exception) -> bool:
            """Check if exception is a transient connection error worth retrying."""
            name = type(e).__name__.lower()
            msg = str(e).lower()
            if isinstance(e, ConnectionError):
                return True
            if "connection" in name or "connection" in msg:
                return True
            if "connect" in name or "connect" in msg:
                return True
            if "timeout" in name or "timeout" in msg:
                return True
            return False

        max_connection_retries = 2  # 3 total attempts
        for conn_attempt in range(max_connection_retries + 1):
            try:
                # Call OpenAI API (with rate-limit handling and exponential backoff)
                response = call_with_guard(
                    lambda: self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg}
                        ],
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                )
                break
            except Exception as e:
                if _is_connection_error(e) and conn_attempt < max_connection_retries:
                    delay = 2.0 + conn_attempt  # 2s, then 3s
                    logger.warning(
                        f"Connection error, retry {conn_attempt + 1}/{max_connection_retries + 1} in {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    raise

        try:
            answer = response.choices[0].message.content
            # Normalize bare citations (e.g. "GPTQ_2022, GPTQ_2022_chunk_0027") to [Source: X, Chunk: Y]
            answer = self._normalize_bare_citations(answer)
            
            # Extract citations from answer
            citations = self._extract_citations(answer)
            
            # Build metadata
            metadata = {
                'model': self.model,
                'temperature': self.temperature,
                'chunks_used': len(chunks),
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Answer generated ({metadata['total_tokens']} tokens)")
            
            return {
                'answer': answer,
                'citations': citations,
                'chunks': chunks,  # Include chunks for reference
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                'answer': f"ERROR: Failed to generate answer: {str(e)}",
                'citations': [],
                'metadata': {
                    'error': str(e)
                }
            }
    
    def _normalize_bare_citations(self, text: str) -> str:
        """Convert bare 'SourceID, ChunkID' or 'SourceID ChunkID' to [Source: X, Chunk: Y]."""
        def _wrap(m: re.Match) -> str:
            return f"[Source: {m.group(1)}, Chunk: {m.group(2)}]"
        text = re.sub(r"(\w+_\d{4}),\s*(\1_chunk_\d+)", _wrap, text)
        text = re.sub(r"(\w+_\d{4})\s+(\1_chunk_\d+)", _wrap, text)
        return text
    
    def _extract_citations(self, answer: str) -> List[Dict]:
        """
        Extract citations from the answer.
        
        Looks for patterns like:
        - [Source: Phi3_2024, Chunk: Phi3_2024_chunk_0001]
        - [Phi3_2024, Phi3_2024_chunk_0001]
        
        Returns list of {source_id, chunk_id} dicts
        """
        import re
        
        citations = []
        
        # Pattern 1: [Source: X, Chunk: Y]
        pattern1 = r'\[Source:\s*([^,]+),\s*Chunk:\s*([^\]]+)\]'
        matches1 = re.findall(pattern1, answer)
        for source_id, chunk_id in matches1:
            citations.append({
                'source_id': source_id.strip(),
                'chunk_id': chunk_id.strip()
            })
        
        # Pattern 2: [source_id, chunk_id]
        pattern2 = r'\[([A-Za-z0-9_]+),\s*([A-Za-z0-9_]+)\]'
        matches2 = re.findall(pattern2, answer)
        for source_id, chunk_id in matches2:
            # Only add if not already in citations
            citation = {'source_id': source_id.strip(), 'chunk_id': chunk_id.strip()}
            if citation not in citations:
                citations.append(citation)
        
        return citations
    
    def format_response(self, result: Dict) -> str:
        """Format the generation result for display."""
        output = []
        output.append("="*80)
        output.append("ANSWER")
        output.append("="*80)
        output.append(result['answer'])
        output.append("")
        
        if result['citations']:
            output.append("="*80)
            output.append(f"CITATIONS ({len(result['citations'])} found)")
            output.append("="*80)
            for i, citation in enumerate(result['citations'], 1):
                output.append(f"{i}. Source: {citation['source_id']}, Chunk: {citation['chunk_id']}")
            output.append("")
        
        if 'metadata' in result and 'error' not in result['metadata']:
            metadata = result['metadata']
            output.append("="*80)
            output.append("METADATA")
            output.append("="*80)
            output.append(f"Model: {metadata.get('model', 'N/A')}")
            output.append(f"Chunks used: {metadata.get('chunks_used', 'N/A')}")
            output.append(f"Tokens: {metadata.get('total_tokens', 'N/A')} (prompt: {metadata.get('prompt_tokens', 'N/A')}, completion: {metadata.get('completion_tokens', 'N/A')})")
            output.append(f"Timestamp: {metadata.get('timestamp', 'N/A')}")
        
        return "\n".join(output)


def main():
    """Test the generator (requires OpenAI API key)."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test answer generation")
    parser.add_argument(
        "--query",
        type=str,
        default="What is Phi-3's performance on MMLU benchmark?",
        help="Query to test"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4",
        help="OpenAI model name"
    )
    
    args = parser.parse_args()
    
    # Initialize generator
    logger.info("="*80)
    logger.info("ANSWER GENERATOR TEST")
    logger.info("="*80)
    
    generator = AnswerGenerator(model=args.model)
    
    # Create mock chunks for testing
    mock_chunks = [
        {
            'source_id': 'Phi3_2024',
            'chunk_id': 'Phi3_2024_chunk_0015',
            'text': 'Phi-3-mini achieves 68.8% on MMLU (5-shot), surpassing models with significantly more parameters. The model demonstrates strong performance across diverse knowledge domains.',
            'section': 'Results',
            'similarity_score': 0.92,
            'metadata': {'title': 'Phi-3 Technical Report'}
        },
        {
            'source_id': 'Phi3_2024',
            'chunk_id': 'Phi3_2024_chunk_0016',
            'text': 'On the MMLU benchmark, Phi-3-small (7B parameters) scores 75.3%, while Phi-3-medium (14B) reaches 78.0%. These results position Phi-3 among the top-performing language models in its size category.',
            'section': 'Results',
            'similarity_score': 0.89,
            'metadata': {'title': 'Phi-3 Technical Report'}
        }
    ]
    
    # Generate answer
    logger.info(f"Query: {args.query}")
    result = generator.generate(args.query, mock_chunks)
    
    # Display result
    print("\n" + generator.format_response(result))


if __name__ == "__main__":
    main()
