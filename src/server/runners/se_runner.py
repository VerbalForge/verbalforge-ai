"""
Sentence Equivalence Runner

Picks 2 random words and generates 2 medium + 3 hard Sentence Equivalence questions.
"""

from typing import List

from core.models.enums import PromptQuestionType
from ..services import GeneratorService, MongoDBService
from .base_runner import WordBasedRunner


class SERunner(WordBasedRunner):
    """Sentence Equivalence question generation runner"""

    def __init__(self, generator: GeneratorService, db: MongoDBService):
        super().__init__(generator, db, "SE", "se_runner")

    def get_question_type(self) -> PromptQuestionType:
        """Return Sentence Equivalence question type"""
        return PromptQuestionType.SENTENCE_EQUIVALENCE

    def get_config_key(self) -> str:
        """Return config key for sentence equivalence"""
        return "sentence_equivalence"

    def build_topic_instruction(self, word_details: List[str]) -> str:
        """Build SE-specific topic instruction"""
        return (
            "**VOCABULARY FOCUS**:\n"
            "This will be the vocabulary in focus. "
            "Prepare sentences contexts that naturally incorporate the vocabulary words:\n\n" +
            "\n\n".join(word_details)
        )
