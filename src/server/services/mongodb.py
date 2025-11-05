"""
MongoDB Service

Handles all database operations including connections, storage, and retrieval.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
except ImportError:
    raise ImportError("PyMongo not installed. Run: pip install pymongo")


class MongoDBService:
    """Manages MongoDB connections and operations"""

    def __init__(self, uri: str, database_name: str):
        self.uri = uri
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.questions = None
        self.passages = None
        self.words = None
        self.runner_states = None
        self.used_articles = None
        self.logger = logging.getLogger("VerbalForgeServer.MongoDB")

    def connect(self) -> None:
        """Establish MongoDB connection"""
        try:
            self.logger.info(f"Connecting to MongoDB: {self.uri}")
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)

            # Verify connection works
            self.client.admin.command("ping")
            self.logger.info("Connection verified")

            # Setup database and collections
            self.db = self.client[self.database_name]
            self.questions = self.db.questions
            self.passages = self.db.passages
            self.words = self.db.words
            self.runner_states = self.db.runner_states
            self.used_articles = self.db.used_articles
            
            # Create indexes for better performance
            self._create_indexes()

            self.logger.info(f"Using database: {self.database_name}")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.error(f"Connection failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Setup error: {e}")
            raise

    def _create_indexes(self) -> None:
        """Create database indexes for better performance"""
        try:
            # Index for used_articles collection (unique URL)
            if self.used_articles is not None:
                self.used_articles.create_index("url", unique=True)
                self.logger.info("Created index on used_articles.url")
        except Exception as e:
            self.logger.warning(f"Failed to create indexes: {e}")

    def disconnect(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.logger.info("Connection closed")

    def store_questions(self, questions: List[Dict[str, Any]], batch_id: str) -> int:

        if not questions:
            self.logger.warning("No questions to store")
            return 0

        stored = 0
        timestamp = datetime.now(timezone.utc)

        for question in questions:
            # Generate UUID for _id
            question["_id"] = str(uuid.uuid4())
            question["metadata"] = {
                "created_at": timestamp.isoformat(),
                "updated_at": timestamp.isoformat(),
                "published_at": None,
                "batch_id": batch_id,
            }

            try:
                result = self.questions.insert_one(question)
                if result.inserted_id:
                    stored += 1
            except Exception as e:
                self.logger.error(f"Failed to store question: {e}")

        self.logger.info(f"Stored {stored}/{len(questions)} questions")
        return stored

    def update_questions_with_passage_id(self, question_ids: List[str], passage_id: str) -> int:

        if not question_ids or not passage_id:
            return 0

        try:
            result = self.questions.update_many(
                {"_id": {"$in": question_ids}}, {"$set": {"passage_id": passage_id}}
            )

            self.logger.info(f"Updated {result.modified_count} questions with passage_id")
            return result.modified_count
        except Exception as e:
            self.logger.error(f"Failed to update questions with passage_id: {e}")
            return 0

    def store_single_passage(self, passage_data: Dict[str, Any], batch_id: str) -> str:
        """Store a single passage and return its ID

        Args:
            passage_data: Passage data dict with passage, source, title, question_ids, etc.
            batch_id: Batch identifier

        Returns:
            String passage ID from MongoDB
        """
        if not passage_data or self.passages is None:
            return None

        timestamp = datetime.now(timezone.utc)

        # Start with base metadata
        base_metadata = {
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
            "published_at": None,  # Set to null for new content
            "batch_id": batch_id,
        }
        
        # Merge with any metadata from passage_data (e.g., Atlantic source info)
        if "metadata" in passage_data:
            base_metadata.update(passage_data["metadata"])

        doc = {
            "_id": str(uuid.uuid4()),
            "passage": passage_data.get("passage", ""),
            "source": passage_data.get("source", "Unknown"),
            "title": passage_data.get("title", "Reading Comprehension"),
            "difficulty": passage_data.get("difficulty_level", "medium"),
            "type": passage_data.get("type", "reading_comprehension_passage"),
            "question_ids": passage_data.get("question_ids", []),
            "metadata": base_metadata,
        }

        try:
            result = self.passages.insert_one(doc)
            if result.inserted_id:
                return doc["_id"]
        except Exception as e:
            self.logger.error(f"Failed to store passage: {e}")

        return None

    def store_passages(self, rc_data: Dict[str, Any], batch_id: str) -> List[tuple]:
        """
        Store reading comprehension passages with question references

        Args:
            rc_data: Reading comprehension data with passage and questions
            batch_id: Batch identifier

        Returns:
            List of tuples (passage_id, question_ids) for linking questions to passages
        """
        if not rc_data or self.passages is None:
            return []

        # Extract RC nodes from various input formats
        rc_nodes = []
        if isinstance(rc_data, dict):
            if "reading_comprehensions" in rc_data:
                rc_nodes.extend(rc_data["reading_comprehensions"])
            elif "passage" in rc_data and "questions" in rc_data:
                rc_nodes.append(rc_data)
        elif isinstance(rc_data, list):
            rc_nodes.extend([rc for rc in rc_data if "passage" in rc])

        if not rc_nodes:
            return []

        passage_mappings = []
        timestamp = datetime.now(timezone.utc)

        for rc in rc_nodes:
            # Collect question IDs from this passage
            question_ids = []
            for q in rc.get("questions", []):
                qid = q.get("_id") or q.get("id")
                if qid:
                    question_ids.append(qid)

            # Build passage document
            doc = {
                "_id": str(uuid.uuid4()),
                "passage": rc.get("passage", ""),
                "source": rc.get("source", ""),
                "question_ids": question_ids,
                "metadata": {
                    "created_at": timestamp.isoformat(),
                    "updated_at": timestamp.isoformat(),
                    "published_at": timestamp.isoformat(),
                    "batch_id": batch_id,
                },
            }

            try:
                result = self.passages.insert_one(doc)
                if result.inserted_id:
                    # Store mapping of passage_id to question_ids for linking
                    passage_mappings.append((doc["_id"], question_ids))
            except Exception as e:
                self.logger.error(f"Failed to store passage: {e}")

        self.logger.info(f"Stored {len(passage_mappings)} passage(s)")
        return passage_mappings

    def fetch_words(self, count: int = 2) -> List[Dict[str, Any]]:
        """
        Intelligently fetch words for question generation based on:
        1. Least questioned (by question_ids.length)
        2. Most sourced (by number of sources)
        3. Random selection from best candidates
        
        Args:
            count: Number of words to fetch (default: 2)
            
        Returns:
            List of word documents with their full schema
        """
        if self.words is None:
            self.logger.warning("Words collection not initialized")
            return []
            
        try:
            # Aggregate pipeline to score and rank words
            pipeline = [
                # Add computed fields for scoring
                {
                    "$addFields": {
                        "question_count": {
                            "$cond": {
                                "if": {"$isArray": "$question_ids"},
                                "then": {"$size": "$question_ids"},
                                "else": 0
                            }
                        },
                        "source_count": {
                            "$cond": {
                                "if": {"$isArray": "$sources"},
                                "then": {"$size": "$sources"},
                                "else": 0
                            }
                        }
                    }
                },
                # Sort by: least questioned (ascending), then most sourced (descending)
                {
                    "$sort": {
                        "question_count": 1,  # Fewer questions first
                        "source_count": -1,   # More sources first (tie-breaker)
                    }
                },
                # Get top candidates (10x the requested count for randomization pool)
                {"$limit": count * 10},
                # Randomly sample from the best candidates
                {"$sample": {"size": count}}
            ]
            
            words = list(self.words.aggregate(pipeline))
            
            if words:
                avg_q_count = sum(w.get('question_count', 0) for w in words) / len(words)
                avg_s_count = sum(w.get('source_count', 0) for w in words) / len(words)
                self.logger.info(
                    f"Fetched {len(words)} words (smart selection): "
                    f"avg {avg_q_count:.1f} questions, avg {avg_s_count:.1f} sources"
                )
            else:
                self.logger.warning("No words found with smart selection")
            
            return words
            
        except Exception as e:
            self.logger.error(f"Failed to fetch words: {e}")
            return []
    
    def update_word_questions(self, word_id: str, question_ids: List[str]) -> bool:
        """
        Add question IDs to a word's question_ids array
        
        Args:
            word_id: The _id of the word document
            question_ids: List of question IDs to add
            
        Returns:
            True if successful, False otherwise
        """
        if self.words is None or not word_id or not question_ids:
            return False
            
        try:
            # Use $addToSet to avoid duplicates
            result = self.words.update_one(
                {"_id": word_id},
                {"$addToSet": {"question_ids": {"$each": question_ids}}}
            )
            
            if result.modified_count > 0:
                self.logger.info(f"Updated word '{word_id}' with {len(question_ids)} question IDs")
                return True
            else:
                self.logger.debug(f"Word '{word_id}' already had these question IDs")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update word '{word_id}': {e}")
            return False

    # Runner State Management
    
    def load_runner_state(self, runner_id: str) -> Optional[Dict[str, Any]]:
        """
        Load runner state from database
        
        Args:
            runner_id: Unique identifier for the runner (e.g., 'tc_runner', 'se_runner')
            
        Returns:
            Runner state dict or None if not found
        """
        if self.runner_states is None:
            return None
            
        try:
            state = self.runner_states.find_one({"runner_id": runner_id})
            if state:
                self.logger.info(f"Loaded state for runner '{runner_id}'")
            return state
        except Exception as e:
            self.logger.error(f"Failed to load state for runner '{runner_id}': {e}")
            return None
    
    def save_runner_state(self, runner_id: str, state_data: Dict[str, Any]) -> bool:
        """
        Save runner state to database
        
        Args:
            runner_id: Unique identifier for the runner
            state_data: State data to save
            
        Returns:
            True if successful, False otherwise
        """
        if self.runner_states is None:
            return False
            
        try:
            # Add timestamp
            state_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Upsert: update if exists, insert if not
            result = self.runner_states.update_one(
                {"runner_id": runner_id},
                {"$set": state_data},
                upsert=True
            )
            
            self.logger.debug(f"Saved state for runner '{runner_id}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save state for runner '{runner_id}': {e}")
            return False
    
    def mark_runner_running(self, runner_id: str, is_running: bool) -> bool:
        """
        Mark runner as running or not running
        
        Args:
            runner_id: Unique identifier for the runner
            is_running: True if runner is currently running
            
        Returns:
            True if successful, False otherwise
        """
        if self.runner_states is None:
            return False
            
        try:
            result = self.runner_states.update_one(
                {"runner_id": runner_id},
                {"$set": {"is_running": is_running, "updated_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark runner '{runner_id}' running status: {e}")
            return False
    
    # Article Tracking Methods
    
    def is_article_used(self, article_url: str) -> bool:
        """
        Check if an article URL has been used before
        
        Args:
            article_url: URL of the article to check
            
        Returns:
            True if article has been used, False otherwise
        """
        if self.used_articles is None:
            return False
            
        try:
            result = self.used_articles.find_one({"url": article_url})
            return result is not None
        except Exception as e:
            self.logger.error(f"Failed to check article usage: {e}")
            return False
    
    def mark_article_used(self, article_url: str, article_title: str, source: str) -> bool:
        """
        Mark an article as used
        
        Args:
            article_url: URL of the article
            article_title: Title of the article
            source: Source name (e.g., "ScienceDaily")
            
        Returns:
            True if successful, False otherwise
        """
        if self.used_articles is None:
            return False
            
        try:
            timestamp = datetime.now(timezone.utc)
            self.used_articles.insert_one({
                "url": article_url,
                "title": article_title,
                "source": source,
                "used_at": timestamp.isoformat(),
                "created_at": timestamp.isoformat()
            })
            self.logger.info(f"Marked article as used: {article_title}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark article as used: {e}")
            return False
    
    def get_used_articles_count(self, source: Optional[str] = None) -> int:
        """
        Get count of used articles, optionally filtered by source
        
        Args:
            source: Optional source name to filter by
            
        Returns:
            Count of used articles
        """
        if self.used_articles is None:
            return 0
            
        try:
            query = {"source": source} if source else {}
            return self.used_articles.count_documents(query)
        except Exception as e:
            self.logger.error(f"Failed to count used articles: {e}")
            return 0
    
    def reset_runner_states(self) -> bool:
        """
        Reset all runner states (clears schedules and stats)
        
        Returns:
            True if successful, False otherwise
        """
        if self.runner_states is None:
            return False
            
        try:
            result = self.runner_states.delete_many({})
            count = result.deleted_count
            self.logger.info(f"Reset {count} runner state(s)")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reset runner states: {e}")
            return False
    
    def reset_used_articles(self) -> bool:
        """
        Reset used articles tracking (allows articles to be reused)
        
        Returns:
            True if successful, False otherwise
        """
        if self.used_articles is None:
            return False
            
        try:
            result = self.used_articles.delete_many({})
            count = result.deleted_count
            self.logger.info(f"Reset {count} used article(s)")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reset used articles: {e}")
            return False
