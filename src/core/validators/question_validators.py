"""Question-specific validators using DRY principles"""

from typing import Dict, List, Any
import logging
from .base_validator import BaseValidator
from ..models.questions import (
    TextCompletionQuestion,
    SentenceEquivalenceQuestion,
    ReadingComprehensionQuestion,
)

logger = logging.getLogger(__name__)


class QuestionValidator(BaseValidator):
    """Validator for GRE questions using DRY principles"""

    def validate_question_structure(self, question_data: Dict[str, Any]) -> List[str]:
        """Validate basic question structure"""
        errors = []

        # Validate required fields
        errors.extend(self.validate_required_fields(question_data, ["question_text", "choices"]))
        if errors:
            return errors

        # Validate choices type
        errors.extend(self.validate_field_type(question_data, "choices", list))
        if errors:
            return errors

        # Validate each choice
        errors.extend(
            self.validate_list_items(
                question_data.get("choices", []),
                "Choice",
                self.validate_choice_structure,
            )
        )

        return errors

    def validate_question_quality(self, question_text: str) -> List[str]:
        """Validate question text quality"""
        errors = []

        # Check minimum length
        errors.extend(self.validate_text_length(question_text, min_len=20))

        # Check sentence structure
        has_blanks = "_____" in question_text
        errors.extend(self.validate_sentence_structure(question_text, allow_blanks=has_blanks))

        # Validate blanks for text completion
        if has_blanks:
            blank_count = self.count_blanks(question_text)
            if blank_count == 0:
                errors.append("Text completion question must contain blanks")
            elif blank_count > 3:
                errors.append(f"Too many blanks in question ({blank_count}, maximum 3)")

        return errors

    def validate_complete_question(self, question_data: Dict[str, Any]) -> List[str]:
        """Validate complete question including structure and quality"""
        errors = []

        # Validate structure
        structure_errors = self.validate_question_structure(question_data)
        errors.extend(structure_errors)

        if not structure_errors:
            # Validate quality
            question_text = question_data.get("question_text", "")
            quality_errors = self.validate_question_quality(question_text)
            errors.extend(quality_errors)

        return errors


class TextCompletionValidator(QuestionValidator):
    """Validator for Text Completion questions"""

    def validate(self, question_data: Dict[str, Any]) -> List[str]:
        """Validate text completion question"""
        errors = self.validate_complete_question(question_data)
        if errors:
            return errors

        try:
            tc_question = TextCompletionQuestion(**question_data)
            logger.info(f"Text completion validation passed: {tc_question.get_question_type()}")
            return []
        except Exception as e:
            error_msg = f"Text completion validation failed: {str(e)}"
            logger.warning(error_msg)
            return [error_msg]


class SentenceEquivalenceValidator(QuestionValidator):
    """Validator for Sentence Equivalence questions"""

    def validate(self, question_data: Dict[str, Any]) -> List[str]:
        """Validate sentence equivalence question"""
        errors = self.validate_complete_question(question_data)
        if errors:
            return errors

        try:
            se_question = SentenceEquivalenceQuestion(**question_data)
            logger.info(
                f"Sentence equivalence validation passed: {se_question.get_question_type()}"
            )
            return []
        except Exception as e:
            error_msg = f"Sentence equivalence validation failed: {str(e)}"
            logger.warning(error_msg)
            return [error_msg]


class ReadingComprehensionValidator(QuestionValidator):
    """Validator for Reading Comprehension questions"""

    def validate(self, question_data: Dict[str, Any]) -> List[str]:
        """Validate reading comprehension question"""
        errors = self.validate_complete_question(question_data)
        if errors:
            return errors

        try:
            rc_question = ReadingComprehensionQuestion(**question_data)
            logger.info(f"RC validation passed: {rc_question.get_question_type()}")
            return []
        except Exception as e:
            error_msg = f"Reading comprehension validation failed: {str(e)}"
            logger.warning(error_msg)
            return [error_msg]


class QuestionValidatorFactory:
    """Factory for creating appropriate validators"""

    @staticmethod
    def get_validator(question_type: str) -> QuestionValidator:
        """Get appropriate validator based on question type"""
        validators = {
            "text_completion": TextCompletionValidator(),
            "sentence_equivalence": SentenceEquivalenceValidator(),
            "reading_comprehension": ReadingComprehensionValidator(),
            "reading_comprehension_single": ReadingComprehensionValidator(),
            "reading_comprehension_multiple": ReadingComprehensionValidator(),
            "reading_comprehension_highlight": ReadingComprehensionValidator(),
        }
        return validators.get(question_type, QuestionValidator())

    @staticmethod
    def validate_question(question_data: Dict[str, Any]) -> List[str]:
        """Validate question using appropriate validator"""
        question_type = question_data.get("question_type", "")
        validator = QuestionValidatorFactory.get_validator(question_type)
        return validator.validate(question_data)


def create_question_instance(question_data: Dict[str, Any]):
    """Create appropriate question instance from data"""
    question_type = question_data.get("question_type", "")

    # Map question types to model classes
    type_map = {
        "text_completion": TextCompletionQuestion,
        "text_completion_single": TextCompletionQuestion,
        "text_completion_double": TextCompletionQuestion,
        "text_completion_triple": TextCompletionQuestion,
        "sentence_equivalence": SentenceEquivalenceQuestion,
        "reading_comprehension": ReadingComprehensionQuestion,
        "reading_comprehension_single": ReadingComprehensionQuestion,
        "reading_comprehension_multiple": ReadingComprehensionQuestion,
        "reading_comprehension_highlight": ReadingComprehensionQuestion,
    }

    model_class = type_map.get(question_type)
    if not model_class:
        raise ValueError(f"Unknown question type: {question_type}")

    return model_class(**question_data)
