"""
Text Completion Question Generation Task

Handles generation of all text completion questions across difficulty levels.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from core.models.enums import PromptQuestionType
from ..config import QUESTION_CONFIG
from ..services import GeneratorService, MongoDBService


async def generate_text_completion(
    generator: GeneratorService, db: MongoDBService, running_flag: callable
) -> List[Dict]:
    """
    Generate and store text completion questions

    Args:
        generator: Question generator service
        db: MongoDB service for storage
        running_flag: Callable that returns True if server should keep running

    Returns:
        List of generated questions
    """
    logger = logging.getLogger("VerbalForgeServer.Tasks.TC")
    config = QUESTION_CONFIG["text_completion"]

    total = sum(config.values())
    logger.info(f"Starting TC generation: {total} questions total")

    all_questions = []
    difficulties = [
        ("easy", config["easy"]),
        ("medium", config["medium"]),
        ("hard", config["hard"]),
    ]

    for difficulty, count in difficulties:
        if not running_flag():
            logger.info("Shutdown signal received, stopping")
            break

        if count == 0:
            continue

        logger.info(f"Generating {count} {difficulty} questions...")

        max_retries = 2
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} after 2s delay")
                    await asyncio.sleep(180)

                # Generate questions with timeout
                result = await asyncio.wait_for(
                    generator.generate(
                        count=count,
                        question_type=PromptQuestionType.TEXT_COMPLETION,
                        difficulty=difficulty,
                    ),
                    timeout=180.0,
                )

                if not running_flag():
                    break

                # Extract and store questions
                questions = generator.extract_questions(result)
                if questions:
                    batch_id = f"text_completion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    stored = db.store_questions(questions, batch_id)

                    if stored > 0:
                        all_questions.extend(questions)
                        logger.info(f"Stored {stored} {difficulty} questions")
                break  # Success, exit retry loop

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}, retrying...")
                else:
                    logger.error(
                        f"Timeout generating {difficulty} questions after {max_retries} attempts"
                    )
            except asyncio.CancelledError:
                logger.info("Task cancelled")
                raise
            except Exception as e:
                logger.error(f"Error generating {difficulty} questions: {e}")
                break  # Don't retry on non-timeout errors

    logger.info(f"TC generation complete: {len(all_questions)} questions")
    return all_questions
