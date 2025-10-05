"""
GRE Question Generation Prompts

This package contains the system and generation prompts for different GRE question types.
Each prompt module provides:
- SYSTEM_PROMPT: The system-level instructions for the LLM
- GENERATION_PROMPT: The user-level template for generating questions
"""

from . import text_completion
from . import sentence_equivalence
from . import reading_comprehension

__all__ = [
    "text_completion",
    "sentence_equivalence",
    "reading_comprehension",
]
