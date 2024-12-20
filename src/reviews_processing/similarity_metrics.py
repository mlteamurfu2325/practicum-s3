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
    """Download and load the Russian language model."""
    model_name = 'ru_core_news_sm'
    try:
        return spacy.load(model_name)
    except OSError:
        print(f"Downloading {model_name} model...")
        spacy.cli.download(model_name)
        return spacy.load(model_name)

# Initialize spaCy
nlp = ensure_spacy_model()

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
    Calculate similarity scores between generated review and reference reviews.
    
    Args:
        generated_review: The AI-generated review
        reference_reviews: List of real reviews used as reference
        
    Returns:
        List of dictionaries containing similarity scores for each reference review
    """
    # Initialize ROUGE scorer with Russian-specific settings
    scorer = rouge_scorer.RougeScorer(
        ['rouge1', 'rouge2', 'rougeL'],
        use_stemmer=True,
        tokenizer=lambda x: [token.text for token in nlp(x) if not token.is_punct and not token.is_space]
    )
    
    # Initialize BLEU smoothing with more lenient method
    smoothing = SmoothingFunction().method4  # method4 is more suitable for short texts
    
    metrics = []
    gen_doc = nlp(generated_review.lower())
    
    # Get content words from generated review (excluding stopwords and punctuation)
    gen_tokens = [token.lemma_ for token in gen_doc 
                 if not token.is_punct and not token.is_space and not token.is_stop]
    
    for ref_review in reference_reviews:
        ref_doc = nlp(ref_review.lower())
        
        # Get content words from reference review
        ref_tokens = [token.lemma_ for token in ref_doc 
                     if not token.is_punct and not token.is_space and not token.is_stop]
        
        # Calculate BLEU score with multiple n-gram weights
        weights = (0.4, 0.3, 0.2, 0.1)  # Give more weight to unigrams and bigrams
        bleu_score = sentence_bleu(
            [ref_tokens],
            gen_tokens,
            weights=weights,
            smoothing_function=smoothing
        )
        
        # Calculate ROUGE scores
        rouge_scores = scorer.score(generated_review, ref_review)
        
        # Calculate semantic similarity using spaCy
        semantic_sim = gen_doc.similarity(ref_doc)
        
        # Combine ROUGE scores with weights
        rouge_avg = np.mean([
            rouge_scores['rouge1'].fmeasure * 0.4,  # More weight to unigrams
            rouge_scores['rouge2'].fmeasure * 0.3,  # Less weight to bigrams
            rouge_scores['rougeL'].fmeasure * 0.3   # Less weight to longest common subsequence
        ])
        
        # Combine different metrics
        final_score = np.mean([
            bleu_score * 0.3,      # 30% weight to BLEU
            rouge_avg * 0.3,       # 30% weight to ROUGE
            semantic_sim * 0.4     # 40% weight to semantic similarity
        ])
        
        metrics.append({
            'bleu': round(bleu_score, 3),
            'rouge': round(rouge_avg, 3),
            'semantic': round(semantic_sim, 3),
            'combined': round(final_score, 3)
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
