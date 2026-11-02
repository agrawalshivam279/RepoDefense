"""Deterministic fallbacks for summaries and questions when LLM is unavailable."""

import uuid
from typing import List

from app.schemas.question import (
    GroundedQuestion,
    QuestionCategory,
    QuestionGenerationInput,
)
from app.schemas.summary import ProjectSummary, ProjectSummaryInput


def build_deterministic_fallback_summary(meta: ProjectSummaryInput) -> ProjectSummary:
    """Constructs a deterministic, evidence-grounded summary when LLM is unavailable."""
    primary_lang = "Unknown"
    if meta.top_languages:
        primary_lang = meta.top_languages[0].split("(")[0].strip()

    title = f"{meta.project_name} Codebase Overview"
    tagline = f"Software project in {primary_lang} with {meta.total_files} analyzed files."

    style = "Modular Application"
    dep_text = " ".join(d.lower() for d in meta.dependencies)
    if any(k in dep_text for k in ["fastapi", "express", "flask"]):
        style = "REST API Service"
    elif any(k in dep_text for k in ["next", "react"]):
        style = "Full-Stack Web Application"

    known_frameworks = ["fastapi", "flask", "django", "next", "react", "express", "torch"]
    frameworks = [
        dep for dep in meta.dependencies
        if any(fw in dep.lower() for fw in known_frameworks)
    ][:5]

    components = meta.evidence_tags[:5] if meta.evidence_tags else ["Core Application Logic"]
    sample_deps = ", ".join(meta.dependencies[:3]) if meta.dependencies else primary_lang

    defense_topics = [
        f"Scalability and dependency lifecycle for primary packages ({sample_deps})",
        "Error handling, input validation, and boundary exception safety across modules",
    ]

    top_authors = (
        ", ".join(meta.top_contributors[:2])
        if meta.top_contributors
        else "the project team"
    )

    narrative = (
        f"{meta.project_name} contains {meta.total_files} source files totaling "
        f"{meta.total_lines} lines of code. The primary language is {primary_lang}. "
        f"Key detected architectural components include: {', '.join(components)}. "
        f"Recent contributions reflect active development led by {top_authors}."
    )

    return ProjectSummary(
        title=title,
        tagline=tagline,
        primary_language=primary_lang,
        detected_frameworks=frameworks,
        architectural_style=style,
        key_components=components,
        potential_defense_topics=defense_topics,
        narrative=narrative,
    )


def build_deterministic_fallback_questions(
    input_data: QuestionGenerationInput,
) -> List[GroundedQuestion]:
    """Generates deterministic, evidence-grounded questions when LLM is unavailable."""
    questions: list[GroundedQuestion] = []
    category_cycle = [
        QuestionCategory.ARCHITECTURE,
        QuestionCategory.SCALABILITY,
        QuestionCategory.RELIABILITY,
        QuestionCategory.SECURITY,
        QuestionCategory.TRADEOFFS,
    ]

    for idx, item in enumerate(input_data.evidence_items):
        cat = category_cycle[idx % len(category_cycle)]
        ev_type = item.evidence_type.lower()

        if "db" in ev_type or "database" in ev_type:
            q_text = (
                f"In `{item.file_path}`, your database configuration defines {item.title}. "
                "How does connection pooling handle high concurrency spikes?"
            )
            cat = QuestionCategory.SCALABILITY
        elif "auth" in ev_type:
            q_text = (
                f"Looking at `{item.file_path}`, what security guarantees prevent token forgery "
                "or unauthorized privilege escalation across protected endpoints?"
            )
            cat = QuestionCategory.SECURITY
        elif "queue" in ev_type:
            q_text = (
                f"In `{item.file_path}`, your queue handles background tasks. "
                "What is your dead-letter and job retry strategy if worker processes crash?"
            )
            cat = QuestionCategory.RELIABILITY
        else:
            q_text = (
                f"In `{item.file_path}`, you implemented {item.title}. "
                "What architectural trade-offs led to this design versus alternative approaches?"
            )

        context_hint = (
            f"Referencing {item.title} in {item.file_path} "
            f"(lines {item.start_line}-{item.end_line})"
        )
        questions.append(
            GroundedQuestion(
                id=str(uuid.uuid4()),
                category=cat,
                question_text=q_text,
                context_hint=context_hint,
                cited_evidence_ids=[item.id],
                cited_files=[item.file_path],
            )
        )

    if not questions:
        questions.append(
            GroundedQuestion(
                id=str(uuid.uuid4()),
                category=QuestionCategory.ARCHITECTURE,
                question_text=(
                    f"How is the overall module boundary structured in {input_data.project_name}, "
                    "and how are shared concerns managed across domain layers?"
                ),
                context_hint="General project architecture",
                cited_evidence_ids=[],
                cited_files=[],
            )
        )

    return questions[:input_data.requested_count]
