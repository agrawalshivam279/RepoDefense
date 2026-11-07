import posixpath

from app.schemas.architecture import (
    ArchitecturalRisk,
    ArchitecturePatternType,
    DetectedPattern,
    PatternConfidenceTier,
    PatternIndicator,
)


def get_confidence_tier(score: float) -> PatternConfidenceTier:
    """Categorize confidence score into High, Moderate, or Low."""
    if score >= 0.75:
        return PatternConfidenceTier.HIGH
    if score >= 0.45:
        return PatternConfidenceTier.MODERATE
    return PatternConfidenceTier.LOW


def _ind(itype: str, desc: str, weight: float, matched: list[str]) -> PatternIndicator:
    return PatternIndicator(
        indicator_type=itype,
        description=desc,
        weight=round(weight, 2),
        matched_items=matched,
    )


def normalize_directory_tokens(file_paths: list[str]) -> tuple[dict[str, int], set[str]]:
    """Extract directory frequency counts and top-level module names."""
    dir_counts: dict[str, int] = {}
    top_dirs: set[str] = set()

    for raw_path in file_paths:
        norm = posixpath.normpath(raw_path.replace("\\", "/"))
        parts = [p.lower() for p in norm.split("/") if p and p not in {".", ".."}]
        if not parts:
            continue
        if len(parts) > 1:
            top_dirs.add(parts[0])
            for part in parts[:-1]:
                dir_counts[part] = dir_counts.get(part, 0) + 1
        else:
            dir_counts["<root>"] = dir_counts.get("<root>", 0) + 1

    return dir_counts, top_dirs


def eval_modular_monolith(
    top_dirs: set[str], dir_counts: dict[str, int], deps: set[str]
) -> DetectedPattern:
    """Evaluate signals for frontend/backend or multi-package modular monolith."""
    indicators: list[PatternIndicator] = []
    score = 0.0

    duo = {"frontend", "backend"} if {"frontend", "backend"}.issubset(top_dirs) else set()
    duo = duo or ({"client", "server"} if {"client", "server"}.issubset(top_dirs) else set())
    has_packages = top_dirs.intersection({"packages", "apps", "modules", "libs"})

    if duo:
        score += 0.55
        indicators.append(
            _ind("directory", "Top-level client/server or fullstack modules", 0.55, list(duo))
        )
    elif has_packages:
        score += 0.45
        indicators.append(
            _ind("directory", "Monorepo or multi-package topology", 0.45, list(has_packages))
        )

    full_stack_deps = deps.intersection({"fastapi", "next", "react", "vue", "django", "express"})
    if len(full_stack_deps) >= 2:
        score += 0.30
        indicators.append(
            _ind("dependency", "Multi-tier framework dependencies", 0.30, list(full_stack_deps))
        )

    final = min(1.0, round(score, 2))
    return DetectedPattern(
        pattern_type=ArchitecturePatternType.MODULAR_MONOLITH,
        pattern_name="Modular Monolith",
        confidence_score=final,
        tier=get_confidence_tier(final),
        summary="Unified codebase structured into isolated, decoupled functional modules or tiers.",
        indicators=indicators,
    )


def eval_mvc(dir_counts: dict[str, int], deps: set[str]) -> DetectedPattern:
    """Evaluate Model-View-Controller pattern signals."""
    indicators: list[PatternIndicator] = []
    score = 0.0

    dirs = {"controllers", "models", "views", "templates"}.intersection(dir_counts.keys())
    if len(dirs) >= 2:
        w = round(0.30 * len(dirs), 2)
        score += w
        indicators.append(_ind("directory", "Standard MVC directory structure", w, list(dirs)))

    mvc_deps = deps.intersection({"django", "rails", "express", "laravel", "spring", "nestjs"})
    if mvc_deps:
        score += 0.30
        indicators.append(_ind("dependency", "Classic MVC web framework", 0.30, list(mvc_deps)))

    final = min(1.0, round(score, 2))
    return DetectedPattern(
        pattern_type=ArchitecturePatternType.MVC,
        pattern_name="Model-View-Controller (MVC)",
        confidence_score=final,
        tier=get_confidence_tier(final),
        summary="Separation of application data, user presentation, and incoming request routing.",
        indicators=indicators,
    )


def eval_clean_architecture(dir_counts: dict[str, int]) -> DetectedPattern:
    """Evaluate Clean or Hexagonal Architecture domain separation signals."""
    indicators: list[PatternIndicator] = []
    score = 0.0

    core = {"domain", "core", "entities"}.intersection(dir_counts.keys())
    adapters = {"ports", "adapters", "use_cases", "interfaces"}.intersection(dir_counts.keys())

    if core and adapters:
        score += 0.75
        indicators.append(
            _ind("directory", "Hexagonal / Clean boundary separation", 0.75, list(core | adapters))
        )
    elif core or adapters:
        score += 0.40
        indicators.append(
            _ind("directory", "Partial domain or adapter layer", 0.40, list(core | adapters))
        )

    final = min(1.0, round(score, 2))
    return DetectedPattern(
        pattern_type=ArchitecturePatternType.CLEAN_ARCHITECTURE,
        pattern_name="Clean / Hexagonal Architecture",
        confidence_score=final,
        tier=get_confidence_tier(final),
        summary="Domain-centric architecture isolating business logic from external frameworks.",
        indicators=indicators,
    )


def eval_event_driven(
    dir_counts: dict[str, int], deps: set[str], evidence_types: set[str]
) -> DetectedPattern:
    """Evaluate asynchronous event-driven or background queue architecture."""
    indicators: list[PatternIndicator] = []
    score = 0.0

    dirs = {"workers", "consumers", "events", "queues", "subscribers"}.intersection(
        dir_counts.keys()
    )
    if dirs:
        score += 0.40
        indicators.append(
            _ind("directory", "Asynchronous worker or event directories", 0.40, list(dirs))
        )

    q_deps = deps.intersection({"arq", "celery", "redis", "aiokafka", "kafka", "pika", "bullmq"})
    if q_deps:
        score += 0.35
        indicators.append(_ind("dependency", "Message broker or queue client", 0.35, list(q_deps)))

    if "queue" in evidence_types:
        score += 0.20
        indicators.append(_ind("evidence", "Background queue evidence", 0.20, ["queue"]))

    final = min(1.0, round(score, 2))
    return DetectedPattern(
        pattern_type=ArchitecturePatternType.EVENT_DRIVEN,
        pattern_name="Event-Driven / Worker Queue",
        confidence_score=final,
        tier=get_confidence_tier(final),
        summary=(
            "Decoupled asynchronous processing driven by message brokers or background workers."
        ),
        indicators=indicators,
    )


def eval_layered_architecture(dir_counts: dict[str, int]) -> DetectedPattern:
    """Evaluate traditional N-tier horizontal layered separation."""
    indicators: list[PatternIndicator] = []
    score = 0.0

    layers = {"api", "routes", "services", "repositories", "dao", "models"}.intersection(
        dir_counts.keys()
    )
    if len(layers) >= 2:
        score = min(0.85, 0.25 * len(layers))
        indicators.append(
            _ind(
                "directory",
                "N-tier horizontal separation (API, Service, Data)",
                score,
                list(layers),
            )
        )

    final = min(1.0, round(score, 2))
    return DetectedPattern(
        pattern_type=ArchitecturePatternType.LAYERED_ARCHITECTURE,
        pattern_name="Layered (N-Tier) Architecture",
        confidence_score=final,
        tier=get_confidence_tier(final),
        summary="Traditional horizontal layer separation between presentation, logic, and data.",
        indicators=indicators,
    )


def detect_architectural_risks(
    dir_counts: dict[str, int], file_count: int, deps: set[str], evidence_types: set[str]
) -> list[ArchitecturalRisk]:
    """Detect structural smells, flat hierarchies, and missing layer separations."""
    risks: list[ArchitecturalRisk] = []

    root_files = dir_counts.get("<root>", 0)
    if root_files >= 15:
        risks.append(
            ArchitecturalRisk(
                risk_id="FLAT_ROOT_HIERARCHY",
                severity="high",
                title="Unstructured Root Directory",
                description=(
                    f"Repository has {root_files} files directly in root without module grouping."
                ),
                recommendation="Extract code into functional domains or layered directories.",
            )
        )

    api_dirs = dir_counts.get("api", 0) + dir_counts.get("routes", 0)
    service_dirs = dir_counts.get("services", 0) + dir_counts.get("use_cases", 0)
    if api_dirs >= 4 and service_dirs == 0:
        risks.append(
            ArchitecturalRisk(
                risk_id="FAT_ROUTER_MISSING_SERVICES",
                severity="medium",
                title="Router Logic Without Service Layer",
                description="Multiple API route files exist without a dedicated service layer.",
                recommendation="Introduce service classes or use cases to decouple business logic.",
            )
        )

    has_db = "database" in evidence_types or bool(deps.intersection({"sqlalchemy", "prisma", "pg"}))
    has_queue = "queue" in evidence_types or bool(
        deps.intersection({"arq", "celery", "bullmq", "redis"})
    )
    if has_db and not has_queue and file_count >= 25:
        risks.append(
            ArchitecturalRisk(
                risk_id="UNISOLATED_BACKGROUND_TASKS",
                severity="low",
                title="Synchronous Database Execution Bottleneck",
                description=(
                    "High file volume and relational DB usage without a background job queue."
                ),
                recommendation=(
                    "Consider offloading compute-intensive queries to an asynchronous queue."
                ),
            )
        )

    return risks
