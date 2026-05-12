"""AI-powered text generation for FMEA enrichment using Agno."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAILike


class FMEAInsight(BaseModel):
    """Structured output for AI-generated FMEA insights."""
    root_cause_category: str = Field(..., description="Taxonomy category (e.g., 'dataset_bias', 'image_quality')")
    root_cause_analysis: str = Field(..., description="Detailed root cause analysis based on actual assessment data")
    recommended_actions: list[str] = Field(..., description="Prioritized actions targeted to specific root cause")
    mitigation_strategy: str = Field(..., description="Comprehensive mitigation approach aligned with EU AI Act Article 9")
    monitoring_recommendations: list[str] = Field(..., description="Ongoing monitoring through specific metrics and review frequencies")
    evidence_from_data: list[str] = Field(..., description="Citations to specific data points that informed the analysis")


class FMEAAIAgent:
    """AI agent for generating detailed FMEA insights with full assessment context."""

    def __init__(self, model_id: str = "deepseek-v4-flash", api_key: str | None = None, base_url: str = "https://opencode.ai/zen/go/v1"):
        self.agent = Agent(
            name="FMEA Risk Analyst",
            model=OpenAILike(id=model_id, api_key=api_key, base_url=base_url),
            instructions="""You are an expert FMEA risk analyst specializing in AI systems under the EU AI Act and ISO 14971.

Your role is to analyze failure modes identified in AI system assessments and provide:
1. Root cause classification into domain taxonomy categories
2. Evidence-based root cause analysis using actual assessment data
3. Targeted recommended actions addressing specific root causes
4. Mitigation strategies aligned with EU AI Act Article 9 risk management
5. Specific monitoring recommendations with metrics and frequencies

You MUST respond with valid JSON only, no additional text.
All analysis must be evidence-based, citing specific data points from the assessment data provided.""",
            markdown=False,
        )

    async def generate_insights(
        self,
        failure_mode: str,
        severity: int,
        occurrence: int,
        detectability: int,
        domain: str | None = None,
        fairness_results: list[dict] | None = None,
        stress_results: list[dict] | None = None,
        risk_register: list[dict] | None = None,
        existing_controls: str | None = None,
        root_cause_taxonomy: dict[str, str] | None = None,
        action_taxonomy: dict[str, str] | None = None,
    ) -> FMEAInsight:
        """Generate AI-powered insights for a failure mode using full assessment context."""
        prompt = self._build_prompt(
            failure_mode=failure_mode,
            severity=severity,
            occurrence=occurrence,
            detectability=detectability,
            domain=domain,
            fairness_results=fairness_results,
            stress_results=stress_results,
            risk_register=risk_register,
            existing_controls=existing_controls,
            root_cause_taxonomy=root_cause_taxonomy,
            action_taxonomy=action_taxonomy,
        )

        response = await self.agent.arun(prompt)

        content = response.content
        if isinstance(content, str):
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        else:
            data = content

        return FMEAInsight(**data)

    def _format_taxonomy(self, taxonomy: dict[str, str] | None) -> str:
        """Format taxonomy as markdown list."""
        if not taxonomy:
            return "No taxonomy defined"
        return "\n".join([f"- **{cat}**: {desc}" for cat, desc in taxonomy.items()])

    def _format_fairness_metrics(self, fairness_results: list[dict] | None) -> str:
        """Format fairness metrics for prompt."""
        if not fairness_results:
            return "No fairness metrics available"

        lines = []
        for metric in fairness_results[:15]:
            metric_name = metric.get("metric_name", "unknown")
            groups = metric.get("groups", [])
            lines.append(f"- **{metric_name}**:")
            for g in groups[:3]:
                lines.append(f"  - {g.get('group_name', 'unknown')}: {g.get('value', 'N/A')}")
        return "\n".join(lines)

    def _format_stress_results(self, stress_results: list[dict] | None) -> str:
        """Format stress test results for prompt."""
        if not stress_results:
            return "No stress test results available"

        lines = []
        for result in stress_results[:10]:
            name = result.get("perturbation_name", "unknown")
            drop = result.get("performance_drop", 0)
            entropy = result.get("average_entropy", 0)
            lines.append(f"- **{name}**: drop={drop:.3f}, entropy={entropy:.3f}")
        return "\n".join(lines)

    def _format_risk_register(self, risk_register: list[dict] | None) -> str:
        """Format risk register for prompt."""
        if not risk_register:
            return "No risk register entries"

        lines = []
        for record in risk_register[:10]:
            risk_id = record.get("risk_id", "unknown")
            title = record.get("title", "unknown")
            rpn = record.get("rpn", 0)
            controls = record.get("current_controls", "none")
            lines.append(f"- **{risk_id}** ({title}): RPN={rpn}, Controls: {controls}")
        return "\n".join(lines)

    def _build_prompt(
        self,
        failure_mode: str,
        severity: int,
        occurrence: int,
        detectability: int,
        domain: str | None = None,
        fairness_results: list[dict] | None = None,
        stress_results: list[dict] | None = None,
        risk_register: list[dict] | None = None,
        existing_controls: str | None = None,
        root_cause_taxonomy: dict[str, str] | None = None,
        action_taxonomy: dict[str, str] | None = None,
    ) -> str:
        """Build the prompt for the AI agent with full assessment context."""
        rpn = severity * occurrence * detectability
        risk_level = "High" if rpn >= 120 else "Medium" if rpn >= 60 else "Low"

        prompt = f"""## FAILURE MODE UNDER ANALYSIS
- **failure_mode**: {failure_mode}
- **severity**: {severity}/10 (1=minor, 10=catastrophic)
- **occurrence**: {occurrence}/10 (1=rare, 10=frequent)
- **detectability**: {detectability}/10 (1=easily detectable, 10=undetectable)
- **RPN**: {rpn} (Risk Priority Number = severity × occurrence × detectability)
- **risk_level**: {risk_level}

## DOMAIN TAXONOMY (classify root cause into ONE of these categories)
{self._format_taxonomy(root_cause_taxonomy)}

## ACTION TAXONOMY (select and customize action types)
{self._format_taxonomy(action_taxonomy)}

## ASSESSMENT DATA (REAL data from the AI system under analysis)

### 1. FAIRNESS METRICS (source: eu_ai_act fairness evaluation)
These show disparities in model performance across demographic groups. Analyze for causal factors.
{self._format_fairness_metrics(fairness_results)}

### 2. STRESS TEST RESULTS (source: eu_ai_act stress testing)
These show robustness under perturbations. Identify which perturbations cause most degradation.
{self._format_stress_results(stress_results)}

### 3. RISK REGISTER (source: eu_ai_act risk evaluation)
Already-identified risks with existing controls. Use to understand current risk landscape.
{self._format_risk_register(risk_register)}

### 4. EXISTING CONTROLS FOR THIS FAILURE MODE
{existing_controls or "None specified - no existing controls recorded"}

## ANALYSIS REQUIREMENTS
1. **Root Cause Classification**: Choose ONE category from the taxonomy that best explains the root cause
2. **Evidence-Based Analysis**: Cite specific data points (e.g., "senior age group TPR gap of 0.285 indicates dataset bias") to support your analysis
3. **Targeted Recommendations**: Select from action taxonomy and customize to address the specific root cause
4. **EU AI Act Alignment**: Consider Article 9 risk management and Article 5 prohibited practices
5. **Actionable Insights**: Recommendations must be specific, measurable, and implementable

## OUTPUT FORMAT
Return ONLY valid JSON with this structure:
{{
    "root_cause_category": "dataset_bias",
    "root_cause_analysis": "Detailed analysis citing specific data points from the assessment data above...",
    "recommended_actions": ["Action 1 specific to this failure", "Action 2 targeting the root cause", "Action 3 for monitoring"],
    "mitigation_strategy": "Comprehensive strategy description aligned with EU AI Act Article 9...",
    "monitoring_recommendations": ["Specific metric to track", "Review frequency", "Acceptance criteria"],
    "evidence_from_data": ["Citation: metric_name: value", "Citation: perturbation: result"]
}}

IMPORTANT: All analysis must be grounded in the actual assessment data provided above. Do not generate generic recommendations."""

        return prompt


class FMEAInsightGenerator:
    """Generator for FMEA insights using AI (always AI-powered, no fallback)."""

    def __init__(self, use_ai: bool = True, model_id: str = "deepseek-v4-flash", api_key: str | None = None, base_url: str = "https://opencode.ai/zen/go/v1"):
        self.use_ai = use_ai
        self.ai_agent = FMEAAIAgent(model_id=model_id, api_key=api_key, base_url=base_url) if use_ai else None

    async def generate_insights(
        self,
        failure_mode: str,
        severity: int,
        occurrence: int,
        detectability: int,
        domain: str | None = None,
        fairness_results: list[dict] | None = None,
        stress_results: list[dict] | None = None,
        risk_register: list[dict] | None = None,
        existing_controls: str | None = None,
        root_cause_taxonomy: dict[str, str] | None = None,
        action_taxonomy: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Generate insights for a failure mode using full assessment context."""
        if not self.use_ai or not self.ai_agent:
            raise RuntimeError("AI is required for FMEA enrichment - no fallback available")

        insights = await self.ai_agent.generate_insights(
            failure_mode=failure_mode,
            severity=severity,
            occurrence=occurrence,
            detectability=detectability,
            domain=domain,
            fairness_results=fairness_results,
            stress_results=stress_results,
            risk_register=risk_register,
            existing_controls=existing_controls,
            root_cause_taxonomy=root_cause_taxonomy,
            action_taxonomy=action_taxonomy,
        )
        return {
            "root_cause_category": insights.root_cause_category,
            "root_cause_analysis": insights.root_cause_analysis,
            "recommended_actions": insights.recommended_actions,
            "mitigation_strategy": insights.mitigation_strategy,
            "monitoring_recommendations": insights.monitoring_recommendations,
            "evidence_from_data": insights.evidence_from_data,
        }