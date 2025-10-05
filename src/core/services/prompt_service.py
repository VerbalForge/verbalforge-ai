"""Prompt service for GRE question generation"""

from typing import Tuple, Callable, Dict
from ..models.enums import PromptQuestionType
from ..prompts import text_completion, sentence_equivalence, reading_comprehension


def get_text_completion_prompt(
    count: int = 5, difficulty: str = "medium", topic: str = None
) -> Tuple[str, str]:
    """Get system and user prompts for text completion questions"""
    system_prompt = text_completion.SYSTEM_PROMPT

    # Format the generation prompt with parameters
    topic_instruction = (
        f"\nTopic focus: {topic}"
        if topic
        else "\nNo specific topic restriction. Generate diverse, academically rigorous content."
    )
    user_prompt = text_completion.GENERATION_PROMPT.format(
        count=count, difficulty=difficulty, topic_instruction=topic_instruction
    )

    return (system_prompt, user_prompt)


def get_sentence_equivalence_prompt(
    count: int = 5, difficulty: str = "medium", topic: str = None
) -> Tuple[str, str]:
    """Get system and user prompts for sentence equivalence questions"""
    system_prompt = sentence_equivalence.SYSTEM_PROMPT

    # Format the generation prompt with parameters
    topic_instruction = (
        f"\nTopic focus: {topic}"
        if topic
        else "\nNo specific topic restriction. Generate diverse, academically rigorous content."
    )
    user_prompt = sentence_equivalence.GENERATION_PROMPT.format(
        count=count, difficulty=difficulty, topic_instruction=topic_instruction
    )

    return (system_prompt, user_prompt)


def get_reading_comprehension_prompt(
    count: int = 5, difficulty: str = "medium", topic: str = None
) -> Tuple[str, str]:
    """Get system and user prompts for reading comprehension questions"""
    system_prompt = reading_comprehension.SYSTEM_PROMPT

    # Format the generation prompt with parameters
    topic_instruction = (
        f"\nTopic focus: {topic}"
        if topic
        else "\nNo specific topic restriction. Prefer varied domains across sciences, humanities, social sciences, astronomy, economics, US history, psychology, sociology, and the arts."
    )
    topic_value = topic if topic else "varied academic"

    user_prompt = reading_comprehension.GENERATION_PROMPT.format(
        count=count, difficulty=difficulty, topic_instruction=topic_instruction, topic=topic_value
    )

    return (system_prompt, user_prompt)


class PromptService:
    """Service for managing question generation prompts"""

    def __init__(self):
        """Initialize prompt service"""
        self._prompt_map: Dict[PromptQuestionType, Callable] = {
            PromptQuestionType.TEXT_COMPLETION: get_text_completion_prompt,
            PromptQuestionType.SENTENCE_EQUIVALENCE: get_sentence_equivalence_prompt,
            PromptQuestionType.READING_COMPREHENSION: get_reading_comprehension_prompt,
        }

    def get_prompts(
        self,
        question_type: PromptQuestionType,
        count: int = 5,
        difficulty: str = "medium",
        topic: str = None,
    ) -> Tuple[str, str]:
        """Get prompts for specified question type

        Args:
            question_type: Type of question to generate prompts for
            count: Number of questions to generate
            difficulty: Difficulty level
            topic: Optional topic focus

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        prompt_func = self._prompt_map.get(question_type)
        if not prompt_func:
            raise ValueError(f"Unsupported question type: {question_type.value}")

        return prompt_func(count=count, difficulty=difficulty, topic=topic)

    def add_custom_instructions(self, user_prompt: str, custom_instructions: str) -> str:
        """Add custom instructions to user prompt

        Args:
            user_prompt: Base user prompt
            custom_instructions: Additional instructions

        Returns:
            Enhanced user prompt
        """
        if custom_instructions:
            return f"{user_prompt}\n\nAdditional instructions: {custom_instructions}"
        return user_prompt
