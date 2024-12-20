"""LLM integration package for review generation."""
from typing import Dict, Optional, Tuple
from typing_extensions import TypedDict
import logging
import sys
import re
import streamlit as st
from datetime import datetime

from langgraph.graph import StateGraph
from openai import OpenAI
import json

from src.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    DEFAULT_MODEL,
    ERROR_MESSAGES,
    QUALITY_THRESHOLD,
    AVAILABLE_MODELS
)
from src.llm.prompts import (
    VALIDATION_PROMPT,
    GENERATION_PROMPT,
    SELF_CHECK_PROMPT
)


class SessionStateHandler(logging.Handler):
    """Custom logging handler that stores logs in session state."""
    
    def __init__(self):
        super().__init__()

    def emit(self, record):
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S,%03d')
        
        # Get model name from record
        model_name = getattr(record, 'model_name', 'unknown')
        model_display_name = AVAILABLE_MODELS.get(model_name, model_name)
        
        # Format message
        log_entry = f"{timestamp} [{record.levelname}] [{model_display_name}] {record.msg}"
            
        # Store in session state
        if 'app_logs' not in st.session_state:
            st.session_state.app_logs = []
        st.session_state.app_logs.append(log_entry)
        if len(st.session_state.app_logs) > 100:
            st.session_state.app_logs.pop(0)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Remove all handlers from root logger
root = logging.getLogger()
for handler in root.handlers[:]:
    root.removeHandler(handler)

# Create logger
logger = logging.getLogger('review_generator')
logger.setLevel(logging.INFO)
logger.propagate = False

# Add handler for session state
handler = SessionStateHandler()
handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)
logger.addHandler(handler)

# Add console handler for debugging
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
root.addHandler(console_handler)


class ReviewState(TypedDict):
    """Type for the review generation state."""
    theme: str
    rating: int
    category: str
    attempts: int
    real_reviews: Optional[str]
    validation_result: Optional[Dict]
    generated_review: Optional[str]
    check_result: Optional[Dict]


class JsonHelper:
    """Helper class for JSON operations with model-specific logging."""
    
    def __init__(self, logger, model_name):
        self.logger = logger
        self.model_name = model_name

    def clean_json_response(self, content: str) -> str:
        """Clean JSON response from markdown and formatting artifacts."""
        # Remove markdown code block markers
        content = re.sub(r'```(?:json)?\n', '', content)
        content = content.replace('```', '')

        # Remove any leading/trailing whitespace
        content = content.strip()

        # Add missing commas between properties at any level
        def add_commas(match):
            """Add comma after the value if needed."""
            value = match.group(1)
            next_char = match.group(2)
            if value in ['true', 'false', 'null'] or value.isdigit():
                return f'{value},{next_char}'
            if value.endswith('"'):
                return f'{value},{next_char}'
            return f'{value}{next_char}'

        # Match any JSON value followed by a newline and another property
        pattern = r'(true|false|null|\d+|"[^"]*")\s*\n\s*(["{])'
        content = re.sub(pattern, add_commas, content)

        extra = {'model_name': self.model_name}
        self.logger.info(f"Cleaned JSON content: {content}", extra=extra)
        return content

    def parse_json_response(self, content: str, step: str) -> Dict:
        """Safely parse JSON response with logging."""
        extra = {'model_name': self.model_name}
        self.logger.info(f"Parsing {step} response: {content}", extra=extra)
        try:
            cleaned_content = self.clean_json_response(content)
            return json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse {step} JSON response: {str(e)}", extra=extra)
            self.logger.error(f"Raw content: {content}", extra=extra)
            self.logger.error(f"Cleaned content: {cleaned_content}", extra=extra)
            raise ValueError(
                f"Invalid JSON response from {step}. Raw content: {content}"
            )


class ReviewGenerator:
    """Main class for generating reviews using LLM."""

    def __init__(self, model_name=None):
        """Initialize the review generator with OpenRouter client."""
        self.model_name = model_name or DEFAULT_MODEL
        self.logger = logger
        self.extra = {'model_name': self.model_name}
        
        self.logger.info(f"Initializing ReviewGenerator with model: {self.model_name}", extra=self.extra)
        self.client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
            default_headers={"HTTP-Referer": "http://localhost:8501"}
        )
        self.json_helper = JsonHelper(self.logger, self.model_name)
        self.workflow = self._create_workflow()
        self.logger.info("ReviewGenerator initialized successfully", extra=self.extra)

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for review generation."""
        self.logger.info("Creating LangGraph workflow", extra=self.extra)
        # Create a state graph
        workflow = StateGraph(ReviewState)

        # Define the nodes
        def validate(state: ReviewState) -> ReviewState:
            """Validate user input."""
            self.logger.info(f"Validating input theme: {state['theme']}", extra=self.extra)
            self.logger.info("HTTP Request: POST https://openrouter.ai/api/v1/chat/completions", extra=self.extra)
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": VALIDATION_PROMPT.format(
                        input_text=state["theme"]
                    )
                }]
            )
            content = response.choices[0].message.content
            result = self.json_helper.parse_json_response(content, "validation")
            state["validation_result"] = result
            self.logger.info(f"Validation result: {result}", extra=self.extra)
            return state

        def generate(state: ReviewState) -> ReviewState:
            """Generate review based on parameters."""
            self.logger.info(
                f"Generating review for: theme='{state['theme']}', "
                f"rating={state['rating']}, category='{state['category']}'",
                extra=self.extra
            )
            self.logger.info("HTTP Request: POST https://openrouter.ai/api/v1/chat/completions", extra=self.extra)
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": GENERATION_PROMPT.format(
                        category=state["category"],
                        rating=state["rating"],
                        theme=state["theme"],
                        real_reviews=state["real_reviews"]
                    )
                }]
            )
            content = response.choices[0].message.content
            self.logger.info(f"Generated review: {content}", extra=self.extra)
            state["generated_review"] = content
            return state

        def check(state: ReviewState) -> ReviewState:
            """Perform self-check of generated review."""
            self.logger.info("Performing quality check on generated review", extra=self.extra)
            self.logger.info("HTTP Request: POST https://openrouter.ai/api/v1/chat/completions", extra=self.extra)
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": SELF_CHECK_PROMPT.format(
                        generated_review=state["generated_review"],
                        theme=state["theme"],
                        rating=state["rating"],
                        category=state["category"]
                    )
                }]
            )
            content = response.choices[0].message.content
            result = self.json_helper.parse_json_response(content, "quality check")
            state["check_result"] = result
            state["attempts"] += 1
            self.logger.info(
                f"Quality check result: {result}. "
                f"Attempt {state['attempts']}/3",
                extra=self.extra
            )
            return state

        def end(state: ReviewState) -> ReviewState:
            """End node that returns the final state."""
            self.logger.info("Workflow completed", extra=self.extra)
            return state

        # Add nodes
        workflow.add_node("validate", validate)
        workflow.add_node("generate", generate)
        workflow.add_node("check", check)
        workflow.add_node("end", end)

        # Define conditional edges
        def should_generate(state: ReviewState) -> str:
            """Determine if we should proceed to generation."""
            result = (
                "generate" if state["validation_result"]["is_valid"] else "end"
            )
            self.logger.info(f"Validation route decision: {result}", extra=self.extra)
            return result

        def should_regenerate(state: ReviewState) -> str:
            """Determine if we should regenerate the review."""
            if state["attempts"] >= 3:
                self.logger.info("Max attempts reached, ending workflow", extra=self.extra)
                return "end"
            scores = state["check_result"]["scores"]
            passed = all(
                scores[k] >= QUALITY_THRESHOLD[k]
                for k in QUALITY_THRESHOLD
            )
            result = "end" if passed else "generate"
            self.logger.info(
                f"Quality check route decision: {result}. "
                f"Scores: {scores}",
                extra=self.extra
            )
            return result

        # Add edges with conditional routing
        workflow.add_conditional_edges(
            "validate",
            should_generate,
            {
                "generate": "generate",
                "end": "end"
            }
        )
        workflow.add_edge("generate", "check")
        workflow.add_conditional_edges(
            "check",
            should_regenerate,
            {
                "generate": "generate",
                "end": "end"
            }
        )

        # Set entry point
        workflow.set_entry_point("validate")

        # Compile the workflow
        self.logger.info("Workflow created and compiled successfully", extra=self.extra)
        return workflow.compile()

    def generate_review(
        self,
        theme: str,
        rating: int,
        category: str,
        real_reviews: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate a review based on given parameters.

        Args:
            theme: Key theme of the review
            rating: Rating (1-5)
            category: Place category
            real_reviews: Optional string containing real reviews for inspiration

        Returns:
            Tuple of (review text, error message if any)
        """
        self.logger.info(
            f"Starting review generation: theme='{theme}', "
            f"rating={rating}, category='{category}'",
            extra=self.extra
        )
        initial_state: ReviewState = {
            "theme": theme,
            "rating": rating,
            "category": category,
            "attempts": 0,
            "real_reviews": real_reviews or "Примеры отзывов отсутствуют.",
            "validation_result": None,
            "generated_review": None,
            "check_result": None
        }

        try:
            # Run the workflow
            final_state = self.workflow.invoke(initial_state)

            # Check validation result
            if not final_state["validation_result"]["is_valid"]:
                error_type = final_state["validation_result"]["error_type"]
                error_msg = ERROR_MESSAGES[error_type]
                self.logger.info(f"Validation failed: {error_msg}", extra=self.extra)
                return None, error_msg

            # Return generated review if quality check passed
            if final_state.get("check_result"):
                if final_state["check_result"]["verdict"] == "accept":
                    self.logger.info("Review generated and passed quality check", extra=self.extra)
                    return final_state["generated_review"], None
                elif final_state["attempts"] >= 3:
                    msg = "Качество отзыва может быть не оптимальным."
                    self.logger.warning(f"Max attempts reached: {msg}", extra=self.extra)
                    return final_state["generated_review"], msg

            self.logger.info("Review generation failed quality check", extra=self.extra)
            return None, ERROR_MESSAGES["validation_failed"]

        except Exception as e:
            self.logger.error(
                f"Error during review generation: {str(e)}",
                exc_info=True,
                extra=self.extra
            )
            return None, f"{ERROR_MESSAGES['api_error']} ({str(e)})"
