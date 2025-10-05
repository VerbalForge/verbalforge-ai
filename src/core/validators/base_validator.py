"""Base validator with common validation logic (DRY)"""

from typing import Dict, List, Any
import re
import logging

logger = logging.getLogger(__name__)


class BaseValidator:
    """Base validator with reusable validation methods"""

    @staticmethod
    def validate_required_fields(data: Dict[str, Any], fields: List[str]) -> List[str]:
        """Validate that required fields are present"""
        errors = []
        for field in fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        return errors

    @staticmethod
    def validate_field_type(data: Dict[str, Any], field: str, expected_type: type) -> List[str]:
        """Validate field type"""
        errors = []
        if field in data and not isinstance(data[field], expected_type):
            errors.append(
                f"Field '{field}' must be {expected_type.__name__}, got {type(data[field]).__name__}"
            )
        return errors

    @staticmethod
    def validate_list_items(items: List[Any], item_name: str, validator_func, *args) -> List[str]:
        """Validate each item in a list using a validator function"""
        errors = []
        for i, item in enumerate(items):
            item_errors = validator_func(item, *args)
            if item_errors:
                errors.extend([f"{item_name} {i}: {error}" for error in item_errors])
        return errors

    @staticmethod
    def validate_choice_structure(choice: Dict[str, Any]) -> List[str]:
        """Validate a single choice structure"""
        errors = []
        required_fields = ["option", "is_correct", "reasoning"]

        if not isinstance(choice, dict):
            return ["Choice must be a dictionary"]

        for field in required_fields:
            if field not in choice:
                errors.append(f"Missing required field: {field}")

        return errors

    @staticmethod
    def validate_text_length(text: str, min_len: int = 0, max_len: int = None) -> List[str]:
        """Validate text length"""
        errors = []
        text_len = len(text.strip()) if text else 0

        if text_len < min_len:
            errors.append(f"Text too short ({text_len} characters, minimum {min_len})")

        if max_len and text_len > max_len:
            errors.append(f"Text too long ({text_len} characters, maximum {max_len})")

        return errors

    @staticmethod
    def count_blanks(text: str) -> int:
        """Count blanks in text (both simple and numbered)"""
        simple_blanks = text.count("_____")
        numbered_blanks = len(re.findall(r"_____\d+_____", text))
        return numbered_blanks if numbered_blanks > 0 else simple_blanks

    @staticmethod
    def validate_sentence_structure(text: str, allow_blanks: bool = False) -> List[str]:
        """Validate sentence structure"""
        errors = []
        text = text.strip()

        if allow_blanks and "_____" in text:
            acceptable_endings = ("?", ":", ".", ")", "s", "d", "g", "e", "n", "t", "r", "l", "y")
            if not text.endswith(acceptable_endings):
                errors.append(
                    f"Question should end with acceptable punctuation or word ending, ends with: '{text[-1] if text else 'empty'}'"
                )
        else:
            if not text.endswith(("?", ":", ".")):
                errors.append(
                    f"Text should end with proper punctuation, ends with: '{text[-1] if text else 'empty'}'"
                )

        return errors
