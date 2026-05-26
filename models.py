from pydantic import BaseModel, Field
from typing import Optional, Any


class AnalyzeRequest(BaseModel):
    code: str = Field(..., description="Python code to analyze", min_length=1)
    analysis_type: str = Field(
        default="auto",
        description="Type of analysis: auto|style|smells|improve",
    )
    focus_area: Optional[str] = Field(
        default=None,
        description="Focus area for improvements: performance|readability|maintainability",
    )


class ToolResult(BaseModel):
    tool_name: str
    results: list[dict[str, Any]]
    count: int


class AnalyzeResponse(BaseModel):
    agent_reasoning: str
    tools_used: list[str]
    analysis_results: list[ToolResult]
    final_report: str
    code_quality_score: float = Field(..., ge=0, le=10)
