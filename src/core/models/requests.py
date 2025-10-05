"""Request models for API interactions"""

from typing import Optional
from pydantic import BaseModel, Field

from .enums import PromptQuestionType, DifficultyLevel


class GenerationRequest(BaseModel):
    """Request model for question generation"""

    count: int = Field(default=5, ge=1, le=10, description="Number of questions to generate")
    question_type: PromptQuestionType = Field(..., description="Type of questions to generate")
    difficulty_level: DifficultyLevel = Field(default="medium", description="Difficulty level")
    topic: Optional[str] = Field(None, description="Specific topic to focus on")
    custom_instructions: Optional[str] = Field(
        None, description="Additional instructions for generation"
    )
