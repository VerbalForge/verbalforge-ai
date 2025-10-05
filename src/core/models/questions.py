"""Question models with DRY principles and inheritance"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from abc import ABC, abstractmethod
from datetime import datetime
import re

from .enums import QuestionType


class Choice(BaseModel):
    """A question choice with blank number, correctness and reasoning"""

    option: str = Field(..., description="The option text")
    blank: int = Field(..., description="Which blank this option fills (1, 2, or 3)")
    is_correct: bool = Field(..., description="Whether this option is correct")
    reasoning: str = Field(
        ..., description="Detailed explanation of why this option is correct/incorrect"
    )


class GREQuestion(BaseModel, ABC):
    """Base class for all GRE verbal questions with common validation"""

    question_text: str = Field(..., description="The question text")
    choices: List[Choice] = Field(
        ..., description="List of answer choices", min_length=3, max_length=9
    )
    difficulty_level: str = Field(..., description="Difficulty level: easy, medium, or hard")
    topic: Optional[str] = Field(None, description="Topic or subject area")

    @model_validator(mode="after")
    def validate_base_consistency(self):
        """Base validation that applies to all question types"""
        correct_choices = [opt for opt in self.choices if opt.is_correct]
        if not correct_choices:
            raise ValueError("At least one choice must be marked as correct")
        return self

    @abstractmethod
    def get_question_type(self) -> str:
        """Return the specific question type as a string value"""
        pass

    @staticmethod
    def count_blanks(text: str) -> int:
        """Count blanks in question text (DRY helper)"""
        simple_blanks = text.count("_____")
        numbered_blanks = len(re.findall(r"_____\d+_____", text))
        return numbered_blanks if numbered_blanks > 0 else simple_blanks

    def validate_blank_consistency(self, expected_blanks: int, blank_values: List[int]):
        """Validate that all choices have appropriate blank values (DRY helper)"""
        for choice in self.choices:
            if choice.blank not in blank_values:
                raise ValueError(
                    f"Choice has invalid blank={choice.blank}, expected one of {blank_values}"
                )


class TextCompletionQuestion(GREQuestion):
    """Text Completion question model"""

    question_type: str = Field(default="text_completion", description="Question type")

    @model_validator(mode="after")
    def validate_text_completion_specific(self):
        """Text completion specific validations"""
        blank_count = self.count_blanks(self.question_text)
        correct_answers = [opt.option for opt in self.choices if opt.is_correct]

        if blank_count == 1:
            if len(self.choices) != 5:
                raise ValueError(
                    f"Single-blank text completion must have exactly 5 choices, found {len(self.choices)}"
                )
            if len(correct_answers) != 1:
                raise ValueError(
                    f"Single-blank text completion must have exactly 1 correct answer, found {len(correct_answers)}"
                )
            self.validate_blank_consistency(1, [1])
        elif blank_count in [2, 3]:
            expected_choices = blank_count * 3
            if len(self.choices) != expected_choices:
                raise ValueError(
                    f"{blank_count}-blank text completion must have exactly {expected_choices} choices, found {len(self.choices)}"
                )
            if len(correct_answers) != blank_count:
                raise ValueError(
                    f"{blank_count}-blank text completion must have exactly {blank_count} correct answers, found {len(correct_answers)}"
                )
            # Validate 3 choices per blank
            for blank_num in range(1, blank_count + 1):
                blank_choices = [c for c in self.choices if c.blank == blank_num]
                if len(blank_choices) != 3:
                    raise ValueError(
                        f"Blank {blank_num} must have exactly 3 choices, found {len(blank_choices)}"
                    )
        else:
            raise ValueError(f"Text completion must have 1-3 blanks, found {blank_count}")

        return self

    def get_question_type(self) -> str:
        """Return the specific question type based on number of blanks"""
        blank_count = self.count_blanks(self.question_text)
        type_map = {
            1: QuestionType.TEXT_COMPLETION_SINGLE.value,
            2: QuestionType.TEXT_COMPLETION_DOUBLE.value,
            3: QuestionType.TEXT_COMPLETION_TRIPLE.value,
        }
        return type_map.get(blank_count, "text_completion")


class SentenceEquivalenceQuestion(GREQuestion):
    """Sentence Equivalence question model"""

    question_type: str = Field(default="sentence_equivalence", description="Question type")

    @model_validator(mode="after")
    def validate_sentence_equivalence_specific(self):
        """Sentence equivalence specific validations"""
        if len(self.choices) != 6:
            raise ValueError(
                f"Sentence equivalence must have exactly 6 choices, found {len(self.choices)}"
            )

        correct_answers = [opt.option for opt in self.choices if opt.is_correct]
        if len(correct_answers) != 2:
            raise ValueError(
                f"Sentence equivalence must have exactly 2 correct answers, found {len(correct_answers)}"
            )

        blank_count = self.count_blanks(self.question_text)
        if blank_count != 1:
            raise ValueError(f"Sentence equivalence must have exactly 1 blank, found {blank_count}")

        self.validate_blank_consistency(1, [1])
        return self

    def get_question_type(self) -> str:
        return QuestionType.SENTENCE_EQUIVALENCE.value


class ReadingComprehensionQuestion(GREQuestion):
    """Reading Comprehension question model"""

    question_type: str = Field(
        ...,
        description="Specific RC question type: reading_comprehension_single, reading_comprehension_multiple, or reading_comprehension_highlight",
    )

    @model_validator(mode="after")
    def validate_reading_comprehension_specific(self):
        """Reading comprehension specific validations"""
        correct_answers = [opt.option for opt in self.choices if opt.is_correct]
        qt = self.question_type

        validation_rules = {
            QuestionType.READING_COMPREHENSION_SINGLE.value: {
                "choices": (5, 5),
                "correct": (1, 1),
            },
            QuestionType.READING_COMPREHENSION_MULTIPLE.value: {
                "choices": (3, 3),
                "correct": (1, 3),
            },
            QuestionType.READING_COMPREHENSION_HIGHLIGHT.value: {
                "choices": (3, 10),
                "correct": (1, 1),
            },
        }

        if qt not in validation_rules:
            raise ValueError(f"Unknown reading comprehension question type: {qt}")

        rules = validation_rules[qt]
        min_c, max_c = rules["choices"]
        min_corr, max_corr = rules["correct"]

        if not (min_c <= len(self.choices) <= max_c):
            raise ValueError(f"{qt} must have {min_c}-{max_c} choices, found {len(self.choices)}")

        if not (min_corr <= len(correct_answers) <= max_corr):
            raise ValueError(
                f"{qt} must have {min_corr}-{max_corr} correct answers, found {len(correct_answers)}"
            )

        self.validate_blank_consistency(1, [1])
        return self

    def get_question_type(self) -> str:
        """Return the question type as string value"""
        if isinstance(self.question_type, str):
            return self.question_type
        return (
            self.question_type.value
            if hasattr(self.question_type, "value")
            else str(self.question_type)
        )


class ReadingComprehension(BaseModel):
    """Reading Comprehension passage with associated questions"""

    passage: str = Field(
        ..., min_length=150, max_length=2000, description="The reading passage text"
    )
    source: str = Field(
        ..., min_length=10, max_length=200, description="Academic source or reference"
    )
    title: str = Field(
        ..., min_length=5, max_length=200, description="Title of the passage (generated by LLM)"
    )
    difficulty_level: str = Field(
        default="medium", description="Difficulty level (computed as lowest of all child questions)"
    )
    type: str = Field(
        default="reading_comprehension_passage", description="Type identifier for the passage"
    )
    questions: List[ReadingComprehensionQuestion] = Field(
        ..., min_length=1, max_length=6, description="Questions based on the passage"
    )

    @model_validator(mode="after")
    def validate_reading_comprehension(self):
        """Reading comprehension specific validations"""
        # Ensure type is set correctly
        if self.type != "reading_comprehension_passage":
            self.type = "reading_comprehension_passage"

        # Compute difficulty as the lowest (easiest) of all questions
        if self.questions:
            difficulty_order = {"easy": 1, "medium": 2, "hard": 3}
            question_difficulties = [q.difficulty_level for q in self.questions]

            # Get the minimum difficulty (easy < medium < hard)
            min_difficulty = min(question_difficulties, key=lambda d: difficulty_order.get(d, 2))
            self.difficulty_level = min_difficulty

        return self


# Union types for polymorphic handling
AnyGREQuestion = Union[
    TextCompletionQuestion, SentenceEquivalenceQuestion, ReadingComprehensionQuestion
]
AnyGREContent = Union[TextCompletionQuestion, SentenceEquivalenceQuestion, ReadingComprehension]


class QuestionBatch(BaseModel):
    """A batch of GRE questions"""

    questions: List[AnyGREContent] = Field(
        ..., description="List of generated questions or reading comprehension sets"
    )
    batch_id: str = Field(..., description="Unique batch identifier")
    question_type: str = Field(..., description="Type of questions in this batch")
    generation_metadata: dict = Field(default_factory=dict, description="Metadata about generation")

    @field_validator("questions")
    @classmethod
    def validate_batch_size(cls, v):
        """Validate batch contains 1-10 questions"""
        if len(v) < 1 or len(v) > 10:
            raise ValueError("Batch must contain between 1 and 10 questions")
        return v


# Helper functions
def create_batch_id(question_type: str, difficulty: str = "") -> str:
    """Generate a batch ID for grouping questions"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if difficulty:
        return f"{question_type}_{difficulty}_{timestamp}"
    return f"{question_type}_{timestamp}"


def create_reading_comprehension_from_response(
    passage_text: str, source: str, questions_data: List[dict], title: str = None
) -> ReadingComprehension:
    """Create a ReadingComprehension object from LLM response data"""
    questions = [ReadingComprehensionQuestion(**q_data) for q_data in questions_data]

    if not title:
        title = "Reading Comprehension Passage"

    return ReadingComprehension(
        passage=passage_text, source=source, title=title, questions=questions
    )
