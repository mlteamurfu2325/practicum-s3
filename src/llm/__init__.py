"""LLM integration package for review generation."""
from typing import Dict, Optional, Tuple

from langgraph.graph import Graph
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

    def _create_workflow(self) -> Graph:
        """Create the LangGraph workflow for review generation."""
        # Define the nodes
        def validate(state) -> Dict:
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
            return {
                **state,
                "validation_result": result,
                "should_generate": result["is_valid"]
            }

        def generate(state) -> Dict:
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
            return {
                **state,
                "generated_review": response.choices[0].message.content,
                "should_check": True
            }

        def check(state) -> Dict:
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
            check_result = json.loads(response.choices[0].message.content)
            scores = check_result["scores"]
            passed = all(
                scores[k] >= QUALITY_THRESHOLD[k]
                for k in QUALITY_THRESHOLD
            )
            return {
                **state,
                "check_result": check_result,
                "should_regenerate": not passed and state["attempts"] < 3,
                "should_return": passed or state["attempts"] >= 3
            }

        # Create the graph
        workflow = Graph()

        # Add nodes
        workflow.add_node("validate", validate)
        workflow.add_node("generate", generate)
        workflow.add_node("check", check)

        # Add edges
        workflow.add_edge("validate", "generate")
        workflow.add_edge("generate", "check")
        workflow.add_edge("check", "generate")

        # Set entry point
        workflow.set_entry_point("validate")

        return workflow

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
        initial_state = {
            "theme": theme,
            "rating": rating,
            "category": category,
            "attempts": 0,
            "should_generate": False,
            "should_check": False,
            "should_regenerate": False,
            "should_return": False
        }

        try:
            # Run the workflow
            final_state = self.workflow.run(initial_state)

            # Check validation result
            if not final_state["validation_result"]["is_valid"]:
                error_type = final_state["validation_result"]["error_type"]
                return None, ERROR_MESSAGES[error_type]

            # Return generated review if quality check passed
            if final_state["check_result"]["verdict"] == "accept":
                return final_state["generated_review"], None

            # If we reached max attempts, return the best review we got
            if final_state["attempts"] >= 3:
                return (
                    final_state["generated_review"],
                    "Качество отзыва может быть не оптимальным."
                )

            return None, ERROR_MESSAGES["validation_failed"]

        except Exception as e:
            return None, f"{ERROR_MESSAGES['api_error']} ({str(e)})"
