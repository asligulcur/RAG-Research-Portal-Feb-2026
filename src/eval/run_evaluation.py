"""
RAG Evaluation Script
Runs evaluation queries and computes metrics for groundedness and answer relevance.

Usage:
    python src/eval/run_evaluation.py
"""

import os
import sys
import json
import logging
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from rag.rag_pipeline import RAGPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prompt version tracking
PROMPT_VERSION = "v2.0_trust_behavior_enhanced"  # Updated with stronger verification rules and similarity threshold


def compute_groundedness_score(answer: str, citations: List[str]) -> Dict[str, float]:
    """
    Compute groundedness/faithfulness score.
    
    Metrics:
    - Citation density: ratio of sentences with citations
    - Citation count: total number of citations
    - Has citations: binary metric (1 if any citations, 0 otherwise)
    
    Args:
        answer: Generated answer text
        citations: List of citation strings extracted from answer
        
    Returns:
        Dictionary with groundedness metrics
    """
    # Count sentences (rough approximation)
    sentences = [s.strip() for s in answer.split('.') if s.strip()]
    num_sentences = len(sentences)
    
    # Count citations
    num_citations = len(citations)
    
    # Check if answer explicitly says "no evidence" or similar
    no_evidence_phrases = [
        "no evidence",
        "not found",
        "does not contain",
        "corpus does not",
        "no information"
    ]
    has_no_evidence_flag = any(phrase in answer.lower() for phrase in no_evidence_phrases)
    
    # Citation density (citations per sentence)
    citation_density = num_citations / num_sentences if num_sentences > 0 else 0
    
    # Has citations (binary)
    has_citations = 1.0 if num_citations > 0 else 0.0
    
    # Properly flags missing evidence
    properly_flags_missing = 1.0 if (num_citations == 0 and has_no_evidence_flag) else 0.0
    
    return {
        'citation_count': num_citations,
        'citation_density': citation_density,
        'has_citations': has_citations,
        'properly_flags_missing': properly_flags_missing,
        'num_sentences': num_sentences
    }


def compute_answer_relevance_score(query: str, answer: str) -> Dict[str, float]:
    """
    Compute answer relevance score (heuristic-based).
    
    Metrics:
    - Query term coverage: ratio of query terms found in answer
    - Answer length appropriateness: penalty for too short/long answers
    - Directness: checks if answer addresses query directly
    
    Args:
        query: User query
        answer: Generated answer
        
    Returns:
        Dictionary with answer relevance metrics
    """
    # Tokenize query and answer (simple word split)
    query_terms = set(query.lower().split())
    answer_terms = set(answer.lower().split())
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'what', 'how', 'does', 'do', 'why', 'when', 'where'}
    query_terms = query_terms - stop_words
    
    # Query term coverage
    if len(query_terms) > 0:
        covered_terms = query_terms.intersection(answer_terms)
        term_coverage = len(covered_terms) / len(query_terms)
    else:
        term_coverage = 0.0
    
    # Answer length appropriateness (expect 50-500 words)
    word_count = len(answer.split())
    if 50 <= word_count <= 500:
        length_score = 1.0
    elif word_count < 50:
        length_score = word_count / 50.0
    else:
        length_score = max(0.0, 1.0 - (word_count - 500) / 500.0)
    
    # Directness: check if answer starts with addressing the query
    direct_indicators = ['yes', 'no', 'the', 'it', 'they', 'this', 'these']
    first_word = answer.split()[0].lower() if answer.split() else ''
    directness = 1.0 if first_word in direct_indicators else 0.8
    
    return {
        'term_coverage': term_coverage,
        'length_score': length_score,
        'directness': directness,
        'word_count': word_count
    }


def evaluate_query(pipeline: RAGPipeline, query_data: Dict) -> Dict:
    """
    Evaluate a single query through the RAG pipeline.
    
    Args:
        pipeline: RAG pipeline instance
        query_data: Query data from evaluation set
        
    Returns:
        Evaluation results with metrics
    """
    query_id = query_data['id']
    query = query_data['query']
    query_type = query_data['type']
    expected_answer_type = query_data.get('expected_answer_type', 'general')
    
    logger.info(f"Evaluating query {query_id}: {query[:60]}...")
    
    try:
        # Run query through pipeline
        result = pipeline.query(query, k=10)
        
        answer = result.get('answer', '')
        citations = result.get('citations', [])
        retrieved_chunks = result.get('chunks', [])
        
        # Compute metrics
        groundedness_metrics = compute_groundedness_score(answer, citations)
        relevance_metrics = compute_answer_relevance_score(query, answer)
        
        # Store retrieved chunks with relevant metadata
        stored_chunks = []
        for chunk in retrieved_chunks:
            stored_chunks.append({
                'chunk_id': chunk.get('chunk_id'),
                'source_id': chunk.get('source_id'),
                'similarity_score': chunk.get('similarity_score', 0.0),
                'section': chunk.get('section', 'Unknown'),
                'text_preview': chunk.get('text', '')[:300]  # First 300 chars
            })
        
        # Combine results
        evaluation_result = {
            'query_id': query_id,
            'query': query,
            'query_type': query_type,
            'expected_answer_type': expected_answer_type,
            'answer': answer,
            'citations': citations,
            'num_retrieved_chunks': len(retrieved_chunks),
            'retrieved_chunks': stored_chunks,
            'generation_config': {
                'model': pipeline.generator.model,
                'temperature': pipeline.generator.temperature,
                'max_tokens': pipeline.generator.max_tokens,
                'prompt_version': PROMPT_VERSION
            },
            'metrics': {
                'groundedness': groundedness_metrics,
                'answer_relevance': relevance_metrics
            },
            'success': True,
            'error': None
        }
        
        return evaluation_result
        
    except Exception as e:
        logger.error(f"Error evaluating query {query_id}: {e}")
        return {
            'query_id': query_id,
            'query': query,
            'query_type': query_type,
            'expected_answer_type': expected_answer_type,
            'answer': None,
            'citations': [],
            'num_retrieved_chunks': 0,
            'metrics': {},
            'success': False,
            'error': str(e)
        }


def aggregate_metrics(results: List[Dict]) -> Dict:
    """
    Aggregate metrics across all queries.
    
    Args:
        results: List of evaluation results
        
    Returns:
        Aggregated metrics
    """
    successful_results = [r for r in results if r['success']]
    n_success = len(successful_results)
    
    if n_success == 0:
        return {'error': 'No successful evaluations'}
    
    # Aggregate groundedness metrics
    total_citation_count = sum(r['metrics']['groundedness']['citation_count'] for r in successful_results)
    avg_citation_density = sum(r['metrics']['groundedness']['citation_density'] for r in successful_results) / n_success
    pct_with_citations = sum(r['metrics']['groundedness']['has_citations'] for r in successful_results) / n_success * 100
    pct_properly_flags_missing = sum(r['metrics']['groundedness']['properly_flags_missing'] for r in successful_results) / n_success * 100
    
    # Aggregate answer relevance metrics
    avg_term_coverage = sum(r['metrics']['answer_relevance']['term_coverage'] for r in successful_results) / n_success
    avg_length_score = sum(r['metrics']['answer_relevance']['length_score'] for r in successful_results) / n_success
    avg_directness = sum(r['metrics']['answer_relevance']['directness'] for r in successful_results) / n_success
    
    # By query type
    by_type = {}
    for query_type in ['direct', 'synthesis', 'edge_case']:
        type_results = [r for r in successful_results if r['query_type'] == query_type]
        if type_results:
            by_type[query_type] = {
                'count': len(type_results),
                'avg_citation_density': sum(r['metrics']['groundedness']['citation_density'] for r in type_results) / len(type_results),
                'avg_term_coverage': sum(r['metrics']['answer_relevance']['term_coverage'] for r in type_results) / len(type_results)
            }
    
    return {
        'total_queries': len(results),
        'successful_queries': n_success,
        'failed_queries': len(results) - n_success,
        'groundedness': {
            'total_citations': total_citation_count,
            'avg_citation_density': avg_citation_density,
            'pct_with_citations': pct_with_citations,
            'pct_properly_flags_missing': pct_properly_flags_missing
        },
        'answer_relevance': {
            'avg_term_coverage': avg_term_coverage,
            'avg_length_score': avg_length_score,
            'avg_directness': avg_directness
        },
        'by_query_type': by_type
    }


def main():
    """Run evaluation on all queries."""
    logger.info("=" * 60)
    logger.info("Starting RAG Evaluation")
    logger.info("=" * 60)
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY not found in environment!")
        logger.error("Please set it in .env file or export it in your terminal")
        return
    
    # Load query set
    query_set_path = 'src/eval/query_set.json'
    logger.info(f"Loading queries from: {query_set_path}")
    
    with open(query_set_path, 'r') as f:
        query_set = json.load(f)
    
    queries = query_set['queries']
    logger.info(f"Loaded {len(queries)} queries")
    
    # Initialize RAG pipeline
    logger.info("Initializing RAG pipeline...")
    pipeline = RAGPipeline(
        embeddings_dir='outputs/embeddings',
        model='gpt-4',
        api_key=os.getenv('OPENAI_API_KEY')
    )
    logger.info("Pipeline initialized successfully")
    
    # Run evaluation on all queries
    logger.info("\n" + "=" * 60)
    logger.info("Running Evaluation")
    logger.info("=" * 60 + "\n")
    
    results = []
    for i, query_data in enumerate(queries, 1):
        logger.info(f"\n[Query {i}/{len(queries)}]")
        result = evaluate_query(pipeline, query_data)
        results.append(result)
        
        # Print brief summary
        if result['success']:
            logger.info(f"✅ Success - Citations: {len(result['citations'])}, "
                       f"Term coverage: {result['metrics']['answer_relevance']['term_coverage']:.2f}")
        else:
            logger.error(f"❌ Failed - {result['error']}")
    
    # Aggregate metrics
    logger.info("\n" + "=" * 60)
    logger.info("Computing Aggregate Metrics")
    logger.info("=" * 60 + "\n")
    
    aggregate = aggregate_metrics(results)
    
    # Print summary
    logger.info("EVALUATION SUMMARY")
    logger.info("-" * 60)
    logger.info(f"Total Queries: {aggregate['total_queries']}")
    logger.info(f"Successful: {aggregate['successful_queries']}")
    logger.info(f"Failed: {aggregate['failed_queries']}")
    logger.info("")
    logger.info("GROUNDEDNESS METRICS:")
    logger.info(f"  Total Citations: {aggregate['groundedness']['total_citations']}")
    logger.info(f"  Avg Citation Density: {aggregate['groundedness']['avg_citation_density']:.3f}")
    logger.info(f"  % with Citations: {aggregate['groundedness']['pct_with_citations']:.1f}%")
    logger.info(f"  % Properly Flags Missing: {aggregate['groundedness']['pct_properly_flags_missing']:.1f}%")
    logger.info("")
    logger.info("ANSWER RELEVANCE METRICS:")
    logger.info(f"  Avg Term Coverage: {aggregate['answer_relevance']['avg_term_coverage']:.3f}")
    logger.info(f"  Avg Length Score: {aggregate['answer_relevance']['avg_length_score']:.3f}")
    logger.info(f"  Avg Directness: {aggregate['answer_relevance']['avg_directness']:.3f}")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'outputs/evaluation_results_{timestamp}.json'
    
    evaluation_output = {
        'metadata': {
            'timestamp': timestamp,
            'model': 'gpt-4',
            'prompt_version': PROMPT_VERSION,
            'total_queries': len(queries),
            'query_set_version': query_set.get('metadata', {}).get('version', 'v1.0')
        },
        'aggregate_metrics': aggregate,
        'individual_results': results
    }
    
    os.makedirs('outputs', exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(evaluation_output, f, indent=2)
    
    logger.info(f"\n✅ Results saved to: {output_path}")
    logger.info("\n" + "=" * 60)
    logger.info("Evaluation Complete!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
