"""
Reading Comprehension Question Generation Task

Generates RC passages with associated questions.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from core.models.enums import PromptQuestionType
from ..config import QUESTION_CONFIG
from ..services import GeneratorService, MongoDBService


async def generate_reading_comprehension(
    generator: GeneratorService, db: MongoDBService, running_flag: callable
) -> List[Dict]:
    """
    Generate and store reading comprehension passages and questions

    Args:
        generator: Question generator service
        db: MongoDB service
        running_flag: Server running check

    Returns:
        Generated questions list
    """
    logger = logging.getLogger("VerbalForgeServer.Tasks.RC")
    config = QUESTION_CONFIG["reading_comprehension"]

    questions_per_passage = config["questions_per_passage"]
    total_passages = config["easy"] + config["medium"] + config["hard"]
    total_questions = total_passages * questions_per_passage

    logger.info(
        f"Starting RC generation: {total_passages} passages " f"({total_questions} questions total)"
    )

    all_questions = []
    difficulties = [
        ("easy", config["easy"]),
        ("medium", config["medium"]),
        ("hard", config["hard"]),
    ]

    for difficulty, passage_count in difficulties:
        if not running_flag():
            logger.info("Shutdown signal received, stopping")
            break

        if passage_count == 0:
            continue

        for passage_num in range(passage_count):
            if not running_flag():
                break

            logger.info(
                f"Generating passage {passage_num + 1}/{passage_count} "
                f"({difficulty}) with {questions_per_passage} questions..."
            )

            max_retries = 2
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt + 1}/{max_retries} after 2s delay")
                        await asyncio.sleep(2)

                    result = await asyncio.wait_for(
                        generator.generate(
                            count=questions_per_passage,
                            question_type=PromptQuestionType.READING_COMPREHENSION,
                            difficulty=difficulty,
                        ),
                        timeout=300.0,  # 5 minutes for passages
                    )

                    if not running_flag():
                        break

                    if isinstance(result, dict) and "questions" in result:
                        rc_items = result["questions"]
                        batch_id = result.get("metadata", {}).get(
                            "batch_id",
                            f"reading_comprehension_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        )

                        # Each RC item has structure: {"passage": {...}, "questions": [...]}
                        for rc_item in rc_items:
                            if (
                                isinstance(rc_item, dict)
                                and "passage" in rc_item
                                and "questions" in rc_item
                            ):
                                questions = rc_item["questions"]

                                # Store questions first to see which ones succeed
                                q_stored = db.store_questions(questions, batch_id)

                                # Only store passage if at least 1 question was stored
                                if q_stored > 0:
                                    # Get IDs of successfully stored questions
                                    # (MongoDB returns the inserted documents with _id)
                                    stored_question_ids = []
                                    for question in questions:
                                        if "_id" in question:
                                            stored_question_ids.append(str(question["_id"]))

                                    # Store passage with only successfully stored question IDs
                                    passage_data = {
                                        "passage": rc_item["passage"]["text"],
                                        "source": rc_item["passage"].get("source", "Unknown"),
                                        "title": rc_item["passage"].get(
                                            "title", "Reading Comprehension"
                                        ),
                                        "difficulty_level": difficulty,
                                        "type": "reading_comprehension_passage",
                                        "question_ids": stored_question_ids,
                                    }

                                    passage_id = db.store_single_passage(passage_data, batch_id)

                                    # Update stored questions with passage_id
                                    if passage_id:
                                        db.update_questions_with_passage_id(
                                            stored_question_ids, passage_id
                                        )

                                    all_questions.extend(questions[:q_stored])
                                    logger.info(f"Stored {q_stored} questions and 1 passage")
                                else:
                                    logger.warning(
                                        "No valid questions for passage, skipping passage storage"
                                    )
                    else:
                        logger.warning(f"Unexpected result format: {type(result)}")

                    break  # Success, exit retry loop

                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Timeout on attempt {attempt + 1}/{max_retries}, retrying..."
                        )
                    else:
                        logger.error(
                            f"Timeout generating {difficulty} passage {passage_num + 1} after {max_retries} attempts"
                        )
                except asyncio.CancelledError:
                    logger.info("Task cancelled")
                    raise
                except Exception as e:
                    logger.error(f"Error generating {difficulty} passage {passage_num + 1}: {e}")
                    break  # Don't retry on non-timeout errors

    logger.info(f"RC generation complete: {len(all_questions)} questions")
    return all_questions
