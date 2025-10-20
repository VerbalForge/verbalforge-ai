"""
Question Generation Service

Wrapper around the core QuestionOrchestrator for server use.
"""

import sys
import logging
from pathlib import Path
from typing import Any, Dict

# Make sure we can import verbalforge
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core import QuestionOrchestrator
from core.models import PromptQuestionType


class GeneratorService:
    """Manages question generation operations"""

    def __init__(self):
        self.generator = None
        self.logger = logging.getLogger("VerbalForgeServer.Generator")

    def initialize(self) -> None:
        """Initialize the question generator"""
        if self.generator is None:
            self.logger.info("Initializing question orchestrator")
            self.generator = QuestionOrchestrator()

    async def generate(
        self, count: int, question_type: PromptQuestionType, difficulty: str, 
        topic: str = None, timeout: float = 180.0
    ) -> Dict[str, Any]:
        """
        Generate questions with the specified parameters

        Args:
            count: Number of questions to generate
            question_type: Type of questions (TC, SE, RC)
            difficulty: Difficulty level (easy, medium, hard)
            topic: Optional topic/instruction for focused generation
            timeout: Generation timeout in seconds

        Returns:
            Generated questions data
        """
        if not self.generator:
            self.initialize()

        self.logger.info(
            f"Generating {count} {question_type.value} questions " 
            f"at {difficulty} difficulty"
            f"{f' with topic: {topic[:50]}...' if topic else ''}"
        )

        result = await self.generator.generate_questions(
            count=count, 
            question_type=question_type, 
            difficulty_level=difficulty,
            topic=topic
        )

        return result

    async def generate_with_conversation(
        self, count: int, question_type: PromptQuestionType, difficulty: str,
        conversation_history: list, topic: str = None, timeout: float = 180.0
    ) -> tuple[Dict[str, Any], list]:
        """
        Generate questions continuing a conversation
        
        Args:
            count: Number of questions to generate
            question_type: Type of questions (TC, SE, RC)
            difficulty: Difficulty level (easy, medium, hard)
            conversation_history: List of previous conversation messages
            topic: Optional topic/instruction for focused generation
            timeout: Generation timeout in seconds
            
        Returns:
            Tuple of (generated questions data, updated conversation history)
        """
        if not self.generator:
            self.initialize()

        self.logger.info(
            f"Generating {count} {question_type.value} questions " 
            f"at {difficulty} difficulty with conversation history ({len(conversation_history)} messages)"
        )

        # Create generation request
        from core.models.requests import GenerationRequest
        request = GenerationRequest(
            count=count,
            question_type=question_type,
            difficulty_level=difficulty,
            topic=topic,
        )

        result, updated_history = await self.generator.generation_layer.generate_questions_with_conversation(
            request=request,
            conversation_history=conversation_history
        )

        return result, updated_history

    def extract_questions(self, result: Any) -> list:
        """
        Extract questions from generator result

        Handles both QuestionBatch objects and dict formats.
        """
        questions = []

        if hasattr(result, "questions"):
            # QuestionBatch object
            questions = [q.model_dump() for q in result.questions]
        elif isinstance(result, dict):
            # Dictionary format
            if "questions" in result:
                questions.extend(result["questions"])

        return questions
