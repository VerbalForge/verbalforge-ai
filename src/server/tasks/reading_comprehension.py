"""
Reading Comprehension Question Generation Task

Generates RC passages with associated questions using real articles from various sources.
Supports multiple article sources through the modular article_sources package.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.models.enums import PromptQuestionType
from ..config import QUESTION_CONFIG
from ..services import GeneratorService, MongoDBService

try:
    from ..article_sources import ArticleSourceFactory
    ARTICLE_FETCHER_AVAILABLE = True
except ImportError:
    ARTICLE_FETCHER_AVAILABLE = False


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

    # Get list of available article sources
    available_sources = []
    if ARTICLE_FETCHER_AVAILABLE:
        try:
            available_sources = ArticleSourceFactory.get_available_sources()
            logger.info(f"Article sources available: {', '.join(available_sources)}")
        except Exception as e:
            logger.warning(f"Failed to get available sources: {e}. Using generic passages.")
    else:
        logger.warning("Article fetcher not available. Using generic passages.")

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

            # Fetch article for this passage (weighted random selection favoring scientific sources)
            topic_instruction = None
            article_metadata = {}
            
            if available_sources:
                try:
                    # Use weighted random selection (scientific sources get higher weight)
                    source_name = ArticleSourceFactory.get_random_source()
                    article_source = ArticleSourceFactory.get_source(source_name) if source_name else None
                    
                    if article_source:
                        articles = article_source.fetch_articles(count=1)
                        if articles:
                            article = articles[0]
                            topic_instruction = article_source.format_for_rc_generation(article)
                            article_metadata = {
                                'source_url': article['url'],
                                'source_title': article['title'],
                                'source_section': article['section'],
                                'source_attribution': article['source']
                            }
                            logger.info(f"Using article: '{article['title']}' from {article['source']} ({article['section']})")
                        else:
                            logger.warning(f"No article available, using generic passage")
                except Exception as e:
                    logger.warning(f"Error fetching article: {e}. Using generic passage.")

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
                            topic=topic_instruction  # Pass Atlantic article context
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
                                    timestamp = datetime.now(timezone.utc)
                                    
                                    passage_data = {
                                        "passage": rc_item["passage"]["text"],
                                        "source": rc_item["passage"].get("source", "Unknown"),
                                        "title": rc_item["passage"].get(
                                            "title", "Reading Comprehension"
                                        ),
                                        "difficulty_level": difficulty,
                                        "type": "reading_comprehension_passage",
                                        "question_ids": stored_question_ids,
                                        "metadata": {
                                            "created_at": timestamp.isoformat(),
                                            "batch_id": batch_id,
                                        }
                                    }
                                    
                                    # Add Atlantic article metadata if available
                                    if article_metadata:
                                        passage_data["metadata"].update({
                                            "source_url": article_metadata.get('source_url'),
                                            "source_title": article_metadata.get('source_title'),
                                            "source_section": article_metadata.get('source_section'),
                                            "source_attribution": "The Atlantic"
                                        })
                                        logger.info(f"Stored passage with Atlantic source: {article_metadata.get('source_url')}")

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
