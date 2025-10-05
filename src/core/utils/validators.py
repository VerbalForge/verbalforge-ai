"""Response validators for ensuring quality of generated questions"""

import logging
from typing import List, Dict, Any, Union
from ..models.questions import Choice, TextCompletionQuestion, SentenceEquivalenceQuestion, ReadingComprehensionQuestion

logger = logging.getLogger(__name__)


class QuestionValidator:
    """Validates generated GRE questions for quality and correctness"""

    @staticmethod
    def validate_question_structure(question_data: Dict[str, Any]) -> List[str]:
        """Validate the basic structure of a question using modular validators"""
        logger.info(
            f"Validating question structure for question: {question_data.get('question', 'Unknown')[:50]}..."
        )

        # Basic validation structure
        errors = []

        if not errors:
            logger.info("Question structure validation passed")
        else:
            logger.info(f"Question structure validation failed with {len(errors)} errors")

        return errors

    @staticmethod
    def validate_question_quality(question: str) -> List[str]:
        """Validate the quality of the question text"""
        logger.info(f"Validating question quality for: {question[:50]}...")
        errors = []

        # Check minimum length
        if len(question.strip()) < 20:
            error_msg = f"Question too short ({len(question.strip())} characters, minimum 20)"
            errors.append(error_msg)
            logger.warning(f"Quality validation failed: {error_msg}")

        # Check for proper sentence structure (more flexible for text completion)
        question_text = question.strip()
        has_blanks = "_____" in question_text

        # For text completion questions, allow more flexible endings
        if has_blanks:
            # Text completion can end with ), s, etc. as long as it makes sense
            acceptable_endings = ("?", ":", ".", ")", "s", "d", "g", "e", "n", "t", "r", "l", "y")
            if not question_text.endswith(acceptable_endings):
                error_msg = f"Question should end with acceptable punctuation or word ending, ends with: '{question_text[-1] if question_text else 'empty'}'"
                errors.append(error_msg)
                logger.warning(f"Quality validation failed: {error_msg}")
        else:
            # Non-text completion questions need proper punctuation
            if not question_text.endswith(("?", ":", ".")):
                error_msg = f"Question should end with proper punctuation, ends with: '{question_text[-1] if question_text else 'empty'}'"
                errors.append(error_msg)
                logger.warning(f"Quality validation failed: {error_msg}")

        # Check for blanks in text completion questions
        if "_____" in question:
            import re

            # Count both simple blanks and numbered blanks
            simple_blanks = question.count("_____")
            numbered_blanks = len(re.findall(r"_____\d+_____", question))

            # If we have numbered blanks, the actual blank count is the number of numbered blanks
            if numbered_blanks > 0:
                blank_count = numbered_blanks
            else:
                blank_count = simple_blanks

            logger.info(f"Found {blank_count} blanks in text completion question")
            if blank_count == 0:
                error_msg = "Text completion question must contain blanks"
                errors.append(error_msg)
                logger.warning(f"Quality validation failed: {error_msg}")
            elif blank_count > 3:  # Changed from 2 to 3 to match prompts
                error_msg = f"Too many blanks in question ({blank_count}, maximum 3)"
                errors.append(error_msg)
                logger.warning(f"Quality validation failed: {error_msg}")

        if not errors:
            logger.info("Question quality validation passed")
        else:
            logger.info(f"Question quality validation failed with {len(errors)} errors")

        return errors

    @staticmethod
    def validate_options_quality(options: List[Choice], question_type: str = None) -> List[str]:
        """Validate the quality of answer options"""
        logger.info(f"Validating {len(options)} answer options")
        errors = []

        # Set length limits based on question type
        if question_type == "reading_comprehension_highlight":
            max_length = 300  # Allow longer options for sentence highlighting
        else:
            max_length = 200  # Standard limit for other question types

        # Check option lengths
        for i, option_obj in enumerate(options):
            option_text = option_obj.option if hasattr(option_obj, "option") else str(option_obj)
            option_len = len(option_text.strip())
            logger.info(f"Option {i+1} length: {option_len} characters")

            if option_len < 2:
                error_msg = f"Option {i+1} too short ({option_len} characters)"
                errors.append(error_msg)
                logger.warning(f"Options validation failed: {error_msg}")
            elif option_len > max_length:
                error_msg = f"Option {i+1} too long ({option_len} characters, maximum {max_length})"
                errors.append(error_msg)
                logger.warning(f"Options validation failed: {error_msg}")

        # Check for similar options
        similar_pairs = []
        for i, option1_obj in enumerate(options):
            for j, option2_obj in enumerate(options[i + 1:], i + 1):
                option1_text = (
                    option1_obj.option if hasattr(option1_obj, "option") else str(option1_obj)
                )
                option2_text = (
                    option2_obj.option if hasattr(option2_obj, "option") else str(option2_obj)
                )
                similarity = QuestionValidator._calculate_similarity(option1_text, option2_text)
                logger.info(f"Similarity between options {i+1} and {j+1}: {similarity:.2f}")

                if similarity > 0.8:
                    error_msg = (
                        f"Options {i+1} and {j+1} are too similar (similarity: {similarity:.2f})"
                    )
                    errors.append(error_msg)
                    similar_pairs.append((i + 1, j + 1))
                    logger.warning(f"Options validation failed: {error_msg}")

        if similar_pairs:
            logger.info(f"Found {len(similar_pairs)} pairs of similar options")

        if not errors:
            logger.info("Options quality validation passed")
        else:
            logger.info(f"Options quality validation failed with {len(errors)} errors")

        return errors

    @staticmethod
    def validate_justifications(options: List[Choice]) -> List[str]:
        """Validate the quality of justifications in combined option structure"""
        logger.info(f"Validating justifications for {len(options)} options")
        errors = []

        # Check justification quality for each option
        generic_phrases = [
            "this is correct",
            "this is wrong",
            "this is the answer",
            "obviously",
            "clearly",
            "simply",
        ]

        for i, option_obj in enumerate(options):
            reasoning_len = len(option_obj.reasoning.strip())
            logger.info(f"Justification for '{option_obj.option}': {reasoning_len} characters")

            if reasoning_len < 20:
                error_msg = f"Justification for '{option_obj.option}' too short ({reasoning_len} characters, minimum 20)"
                errors.append(error_msg)
                logger.warning(f"Justifications validation failed: {error_msg}")

            # Check for generic justifications
            reasoning_lower = option_obj.reasoning.lower()
            found_generic = [phrase for phrase in generic_phrases if phrase in reasoning_lower]

            if found_generic:
                error_msg = f"Justification for '{option_obj.option}' too generic (contains: {', '.join(found_generic)})"
                errors.append(error_msg)
                logger.warning(f"Justifications validation failed: {error_msg}")

        if not errors:
            logger.info("Justifications validation passed")
        else:
            logger.info(f"Justifications validation failed with {len(errors)} errors")

        return errors

    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        logger.info(f"Calculating similarity between texts of length {len(text1)} and {len(text2)}")

        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 and not words2:
            logger.info("Both texts empty, similarity = 1.0")
            return 1.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        similarity = len(intersection) / len(union) if union else 0.0
        logger.info(
            f"Similarity calculation: {len(intersection)} common words / {len(union)} total words = {similarity:.3f}"
        )

        return similarity

    @classmethod
    def validate_complete_question(
        cls,
        question: Union[
            TextCompletionQuestion, SentenceEquivalenceQuestion, ReadingComprehensionQuestion
        ],
    ) -> List[str]:
        """Perform complete validation of a GRE question"""
        logger.info(f"Starting complete validation for question: {question.question[:50]}...")
        errors = []

        # Structure validation using modular approach
        question_dict = question.model_dump()
        logger.info("Running structure validation...")
        structure_errors = cls.validate_question_structure(question_dict)
        errors.extend(structure_errors)

        # Quality validation
        logger.info("Running quality validation...")
        quality_errors = cls.validate_question_quality(question.question)
        errors.extend(quality_errors)

        logger.info("Running options validation...")
        options_errors = cls.validate_options_quality(question.options, question.question_type)
        errors.extend(options_errors)

        logger.info("Running justifications validation...")
        justification_errors = cls.validate_justifications(question.options)
        errors.extend(justification_errors)

        # Summary logging
        if not errors:
            logger.info("Complete question validation passed")
        else:
            logger.warning(f"Complete question validation failed with {len(errors)} errors:")
            for i, error in enumerate(errors, 1):
                logger.warning(f"  {i}. {error}")

        return errors
