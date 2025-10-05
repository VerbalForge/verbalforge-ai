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

            self.logger.info(f"Using database: {self.database_name}")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.error(f"Connection failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Setup error: {e}")
            raise

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
            # Add server metadata
            question["question_id"] = str(uuid.uuid4())
            question["metadata"] = {
                "created_at": timestamp.isoformat(),
                "updated_at": timestamp.isoformat(),
                "published_at": timestamp.isoformat(),
                "batch_id": batch_id,
            }

            try:
                result = self.questions.insert_one(question)
                if result.inserted_id:
                    question["_id"] = result.inserted_id  # Add MongoDB ID to the dict
                    stored += 1
            except Exception as e:
                self.logger.error(f"Failed to store question: {e}")

        self.logger.info(f"Stored {stored}/{len(questions)} questions")
        return stored

    def update_questions_with_passage_id(self, question_ids: List[str], passage_id: str) -> int:

        if not question_ids or not passage_id:
            return 0

        try:
            from bson import ObjectId

            object_ids = [ObjectId(qid) for qid in question_ids]

            result = self.questions.update_many(
                {"_id": {"$in": object_ids}}, {"$set": {"passage_id": passage_id}}
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

        doc = {
            "passage": passage_data.get("passage", ""),
            "source": passage_data.get("source", "Unknown"),
            "title": passage_data.get("title", "Reading Comprehension"),
            "difficulty_level": passage_data.get("difficulty_level", "medium"),
            "type": passage_data.get("type", "reading_comprehension_passage"),
            "question_ids": passage_data.get("question_ids", []),
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
                return str(result.inserted_id)
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
                qid = q.get("question_id") or q.get("id")
                if qid:
                    question_ids.append(qid)

            # Build passage document
            doc = {
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
                    passage_mappings.append((str(result.inserted_id), question_ids))
            except Exception as e:
                self.logger.error(f"Failed to store passage: {e}")

        self.logger.info(f"Stored {len(passage_mappings)} passage(s)")
        return passage_mappings
