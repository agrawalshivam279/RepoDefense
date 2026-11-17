"""Centralized prompts and XML formatting for Targeted Re-Testing."""

import re
from typing import Optional


def sanitize_prompt_text(text: Optional[str], max_len: int = 2000) -> str:
    """Sanitize and clamp untrusted candidate or repository input for LLM prompts."""
    if not text:
        return ""
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    clean = clean.strip()
    return clean[:max_len]


RETEST_SYSTEM_PROMPT = """You are a Principal Software Engineer conducting a rigorous re-test.
Your objective is to evaluate whether a candidate has remediated their architectural weakness.

Rules:
1. Ground the re-test in the weakness topic, category, original question, and mentor feedback.
2. Formulate a challenging, realistic production scenario or constraint (e.g. 10x traffic spike).
3. Demand specific architectural tradeoffs, concrete mechanisms, and system design defenses.
4. Output must be strictly valid JSON matching the requested schema. No markdown fences.
"""

RETEST_EVALUATION_SYSTEM_PROMPT = """You are an objective Principal Software Engineer.
Evaluate the candidate's targeted re-test defense against the specific production constraint.

Evaluation Rubric:
- Score 0 to 100 based on technical depth, recognition of failure modes, and mitigation design.
- Pass threshold is 70.0. A passing answer must identify bottlenecks and propose viable solutions.
- Be objective and constructively critical. Score superficial answers below 60.
- Output must be strictly valid JSON matching the requested schema.
"""


def format_retest_generation_prompt(
    category: str,
    topic: str,
    severity: str,
    original_prompt: str,
    feedback: str,
    candidate_prior_response: Optional[str] = None,
) -> str:
    """Format user prompt for generating a targeted re-test question with XML boundaries."""
    sanitized_orig = sanitize_prompt_text(original_prompt, max_len=1500)
    sanitized_feed = sanitize_prompt_text(feedback, max_len=1500)
    sanitized_prior = sanitize_prompt_text(candidate_prior_response, max_len=1000)

    prior_block = (
        f"<candidate_prior_response>\n{sanitized_prior}\n</candidate_prior_response>\n"
        if sanitized_prior
        else ""
    )

    return f"""Synthesize a targeted re-test question based on the candidate's weakness.

<weakness_context>
Category: {category}
Topic: {topic}
Severity: {severity}
</weakness_context>

<original_question>
{sanitized_orig}
</original_question>

<mentor_feedback>
{sanitized_feed}
</mentor_feedback>

{prior_block}
Generate a targeted re-test scenario that tests whether the candidate has remediated this gap.
Respond with JSON matching:
{{
  "question_text": "Detailed re-test question presenting a production scenario",
  "architectural_constraint": "Specific production constraint (e.g. 20k req/s)",
  "evaluation_rubric": "Key architectural expectations required to earn a passing score"
}}
"""


def format_retest_evaluation_prompt(
    category: str,
    topic: str,
    retest_question: str,
    constraint: str,
    rubric: str,
    candidate_response: str,
) -> str:
    """Format prompt for evaluating the candidate's re-test defense."""
    sanitized_q = sanitize_prompt_text(retest_question, max_len=1500)
    sanitized_c = sanitize_prompt_text(constraint, max_len=1000)
    sanitized_rubric = sanitize_prompt_text(rubric, max_len=1000)
    sanitized_ans = sanitize_prompt_text(candidate_response, max_len=4000)

    return f"""Evaluate the candidate's defense against the targeted re-test question.

<context>
Category: {category}
Topic: {topic}
</context>

<retest_question>
{sanitized_q}
</retest_question>

<architectural_constraint>
{sanitized_c}
</architectural_constraint>

<evaluation_rubric>
{sanitized_rubric}
</evaluation_rubric>

<candidate_defense>
{sanitized_ans}
</candidate_defense>

Respond with JSON matching:
{{
  "score": 75.0,
  "passed": true,
  "feedback": "Comprehensive technical evaluation explaining what was done well",
  "key_improvements": ["Identified pool exhaustion risk", "Proposed token-bucket rate limiter"],
  "remaining_gaps": ["Did not address cache stampede on invalidation"]
}}
"""
