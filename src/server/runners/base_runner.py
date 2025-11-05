"""
Base Runner Classes

Provides common functionality for word-based question generation runners.
"""

import asyncio
import logging
from abc import abstractmethod
from datetime import datetime
from typing import Dict, List, Callable

from core.models.enums import PromptQuestionType
from ..config import QUESTION_CONFIG, RUNNER_INTERVALS
from ..services import GeneratorService, MongoDBService
from .stateful_worker import StatefulWorker


class WordBasedRunner(StatefulWorker):
    """
    Base class for TC and SE runners that use vocabulary words.
    
    Combines StatefulWorker with word-based question generation logic.
    """

    def __init__(
        self, 
        generator: GeneratorService, 
        db: MongoDBService, 
        runner_name: str,
        runner_id: str
    ):
        self.generator = generator
        self.runner_name = runner_name
        
        # Initialize stateful worker
        interval_hours = RUNNER_INTERVALS.get(runner_id, 2.0)
        super().__init__(
            db=db,
            runner_id=runner_id,
            runner_type=self.get_config_key(),
            interval_hours=interval_hours,
            logger_name=f"VerbalForgeServer.Runners.{runner_name}"
        )

    # Abstract methods for subclasses to implement

    @abstractmethod
    def get_question_type(self) -> PromptQuestionType:
        """Return the question type for this runner"""
        pass

    @abstractmethod
    def get_config_key(self) -> str:
        """Return the config key (e.g., 'text_completion', 'sentence_equivalence')"""
        pass

    @abstractmethod
    def build_topic_instruction(self, word_details: List[str]) -> str:
        """Build question-type-specific topic instruction"""
        pass

    # Helper methods

    def get_batch_id_prefix(self) -> str:
        """Return the batch ID prefix for this question type"""
        return self.get_config_key()

    def extract_words_in_question(self, question: Dict, target_words_set: set) -> List[str]:
        """Extract which target words actually appear in this question's choices"""
        words_found = []
        choices = question.get("choices", [])
        
        for choice in choices:
            option_text = choice.get("option", "").lower()
            for word in target_words_set:
                if word.lower() in option_text:
                    words_found.append(word)
                    
        return list(set(words_found))  # Remove duplicates

    # Main generation logic (implements StatefulWorker.execute_generation)

    async def execute_generation(self, running_flag: Callable[[], bool]) -> List[Dict]:
        """
        Execute word-based question generation.
        Implements StatefulWorker.execute_generation()
        
        Args:
            running_flag: Callable that returns True while worker should keep running
            
        Returns:
            List of generated questions
        """
        config = QUESTION_CONFIG[self.get_config_key()]
        total = config["medium"] + config["hard"]
        
        self.logger.info(f"Starting {self.runner_name} generation: {total} questions total")

        # Fetch smart target vocabulary words
        target_words = self.db.fetch_words(count=2)
        if not target_words:
            self.logger.error("No target words available")
            return []

        # Prepare generation context
        word_map, word_details, target_words_set = self._prepare_word_context(target_words)
        topic_instruction = self.build_topic_instruction(word_details)
        
        self.logger.info(
            f"Using {len(target_words)} target words: "
            f"{[w.get('word', '') for w in target_words]}"
        )

        # Generate questions across difficulty levels
        all_questions, word_to_questions = await self._generate_all_difficulties(
            config=config,
            topic_instruction=topic_instruction,
            target_words_set=target_words_set,
            running_flag=running_flag
        )

        # Update word mappings in database
        self._update_word_mappings(word_to_questions, word_map, len(target_words))

        self.logger.info(
            f"{self.runner_name} generation complete: "
            f"{len(all_questions)} questions for {len(target_words)} words"
        )
        return all_questions

    def _prepare_word_context(self, target_words: List[Dict]) -> tuple:
        """
        Prepare word context for generation
        
        Returns:
            (word_map, word_details, target_words_set)
        """
        word_map = {}
        word_details = []
        
        for word_data in target_words:
            word_map[word_data["_id"]] = word_data
            word = word_data.get("word", "")
            
            # Build detailed word info
            word_info = f"**{word}**"
            meanings = word_data.get("meanings", [])
            
            if meanings:
                definitions = [m.get("definition", "") for m in meanings[:2]]
                word_info += f"\n  - Definitions: {'; '.join(definitions)}"
                
            word_details.append(word_info)
        
        target_words_set = set(w.get("word", "") for w in target_words)
        
        return word_map, word_details, target_words_set

    async def _generate_all_difficulties(
        self,
        config: Dict,
        topic_instruction: str,
        target_words_set: set,
        running_flag: Callable[[], bool]
    ) -> tuple:
        """
        Generate questions across all difficulty levels
        
        Returns:
            (all_questions, word_to_questions)
        """
        all_questions = []
        word_to_questions = {}
        conversation_history = []
        
        difficulties = [
            ("medium", config["medium"]),
            ("hard", config["hard"]),
        ]

        for difficulty, count in difficulties:
            if not running_flag() or count == 0:
                break

            self.logger.info(f"Generating {count} {difficulty} questions...")

            questions = await self._generate_questions_with_retry(
                count=count,
                difficulty=difficulty,
                topic_instruction=topic_instruction,
                conversation_history=conversation_history,
                running_flag=running_flag
            )

            if questions:
                all_questions.extend(questions)
                self._map_questions_to_words(
                    questions, target_words_set, word_to_questions
                )

        return all_questions, word_to_questions

    def _map_questions_to_words(
        self,
        questions: List[Dict],
        target_words_set: set,
        word_to_questions: Dict[str, List[str]]
    ) -> None:
        """Map questions to words that appear in their choices"""
        for question in questions:
            q_id = question.get("_id")
            if not q_id:
                continue
                
            words_in_q = self.extract_words_in_question(question, target_words_set)
            for word in words_in_q:
                if word not in word_to_questions:
                    word_to_questions[word] = []
                word_to_questions[word].append(q_id)

    async def _generate_questions_with_retry(
        self,
        count: int,
        difficulty: str,
        topic_instruction: str,
        conversation_history: List,
        running_flag: Callable[[], bool],
        max_retries: int = 2,
        retry_delay: int = 180
    ) -> List[Dict]:
        """
        Generate questions with retry logic
        
        Returns:
            List of generated questions, or empty list on failure
        """
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay")
                    await asyncio.sleep(retry_delay)

                # Use conversation-based generation to maintain context
                self.logger.info(f"Generating with conversation context ({len(conversation_history)} messages)")
                result, updated_history = await asyncio.wait_for(
                    self.generator.generate_with_conversation(
                        count=count,
                        question_type=self.get_question_type(),
                        difficulty=difficulty,
                        conversation_history=conversation_history,
                        topic=topic_instruction
                    ),
                    timeout=180.0,
                )

                # Update conversation history for next difficulty
                conversation_history.clear()
                conversation_history.extend(updated_history)

                if not running_flag():
                    break

                # Extract and store questions immediately
                questions = self.generator.extract_questions(result)
                if questions:
                    batch_id = f"{self.get_batch_id_prefix()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{difficulty}"
                    stored = self.db.store_questions(questions, batch_id)

                    if stored > 0:
                        self.logger.info(f"Stored {stored} {difficulty} questions immediately to MongoDB")
                        return questions
                        
                # If no questions, fall through to retry
                self.logger.warning(f"No questions extracted from result")

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}, retrying...")
                else:
                    self.logger.error(
                        f"Timeout generating {difficulty} questions after {max_retries} attempts"
                    )
            except asyncio.CancelledError:
                self.logger.info("Task cancelled")
                raise
            except Exception as e:
                self.logger.error(f"Error generating {difficulty} questions: {e}")
                break  # Don't retry on non-timeout errors

        return []

    def _update_word_mappings(
        self,
        word_to_questions: Dict[str, List[str]],
        word_map: Dict,
        total_words: int
    ) -> None:
        """Update word documents with question IDs"""
        if word_to_questions:
            for word, question_ids in word_to_questions.items():
                # Find the word_id from word_map
                word_id = None
                for wid, word_data in word_map.items():
                    if word_data.get("word", "").lower() == word.lower():
                        word_id = wid
                        break
                
                if word_id:
                    self.db.update_word_questions(word_id, question_ids)
                    self.logger.info(f"Updated word '{word}' with {len(question_ids)} question(s)")
            
            self.logger.info(
                f"Updated {len(word_to_questions)} words with questions (out of {total_words} target words)"
            )
        else:
            self.logger.warning("No word-to-question mappings found")
