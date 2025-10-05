"""Generation tasks for different question types"""

from .text_completion import generate_text_completion
from .sentence_equivalence import generate_sentence_equivalence
from .reading_comprehension import generate_reading_comprehension

__all__ = [
    "generate_text_completion",
    "generate_sentence_equivalence",
    "generate_reading_comprehension",
]
