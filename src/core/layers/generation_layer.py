"""Generation layer for creating GRE questions"""

import json
import time
import logging
from typing import Optional, Dict, Any
from ..models.requests import GenerationRequest
from ..models.questions import QuestionBatch, create_reading_comprehension_from_response
from ..models.enums import PromptQuestionType
from ..services.llm_service import LLMService
from ..services.prompt_service import PromptService
from ..validators.question_validators import create_question_instance
from ..utils.question_agent_utils import extract_json_payload, normalize_difficulty

logger = logging.getLogger(__name__)


class GenerationLayer:
    """Layer specialized in generating GRE verbal questions"""

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize the question generation layer

        Args:
            llm_service: LLM service to use. If None, creates default service.
        """
        logger.info("Initializing GenerationLayer")

        if llm_service:
            logger.info(f"Using provided LLM service with provider: {llm_service.provider_type}")
            self.llm_service = llm_service
        else:
            logger.info("Creating default LLM service")
            self.llm_service = LLMService()

        self.prompt_service = PromptService()
        logger.info("GenerationLayer initialized successfully")

    async def generate_questions(self, request: GenerationRequest) -> QuestionBatch:
        """Generate a batch of questions based on the request

        Args:
            request: Generation request with parameters

        Returns:
            QuestionBatch with generated questions
        """
        start_time = time.time()
        logger.info(
            f"Starting question generation for {request.count} {request.question_type.value} questions, "
            f"Settings - Difficulty: {request.difficulty_level}, Topic: {request.topic or 'General'}"
        )

        # Get appropriate prompts
        system_prompt, generation_prompt = self.prompt_service.get_prompts(
            question_type=request.question_type,
            count=request.count,
            difficulty=request.difficulty_level.value,
            topic=request.topic,
        )

        # Add custom instructions if provided
        if request.custom_instructions:
            generation_prompt = self.prompt_service.add_custom_instructions(
                generation_prompt, request.custom_instructions
            )
            logger.info(f"Added custom instructions: {request.custom_instructions}")

        # Generate questions using LLM
        try:
            llm_start = time.time()
            logger.info(
                f"Calling LLM API for question generation using provider: {self.llm_service.provider_type}"
            )

            response = await self.llm_service.generate_response(
                system_prompt=system_prompt, user_prompt=generation_prompt
            )

            llm_time = time.time() - llm_start
            logger.info(
                f"LLM API call completed in {llm_time:.2f}s. Response Metadata - "
                f"Tokens: {response.tokens_used}, Cost: ${response.cost_estimate:.4f}. "
                f"Response Content Length: {len(response.content)} characters"
            )

            # Parse and process response
            questions = self._parse_and_create_questions(response.content, request)

            # Create batch
            batch = self._create_batch(questions, request, response, start_time)

            total_time = time.time() - start_time
            logger.info(f"Question generation completed successfully in {total_time:.2f}s")
            logger.info(
                f"Generated batch '{batch.batch_id}' with {len(questions)} high-quality questions"
            )

            return batch

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Question generation failed after {elapsed_time:.2f}s: {e}")
            logger.info(
                f"Generation request details: count={request.count}, "
                f"type={request.question_type.value}, difficulty={request.difficulty_level}"
            )
            raise

    async def generate_questions_with_conversation(
        self, request: GenerationRequest, conversation_history: list
    ) -> tuple[QuestionBatch, list]:
        """Generate questions continuing an existing conversation
        
        Args:
            request: Generation request with parameters
            conversation_history: List of message dicts from previous interactions
                                 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, 
                                  {"role": "assistant", "content": "..."}, ...]
        
        Returns:
            Tuple of (QuestionBatch, updated_conversation_history)
        """
        start_time = time.time()
        logger.info(
            f"Continuing conversation for {request.count} {request.question_type.value} questions, "
            f"Settings - Difficulty: {request.difficulty_level}, Conversation length: {len(conversation_history)} messages"
        )

        # Get appropriate prompts
        system_prompt, generation_prompt = self.prompt_service.get_prompts(
            question_type=request.question_type,
            count=request.count,
            difficulty=request.difficulty_level.value,
            topic=request.topic,
        )

        # Add custom instructions if provided
        if request.custom_instructions:
            generation_prompt = self.prompt_service.add_custom_instructions(
                generation_prompt, request.custom_instructions
            )

        # Build conversation messages
        # If conversation is empty, add system prompt
        if not conversation_history:
            conversation_history = [{"role": "system", "content": system_prompt}]
        
        # Add the new user request
        conversation_history.append({"role": "user", "content": generation_prompt})

        # Generate questions using LLM with conversation history
        try:
            llm_start = time.time()
            logger.info(
                f"Calling LLM API with conversation history ({len(conversation_history)} messages)"
            )

            response = await self.llm_service.generate_with_history(conversation_history)

            llm_time = time.time() - llm_start
            logger.info(
                f"LLM API call completed in {llm_time:.2f}s. Response Metadata - "
                f"Tokens: {response.tokens_used}, Cost: ${response.cost_estimate:.4f}"
            )

            # Add assistant response to conversation
            conversation_history.append({"role": "assistant", "content": response.content})

            # Parse and process response
            questions = self._parse_and_create_questions(response.content, request)

            # Create batch
            batch = self._create_batch(questions, request, response, start_time)

            total_time = time.time() - start_time
            logger.info(f"Question generation with conversation completed in {total_time:.2f}s")
            logger.info(
                f"Generated batch '{batch.batch_id}' with {len(questions)} questions, "
                f"Conversation now has {len(conversation_history)} messages"
            )

            return batch, conversation_history

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Conversation-based generation failed after {elapsed_time:.2f}s: {e}")
            raise

    def _parse_and_create_questions(self, content: str, request: GenerationRequest) -> list:
        """Parse LLM response and create question objects

        Args:
            content: Raw LLM response content
            request: Original generation request

        Returns:
            List of question objects
        """
        try:
            cleaned_content = extract_json_payload(content)
            response_data = json.loads(cleaned_content)
            logger.info("JSON parsing completed")

            # Handle different response formats based on question type
            if request.question_type == PromptQuestionType.READING_COMPREHENSION:
                # Reading Comprehension format: {"passage": {...}, "questions": [...]}
                if (
                    not isinstance(response_data, dict)
                    or "questions" not in response_data
                    or "passage" not in response_data
                ):
                    raise ValueError("Invalid Reading Comprehension response format")

                passage_data = response_data.get("passage", {})
                questions_data = response_data["questions"]
                logger.info(f"Parsed RC format with passage and {len(questions_data)} questions")
            else:
                # Text Completion and Sentence Equivalence format: direct array of questions
                questions_data = response_data
                passage_data = None
                logger.info(f"Parsed question array format with {len(questions_data)} questions")

            # Normalize questions
            normalized_questions = self._normalize_questions(questions_data)

            # Create question objects
            questions = self._create_question_objects(
                normalized_questions, passage_data, request.question_type
            )

            logger.info(f"Successfully created {len(questions)} question objects")
            return questions

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed response content (first 500 chars): {content[:500] if content else 'None'}"
            )
            raise Exception(f"LLM returned invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Response processing failed: {e}")
            raise Exception(f"Failed to process LLM response: {str(e)}")

    def _normalize_questions(self, questions_data: list) -> list:
        normalized = []
        for q in questions_data:
            q = dict(q)

            # Ensure all choices have the 'blank' field
            if "choices" in q and isinstance(q["choices"], list):
                for choice in q["choices"]:
                    if isinstance(choice, dict) and "blank" not in choice:
                        choice["blank"] = 1  # Default to 1 for single blank questions

            # Normalize difficulty
            if "difficulty_level" in q:
                q["difficulty_level"] = normalize_difficulty(q.get("difficulty_level"))

            # Ensure question_type is present/normalized
            if not q.get("question_type"):
                # Infer from blanks if missing
                blanks = str(q.get("question_text", "")).count("_____")
                q["question_type"] = (
                    "text_completion_single"
                    if blanks == 1
                    else (
                        "text_completion_double"
                        if blanks == 2
                        else (
                            "text_completion_triple"
                            if blanks == 3
                            else q.get("question_type", "text_completion")
                        )
                    )
                )

            normalized.append(q)

        logger.info(f"Normalized {len(normalized)} question entries")
        return normalized

    def _create_question_objects(
        self, questions_data: list, passage_data: Optional[dict], question_type: PromptQuestionType
    ) -> list:
        """Create question objects from normalized data

        Args:
            questions_data: Normalized question data
            passage_data: Optional passage data for RC questions
            question_type: Type of questions being created

        Returns:
            List of question objects
        """
        questions = []
        skipped_questions = 0

        # Handle Reading Comprehension as a single object
        if question_type == PromptQuestionType.READING_COMPREHENSION:
            try:
                logger.info("Processing Reading Comprehension as a single object")

                if passage_data and isinstance(passage_data, dict):
                    passage_text = passage_data.get("passage") or passage_data.get("text", "")
                    source = passage_data.get("source", "Generated passage")
                    title = passage_data.get("title", "Reading Comprehension Passage")

                    logger.info(
                        f"Creating ReadingComprehension with passage length: {len(passage_text)} chars, title: {title}"
                    )

                    # Create ReadingComprehension object with all questions
                    rc_object = create_reading_comprehension_from_response(
                        passage_text=passage_text,
                        source=source,
                        title=title,
                        questions_data=questions_data,
                    )

                    questions.append(rc_object)
                    logger.info(
                        f"Created ReadingComprehension object with {len(rc_object.questions)} questions, difficulty: {rc_object.difficulty_level}, type: {rc_object.type}"
                    )
                else:
                    logger.error("Reading Comprehension requires passage data but none found")
                    raise ValueError("Reading Comprehension requires passage data in response")

            except Exception as e:
                logger.error(f"Failed to process Reading Comprehension: {e}")
                skipped_questions += len(questions_data)

        else:
            # Handle Text Completion and Sentence Equivalence questions individually
            for i, q_data in enumerate(questions_data, 1):
                try:
                    logger.info(f"Processing question {i}/{len(questions_data)}")
                    question = create_question_instance(q_data)
                    logger.info(
                        f"Successfully created and validated question object for question {i}"
                    )
                    questions.append(question)
                    logger.info(f"Question {i} passed validation and added to batch")
                except Exception as e:
                    skipped_questions += 1
                    logger.error(f"Failed to create question {i} from data: {e}")
                    logger.info(f"Failed question data: {q_data}")
                    continue

        if skipped_questions > 0:
            logger.warning(f"Skipped {skipped_questions} invalid questions during creation")

        return questions

    def _create_batch(
        self, questions: list, request: GenerationRequest, response, start_time: float
    ) -> QuestionBatch:
        """Create question batch with metadata

        Args:
            questions: List of question objects
            request: Original generation request
            response: LLM response object
            start_time: Generation start timestamp

        Returns:
            QuestionBatch with metadata
        """
        batch = QuestionBatch(
            questions=questions,
            batch_id=f"batch_{request.question_type.value}_{len(questions)}",
            question_type=request.question_type.value,
            generation_metadata={
                "llm_provider": self.llm_service.provider_type,
                "model": self.llm_service._get_model_name(),
                "tokens_used": response.tokens_used,
                "cost_estimate": response.cost_estimate,
                "generation_time": response.response_time,
                "total_processing_time": time.time() - start_time,
                "questions_requested": request.count,
                "questions_generated": len(questions),
                "questions_valid": len(questions),
                "questions_skipped": 0,
            },
        )

        logger.info(f"Question batch '{batch.batch_id}' created successfully")
        return batch

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics from the LLM service

        Returns:
            Dictionary with usage statistics
        """
        logger.info("Retrieving usage statistics from LLM service")
        return self.llm_service.get_usage_stats()
