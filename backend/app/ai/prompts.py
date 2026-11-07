"""Centralized system and task prompts for RepoDefense AI persona and workflows."""

import html
from typing import Any

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
Principles: 1. Strict evidence grounding. 2. Incisive stress-testing. \
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
3. Branching: If depth >=6, provide stress_test_prompt. If depth <6, mentor_hint & retest_question.
4. Pushback Detection: If answer is superficial, vague, evades details, or uses buzzwords \
without substance, set is_vague=true and provide pushback_prompt demanding code mechanisms.
5. Output strictly a single JSON object conforming to schema.

Schema:
{"passed_initial_defense":true,"depth_score":7,"grounding_verified":true,\
"feedback":"<str>","stress_test_prompt":"<str|null>","mentor_hint":"<str|null>",\
"retest_question":"<str|null>","is_vague":false,"pushback_prompt":"<str|null>"}
"""

SECONDARY_EVALUATION_SYSTEM_PROMPT = """You are a Principal Software Engineer evaluating a \
candidate's response to a production stress-test or mentor re-test at RepoDefense.
Assess whether the candidate proposed viable mitigations (pooling, caching, idempotency, fallbacks).

Schema:
{"handled_successfully":true,"follow_up_score":8,"feedback":"<str>"}
"""

DEFENSE_REPORT_SYSTEM_PROMPT = """You are a rigorous Principal Software Engineer conducting an \
executive architectural review at RepoDefense. Synthesize completed interview into an objective \
report.
Principles: 1. Verdict ("Certified Principal Defense"|"Solid Architectural Defense"|\
"Remediation Required"). 2. Key Strengths: 2-4 concrete technical decisions. \
3. Critical Blind Spots: 2-4 failure modes missed. 4. Actionable Recommendations: 2-4 mitigations. \
5. Output strictly a single JSON object without fences.

Schema:
{"verdict":"<str>","summary":"<str>","key_strengths":["<str>"],\
"critical_blind_spots":["<str>"],"actionable_recommendations":["<str>"]}
"""

CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are a rigorous Principal Software Engineer at RepoDefense.
Analyze candidate's resume/profile to extract concrete, verifiable technical claims.
Principles: 1. Extract ONLY verifiable technical statements regarding architecture, scalability, \
performance, database design, security, frameworks, or infrastructure.
2. Filter out fluffy buzzwords and soft skills. 3. Categorize into domain enum.
4. Extract specific tools/technologies cited. 5. Output JSON array without markdown fences.

Schema:
[{"statement":"<str>","category":"<cat>","technologies":["<tech>"],"verifiable":true,\
"source_context":"<original resume excerpt>"}]
"""

CLAIM_VERIFICATION_SYSTEM_PROMPT = """You are a rigorous Principal Software Engineer at RepoDefense.
Verify whether a candidate's technical claim is supported, contradicted, or unverifiable \
based strictly on provided repository code chunks, architecture evidence, and dependencies.
Principles:
1. Grounding: If evidence directly supports claim with code/architecture, status is "supported" \
(confidence 0.70-1.00). Cite exact file_path and relevant line/symbol.
2. Contradiction: If code demonstrates contrary patterns (e.g. claimed Redis but uses raw \
un-cached DB; claimed GraphQL but only REST exists), status is "contradicted" \
(confidence 0.65-1.00).
3. Unverifiable: If code contains neither proof nor refutation, status is "unverifiable" \
(confidence 0.50-0.90).
4. No hallucination: NEVER cite files or lines not present in <codebase_evidence>.
5. Suggested questions: Provide 1-2 follow-up interview questions to stress-test candidate depth.
6. Output strictly a single JSON object conforming to schema without markdown fences.

Schema:
{"claim_id":"<id>","statement":"<statement>","status":"supported|contradicted|unverifiable",\
"confidence_score":0.85,"reasoning":"<explanation>",\
"citations":[{"file_path":"<path>","start_line":10,"end_line":45,"symbol_name":"<sym>",\
"snippet":"<snippet>","relevance_score":0.9,"source_type":"code_chunk|evidence|dependency"}],\
"suggested_defense_questions":["<q1>","<q2>"]}
"""


def _sanitize_meta_str(val: str) -> str:
    """Escapes user-supplied metadata strings to mitigate prompt injection."""
    clean = html.escape(val.strip())
    for tag in [
        "repository_metadata", "evidence_catalog", "candidate_defense",
        "candidate_transcript", "interview_overview", "resume_text",
        "claim", "codebase_evidence",
    ]:
        clean = clean.replace(f"</{tag}>", "").replace(f"<{tag}>", "")
    return clean


def format_project_summary_user_prompt(meta: ProjectSummaryInput) -> str:
    """Formats consolidated repository facts into XML-delimited prompt context."""
    langs = "\n".join(
        f"  <language>{_sanitize_meta_str(lang)}</language>" for lang in meta.top_languages
    ) or "  <language>None</language>"
    deps = "\n".join(
        f"  <dependency>{_sanitize_meta_str(d)}</dependency>" for d in meta.dependencies[:30]
    ) or "  <dependency>None</dependency>"
    evidence = "\n".join(
        f"  <evidence_item>{_sanitize_meta_str(e)}</evidence_item>" for e in meta.evidence_tags[:30]
    ) or "  <evidence_item>None</evidence_item>"
    contribs = "\n".join(
        f"  <contributor>{_sanitize_meta_str(c)}</contributor>" for c in meta.top_contributors[:5]
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

Analyze the repository evidence above and output structured ProjectSummary JSON."""


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
Generate exactly {input_data.requested_count} questions as a strict JSON array."""


def format_defense_evaluation_user_prompt(
    question_text: str, context_hint: str, cited_files: list[str], candidate_answer: str,
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
Evaluate candidate defense against repository context and output EvaluationOutput JSON."""


def format_secondary_evaluation_user_prompt(context_prompt: str, candidate_answer: str) -> str:
    """Formats secondary follow-up response into XML-delimited evaluation prompt."""
    return f"""<follow_up_prompt>
{_sanitize_meta_str(context_prompt)}
</follow_up_prompt>
<candidate_defense>
{_sanitize_meta_str(candidate_answer)}
</candidate_defense>
Evaluate whether candidate handled this follow-up and output SecondaryEvaluationOutput JSON."""


def format_defense_report_user_prompt(overview: str, transcript: str) -> str:
    """Formats interview results into XML-delimited evaluation prompt."""
    return f"""<interview_overview>
{_sanitize_meta_str(overview)}
</interview_overview>
<candidate_transcript>
{_sanitize_meta_str(transcript)}
</candidate_transcript>
Synthesize final architectural evaluation report and output JSON adhering to schema."""


def format_claim_extraction_user_prompt(resume_text: str) -> str:
    """Formats resume text into XML-delimited prompt for technical claim extraction."""
    return f"""<resume_text>
{_sanitize_meta_str(resume_text)}
</resume_text>
Extract all concrete technical claims from resume text above and output strictly a JSON array."""


def format_claim_verification_user_prompt(
    claim_id: str,
    statement: str,
    category: str,
    technologies: list[str],
    chunks: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
    dependencies: list[str],
) -> str:
    """Formats technical claim and retrieved repository evidence into XML-delimited prompt."""
    tech_str = ", ".join(_sanitize_meta_str(t) for t in technologies) or "None cited"
    deps_str = ", ".join(_sanitize_meta_str(d) for d in dependencies[:30]) or "None detected"

    chunk_blocks = [
        f"  <code_chunk file=\"{_sanitize_meta_str(c.get('file_path', ''))}\" "
        f"similarity=\"{c.get('similarity', 0.0):.2f}\">\n"
        f"    {_sanitize_meta_str(c.get('chunk_content', ''))[:400]}\n"
        f"  </code_chunk>"
        for c in chunks[:5]
    ]
    chunks_xml = "\n".join(chunk_blocks) if chunk_blocks else (
        "  <code_chunk>No chunks retrieved</code_chunk>"
    )

    ev_blocks = [
        f"  <arch_evidence type=\"{_sanitize_meta_str(e.get('evidence_type', ''))}\" "
        f"file=\"{_sanitize_meta_str(e.get('file_path', ''))}\">\n"
        f"    {_sanitize_meta_str(e.get('title', ''))}: "
        f"{_sanitize_meta_str(e.get('description', ''))}\n"
        f"  </arch_evidence>"
        for e in evidence_items[:5]
    ]
    ev_xml = "\n".join(ev_blocks) if ev_blocks else "  <arch_evidence>None recorded</arch_evidence>"

    return f"""<claim id="{_sanitize_meta_str(claim_id)}" category="{_sanitize_meta_str(category)}">
  <statement>{_sanitize_meta_str(statement)}</statement>
  <claimed_technologies>{tech_str}</claimed_technologies>
</claim>
<codebase_evidence>
  <project_dependencies>{deps_str}</project_dependencies>
  <semantic_code_chunks>
{chunks_xml}
  </semantic_code_chunks>
  <architectural_evidence>
{ev_xml}
  </architectural_evidence>
</codebase_evidence>
Evaluate whether code evidence supports, contradicts, or cannot verify claim. Output JSON."""

MERMAID_DIAGRAM_SYSTEM_PROMPT = """You are a Principal Software Engineer at RepoDefense.
Synthesize repository dependencies and evidence into an elegant Mermaid flowchart (flowchart TD).
Rules:
1. First line must be strictly "flowchart TD".
2. Group nodes into subgraphs (subgraph <TierName> ... end) for:
   - Frontend / Client Tier
   - API / Backend Service Tier
   - Asynchronous Queues / Workers Tier (if present)
   - Persistence / Cache Tier
   - External Services / Auth Tier
3. Use alphanumeric node IDs with underscores (e.g. client_web, api_fastapi, db_postgres).
4. ALWAYS quote node labels: id["Label Text"]. Never use unquoted parentheses or brackets.
5. Create logical directional edges (e.g. client_web --> api_fastapi --> db_postgres).
6. Output strictly a single JSON object without markdown fences:
{"diagram_type":"flowchart TD","mermaid_code":"<raw_mermaid_code>","summary":"<summary_text>"}
"""


def format_mermaid_diagram_user_prompt(
    project_name: str,
    dependencies: list[str],
    evidence_tags: list[str],
    top_directories: list[str],
) -> str:
    """Formats dependencies and architecture evidence into XML prompt for Mermaid diagram."""
    deps_str = ", ".join(_sanitize_meta_str(d) for d in dependencies[:30]) or "None"
    ev_str = ", ".join(_sanitize_meta_str(e) for e in evidence_tags[:25]) or "None"
    dirs_str = ", ".join(_sanitize_meta_str(d) for d in top_directories[:15]) or "None"
    return f"""<repository_architecture project="{_sanitize_meta_str(project_name)}">
  <top_directories>{dirs_str}</top_directories>
  <dependencies>{deps_str}</dependencies>
  <architectural_evidence>{ev_str}</architectural_evidence>
</repository_architecture>
Generate a valid Mermaid flowchart TD diagram for this repository. Output strict JSON."""
