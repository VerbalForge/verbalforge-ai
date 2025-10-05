"""Main orchestrator for GRE question generation"""

import logging
import time
from typing import Optional, Dict, Any
from .models.enums import PromptQuestionType
from .models.requests import GenerationRequest
from .services.llm_service import LLMService
from .services.validation_service import ValidationService
from .services.formatting_service import FormattingService
from .layers.generation_layer import GenerationLayer
from .utils.providers_config import validate_api_keys

logger = logging.getLogger(__name__)


class QuestionOrchestrator:
    """Main orchestrator for GRE question generation workflow"""

    def __init__(self, llm_provider: Optional[str] = None):
        """Initialize the question orchestrator

        Args:
            llm_provider: LLM provider to use ('openai' or 'azure_openai')
        """
        logger.info(
            f"Initializing QuestionOrchestrator with provider: {llm_provider or 'auto-detect'}"
        )

        # Validate API keys
        logger.info("Validating API keys")
        if not validate_api_keys():
            logger.error("No valid API keys found")
            raise ValueError(
                "No valid API keys found. Please configure OPENAI_API_KEY or AZURE_OPENAI_API_KEY"
            )

        logger.info("API keys validated successfully")

        # Initialize services and layers
        logger.info("Initializing services and layers")
        self.llm_service = LLMService(provider=llm_provider)
        self.generation_layer = GenerationLayer(self.llm_service)
        self.validation_service = ValidationService()
        self.formatting_service = FormattingService()

        logger.info(
            f"QuestionOrchestrator initialization completed with {self.llm_service.provider_type} provider"
        )

    async def generate_questions(
        self,
        count: int = 5,
        question_type: PromptQuestionType = PromptQuestionType.TEXT_COMPLETION,
        difficulty_level: str = "medium",
        topic: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        validate_output: bool = True,
    ) -> Dict[str, Any]:
        """Generate GRE questions

        Args:
            count: Number of questions to generate (1-10)
            question_type: Type of questions to generate
            difficulty_level: Difficulty level ('easy', 'medium', 'hard')
            topic: Optional topic to focus on
            custom_instructions: Additional instructions for generation
            validate_output: Whether to validate and filter questions

        Returns:
            Dictionary with questions in the specified JSON format
        """
        start_time = time.time()

        logger.info(
            f"Starting generation of {count} {question_type.value} questions at {difficulty_level} level"
        )
        if topic:
            logger.info(f"Topic focus: {topic}")
        if custom_instructions:
            logger.info(f"Custom instructions provided: {len(custom_instructions)} characters")
        logger.info(f"Output validation: {'enabled' if validate_output else 'disabled'}")

        # Create generation request
        request = GenerationRequest(
            count=count,
            question_type=question_type,
            difficulty_level=difficulty_level,
            topic=topic,
            custom_instructions=custom_instructions,
        )

        try:
            # Generate questions
            logger.info("Requesting question generation from generation layer")
            batch = await self.generation_layer.generate_questions(request)
            generation_time = time.time() - start_time

            logger.info(
                f"Initial generation completed in {generation_time:.2f}s - {len(batch.questions)} questions generated"
            )

            # Validate if requested
            if validate_output:
                logger.info("Starting output validation and filtering")
                validation_start = time.time()
                batch = self.validation_service.validate_and_filter_batch(batch)
                validation_time = time.time() - validation_start
                logger.info(
                    f"Validation completed in {validation_time:.2f}s - {len(batch.questions)} questions remaining"
                )
            else:
                logger.info("Skipping validation as requested")

            # Convert to output format
            logger.info("Formatting output to JSON")
            output = self.formatting_service.format_to_json(batch)

            # Log usage stats
            usage_stats = self.generation_layer.get_usage_stats()
            total_time = time.time() - start_time

            logger.info(f"Generation completed successfully in {total_time:.2f}s")
            logger.info(
                f"Token usage: {usage_stats['total_tokens']} tokens, "
                f"estimated cost: ${usage_stats['estimated_total_cost']:.6f}"
            )

            # Log output info
            if isinstance(output, dict):
                if "questions" in output:
                    logger.info(
                        f"Final output contains {len(output['questions'])} questions with metadata"
                    )
                elif "metadata" in output and "total_questions" in output["metadata"]:
                    logger.info(
                        f"Final output contains {output['metadata']['total_questions']} questions with metadata"
                    )
                else:
                    logger.info("Final output formatted successfully")
            else:
                logger.info("Final output formatted successfully")

            return output

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Question generation failed after {elapsed_time:.2f}s: {e}")
            logger.info(
                f"Failed request details - count: {count}, type: {question_type.value}, "
                f"difficulty: {difficulty_level}"
            )
            raise

    def get_supported_question_types(self) -> list[str]:
        """Get list of supported question types

        Returns:
            List of supported question type values
        """
        logger.info("Retrieving supported question types")
        question_types = [qt.value for qt in PromptQuestionType]
        logger.info(f"Available question types: {question_types}")
        return question_types

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics

        Returns:
            Dictionary with usage statistics
        """
        logger.info("Retrieving usage statistics from generation layer")
        stats = self.generation_layer.get_usage_stats()
        logger.info(
            f"Current usage stats - calls: {stats.get('total_requests', 0)}, "
            f"tokens: {stats.get('total_tokens', 0)}, cost: ${stats.get('estimated_total_cost', 0):.6f}"
        )
        return stats

    def validate_questions(self, questions_data: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a list of questions without generating new ones

        Args:
            questions_data: List of question dictionaries

        Returns:
            Validation results
        """
        logger.info(f"Validating {len(questions_data)} existing questions")

        try:
            result = self.validation_service.validate_questions_from_dict(questions_data)
            logger.info(
                f"Validation completed - {result['valid_items']}/{result['total_questions']} questions valid"
            )
            return result
        except Exception as e:
            logger.error(f"Question validation failed: {e}")
            raise

    def generate_quality_report(self, questions_data: list[Dict[str, Any]]) -> str:
        """Generate a quality report for given questions

        Args:
            questions_data: List of question dictionaries

        Returns:
            Formatted quality report
        """
        logger.info(f"Generating quality report for {len(questions_data)} questions")

        try:
            report = self.validation_service.generate_quality_report(questions_data)
            logger.info(f"Quality report generated successfully - {len(report)} characters")
            return report
        except Exception as e:
            logger.error(f"Quality report generation failed: {e}")
            raise
