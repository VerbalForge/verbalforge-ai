"""Enumerations for VerbalForge"""

from enum import Enum


class PromptQuestionType(str, Enum):
    """Types of GRE verbal questions for prompt generation"""

    TEXT_COMPLETION = "text_completion"
    SENTENCE_EQUIVALENCE = "sentence_equivalence"
    READING_COMPREHENSION = "reading_comprehension"


class QuestionType(str, Enum):
    """Types of GRE verbal questions for classification"""

    TEXT_COMPLETION_SINGLE = "text_completion_single"
    TEXT_COMPLETION_DOUBLE = "text_completion_double"
    TEXT_COMPLETION_TRIPLE = "text_completion_triple"
    SENTENCE_EQUIVALENCE = "sentence_equivalence"
    READING_COMPREHENSION_SINGLE = "reading_comprehension_single"
    READING_COMPREHENSION_MULTIPLE = "reading_comprehension_multiple"
    READING_COMPREHENSION_HIGHLIGHT = "reading_comprehension_highlight"


class DifficultyLevel(str, Enum):
    """Difficulty levels for GRE questions"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
