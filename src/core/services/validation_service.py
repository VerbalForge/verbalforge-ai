"""Validation service for orchestrating question validation"""

import logging
import time
from typing import List, Dict, Any
from ..models.questions import QuestionBatch
from ..layers.validation_layer import ValidationLayer

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating and filtering question batches"""

    def __init__(self):
        """Initialize validation service"""
        logger.info("Initializing ValidationService")
        self.validation_layer = ValidationLayer()
        logger.info("ValidationLayer initialized successfully")

    def validate_and_filter_batch(self, batch: QuestionBatch) -> QuestionBatch:
        """Validate a batch and return only valid questions

        Args:
            batch: QuestionBatch to validate

        Returns:
            QuestionBatch with only valid questions
        """
        start_time = time.time()
        logger.info(
            f"Starting validation for batch '{batch.batch_id}' with {len(batch.questions)} questions"
        )

        validation_result = self.validation_layer.validate_batch(batch)
        valid_count = validation_result["valid_items"]
        total_count = validation_result["total_questions"]
        quality_score = validation_result.get("overall_quality_score", 0)

        elapsed_time = time.time() - start_time

        logger.info(
            f"Validation completed in {elapsed_time:.2f}s: {valid_count}/{total_count} questions valid ({valid_count/total_count*100:.1f}%)"
        )
        logger.info(f"Overall quality score: {quality_score:.1%}")

        if valid_count < total_count:
            logger.warning(f"Filtered out {total_count - valid_count} invalid questions")

            # Log details about filtered questions
            for i, result in enumerate(validation_result.get("validation_results", [])):
                if not result["is_valid"]:
                    logger.warning(
                        f"Question {i+1} failed validation: {len(result['errors'])} errors"
                    )
                    for error in result["errors"][:3]:  # Show first 3 errors
                        logger.info(f"  • {error}")
                    if len(result["errors"]) > 3:
                        logger.info(f"  • ... and {len(result['errors']) - 3} more errors")

        filtered_batch = self.validation_layer.filter_valid_questions(batch)
        logger.info(
            f"Returning filtered batch with {len(filtered_batch.questions)} high-quality questions"
        )

        return filtered_batch

    def validate_questions_from_dict(self, questions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a list of question dictionaries

        Args:
            questions_data: List of question dictionaries

        Returns:
            Validation results
        """
        logger.info(f"Validating {len(questions_data)} questions from dictionary data")
        return self.validation_layer.validate_questions_from_dict(questions_data)

    def generate_quality_report(self, questions_data: List[Dict[str, Any]]) -> str:
        """Generate a quality report for given questions

        Args:
            questions_data: List of question dictionaries

        Returns:
            Formatted quality report
        """
        logger.info(f"Generating quality report for {len(questions_data)} questions")
        return self.validation_layer.generate_quality_report(questions_data)
