import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent import run_analysis_agent
from models import AnalyzeRequest, AnalyzeResponse

VALID_ANALYSIS_TYPES = {"auto", "style", "smells", "improve"}
VALID_FOCUS_AREAS = {"performance", "readability", "maintainability"}

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")
    yield


app = FastAPI(
    title="Code Quality Analyzer Agent",
    description="AI agent that analyzes Python code quality using Google Gemini and real AST-based tools.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Code Quality Analyzer Agent",
        "version": "1.0.0",
        "endpoints": {"analyze": "POST /analyze"},
        "analysis_types": list(VALID_ANALYSIS_TYPES),
        "focus_areas": list(VALID_FOCUS_AREAS),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_code(request: AnalyzeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="'code' field cannot be empty.")

    if request.analysis_type not in VALID_ANALYSIS_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"'analysis_type' must be one of: {sorted(VALID_ANALYSIS_TYPES)}",
        )

    if request.focus_area and request.focus_area not in VALID_FOCUS_AREAS:
        raise HTTPException(
            status_code=422,
            detail=f"'focus_area' must be one of: {sorted(VALID_FOCUS_AREAS)}",
        )

    if request.analysis_type == "improve" and not request.focus_area:
        request = request.model_copy(update={"focus_area": "readability"})

    result = await run_analysis_agent(request)
    return result
