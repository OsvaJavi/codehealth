import asyncio
import os

import google.generativeai as genai

from models import AnalyzeRequest, AnalyzeResponse, ToolResult
from tools import analyze_code_style, detect_code_smells, suggest_improvements

# ──────────────────────────────────────────────────────────────────────────────
# Tool definitions — Gemini function-calling schema
# ──────────────────────────────────────────────────────────────────────────────

TOOLS = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="analyze_code_style",
            description=(
                "Analyzes Python code for PEP 8 style violations including line length, "
                "trailing whitespace, indentation, naming conventions (snake_case for functions, "
                "PascalCase for classes), and missing whitespace. Returns a list of violations "
                "with line number, rule code, and description."
            ),
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "code": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="The Python source code to analyze",
                    ),
                    "strict_mode": genai.protos.Schema(
                        type=genai.protos.Type.BOOLEAN,
                        description="If true, uses the strict 79-char line limit. Default is 100.",
                    ),
                },
                required=["code"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="detect_code_smells",
            description=(
                "Detects code smells and anti-patterns in Python code including long functions, "
                "too many parameters, deep nesting, high cyclomatic complexity, unused variables, "
                "magic numbers, bare except clauses, and print() statements outside __main__ guards. "
                "Each smell includes a severity level: LOW, MEDIUM, or HIGH."
            ),
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "code": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="The Python source code to analyze",
                    ),
                    "complexity_threshold": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Cyclomatic complexity threshold before flagging. Default is 10.",
                    ),
                },
                required=["code"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="suggest_improvements",
            description=(
                "Suggests concrete refactoring improvements for Python code based on a focus area. "
                "'performance': list comprehensions, avoiding string concat in loops, truthiness checks. "
                "'readability': missing docstrings, negative conditions. "
                "'maintainability': missing type hints, broad exceptions, global variables, long functions. "
                "Each suggestion includes a priority (LOW/MEDIUM/HIGH/CRITICAL) and expected impact."
            ),
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "code": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="The Python source code to analyze",
                    ),
                    "focus_area": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="The improvement focus area",
                        enum=["performance", "readability", "maintainability"],
                    ),
                },
                required=["code", "focus_area"],
            ),
        ),
    ]
)

SYSTEM_PROMPT = """You are an expert Python code quality analyst agent. Your job is to analyze \
Python code using specialized tools and produce a clear, actionable quality report.

## Tool Selection Guidelines

Choose tools based on the analysis_type field provided by the user:

- analysis_type="style"   → use ONLY analyze_code_style
- analysis_type="smells"  → use ONLY detect_code_smells
- analysis_type="improve" → use ONLY suggest_improvements (choose the most appropriate \
focus_area from: performance, readability, maintainability — or default to "readability")
- analysis_type="auto"    → run ALL THREE tools to give a complete picture

## Response Format

After running the tools, write a concise final report that:
1. Summarizes the overall code quality in 1-2 sentences
2. Highlights the most critical issues found (if any)
3. Lists the top 3 actionable recommendations
4. States the quality score rationale

Keep the report professional, specific, and developer-friendly. Avoid repeating raw tool output verbatim.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Tool dispatcher
# ──────────────────────────────────────────────────────────────────────────────

def _execute_tool(name: str, inputs: dict) -> list[dict]:
    if name == "analyze_code_style":
        return analyze_code_style(
            code=inputs["code"],
            strict_mode=inputs.get("strict_mode", False),
        )
    if name == "detect_code_smells":
        return detect_code_smells(
            code=inputs["code"],
            complexity_threshold=inputs.get("complexity_threshold", 10),
        )
    if name == "suggest_improvements":
        return suggest_improvements(
            code=inputs["code"],
            focus_area=inputs.get("focus_area", "readability"),
        )
    return []


def _calculate_quality_score(tool_results: list[ToolResult]) -> float:
    score = 10.0
    for result in tool_results:
        for item in result.results:
            severity = item.get("severity", "")
            priority = item.get("priority", "")
            rule = item.get("rule", "")

            if severity == "HIGH":
                score -= 1.5
            elif severity == "MEDIUM":
                score -= 0.8
            elif severity == "LOW":
                score -= 0.3
            elif rule:
                score -= 0.25
            elif priority in ("CRITICAL", "HIGH"):
                score -= 0.5
            elif priority == "MEDIUM":
                score -= 0.2
            elif priority == "LOW":
                score -= 0.1

    return max(0.0, round(score, 1))


# ──────────────────────────────────────────────────────────────────────────────
# Gemini agentic loop (synchronous — called via asyncio.to_thread)
# ──────────────────────────────────────────────────────────────────────────────

def _run_analysis_sync(request: AnalyzeRequest) -> AnalyzeResponse:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        tools=[TOOLS],
        system_instruction=SYSTEM_PROMPT,
    )

    # disable automatic function calling so we control the loop manually
    chat = model.start_chat(enable_automatic_function_calling=False)

    user_message = (
        f"Please analyze the following Python code.\n\n"
        f"analysis_type: {request.analysis_type}\n"
        f"focus_area: {request.focus_area or 'not specified'}\n\n"
        f"```python\n{request.code}\n```"
    )

    response = chat.send_message(user_message)

    tool_results_collected: list[ToolResult] = []
    tools_used: list[str] = []
    initial_reasoning = ""
    final_report = ""
    first_turn = True

    while True:
        # Split response parts into text and function-call buckets
        text_parts: list[str] = []
        fn_call_parts = []

        for part in response.parts:
            try:
                if part.function_call.name:
                    fn_call_parts.append(part)
                    continue
            except AttributeError:
                pass
            try:
                if part.text:
                    text_parts.append(part.text)
            except AttributeError:
                pass

        response_text = "\n".join(text_parts).strip()

        if first_turn and response_text:
            initial_reasoning = response_text

        # No function calls → Gemini is done; collect the final report
        if not fn_call_parts:
            final_report = response_text
            break

        # Execute every function call Gemini requested (may be multiple)
        fn_response_parts = []
        for part in fn_call_parts:
            fc = part.function_call
            tool_name = fc.name
            tool_args = dict(fc.args)

            if tool_name not in tools_used:
                tools_used.append(tool_name)

            result = _execute_tool(tool_name, tool_args)

            tool_results_collected.append(
                ToolResult(
                    tool_name=tool_name,
                    results=result if isinstance(result, list) else [result],
                    count=len(result) if isinstance(result, list) else 1,
                )
            )

            fn_response_parts.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=tool_name,
                        response={"result": result},
                    )
                )
            )

        # Send all tool results back to Gemini in one turn
        response = chat.send_message(fn_response_parts)
        first_turn = False

    quality_score = _calculate_quality_score(tool_results_collected)

    return AnalyzeResponse(
        agent_reasoning=initial_reasoning or f"Running '{request.analysis_type}' analysis with Gemini...",
        tools_used=tools_used,
        analysis_results=tool_results_collected,
        final_report=final_report or "Analysis complete.",
        code_quality_score=quality_score,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public async entry point (FastAPI-compatible)
# ──────────────────────────────────────────────────────────────────────────────

async def run_analysis_agent(request: AnalyzeRequest) -> AnalyzeResponse:
    # google-generativeai is synchronous; run it in a thread so we don't
    # block the FastAPI event loop.
    return await asyncio.to_thread(_run_analysis_sync, request)
