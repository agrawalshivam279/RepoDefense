"""Centralized system and task prompts for RepoDefense AI persona and workflows."""

import html

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


def _sanitize_meta_str(val: str) -> str:
    """Escapes user-supplied metadata strings to mitigate prompt injection."""
    clean = html.escape(val.strip())
    # Strip any attempt to close XML boundary tags
    clean = clean.replace("</repository_metadata>", "").replace("<repository_metadata>", "")
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
