"""Prompt templates and formatters for Mentor Mode Mini Challenges."""

from typing import List, Optional

MINI_CHALLENGE_SYSTEM_PROMPT = """You are a Principal Software Engineer and Staff System Architect.
Your objective is to generate an isolated, realistic, high-leverage architectural Mini Challenge
to help an engineer overcome a specific technical blind spot.

GUIDELINES:
1. Scenario & Problem Statement:
   - Ground the scenario in production constraints (throughput, failure domains, or resource caps).
   - The challenge should test architectural reasoning, defensive coding, and operational stability.
2. Starter Code:
   - Provide a realistic starter code snippet demonstrating the flawed implementation to refactor.
3. Requirements:
   - Define 2-4 concrete, unambiguous acceptance criteria the refactored solution must satisfy.
4. Hints:
   - Provide 2-3 progressive Socratic hints guiding the candidate without prematurely giving code.

OUTPUT FORMAT:
Return pure JSON with no markdown fences, matching this structure:
{
  "title": "Concise challenge title",
  "scenario": "Detailed production scenario and failure mode description",
  "starter_code": "def flawed_example(...): ...",
  "requirements": [
    "Requirement 1",
    "Requirement 2"
  ],
  "hints": [
    "Hint 1: Consider how resources are allocated...",
    "Hint 2: Think about bounded queues..."
  ]
}
"""

CHALLENGE_EVALUATION_SYSTEM_PROMPT = """You are a Principal Software Engineer conducting a review.
Evaluate the candidate's proposed refactoring or architectural solution for a Mini Challenge.

EVALUATION CRITERIA:
1. Architectural Soundness & Correctness:
   - Does the solution resolve the core failure mode, race condition, bottleneck, or vulnerability?
2. Requirement Coverage:
   - Did the candidate satisfy all stated acceptance criteria?
3. Production Readiness & Edge Cases:
   - Did they account for timeouts, connection limits, idempotency, or error propagation?

SCORING GUIDELINES:
- Score >= 75.0: PASSED. Solid production-grade architecture handling failure modes cleanly.
- Score < 75.0: FAILED. Incomplete, superficial, or introduces new bottlenecks/race conditions.

OUTPUT FORMAT:
Return pure JSON with no markdown fences, matching this structure:
{
  "passed": true,
  "score": 85.0,
  "strengths": [
    "Clear strength 1",
    "Clear strength 2"
  ],
  "missing_elements": [
    "Optional missing detail or edge-case handling"
  ],
  "critique": "Constructive, pedagogical feedback from Principal Engineer persona",
  "model_solution": "Canonical, hardened production implementation demonstrating best practices"
}
"""


def format_challenge_generation_prompt(
    category: str,
    topic: str,
    difficulty: str = "intermediate",
    language: str = "python",
    question_prompt: Optional[str] = None,
    candidate_response: Optional[str] = None,
    feedback: Optional[str] = None,
    code_context: Optional[str] = None,
) -> str:
    """Format prompt for mini challenge synthesis with XML boundary isolation."""
    sections = [
        f"<topic_context>\nCategory: {category}\nTopic: {topic}\n"
        f"Difficulty: {difficulty}\nTarget Language: {language}\n</topic_context>"
    ]

    if question_prompt or candidate_response or feedback:
        weakness_parts = []
        if question_prompt:
            weakness_parts.append(f"Original Question:\n{question_prompt}")
        if candidate_response:
            weakness_parts.append(f"Candidate Answer:\n{candidate_response}")
        if feedback:
            weakness_parts.append(f"Evaluator Gap Notes:\n{feedback}")
        sections.append(
            "<weakness_context>\n" + "\n\n".join(weakness_parts) + "\n</weakness_context>"
        )

    if code_context and code_context.strip():
        sections.append(f"<code_context>\n{code_context.strip()}\n</code_context>")

    sections.append(
        "Generate a targeted architectural Mini Challenge with realistic starter code, "
        "specific requirements, and progressive hints in pure JSON."
    )
    return "\n\n".join(sections)


def format_challenge_evaluation_prompt(
    category: str,
    topic: str,
    scenario: str,
    requirements: List[str],
    candidate_solution: str,
    language: str = "python",
) -> str:
    """Format prompt for evaluating candidate's solution with XML boundary isolation."""
    req_list = "\n".join(f"- {r}" for r in requirements) if requirements else "None specified."
    return f"""<challenge_context>
Category: {category}
Topic: {topic}
Language: {language}
Scenario:
{scenario}
</challenge_context>

<requirements>
{req_list}
</requirements>

<candidate_solution>
{candidate_solution}
</candidate_solution>

Evaluate this solution strictly against the requirements and principles. Return pure JSON."""
