"""Formatting service for converting question batches to output format"""

import logging
from typing import Dict, Any
from ..models.questions import QuestionBatch, ReadingComprehension

logger = logging.getLogger(__name__)


class FormattingService:
    """Service for formatting question batches into output JSON"""

    def format_to_json(self, batch: QuestionBatch) -> Dict[str, Any]:
        """Format question batch to JSON output

        Args:
            batch: QuestionBatch to format

        Returns:
            Dictionary with formatted output
        """
        logger.info(f"Formatting batch '{batch.batch_id}' with {len(batch.questions)} items")

        # Format questions based on type
        formatted_questions = []
        total_questions = 0

        for item in batch.questions:
            if isinstance(item, ReadingComprehension):
                # Reading comprehension: passage with multiple questions
                formatted_rc = {
                    "passage": {
                        "text": item.passage,
                        "source": item.source,
                    },
                    "questions": [self._format_question(q) for q in item.questions],
                }
                formatted_questions.append(formatted_rc)
                total_questions += len(item.questions)
            else:
                # Individual question (TC or SE)
                formatted_questions.append(self._format_question(item))
                total_questions += 1

        output = {
            "questions": formatted_questions,
            "metadata": {
                "batch_id": batch.batch_id,
                "question_type": batch.question_type,
                "total_questions": total_questions,
                **batch.generation_metadata,
            },
        }

        logger.info(f"Formatted {total_questions} questions successfully")
        return output

    def _format_question(self, question) -> Dict[str, Any]:
        """Format individual question

        Args:
            question: Question object to format

        Returns:
            Dictionary with formatted question
        """
        return {
            "question_text": question.question_text,
            "choices": [
                {
                    "option": choice.option,
                    "blank": choice.blank,
                    "is_correct": choice.is_correct,
                    "reasoning": choice.reasoning,
                }
                for choice in question.choices
            ],
            "difficulty_level": question.difficulty_level,
            "topic": question.topic,
            "question_type": question.question_type,
        }
