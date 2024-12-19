from nltk.translate.bleu_score import sentence_bleu
from rouge_score import rouge_scorer
import nltk
import re

def preprocess_text(text):
    """Preprocess text for metric calculation."""
    # Convert to lowercase and remove punctuation
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.split()

def calculate_bleu(generated_text, reference_texts):
    """Calculate BLEU score between generated text and reference texts."""
    try:
        # Download required NLTK data if not present
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')

        # Preprocess texts
        generated_tokens = preprocess_text(generated_text)
        reference_tokens = [preprocess_text(ref) for ref in reference_texts]
        
        # Calculate BLEU score
        return sentence_bleu(reference_tokens, generated_tokens)
    except Exception as e:
        print(f"Error calculating BLEU score: {e}")
        return 0.0

def calculate_rouge(generated_text, reference_texts):
    """Calculate ROUGE scores between generated text and reference texts."""
    try:
        scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        
        # Calculate ROUGE scores against each reference
        scores_per_ref = []
        for ref in reference_texts:
            scores = scorer.score(generated_text, ref)
            scores_per_ref.append({
                'rouge1': scores['rouge1'].fmeasure,
                'rouge2': scores['rouge2'].fmeasure,
                'rougeL': scores['rougeL'].fmeasure
            })
        
        # Calculate average scores
        avg_scores = {
            'rouge1': sum(s['rouge1'] for s in scores_per_ref) / len(scores_per_ref),
            'rouge2': sum(s['rouge2'] for s in scores_per_ref) / len(scores_per_ref),
            'rougeL': sum(s['rougeL'] for s in scores_per_ref) / len(scores_per_ref)
        }
        
        return avg_scores
    except Exception as e:
        print(f"Error calculating ROUGE scores: {e}")
        return {'rouge1': 0.0, 'rouge2': 0.0, 'rougeL': 0.0}
