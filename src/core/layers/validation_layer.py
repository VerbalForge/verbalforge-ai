"""Validation layer for ensuring question quality"""

import logging
from typing import List, Dict, Any, Union
from ..models.questions import QuestionBatch, ReadingComprehension
from ..validators.question_validators import QuestionValidator

logger = logging.getLogger(__name__)


class ValidationLayer:
    """Layer for validating and improving question quality"""

    def __init__(self):
        """Initialize the validation layer"""
        self.validator = QuestionValidator()

    def validate_question(
        self, question: Union[Dict[str, Any], ReadingComprehension]
    ) -> Dict[str, Any]:
        """Validate a single question or ReadingComprehension object

        Args:
            question: Question or ReadingComprehension object to validate

        Returns:
            Validation result with errors and suggestions
        """
        if isinstance(question, ReadingComprehension):
            # Validate ReadingComprehension object
            errors = []

            # Validate the passage
            if not question.passage or not question.passage.strip():
                errors.append("Reading passage text is missing or empty")
            elif len(question.passage.strip()) < 50:
                errors.append("Reading passage is too short (minimum 50 characters)")

            # Validate that there are questions
            if not question.questions:
                errors.append("ReadingComprehension object has no questions")
            elif len(question.questions) < 1:
                errors.append("ReadingComprehension object must have at least 1 question")

            # Validate each individual question within the ReadingComprehension
            question_errors = []
            for i, q in enumerate(question.questions):
                q_dict = {
                    "question_text": q.question_text,
                    "choices": [
                        {
                            "option": c.option,
                            "blank": c.blank,
                            "is_correct": c.is_correct,
                            "reasoning": c.reasoning,
                        }
                        for c in q.choices
                    ],
                    "difficulty_level": q.difficulty_level,
                    "topic": q.topic,
                    "question_type": q.question_type,
                }
                q_errors = self.validator.validate_complete_question(q_dict)
                if q_errors:
                    question_errors.extend([f"Question {i+1}: {error}" for error in q_errors])

            errors.extend(question_errors)

            return {
                "question_id": getattr(question, "id", "unknown"),
                "question_type": "ReadingComprehension",
                "is_valid": len(errors) == 0,
                "errors": errors,
                "suggestions": self._generate_suggestions(errors),
                "sub_questions_count": len(question.questions) if question.questions else 0,
            }
        else:
            if isinstance(question, dict):
                errors = self.validator.validate_complete_question(question)
                question_id = question.get("id", "unknown")
                question_type = question.get("question_type", "Unknown")
            else:
                q_dict = {
                    "question_text": question.question_text,
                    "choices": [
                        {
                            "option": c.option,
                            "blank": c.blank,
                            "is_correct": c.is_correct,
                            "reasoning": c.reasoning,
                        }
                        for c in question.choices
                    ],
                    "difficulty_level": question.difficulty_level,
                    "topic": question.topic,
                    "question_type": question.question_type,
                }
                errors = self.validator.validate_complete_question(q_dict)
                question_id = getattr(question, "id", "unknown")
                question_type = question.question_type

            return {
                "question_id": question_id,
                "question_type": question_type,
                "is_valid": len(errors) == 0,
                "errors": errors,
                "suggestions": self._generate_suggestions(errors),
            }

    def validate_batch(self, batch: QuestionBatch) -> Dict[str, Any]:
        """Validate a batch of questions

        Args:
            batch: Batch to validate

        Returns:
            Batch validation results
        """
        logger.info(f"Validating batch {batch.batch_id} with {len(batch.questions)} items")

        results = []
        total_errors = 0
        total_sub_questions = 0

        for i, question in enumerate(batch.questions):
            validation_result = self.validate_question(question)
            validation_result["question_index"] = i
            results.append(validation_result)

            if not validation_result["is_valid"]:
                total_errors += len(validation_result["errors"])

            # Count sub-questions for ReadingComprehension objects
            if isinstance(question, ReadingComprehension):
                total_sub_questions += len(question.questions) if question.questions else 0
            else:
                total_sub_questions += 1

        valid_questions = sum(1 for r in results if r["is_valid"])

        return {
            "batch_id": batch.batch_id,
            "total_items": len(batch.questions),
            "total_questions": total_sub_questions,
            "valid_items": valid_questions,
            "invalid_items": len(batch.questions) - valid_questions,
            "total_errors": total_errors,
            "validation_results": results,
            "overall_quality_score": self._calculate_quality_score(results),
        }

    def filter_valid_questions(self, batch: QuestionBatch) -> QuestionBatch:
        """Filter out invalid questions from a batch

        Args:
            batch: Original batch

        Returns:
            New batch with only valid questions
        """
        valid_questions = []

        for question in batch.questions:
            validation_result = self.validate_question(question)
            if validation_result["is_valid"]:
                valid_questions.append(question)
            else:
                logger.warning(f"Removing invalid question: {validation_result['errors']}")

        # Create new batch with valid questions
        filtered_batch = QuestionBatch(
            questions=valid_questions,
            batch_id=f"{batch.batch_id}_filtered",
            question_type=batch.question_type,
            generation_metadata=batch.generation_metadata.copy(),
        )

        # Add filtering metadata
        filtered_batch.generation_metadata.update(
            {
                "filtered": True,
                "original_count": len(batch.questions),
                "filtered_count": len(valid_questions),
                "removed_count": len(batch.questions) - len(valid_questions),
            }
        )

        logger.info(
            f"Filtered batch: {len(valid_questions)}/{len(batch.questions)} questions valid"
        )

        return filtered_batch

    def validate_questions_from_dict(self, questions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate questions from dictionary data

        Args:
            questions_data: List of question dictionaries

        Returns:
            Validation results
        """
        results = []
        for i, q_data in enumerate(questions_data):
            result = self.validate_question(q_data)
            result["question_index"] = i
            results.append(result)

        valid_count = sum(1 for r in results if r["is_valid"])

        return {
            "total_questions": len(questions_data),
            "valid_items": valid_count,
            "invalid_items": len(questions_data) - valid_count,
            "validation_results": results,
            "overall_quality_score": self._calculate_quality_score(results),
        }

    def generate_quality_report(self, questions_data: List[Dict[str, Any]]) -> str:
        """Generate quality report from question data

        Args:
            questions_data: List of question dictionaries

        Returns:
            Formatted quality report string
        """
        validation_result = self.validate_questions_from_dict(questions_data)

        report = f"""
=== Question Quality Report ===
Total Questions: {validation_result['total_questions']}
Valid Questions: {validation_result['valid_items']}
Invalid Questions: {validation_result['invalid_items']}
Quality Score: {validation_result['overall_quality_score']:.1%}
"""

        if validation_result["invalid_items"] > 0:
            report += "\n=== Issues Found ===\n"
            for result in validation_result["validation_results"]:
                if not result["is_valid"]:
                    report += f"Question {result['question_index'] + 1}:\n"
                    for error in result["errors"]:
                        report += f"  - {error}\n"
                    report += "\n"

        return report

    def _generate_suggestions(self, errors: List[str]) -> List[str]:
        """Generate improvement suggestions based on errors (DRY)"""
        suggestion_map = {
            "too short": "Increase content length and add more detail",
            "too similar": "Make answer options more distinct from each other",
            "generic": "Provide more specific and detailed explanations",
            "correct answer": "Ensure correct answer matches one of the provided options",
            "justification": "Provide justifications for all answer options",
            "punctuation": "Fix punctuation and formatting issues",
            "passage": "Improve the reading passage with more substantial content",
            "readingcomprehension": "Ensure ReadingComprehension has valid passage and questions",
            "has no": "Add questions to the ReadingComprehension object",
        }

        suggestions = set()
        for error in errors:
            error_lower = error.lower()
            for keyword, suggestion in suggestion_map.items():
                if keyword in error_lower:
                    suggestions.add(suggestion)
                    break
            else:
                suggestions.add("Review and improve question structure")

        return list(suggestions)

    def _calculate_quality_score(self, validation_results: List[Dict[str, Any]]) -> float:
        """Calculate overall quality score for a batch (0-1 scale)"""
        if not validation_results:
            return 0.0

        # Base score from validity
        valid_count = sum(1 for r in validation_results if r["is_valid"])
        base_score = valid_count / len(validation_results)

        # Penalty for errors in invalid questions
        total_errors = sum(len(r["errors"]) for r in validation_results if not r["is_valid"])
        error_penalty = min(total_errors * 0.1, 0.3)  # Max 30% penalty

        final_score = max(0.0, base_score - error_penalty)
        return round(final_score, 3)
