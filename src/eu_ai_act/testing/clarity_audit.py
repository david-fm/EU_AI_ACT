"""Clarity audit module for evaluating FMEA report quality.

This module provides a regression testing tool that evaluates whether
AI-generated FMEA reports are understandable and actionable, given
context about the model and training setup.
"""

from __future__ import annotations

import asyncio
import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAILike


@dataclass
class ClarityResult:
    """Result of a clarity audit."""

    understandable: bool
    score: int
    summary: str
    strengths: list[str]
    gaps: list[str]
    missing_context: list[str]
    recommendations: list[str]
    is_actionable: bool

    def __post_init__(self):
        if not 1 <= self.score <= 10:
            raise ValueError("Score must be between 1 and 10")


class ClarityAuditAgent:
    """Agent that evaluates FMEA report clarity and quality."""

    def __init__(
        self,
        model_id: str = "deepseek-v4-flash",
        api_key: str | None = None,
        base_url: str = "https://opencode.ai/zen/go/v1",
    ):
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url
        self._agent = None

    @property
    def agent(self) -> Agent:
        if self._agent is None:
            self._agent = Agent(
                name="Clarity Auditor",
                model=OpenAILike(
                    id=self.model_id,
                    api_key=self.api_key,
                    base_url=self.base_url,
                ),
                instructions="""You are an expert compliance auditor specializing in EU AI Act risk management documentation.

Your role is to evaluate whether FMEA (Failure Mode and Effects Analysis) reports are:
1. **Understandable** - Clear to a domain expert (radiologist, clinician)
2. **Evidence-based** - Grounded in actual model/data characteristics
3. **Actionable** - Enables compliance officers to make decisions
4. **Complete** - No critical missing context from the training setup

## Evaluation Criteria (score 1-10)

**10-9**: Excellent - Crystal clear, fully evidenced, immediately actionable
**8-7**: Good - Clear with minor gaps, generally actionable
**6-5**: Marginal - Some sections unclear or missing context
**4-3**: Poor - Significant gaps, hard to follow
**2-1**: Failing - Incomprehensible or completely lacks evidence

## Your Task

1. Read the FMEA report and model information provided
2. Identify what the report does well (strengths)
3. Identify gaps, missing context, or unclear sections
4. Note what model/data info from the notebook is NOT referenced in the report
5. Provide specific recommendations to improve the report
6. Determine if a compliance officer could act on this report

## Output Format

Return ONLY valid JSON with this structure:
{
    "understandable": true/false,
    "score": 8,
    "summary": "One-line overall assessment",
    "strengths": ["Strength 1", "Strength 2"],
    "gaps": ["Gap 1 - specific issue", "Gap 2 - missing detail"],
    "missing_context": ["Model characteristic X from notebook not referenced in report"],
    "recommendations": ["Specific recommendation to fix gap 1", "Specific recommendation to fix gap 2"],
    "is_actionable": true/false
}

IMPORTANT: Output valid JSON only. No markdown, no additional text.""",
                markdown=False,
            )
        return self._agent

    async def _parse_notebook(self, notebook_path: Path) -> dict[str, Any]:
        """Extract model and training information from a Jupyter notebook."""
        with open(notebook_path, encoding="utf-8") as f:
            notebook = json.load(f)

        info: dict[str, Any] = {
            "model_architecture": None,
            "dataset": None,
            "training_params": {},
            "key_components": [],
        }

        code_context = []
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") == "code":
                source = "".join(cell.get("source", []))
                code_context.append(source)

        full_code = "\n".join(code_context)

        if match := re.search(r"from tensorflow\.keras\.applications\s+import\s+(\w+)", full_code):
            info["model_architecture"] = match.group(1)
        elif match := re.search(r"tf\.keras\.applications\.(\w+)", full_code):
            info["model_architecture"] = match.group(1)

        if "MobileNet" in full_code:
            info["key_components"].append("MobileNet backbone")
        if "mixed_precision" in full_code or "mixed_float16" in full_code:
            info["training_params"]["mixed_precision"] = True
        if "early_stopping" in full_code:
            info["training_params"]["early_stopping"] = True
        if "model_checkpoint" in full_code:
            info["training_params"]["model_checkpoint"] = True

        batch_size_match = re.search(r"TRAIN_BATCH_SIZE\s*=\s*(\d+)", full_code)
        if batch_size_match:
            info["training_params"]["train_batch_size"] = int(batch_size_match.group(1))
        eval_batch_match = re.search(r"EVAL_BATCH_SIZE\s*=\s*(\d+)", full_code)
        if eval_batch_match:
            info["training_params"]["eval_batch_size"] = int(eval_batch_match.group(1))

        if "NIH" in full_code or "Chest X-ray" in full_code:
            info["dataset"] = "NIH Chest X-rays"
        if "polars" in full_code:
            info["training_params"]["data_library"] = "polars"
        if "flow_from_dataframe" in full_code:
            info["training_params"]["data_augmentation"] = "flow_from_dataframe"

        epochs_match = re.search(r"epochs?\s*=\s*(\d+)", full_code)
        if epochs_match:
            info["training_params"]["epochs"] = int(epochs_match.group(1))

        return info

    async def _parse_python_file(self, python_path: Path) -> dict[str, Any]:
        """Extract model and training information from a Python file."""
        with open(python_path, encoding="utf-8") as f:
            source = f.read()

        info: dict[str, Any] = {
            "model_architecture": None,
            "dataset": None,
            "training_params": {},
            "key_components": [],
        }

        if "tensorflow" in source or "keras" in source:
            info["key_components"].append("TensorFlow/Keras")
        if "torch" in source or "pytorch" in source:
            info["key_components"].append("PyTorch")

        if "MobileNet" in source:
            info["model_architecture"] = "MobileNet"
        if "ResNet" in source:
            info["model_architecture"] = "ResNet"
        if "EfficientNet" in source:
            info["model_architecture"] = "EfficientNet"

        batch_match = re.search(r"batch_size\s*[=:]\s*(\d+)", source, re.IGNORECASE)
        if batch_match:
            info["training_params"]["batch_size"] = int(batch_match.group(1))

        epochs_match = re.search(r"epochs?\s*[=:]\s*(\d+)", source, re.IGNORECASE)
        if epochs_match:
            info["training_params"]["epochs"] = int(epochs_match.group(1))

        if "NIH" in source or "chest" in source.lower():
            info["dataset"] = "Medical imaging dataset"

        return info

    async def _load_model_info(
        self,
        notebook_path: Path | None = None,
        python_path: Path | None = None,
    ) -> str:
        """Load and format model information from notebook or Python file."""
        if notebook_path:
            info = await self._parse_notebook(notebook_path)
        elif python_path:
            info = await self._parse_python_file(python_path)
        else:
            return "No model information provided"

        lines = ["## MODEL INFORMATION (from training script/notebook)"]
        if info["model_architecture"]:
            lines.append(f"- **Architecture**: {info['model_architecture']}")
        if info["dataset"]:
            lines.append(f"- **Dataset**: {info['dataset']}")
        if info["key_components"]:
            lines.append(f"- **Key components**: {', '.join(info['key_components'])}")
        if info["training_params"]:
            lines.append("- **Training parameters**:")
            for k, v in info["training_params"].items():
                lines.append(f"  - {k}: {v}")
        if not info["model_architecture"] and not info["dataset"]:
            lines.append("- (Could not extract model details from file)")

        return "\n".join(lines)

    async def audit(
        self,
        report_path: Path,
        notebook_path: Path | None = None,
        python_path: Path | None = None,
    ) -> ClarityResult:
        """Audit an FMEA report for clarity and quality.

        Args:
            report_path: Path to the markdown FMEA report
            notebook_path: Path to training notebook (alternative to python_path)
            python_path: Path to Python file with model info (alternative to notebook_path)

        Returns:
            ClarityResult with score and detailed feedback
        """
        with open(report_path, encoding="utf-8") as f:
            report_content = f.read()

        model_info = await self._load_model_info(notebook_path, python_path)

        prompt = f"""## TASK: Evaluate this FMEA report for clarity and actionability

{model_info}

---

## FMEA REPORT TO EVALUATE

{report_content}

---

Evaluate the report using the criteria in your instructions. Return ONLY JSON."""

        response = await self.agent.arun(prompt)

        content = response.content
        if isinstance(content, str):
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in agent response")
        else:
            data = content

        return ClarityResult(
            understandable=data.get("understandable", False),
            score=data.get("score", 5),
            summary=data.get("summary", "No summary provided"),
            strengths=data.get("strengths", []),
            gaps=data.get("gaps", []),
            missing_context=data.get("missing_context", []),
            recommendations=data.get("recommendations", []),
            is_actionable=data.get("is_actionable", False),
        )


def audit(
    report_path: str | Path,
    notebook_path: str | Path | None = None,
    python_path: str | Path | None = None,
    model_id: str = "deepseek-v4-flash",
    api_key: str | None = None,
    base_url: str = "https://opencode.ai/zen/go/v1",
    warn_threshold: int = 7,
) -> ClarityResult:
    """Synchronous wrapper for ClarityAuditAgent.audit().

    Issues a warning if score < warn_threshold.

    Args:
        report_path: Path to markdown FMEA report
        notebook_path: Path to training notebook (alternative to python_path)
        python_path: Path to Python model file (alternative to notebook_path)
        model_id: AI model to use
        api_key: API key for AI model
        base_url: Base URL for API
        warn_threshold: Score below which to issue warning (default 7)

    Returns:
        ClarityResult
    """
    agent = ClarityAuditAgent(model_id=model_id, api_key=api_key, base_url=base_url)

    report_p = Path(report_path)
    notebook_p = Path(notebook_path) if notebook_path else None
    python_p = Path(python_path) if python_path else None

    result = asyncio.run(agent.audit(report_p, notebook_p, python_p))

    if result.score < warn_threshold:
        warnings.warn(
            f"Clarity audit WARNING: Score {result.score}/10 (threshold: {warn_threshold})\n"
            f"Summary: {result.summary}\n"
            f"Gaps: {result.gaps}\n"
            f"Missing context: {result.missing_context}\n"
            f"Recommendations: {result.recommendations}",
            UserWarning,
        )

    return result


def print_report(result: ClarityResult) -> None:
    """Print a formatted clarity audit report."""
    status = "PASS" if result.score >= 7 else "WARNING"
    print(f"\n{'='*60}")
    print(f"Clarity Audit Report")
    print(f"{'='*60}")
    print(f"Status: [{status}] Score: {result.score}/10")
    print(f"Understandable: {result.understandable}")
    print(f"Actionable: {result.is_actionable}")
    print(f"\nSummary: {result.summary}")
    print(f"\nStrengths:")
    for s in result.strengths:
        print(f"  + {s}")
    print(f"\nGaps:")
    for g in result.gaps:
        print(f"  - {g}")
    if result.missing_context:
        print(f"\nMissing context from training:")
        for m in result.missing_context:
            print(f"  ! {m}")
    if result.recommendations:
        print(f"\nRecommendations:")
        for r in result.recommendations:
            print(f"  > {r}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit FMEA report clarity")
    parser.add_argument("--report", required=True, help="Path to markdown report")
    parser.add_argument("--notebook", help="Path to training notebook")
    parser.add_argument("--python", dest="python_file", help="Path to Python model file")
    parser.add_argument("--model-id", default="deepseek-v4-flash")
    parser.add_argument("--api-key")
    parser.add_argument("--base-url", default="https://opencode.ai/zen/go/v1")
    parser.add_argument("--threshold", type=int, default=7, help="Warning threshold")
    args = parser.parse_args()

    result = audit(
        report_path=args.report,
        notebook_path=args.notebook,
        python_path=args.python_file,
        model_id=args.model_id,
        api_key=args.api_key,
        base_url=args.base_url,
        warn_threshold=args.threshold,
    )
    print_report(result)