"""LLM-as-judge: an independent verdict on whether a run actually succeeded.

Independent of the agent's own self-report (agents over-report success). The LLM client
is injected so this is unit-testable with a mock.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel

from app.models.enums import RunVerdictResult

_JUDGE_SYSTEM = (
    "You are an impartial auditor of a job-application automation run. Decide whether the "
    "application was actually submitted, based only on the evidence in the trajectory. Do "
    "not trust the agent's own claim of success. Respond with the structured verdict."
)


class JudgeOutput(BaseModel):
    verdict: RunVerdictResult
    confidence: float = 0.0
    reason: str = ""


class _StructuredLLM(Protocol):
    async def complete_with_structured_output(
        self, *, prompt: str, output_schema: type[BaseModel], system_prompt: str, purpose: str
    ) -> Any: ...


async def judge_run(llm: _StructuredLLM, summary: dict[str, Any]) -> JudgeOutput:
    """Ask the LLM to judge a run from its trajectory summary."""
    prompt = (
        "Judge this application run. Evidence (final URL, last screenshot description, "
        "the agent's reported result, and any errors):\n"
        f"{json.dumps(summary, default=str)[:4000]}\n\n"
        "Was the application actually submitted? Give verdict, confidence (0-1), and reason."
    )
    result = await llm.complete_with_structured_output(
        prompt=prompt,
        output_schema=JudgeOutput,
        system_prompt=_JUDGE_SYSTEM,
        purpose="harness_judge",
    )
    return result if isinstance(result, JudgeOutput) else JudgeOutput.model_validate(result)
