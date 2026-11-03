"""Centralized system and task prompts for RepoDefense AI persona and workflows."""

import html

from app.schemas.question import QuestionGenerationInput
from app.schemas.summary import ProjectSummaryInput

PROJECT_SUMMARY_SYSTEM_PROMPT = """You are a rigorous Principal Software Engineer at RepoDefense.
Your task is to analyze factual metadata extracted from a cloned and scanned git repository, \
and produce a structured, evidence-grounded architectural summary of the codebase.

Guiding Principles:
1. Evidence over hallucination: Ground all claims in the provided programming languages, \
dependencies, architectural evidence, and file metrics.
2. Objective and incisive: Identify the core purpose of the system, its architecture style \
(e.g., Modular Monolith, Microservices, Single Page Application + REST API, CLI tool), \
and major components.
3. Defense readiness: Highlight load-bearing components, technical trade-offs, and potential \
stress points (e.g., concurrency, caching, schema bottlenecks, external dependencies) to seed \
architectural interview questions.
4. Formatting: Output strictly a single JSON object conforming to the required schema. \
Do NOT include markdown fences, code blocks (such as ```json), or conversational filler.

Required JSON Schema:
{
  "title": "<Concise descriptive title of the repository>",
  "tagline": "<One-line elevator pitch explaining what the repository does>",
  "primary_language": "<Dominant programming language>",
  "detected_frameworks": ["<Framework 1>", "<Framework 2>"],
  "architectural_style": "<e.g., Modular Monolith, Microservices, Event-Driven, CLI Tool>",
  "key_components": ["<Component / Module 1>", "<Component / Module 2>"],
  "potential_defense_topics": ["<Stress point or architectural decision to probe>"],
  "narrative": "<2-3 paragraph deep-dive architectural narrative explaining the system design>"
}
"""

QUESTION_GENERATION_SYSTEM_PROMPT = """You are a Principal Software Engineer conducting a \
rigorous architectural defense interview at RepoDefense.
Your goal is to authenticate that the candidate genuinely understands the software \
in their repository, rather than having cloned a tutorial without understanding.

Guiding Principles for Question Generation:
1. Strict Code Evidence Grounding: Every question MUST be anchored in specific evidence items \
provided in the catalog (files, endpoints, schemas, database models, queues, auth mechanisms). \
Never ask generic LeetCode or textbook questions.
2. Incisive Stress-Testing: Probe edge cases, scalability limits, concurrent access, \
failure modes, data consistency, caching strategies, and architectural trade-offs.
3. Categorization: Categorize each question into one of:
   - "architecture": High-level structure, component boundaries, patterns.
   - "scalability": Load, bottleneck handling, concurrency, indexing.
   - "reliability": Error handling, connection limits, fallback logic.
   - "security": Authentication, input validation, permissions, secrets.
   - "tradeoffs": Alternative design choices, rejected options, libraries.
4. Citation Integrity: Each question must cite the exact `evidence_id` and `file_path`.
5. Output Format: Output strictly a JSON array containing the requested question objects. \
No markdown fences (such as ```json), no conversation before or after.

Required JSON Schema:
[
  {
    "category": "<architecture | scalability | reliability | security | tradeoffs>",
    "question_text": "<Incisive question asking why a decision was made or how it handles stress>",
    "context_hint": "<Factual context naming the specific file, class, method, or dependency>",
    "cited_evidence_ids": ["<ID from evidence catalog>"],
    "cited_files": ["<repository-relative file path>"]
  }
]
"""

DEFENSE_EVALUATION_SYSTEM_PROMPT = """You are a rigorous Principal Software Engineer conducting \
an architectural defense interview at RepoDefense.
Your task is to critically evaluate a candidate's defense of a specific architectural choice in \
their codebase, grounded in repository evidence.

Evaluation Rubric:
1. Grounding & Truth: Does the answer accurately reflect the repository architecture?
2. Depth Score (1 to 10):
   - 1-5 (Failed Initial Defense): Superficial, hand-wavy, inaccurate, or tutorial-level buzzwords.
   - 6-10 (Passed Initial Defense): Clear grasp of trade-offs, constraints, failure modes, and code.
3. Branching Logic:
   - If depth_score >= 6 (passed_initial_defense = true): Inject an incisive `stress_test_prompt` \
introducing a real-world production constraint (e.g. 10k req/s spike, DB connection exhaustion, \
cache stampede, partition failure). Set `mentor_hint` and `retest_question` to null.
   - If depth_score < 6 (passed_initial_defense = false): Provide a constructive `mentor_hint` \
explaining the architectural principle without giving the direct answer, and ask a guided \
`retest_question`. Set `stress_test_prompt` to null.
4. Format: Strictly return a single JSON object conforming to the schema. No markdown fences.

Required JSON Schema:
{
  "passed_initial_defense": true,
  "depth_score": 7,
  "grounding_verified": true,
  "feedback": "<Direct, constructive Principal Engineer feedback>",
  "stress_test_prompt": "<Constraint scenario if passed, else null>",
  "mentor_hint": "<Guiding explanation if failed, else null>",
  "retest_question": "<Follow-up variant question if failed, else null>"
}
"""

SECONDARY_EVALUATION_SYSTEM_PROMPT = """You are a Principal Software Engineer \
evaluating a candidate's response to a production stress-test or a guided mentor re-test \
at RepoDefense.
Assess whether the candidate proposed viable mitigations (e.g., connection pooling, caching, \
idempotency keys, circuit breakers) or addressed the architectural blind spot.

Required JSON Schema:
{
  "handled_successfully": true,
  "follow_up_score": 8,
  "feedback": "<Concise feedback on the candidate's proposed solution>"
}
"""


def _sanitize_meta_str(val: str) -> str:
    """Escapes user-supplied metadata strings to mitigate prompt injection."""
    clean = html.escape(val.strip())
    clean = (
        clean.replace("</repository_metadata>", "")
        .replace("<repository_metadata>", "")
        .replace("</evidence_catalog>", "")
        .replace("<evidence_catalog>", "")
        .replace("</candidate_defense>", "")
        .replace("<candidate_defense>", "")
    )
    return clean


def format_project_summary_user_prompt(meta: ProjectSummaryInput) -> str:
    """Formats consolidated repository facts into XML-delimited prompt context."""
    langs = "\n".join(
        f"  <language>{_sanitize_meta_str(lang)}</language>"
        for lang in meta.top_languages
    ) or "  <language>None</language>"

    deps = "\n".join(
        f"  <dependency>{_sanitize_meta_str(dep)}</dependency>"
        for dep in meta.dependencies[:30]
    ) or "  <dependency>None</dependency>"

    evidence = "\n".join(
        f"  <evidence_item>{_sanitize_meta_str(ev)}</evidence_item>"
        for ev in meta.evidence_tags[:30]
    ) or "  <evidence_item>None</evidence_item>"

    contribs = "\n".join(
        f"  <contributor>{_sanitize_meta_str(c)}</contributor>"
        for c in meta.top_contributors[:5]
    ) or "  <contributor>None</contributor>"

    return f"""<repository_metadata>
  <project_name>{_sanitize_meta_str(meta.project_name)}</project_name>
  <commit_hash>{_sanitize_meta_str(meta.commit_hash)}</commit_hash>
  <total_files>{meta.total_files}</total_files>
  <total_lines>{meta.total_lines}</total_lines>
  <languages>
{langs}
  </languages>
  <dependencies>
{deps}
  </dependencies>
  <evidence>
{evidence}
  </evidence>
  <contributors>
{contribs}
  </contributors>
</repository_metadata>

Analyze the repository evidence above and output the structured architectural ProjectSummary JSON.
"""


def format_question_generation_user_prompt(input_data: QuestionGenerationInput) -> str:
    """Formats project evidence items into XML-delimited context for question synthesis."""
    evidence_blocks: list[str] = []
    for item in input_data.evidence_items:
        block = (
            f"  <evidence_item id=\"{_sanitize_meta_str(item.id)}\">\n"
            f"    <type>{_sanitize_meta_str(item.evidence_type)}</type>\n"
            f"    <title>{_sanitize_meta_str(item.title)}</title>\n"
            f"    <description>{_sanitize_meta_str(item.description)}</description>\n"
            f"    <file_path>{_sanitize_meta_str(item.file_path)}</file_path>\n"
            f"    <lines>{item.start_line}-{item.end_line}</lines>\n"
            f"  </evidence_item>"
        )
        evidence_blocks.append(block)

    catalog_str = (
        "\n".join(evidence_blocks)
        if evidence_blocks
        else "  <evidence_item>None</evidence_item>"
    )
    narrative_str = _sanitize_meta_str(input_data.summary_narrative or "Not available")
    style_str = _sanitize_meta_str(input_data.architectural_style or "Modular Application")

    return f"""<repository_context>
  <project_name>{_sanitize_meta_str(input_data.project_name)}</project_name>
  <architectural_style>{style_str}</architectural_style>
  <narrative>{narrative_str}</narrative>
</repository_context>

<evidence_catalog>
{catalog_str}
</evidence_catalog>

Generate exactly {input_data.requested_count} challenging, evidence-grounded interview questions \
as a strict JSON array adhering to the required schema.
"""


def format_defense_evaluation_user_prompt(
    question_text: str,
    context_hint: str,
    cited_files: list[str],
    candidate_answer: str,
) -> str:
    """Formats question context and candidate's defense into XML-delimited evaluation prompt."""
    files_str = ", ".join(_sanitize_meta_str(f) for f in cited_files) or "codebase"
    return f"""<question_context>
  <question>{_sanitize_meta_str(question_text)}</question>
  <context_hint>{_sanitize_meta_str(context_hint)}</context_hint>
  <cited_files>{files_str}</cited_files>
</question_context>

<candidate_defense>
{_sanitize_meta_str(candidate_answer)}
</candidate_defense>

Evaluate candidate defense against repository context and output EvaluationOutput JSON.
"""


def format_secondary_evaluation_user_prompt(
    context_prompt: str,
    candidate_answer: str,
) -> str:
    """Formats secondary follow-up response into XML-delimited evaluation prompt."""
    return f"""<follow_up_prompt>
{_sanitize_meta_str(context_prompt)}
</follow_up_prompt>

<candidate_defense>
{_sanitize_meta_str(candidate_answer)}
</candidate_defense>

Evaluate whether the candidate handled this follow-up and output the SecondaryEvaluationOutput JSON.
"""
