"""Module for calculating similarity metrics between reviews."""

import spacy
from spacy.language import Language
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from typing import List, Dict, Tuple
import numpy as np
import subprocess
import sys

def ensure_spacy_model():
    """Ensure the Russian language model is installed."""
    try:
        spacy.load('ru_core_news_sm')
    except OSError:
        print("Downloading Russian language model...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "ru_core_news_sm"])

# Initialize spaCy
ensure_spacy_model()
nlp = spacy.load('ru_core_news_sm')

def tokenize_text(text: str, nlp: Language) -> List[str]:
    """
    Tokenize text using spaCy's Russian model.
    
    Args:
        text: Text to tokenize
        nlp: Loaded spaCy model
        
    Returns:
        List of tokens
    """
    doc = nlp(text.lower())
    # Use lemmatization for better matching
    return [token.lemma_ for token in doc if not token.is_punct and not token.is_space]

def calculate_metrics(generated_review: str, reference_reviews: List[str]) -> List[Dict[str, float]]:
    """
    Calculate BLEU and ROUGE scores between generated review and reference reviews.
    
    Args:
        generated_review: The AI-generated review
        reference_reviews: List of real reviews used as reference
        
    Returns:
        List of dictionaries containing BLEU and ROUGE scores for each reference review
    """
    # Initialize ROUGE scorer with stemming for Russian
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    
    # Initialize BLEU smoothing
    smoothing = SmoothingFunction().method1
    
    metrics = []
    
    # Tokenize generated review once
    gen_tokens = tokenize_text(generated_review, nlp)
    
    for ref_review in reference_reviews:
        # Calculate BLEU score with spaCy tokenization
        ref_tokens = tokenize_text(ref_review, nlp)
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
