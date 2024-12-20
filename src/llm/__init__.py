"""LLM integration package for review generation."""
from typing import Dict, Optional, Tuple
from typing_extensions import TypedDict
import logging
import sys
import re

from langgraph.graph import StateGraph
from openai import OpenAI
import json

from src.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    DEFAULT_MODEL,
    ERROR_MESSAGES,
    QUALITY_THRESHOLD
)
from src.llm.prompts import (
    VALIDATION_PROMPT,
    GENERATION_PROMPT,
    SELF_CHECK_PROMPT
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


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


def clean_json_response(content: str) -> str:
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

    logger.info(f"Cleaned JSON content: {content}")
    return content


def parse_json_response(content: str, step: str) -> Dict:
    """Safely parse JSON response with logging."""
    logger.info(f"Parsing {step} response: {content}")
    try:
        cleaned_content = clean_json_response(content)
        return json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {step} JSON response: {str(e)}")
        logger.error(f"Raw content: {content}")
        logger.error(f"Cleaned content: {cleaned_content}")
        raise ValueError(
            f"Invalid JSON response from {step}. Raw content: {content}"
        )


class ReviewGenerator:
    """Main class for generating reviews using LLM."""

    def __init__(self, model_name=None):
        """Initialize the review generator with OpenRouter client."""
        logger.info(f"Initializing ReviewGenerator with model: {model_name}")
        self.client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
            default_headers={"HTTP-Referer": "http://localhost:8501"}
        )
        self.model_name = model_name or DEFAULT_MODEL
        self.workflow = self._create_workflow()
        logger.info("ReviewGenerator initialized successfully")

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for review generation."""
        logger.info("Creating LangGraph workflow")
        # Create a state graph
        workflow = StateGraph(ReviewState)

        # Define the nodes
        def validate(state: ReviewState) -> ReviewState:
            """Validate user input."""
            logger.info(f"Validating input theme: {state['theme']}")
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
            result = parse_json_response(content, "validation")
            state["validation_result"] = result
            logger.info(f"Validation result: {result}")
            return state

        def generate(state: ReviewState) -> ReviewState:
            """Generate review based on parameters."""
            logger.info(
                f"Generating review for: theme='{state['theme']}', "
                f"rating={state['rating']}, category='{state['category']}'"
            )
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
            logger.info(f"Generated review: {content}")
            state["generated_review"] = content
            return state

        def check(state: ReviewState) -> ReviewState:
            """Perform self-check of generated review."""
            logger.info("Performing quality check on generated review")
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
            result = parse_json_response(content, "quality check")
            state["check_result"] = result
            state["attempts"] += 1
            logger.info(
                f"Quality check result: {result}. "
                f"Attempt {state['attempts']}/3"
            )
            return state

        def end(state: ReviewState) -> ReviewState:
            """End node that returns the final state."""
            logger.info("Workflow completed")
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
            logger.info(f"Validation route decision: {result}")
            return result

        def should_regenerate(state: ReviewState) -> str:
            """Determine if we should regenerate the review."""
            if state["attempts"] >= 3:
                logger.info("Max attempts reached, ending workflow")
                return "end"
            scores = state["check_result"]["scores"]
            passed = all(
                scores[k] >= QUALITY_THRESHOLD[k]
                for k in QUALITY_THRESHOLD
            )
            result = "end" if passed else "generate"
            logger.info(
                f"Quality check route decision: {result}. "
                f"Scores: {scores}"
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
        logger.info("Workflow created and compiled successfully")
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
        logger.info(
            f"Starting review generation: theme='{theme}', "
            f"rating={rating}, category='{category}'"
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
                logger.info(f"Validation failed: {error_msg}")
                return None, error_msg

            # Return generated review if quality check passed
            if final_state.get("check_result"):
                if final_state["check_result"]["verdict"] == "accept":
                    logger.info("Review generated and passed quality check")
                    return final_state["generated_review"], None
                elif final_state["attempts"] >= 3:
                    msg = "Качество отзыва может быть не оптимальным."
                    logger.warning(f"Max attempts reached: {msg}")
                    return final_state["generated_review"], msg

            logger.info("Review generation failed quality check")
            return None, ERROR_MESSAGES["validation_failed"]

        except Exception as e:
            logger.error(
                f"Error during review generation: {str(e)}",
                exc_info=True
            )
            return None, f"{ERROR_MESSAGES['api_error']} ({str(e)})"
