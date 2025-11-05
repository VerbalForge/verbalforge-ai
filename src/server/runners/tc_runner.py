"""
Text Completion Runner

Picks 2 random words and generates 2 medium + 3 hard Text Completion questions.
"""

from typing import List

from core.models.enums import PromptQuestionType
from ..services import GeneratorService, MongoDBService
from .base_runner import WordBasedRunner


class TCRunner(WordBasedRunner):
    """Text Completion question generation runner"""

    def __init__(self, generator: GeneratorService, db: MongoDBService):
        super().__init__(generator, db, "TC", "tc_runner")

    def get_question_type(self) -> PromptQuestionType:
        """Return Text Completion question type"""
        return PromptQuestionType.TEXT_COMPLETION

    def get_config_key(self) -> str:
        """Return config key for text completion"""
        return "text_completion"

    def build_topic_instruction(self, word_details: List[str]) -> str:
        """Build TC-specific topic instruction"""
        return (
            "**VOCABULARY FOCUS**:\n"
            "This will be the vocabulary in focus. "
            "Prepare sentences contexts that naturally incorporate the vocabulary words:\n\n" +
            "\n\n".join(word_details)
        )
