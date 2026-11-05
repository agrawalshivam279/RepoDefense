"""Centralized system and task prompts for RepoDefense AI persona and workflows."""

import html

from app.schemas.question import QuestionGenerationInput
from app.schemas.summary import ProjectSummaryInput

PROJECT_SUMMARY_SYSTEM_PROMPT = """You are a rigorous Principal Software Engineer at RepoDefense.
Analyze metadata extracted from a cloned and scanned repository to produce a structured summary.
Principles: 1. Ground claims in evidence. 2. Identify core purpose and architecture style. \
3. Highlight load-bearing components and stress points. 4. Output strictly a single JSON object.

Schema:
{"title":"<str>","tagline":"<str>","primary_language":"<str>","detected_frameworks":["<str>"],\
"architectural_style":"<str>","key_components":["<str>"],"potential_defense_topics":["<str>"],\
"narrative":"<str>"}
"""

QUESTION_GENERATION_SYSTEM_PROMPT = """You are a Principal Software Engineer conducting an \
architectural defense interview at RepoDefense. Authenticate candidate understanding.
Principles: 1. Strict evidence grounding (no generic questions). 2. Incisive stress-testing. \
3. Categorize into architecture, scalability, reliability, security, tradeoffs. \
4. Cite exact evidence_id and file_path. 5. Output strictly a JSON array without markdown fences.

Schema:
[{"category":"<cat>","question_text":"<str>","context_hint":"<str>",\
"cited_evidence_ids":["<id>"],"cited_files":["<path>"]}]
"""

DEFENSE_EVALUATION_SYSTEM_PROMPT = """You are a Principal Software Engineer evaluating a \
candidate's defense of their architectural choices at RepoDefense.
Rubric:
1. Grounding: Does the answer reflect the repository architecture?
2. Depth Score (1-10): >=6 passes initial defense, <6 fails.
3. Branching: If depth >=6, provide incisive stress_test_prompt with a production constraint. \
If depth <6, provide mentor_hint explaining principle and a retest_question.
4. Output strictly a single JSON object conforming to schema.

Schema:
{"passed_initial_defense":true,"depth_score":7,"grounding_verified":true,\
"feedback":"<str>","stress_test_prompt":"<str|null>","mentor_hint":"<str|null>",\
"retest_question":"<str|null>"}
"""

SECONDARY_EVALUATION_SYSTEM_PROMPT = """You are a Principal Software Engineer evaluating a \
candidate's response to a production stress-test or mentor re-test at RepoDefense.
Assess whether the candidate proposed viable mitigations (pooling, caching, idempotency, fallbacks).

Schema:
{"handled_successfully":true,"follow_up_score":8,"feedback":"<str>"}
"""

DEFENSE_REPORT_SYSTEM_PROMPT = """You are a rigorous Principal Software Engineer conducting an \
executive architectural review at RepoDefense.
Synthesize the completed interview dialogue and scores into an objective, evidence-grounded report.
Principles:
1. Verdict: "Certified Principal Defense", "Solid Architectural Defense", or "Remediation Required".
2. Key Strengths: 2-4 concrete technical decisions where candidate demonstrated maturity.
3. Critical Blind Spots: 2-4 failure modes or trade-offs candidate missed under stress.
4. Actionable Recommendations: 2-4 pragmatic engineering mitigations (e.g. pooling, caching).
5. Output strictly a single JSON object. No markdown fences.

Schema:
{"verdict":"<str>","summary":"<str>","key_strengths":["<str>"],\
"critical_blind_spots":["<str>"],"actionable_recommendations":["<str>"]}
"""

CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are a rigorous Principal Software Engineer at RepoDefense.
Analyze the candidate's resume/profile to extract concrete, verifiable technical claims.
Principles:
1. Extract ONLY verifiable technical statements regarding architecture, scalability, \
performance, database design, security, frameworks, or infrastructure.
2. Filter out fluffy buzzwords, soft skills, and generic task descriptions.
3. Categorize each claim into one of: architecture, scalability, performance, database, \
security, framework, infrastructure.
4. Extract specific tools/technologies cited in each claim (e.g. ["Redis", "Kafka", "PostgreSQL"]).
5. Output strictly a JSON array of claim objects without markdown fences.

Schema:
[{"statement":"<str>","category":"<cat>","technologies":["<tech>"],"verifiable":true,\
"source_context":"<original resume excerpt>"}]
"""


def _sanitize_meta_str(val: str) -> str:
    """Escapes user-supplied metadata strings to mitigate prompt injection."""
    clean = html.escape(val.strip())
    for tag in [
        "repository_metadata",
        "evidence_catalog",
        "candidate_defense",
        "candidate_transcript",
        "interview_overview",
        "resume_text",
    ]:
        clean = clean.replace(f"</{tag}>", "").replace(f"<{tag}>", "")
    return clean


def format_project_summary_user_prompt(meta: ProjectSummaryInput) -> str:
    """Formats consolidated repository facts into XML-delimited prompt context."""
    langs = "\n".join(
        f"  <language>{_sanitize_meta_str(lang)}</language>"
        for lang in meta.top_languages
    ) or "  <language>None</language>"
    deps = "\n".join(
        f"  <dependency>{_sanitize_meta_str(d)}</dependency>"
        for d in meta.dependencies[:30]
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
  <languages>\n{langs}\n  </languages>
  <dependencies>\n{deps}\n  </dependencies>
  <evidence>\n{evidence}\n  </evidence>
  <contributors>\n{contribs}\n  </contributors>
</repository_metadata>

Analyze the repository evidence above and output structured ProjectSummary JSON.
"""


def format_question_generation_user_prompt(input_data: QuestionGenerationInput) -> str:
    """Formats project evidence items into XML-delimited context for question synthesis."""
    blocks = [
        f"  <evidence_item id=\"{_sanitize_meta_str(it.id)}\">\n"
        f"    <type>{_sanitize_meta_str(it.evidence_type)}</type>\n"
        f"    <title>{_sanitize_meta_str(it.title)}</title>\n"
        f"    <description>{_sanitize_meta_str(it.description)}</description>\n"
        f"    <file_path>{_sanitize_meta_str(it.file_path)}</file_path>\n"
        f"    <lines>{it.start_line}-{it.end_line}</lines>\n"
        f"  </evidence_item>"
        for it in input_data.evidence_items
    ]
    catalog = "\n".join(blocks) if blocks else "  <evidence_item>None</evidence_item>"
    narrative = _sanitize_meta_str(input_data.summary_narrative or "Not available")
    style = _sanitize_meta_str(input_data.architectural_style or "Modular Application")

    return f"""<repository_context>
  <project_name>{_sanitize_meta_str(input_data.project_name)}</project_name>
  <architectural_style>{style}</architectural_style>
  <narrative>{narrative}</narrative>
</repository_context>

<evidence_catalog>
{catalog}
</evidence_catalog>

Generate exactly {input_data.requested_count} questions as a strict JSON array.
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

Evaluate whether the candidate handled this follow-up and output SecondaryEvaluationOutput JSON.
"""


def format_defense_report_user_prompt(
    overview: str,
    transcript: str,
) -> str:
    """Formats interview results into XML-delimited evaluation prompt."""
    return f"""<interview_overview>
{_sanitize_meta_str(overview)}
</interview_overview>

<candidate_transcript>
{_sanitize_meta_str(transcript)}
</candidate_transcript>

Synthesize final architectural evaluation report and output JSON adhering to schema.
"""


def format_claim_extraction_user_prompt(resume_text: str) -> str:
    """Formats resume text into XML-delimited prompt for technical claim extraction."""
    return f"""<resume_text>
{_sanitize_meta_str(resume_text)}
</resume_text>

Extract all concrete technical claims from the resume text above and output strictly a JSON array.
"""
