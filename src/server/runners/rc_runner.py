"""
Reading Comprehension Runner

Picks 2 topics and generates 1 medium + 1 hard Reading Comprehension passage.
Uses real articles from various sources through the modular article_sources package.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Callable

from core.models.enums import PromptQuestionType
from ..config import QUESTION_CONFIG, RUNNER_INTERVALS
from ..services import GeneratorService, MongoDBService
from .stateful_worker import StatefulWorker

try:
    from ..article_sources import ArticleSourceFactory
    ARTICLE_FETCHER_AVAILABLE = True
except ImportError:
    ARTICLE_FETCHER_AVAILABLE = False


class RCRunner(StatefulWorker):
    """Reading Comprehension passage generation runner"""

    def __init__(self, generator: GeneratorService, db: MongoDBService):
        self.generator = generator
        runner_id = "rc_runner"
        runner_name = "RC Runner"
        interval_hours = RUNNER_INTERVALS.get(runner_id, 3.0)
        
        # Initialize parent with consistent logger name
        super().__init__(
            db=db,
            runner_id=runner_id,
            runner_type="reading_comprehension",
            interval_hours=interval_hours,
            logger_name="VerbalForgeServer.Runners.RC"
        )

    async def execute_generation(self, running_flag: Callable[[], bool]) -> List[Dict]:
        """
        Generate and store reading comprehension passages and questions

        Args:
            running_flag: Server running check

        Returns:
            Generated questions list
        """
        config = QUESTION_CONFIG["reading_comprehension"]
        questions_per_passage = config["questions_per_passage"]
        total_passages = config["medium"] + config["hard"]
        total_questions = total_passages * questions_per_passage

        # Get list of available article sources
        available_sources = []
        if ARTICLE_FETCHER_AVAILABLE:
            try:
                available_sources = ArticleSourceFactory.get_available_sources()
                self.logger.info(f"Article sources available: {', '.join(available_sources)}")
                
                # Log used articles statistics
                total_used = self.db.get_used_articles_count()
                self.logger.info(f"Total articles used so far: {total_used}")
                for source in available_sources:
                    source_used = self.db.get_used_articles_count(source)
                    self.logger.info(f"  - {source}: {source_used} articles used")
            except Exception as e:
                self.logger.warning(f"Failed to get available sources: {e}. Using generic passages.")
        else:
            self.logger.warning("Article fetcher not available. Using generic passages.")

        self.logger.info(
            f"Starting RC Runner: {total_passages} passages ({total_questions} questions total)"
        )

        all_questions = []
        difficulties = [
            ("medium", config["medium"]),
            ("hard", config["hard"]),
        ]

        for difficulty, passage_count in difficulties:
            if not running_flag():
                self.logger.info("Shutdown signal received, stopping")
                break

            if passage_count == 0:
                continue

            for passage_num in range(passage_count):
                if not running_flag():
                    break

                self.logger.info(
                    f"Generating passage {passage_num + 1}/{passage_count} "
                    f"({difficulty}) with {questions_per_passage} questions..."
                )

                # Fetch article for this passage (weighted random selection favoring scientific sources)
                topic_instruction = None
                article_metadata = {}
                
                if available_sources:
                    try:
                        # Try to fetch an unused article (retry up to 5 times)
                        max_article_retries = 5
                        article = None
                        
                        for article_attempt in range(max_article_retries):
                            # Use weighted random selection (scientific sources get higher weight)
                            source_name = ArticleSourceFactory.get_random_source()
                            article_source = ArticleSourceFactory.get_source(source_name) if source_name else None
                            
                            if article_source:
                                articles = article_source.fetch_articles(count=1)
                                if articles:
                                    candidate_article = articles[0]
                                    
                                    # Check if this article has been used before
                                    if not self.db.is_article_used(candidate_article['url']):
                                        article = candidate_article
                                        self.logger.info(f"Found unused article: '{article['title']}'")
                                        break
                                    else:
                                        self.logger.info(f"Article already used, fetching another (attempt {article_attempt + 1}/{max_article_retries})")
                        
                        if article:
                            topic_instruction = article_source.format_for_rc_generation(article)
                            article_metadata = {
                                'source_url': article['url'],
                                'source_title': article['title'],
                                'source_section': article['section'],
                                'source_attribution': article['source']
                            }
                            self.logger.info(f"Using article: '{article['title']}' from {article['source']} ({article['section']})")
                        else:
                            self.logger.warning(f"Could not find unused article after {max_article_retries} attempts, using generic passage")
                    except Exception as e:
                        self.logger.warning(f"Error fetching article: {e}. Using generic passage.")

                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            self.logger.info(f"Retry attempt {attempt + 1}/{max_retries} after 2s delay")
                            await asyncio.sleep(2)

                        result = await asyncio.wait_for(
                            self.generator.generate(
                                count=questions_per_passage,
                                question_type=PromptQuestionType.READING_COMPREHENSION,
                                difficulty=difficulty,
                                topic=topic_instruction  # Pass article context
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
                                    q_stored = self.db.store_questions(questions, batch_id)

                                    # Only store passage if at least 1 question was stored
                                    if q_stored > 0:
                                        # Get IDs of successfully stored questions
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
                                        
                                        # Add article metadata if available
                                        if article_metadata:
                                            passage_data["metadata"].update({
                                                "source_url": article_metadata.get('source_url'),
                                                "source_title": article_metadata.get('source_title'),
                                                "source_section": article_metadata.get('source_section'),
                                                "source_attribution": article_metadata.get('source_attribution')
                                            })
                                            self.logger.info(f"Stored passage with source: {article_metadata.get('source_url')}")

                                        passage_id = self.db.store_single_passage(passage_data, batch_id)

                                        # Update stored questions with passage_id
                                        if passage_id:
                                            self.db.update_questions_with_passage_id(
                                                stored_question_ids, passage_id
                                            )
                                            
                                            # Mark article as used if we successfully stored the passage
                                            if article_metadata:
                                                self.db.mark_article_used(
                                                    article_metadata.get('source_url'),
                                                    article_metadata.get('source_title'),
                                                    article_metadata.get('source_attribution')
                                                )

                                        all_questions.extend(questions[:q_stored])
                                        self.logger.info(f"Stored {q_stored} questions and 1 passage")
                                    else:
                                        self.logger.warning(
                                            "No valid questions for passage, skipping passage storage"
                                        )
                        else:
                            self.logger.warning(f"Unexpected result format: {type(result)}")

                        break  # Success, exit retry loop

                    except asyncio.TimeoutError:
                        if attempt < max_retries - 1:
                            self.logger.warning(
                                f"Timeout on attempt {attempt + 1}/{max_retries}, retrying..."
                            )
                        else:
                            self.logger.error(
                                f"Timeout generating {difficulty} passage {passage_num + 1} after {max_retries} attempts"
                            )
                    except asyncio.CancelledError:
                        self.logger.info("Task cancelled")
                        raise
                    except Exception as e:
                        self.logger.error(f"Error generating {difficulty} passage {passage_num + 1}: {e}")
                        break  # Don't retry on non-timeout errors

        self.logger.info(f"RC Runner complete: {len(all_questions)} questions")
        return all_questions
