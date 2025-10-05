"""Response models for API interactions"""

from typing import Optional
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Response from LLM with metadata"""

    content: str = Field(..., description="The response content")
    tokens_used: int = Field(..., description="Number of tokens used")
    model: str = Field(..., description="Model used for generation")
    cost_estimate: Optional[float] = Field(None, description="Estimated cost of the request")
    response_time: float = Field(..., description="Response time in seconds")
