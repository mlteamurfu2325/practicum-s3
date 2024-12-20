"""Module for calculating similarity metrics between reviews."""

import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from typing import List, Dict, Tuple
import numpy as np

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


def calculate_metrics(generated_review: str, reference_reviews: List[str]) -> List[Dict[str, float]]:
    """
    Calculate BLEU and ROUGE scores between generated review and reference reviews.
    
    Args:
        generated_review: The AI-generated review
        reference_reviews: List of real reviews used as reference
        
    Returns:
        List of dictionaries containing BLEU and ROUGE scores for each reference review
    """
    # Initialize ROUGE scorer
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    
    # Initialize BLEU smoothing
    smoothing = SmoothingFunction().method1
    
    metrics = []
    
    for ref_review in reference_reviews:
        # Calculate BLEU score
        ref_tokens = nltk.word_tokenize(ref_review.lower())
        gen_tokens = nltk.word_tokenize(generated_review.lower())
        bleu_score = sentence_bleu([ref_tokens], gen_tokens, smoothing_function=smoothing)
        
        # Calculate ROUGE scores
        rouge_scores = scorer.score(generated_review, ref_review)
        
        # Average of ROUGE scores for simplicity
        rouge_avg = np.mean([
            rouge_scores['rouge1'].fmeasure,
            rouge_scores['rouge2'].fmeasure,
            rouge_scores['rougeL'].fmeasure
        ])
        
        metrics.append({
            'bleu': round(bleu_score, 3),
            'rouge': round(rouge_avg, 3)
        })
    
    return metrics


def calculate_average_scores(metrics: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Calculate average BLEU and ROUGE scores.
    
    Args:
        metrics: List of dictionaries containing BLEU and ROUGE scores
        
    Returns:
        Dictionary with average scores
    """
    if not metrics:
        return {'bleu': 0.0, 'rouge': 0.0}
        
    avg_bleu = np.mean([m['bleu'] for m in metrics])
    avg_rouge = np.mean([m['rouge'] for m in metrics])
    
    return {
        'bleu': round(avg_bleu, 3),
        'rouge': round(avg_rouge, 3)
    }
