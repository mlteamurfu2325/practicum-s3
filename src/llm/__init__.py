"""LLM integration package for review generation."""
from typing import Dict, Optional, Tuple
from typing_extensions import TypedDict

from langgraph.graph import StateGraph
from openai import OpenAI
import json

from src.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    MODEL_NAME,
    ERROR_MESSAGES,
    QUALITY_THRESHOLD
)
from src.llm.prompts import (
    VALIDATION_PROMPT,
    GENERATION_PROMPT,
    SELF_CHECK_PROMPT
)


class ReviewState(TypedDict):
    """Type for the review generation state."""
    theme: str
    rating: int
    category: str
    attempts: int
    validation_result: Optional[Dict]
    generated_review: Optional[str]
    check_result: Optional[Dict]


class ReviewGenerator:
    """Main class for generating reviews using LLM."""

    def __init__(self):
        """Initialize the review generator with OpenRouter client."""
        self.client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
            default_headers={"HTTP-Referer": "http://localhost:8501"}
        )
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for review generation."""
        # Create a state graph
        workflow = StateGraph(ReviewState)

        # Define the nodes
        def validate(state: ReviewState) -> ReviewState:
            """Validate user input."""
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{
                    "role": "user",
                    "content": VALIDATION_PROMPT.format(
                        input_text=state["theme"]
                    )
                }]
            )
            result = json.loads(response.choices[0].message.content)
            state["validation_result"] = result
            return state

        def generate(state: ReviewState) -> ReviewState:
            """Generate review based on parameters."""
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{
                    "role": "user",
                    "content": GENERATION_PROMPT.format(
                        category=state["category"],
                        rating=state["rating"],
                        theme=state["theme"]
                    )
                }]
            )
            state["generated_review"] = response.choices[0].message.content
            return state

        def check(state: ReviewState) -> ReviewState:
            """Perform self-check of generated review."""
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
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
            state["check_result"] = json.loads(
                response.choices[0].message.content
            )
            state["attempts"] += 1
            return state

        def end(state: ReviewState) -> ReviewState:
            """End node that returns the final state."""
            return state

        # Add nodes
        workflow.add_node("validate", validate)
        workflow.add_node("generate", generate)
        workflow.add_node("check", check)
        workflow.add_node("end", end)

        # Define conditional edges
        def should_generate(state: ReviewState) -> str:
            """Determine if we should proceed to generation."""
            return (
                "generate" if state["validation_result"]["is_valid"] else "end"
            )

        def should_regenerate(state: ReviewState) -> str:
            """Determine if we should regenerate the review."""
            if state["attempts"] >= 3:
                return "end"
            scores = state["check_result"]["scores"]
            passed = all(
                scores[k] >= QUALITY_THRESHOLD[k]
                for k in QUALITY_THRESHOLD
            )
            return "end" if passed else "generate"

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
        return workflow.compile()

    def generate_review(
        self,
        theme: str,
        rating: int,
        category: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate a review based on given parameters.

        Args:
            theme: Key theme of the review
            rating: Rating (1-5)
            category: Place category

        Returns:
            Tuple of (review text, error message if any)
        """
        initial_state: ReviewState = {
            "theme": theme,
            "rating": rating,
            "category": category,
            "attempts": 0,
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
                return None, ERROR_MESSAGES[error_type]

            # Return generated review if quality check passed
            if final_state.get("check_result"):
                if final_state["check_result"]["verdict"] == "accept":
                    return final_state["generated_review"], None
                elif final_state["attempts"] >= 3:
                    return (
                        final_state["generated_review"],
                        "Качество отзыва может быть не оптимальным."
                    )

            return None, ERROR_MESSAGES["validation_failed"]

        except Exception as e:
            return None, f"{ERROR_MESSAGES['api_error']} ({str(e)})"
