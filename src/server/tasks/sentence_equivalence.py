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

    # Fetch target vocabulary words ONCE for the entire generation session
    target_words = db.fetch_target_words(count=5)
    
    # Build vocabulary-focused topic instruction
    topic_instruction = None
    word_map = {}  # Map word_id to word data for later updates
    
    if target_words:
        word_details = []
        for word_data in target_words:
            word_map[word_data["_id"]] = word_data
            word = word_data.get("word", "")
            
            # Build detailed word info
            word_info = f"**{word}**"
            
            # Add definitions
            meanings = word_data.get("meanings", [])
            if meanings:
                definitions = [m.get("definition", "") for m in meanings[:2]]  # Limit to 2
                word_info += f"\n  - Definitions: {'; '.join(definitions)}"
                
            word_details.append(word_info)
        
        topic_instruction = (
            f"**VOCABULARY FOCUS**: Generate Sentence Equivalence questions that test these specific GRE vocabulary words. "
            f"Use these words and their synonyms as the correct answer choices, ensuring two synonymous words "
            f"from the list create equivalent sentence meanings:\n\n" + 
            "\n\n".join(word_details) +
            "\n\nCreate sentences where the target vocabulary fits naturally in sophisticated academic contexts."
        )
        
        logger.info(f"Using {len(target_words)} target words for all difficulty levels")

    def get_words_in_question(question: Dict, target_words_set: set) -> List[str]:
        """Extract which target words actually appear in this question's choices"""
        words_found = []
        choices = question.get("choices", [])
        for choice in choices:
            option_text = choice.get("option", "").lower()
            # Check if any target word appears in this option
            for word in target_words_set:
                if word.lower() in option_text:
                    words_found.append(word)
        return list(set(words_found))  # Remove duplicates

    all_questions = []
    word_to_questions = {}  # Map: word -> [question_ids]
    conversation_history = []  # Maintain conversation across difficulty levels
    target_words_set = set(target_words)  # For faster lookup
    
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

                # Always use conversation-based generation to maintain context
                logger.info(f"Generating with conversation context ({len(conversation_history)} messages)")
                result, conversation_history = await asyncio.wait_for(
                    generator.generate_with_conversation(
                        count=count,
                        question_type=PromptQuestionType.SENTENCE_EQUIVALENCE,
                        difficulty=difficulty,
                        conversation_history=conversation_history,
                        topic=topic_instruction
                    ),
                    timeout=180.0,
                )

                if not running_flag():
                    break

                # Extract and store questions immediately
                questions = generator.extract_questions(result)
                if questions:
                    batch_id = f"sentence_equivalence_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{difficulty}"
                    stored = db.store_questions(questions, batch_id)

                    if stored > 0:
                        all_questions.extend(questions)
                        
                        # Map questions to words that actually appear in their choices
                        for question in questions:
                            q_id = question.get("_id")
                            if q_id:
                                words_in_q = get_words_in_question(question, target_words_set)
                                for word in words_in_q:
                                    if word not in word_to_questions:
                                        word_to_questions[word] = []
                                    word_to_questions[word].append(q_id)
                        
                        logger.info(f"Stored {stored} {difficulty} questions immediately to MongoDB")
                        
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

    # Update only words that actually appear in questions
    if word_to_questions:
        for word, question_ids in word_to_questions.items():
            # Find the word_id from word_map
            word_id = None
            for wid, word_text in word_map.items():
                if word_text.lower() == word.lower():
                    word_id = wid
                    break
            
            if word_id:
                db.update_word_questions(word_id, question_ids)
                logger.info(f"Updated word '{word}' with {len(question_ids)} question(s)")
        
        logger.info(f"Updated {len(word_to_questions)} words with questions (out of {len(target_words)} target words)")
    else:
        logger.warning("No word-to-question mappings found")

    logger.info(f"SE generation complete: {len(all_questions)} questions generated for {len(target_words)} vocabulary words")
    return all_questions
