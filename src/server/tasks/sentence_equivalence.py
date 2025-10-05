"""
Sentence Equivalence Question Generation Task

Handles generation of sentence equivalence questions.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from core.models.enums import PromptQuestionType
from ..config import QUESTION_CONFIG
from ..services import GeneratorService, MongoDBService


async def generate_sentence_equivalence(
    generator: GeneratorService, db: MongoDBService, running_flag: callable
) -> List[Dict]:
    """
    Generate and store sentence equivalence questions

    Args:
        generator: Question generator service
        db: MongoDB service
        running_flag: Function returning True while server runs

    Returns:
        Generated questions list
    """
    logger = logging.getLogger("VerbalForgeServer.Tasks.SE")
    config = QUESTION_CONFIG["sentence_equivalence"]

    total = sum(config.values())
    logger.info(f"Starting SE generation: {total} questions total")

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
                    await asyncio.sleep(2)

                result = await asyncio.wait_for(
                    generator.generate(
                        count=count,
                        question_type=PromptQuestionType.SENTENCE_EQUIVALENCE,
                        difficulty=difficulty,
                    ),
                    timeout=180.0,
                )

                if not running_flag():
                    break

                questions = generator.extract_questions(result)
                if questions:
                    batch_id = f"sentence_equivalence_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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

    logger.info(f"SE generation complete: {len(all_questions)} questions")
    return all_questions
