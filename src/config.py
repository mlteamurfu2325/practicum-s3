"""Configuration for LLM integration."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model configuration
DEFAULT_MODEL = "google/gemini-flash-1.5"
AVAILABLE_MODELS = {
    "google/gemini-flash-1.5": "Google Gemini Flash 1.5",
    "openai/gpt-4-turbo": "GPT-4 Turbo",
    "amazon/nova-lite-v1": "Amazon Nova Lite"
}

# Validation settings
MAX_RETRIES = 3
TIMEOUT_SECONDS = 15
MIN_REVIEW_LENGTH = 50
MAX_REVIEW_LENGTH = 500

# Quality thresholds for self-check
QUALITY_THRESHOLD = {
    'theme_relevance': 7,    # out of 10
    'rating_match': 7,       # out of 10
    'language_quality': 7,   # out of 10
    'consistency': 7,        # out of 10
    'category_specificity': 7  # out of 10
}

# Error messages
ERROR_MESSAGES = {
    'non_russian': (
        'Пожалуйста, используйте русский язык для ввода темы отзыва.'
    ),
    'nsfw': 'Пожалуйста, избегайте неприемлемого контента.',
    'irrelevant': (
        'Тема должна быть связана с отзывом о месте или услуге.'
    ),
    'gibberish': (
        'Пожалуйста, введите осмысленный текст для темы отзыва.'
    ),
    'api_error': (
        'Произошла ошибка при генерации отзыва. '
        'Пожалуйста, попробуйте позже.'
    ),
    'validation_failed': (
        'Проверка не пройдена. Пожалуйста, измените параметры отзыва.'
    ),
}
