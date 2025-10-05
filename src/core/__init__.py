"""VerbalForge Core - Refactored modular architecture

This module provides a clean, scalable architecture for GRE question generation:

- models/: Data models and enums
- validators/: Validation logic (DRY principles)
- services/: Business logic services (prompts, LLM, formatting, validation)
- layers/: Processing layers (generation, validation)
- orchestrator.py: Main entry point coordinating the workflow
"""

__version__ = "0.2.0"
__author__ = "VerbalForge Team"

# Import from new structure
try:
    from .orchestrator import QuestionOrchestrator
    from .models import (
        PromptQuestionType,
        QuestionType,
        DifficultyLevel,
        LLMProvider,
        Choice,
        GREQuestion,
        TextCompletionQuestion,
        SentenceEquivalenceQuestion,
        ReadingComprehensionQuestion,
        ReadingComprehension,
        QuestionBatch,
        GenerationRequest,
        LLMResponse,
    )

    __all__ = [
        # Main orchestrator
        "QuestionOrchestrator",
        # Enums
        "PromptQuestionType",
        "QuestionType",
        "DifficultyLevel",
        "LLMProvider",
        # Models
        "Choice",
        "GREQuestion",
        "TextCompletionQuestion",
        "SentenceEquivalenceQuestion",
        "ReadingComprehensionQuestion",
        "ReadingComprehension",
        "QuestionBatch",
        "GenerationRequest",
        "LLMResponse",
    ]
except ImportError as e:
    import logging

    logging.warning(f"Import error in core module: {e}")
    __all__ = []
