"""Deterministic dependency obsolescence, deprecation, and security audit engine."""

import re

from app.schemas.tech_audit import (
    AuditCategory,
    AuditedDependencyItem,
    AuditSeverity,
)

_SEMVER_REGEX = re.compile(r"^[\^~>=<v\s]*(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def parse_semver(version_str: str | None) -> tuple[int, int, int] | None:
    """Extracts (major, minor, patch) integer tuple from a version constraint string."""
    if not version_str or not isinstance(version_str, str):
        return None
    match = _SEMVER_REGEX.search(version_str.strip())
    if not match:
        return None
    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    return (major, minor, patch)


# Deprecated or unmaintained packages regardless of version
_STATIC_PACKAGE_RULES: dict[str, dict[str, str | AuditSeverity | AuditCategory]] = {
    "request": {
        "severity": AuditSeverity.HIGH,
        "category": AuditCategory.DEPRECATED,
        "issue": (
            "Package 'request' was fully deprecated in Feb 2020 and has known "
            "security vulnerabilities."
        ),
        "alternative": "Use native fetch, axios, or undici.",
    },
    "moment": {
        "severity": AuditSeverity.LOW,
        "category": AuditCategory.UNMAINTAINED,
        "issue": "Moment.js is in maintenance-only mode and has large bundle overhead.",
        "alternative": "Use date-fns, dayjs, or native Intl/Temporal.",
    },
    "querystring": {
        "severity": AuditSeverity.LOW,
        "category": AuditCategory.DEPRECATED,
        "issue": "Node.js core 'querystring' module is considered legacy.",
        "alternative": "Use native URLSearchParams API.",
    },
    "flake8": {
        "severity": AuditSeverity.LOW,
        "category": AuditCategory.OUTDATED,
        "issue": "Flake8 uses older AST parsers and slow synchronous inspection.",
        "alternative": "Consider migrating to Ruff for 10-100x faster linting.",
    },
    "pyflakes": {
        "severity": AuditSeverity.LOW,
        "category": AuditCategory.OUTDATED,
        "issue": "Legacy Python syntax inspector.",
        "alternative": "Use Ruff or Flake8.",
    },
}

# Version-based obsolescence and vulnerability thresholds: (min_major, min_minor, min_patch)
_VERSION_RULES: dict[str, dict[str, object]] = {
    "lodash": {
        "min_version": (4, 17, 21),
        "severity": AuditSeverity.CRITICAL,
        "category": AuditCategory.SECURITY_RISK,
        "issue": "Versions < 4.17.21 contain prototype pollution vulnerabilities (CVE-2021-23337).",
        "alternative": "Upgrade to lodash >= 4.17.21 or use native ES2020+ methods.",
    },
    "urllib3": {
        "min_version": (2, 0, 7),
        "severity": AuditSeverity.HIGH,
        "category": AuditCategory.SECURITY_RISK,
        "issue": (
            "Versions < 2.0.7 contain request body injection vulnerabilities "
            "(CVE-2023-45803)."
        ),
        "alternative": "Upgrade to urllib3 >= 2.0.7.",
    },
    "jsonwebtoken": {
        "min_version": (9, 0, 0),
        "severity": AuditSeverity.HIGH,
        "category": AuditCategory.SECURITY_RISK,
        "issue": "Versions < 9.0.0 are vulnerable to algorithm confusion attacks (CVE-2022-23529).",
        "alternative": "Upgrade to jsonwebtoken >= 9.0.0 or use jose.",
    },
    "express": {
        "min_version": (4, 19, 2),
        "severity": AuditSeverity.HIGH,
        "category": AuditCategory.SECURITY_RISK,
        "issue": "Versions < 4.19.2 have open redirect and query string parsing vulnerabilities.",
        "alternative": "Upgrade to express >= 4.19.2 or v5.x.",
    },
    "django": {
        "min_version": (4, 2, 0),
        "severity": AuditSeverity.HIGH,
        "category": AuditCategory.OUTDATED,
        "issue": "Django < 4.2 has reached End-Of-Life and no longer receives security patches.",
        "alternative": "Upgrade to Django 4.2 LTS or 5.x.",
    },
    "react": {
        "min_version": (18, 0, 0),
        "severity": AuditSeverity.MEDIUM,
        "category": AuditCategory.OUTDATED,
        "issue": "React < 18 lacks modern concurrency, server components, and active support.",
        "alternative": "Upgrade to React 18 or 19.",
    },
    "pydantic": {
        "min_version": (2, 0, 0),
        "severity": AuditSeverity.MEDIUM,
        "category": AuditCategory.OUTDATED,
        "issue": "Pydantic v1 is legacy and lacks the Rust-powered core and V2 performance.",
        "alternative": "Upgrade to Pydantic v2.",
    },
    "flask": {
        "min_version": (2, 3, 0),
        "severity": AuditSeverity.MEDIUM,
        "category": AuditCategory.OUTDATED,
        "issue": "Flask < 2.3 is out of support and misses modern async request handlers.",
        "alternative": "Upgrade to Flask >= 3.0 or FastAPI.",
    },
    "axios": {
        "min_version": (1, 6, 0),
        "severity": AuditSeverity.MEDIUM,
        "category": AuditCategory.SECURITY_RISK,
        "issue": "Axios < 1.6.0 vulnerable to SSRF / header injection (CVE-2023-45857).",
        "alternative": "Upgrade to axios >= 1.7.4.",
    },
}


def audit_dependency(
    name: str,
    version: str | None,
    is_dev: bool = False,
) -> AuditedDependencyItem | None:
    """Evaluates a single dependency name and version against known audit rules."""
    pkg_clean = name.strip().lower()

    # 1. Check static package rules
    if pkg_clean in _STATIC_PACKAGE_RULES:
        rule = _STATIC_PACKAGE_RULES[pkg_clean]
        return AuditedDependencyItem(
            name=name,
            version=version,
            is_dev=is_dev,
            severity=rule["severity"],  # type: ignore
            category=rule["category"],  # type: ignore
            issue_description=str(rule["issue"]),
            suggested_alternative=str(rule["alternative"]),
        )

    # 2. Check version-based rules
    if pkg_clean in _VERSION_RULES:
        rule_v = _VERSION_RULES[pkg_clean]
        min_v = rule_v["min_version"]  # tuple of (major, minor, patch)
        parsed = parse_semver(version)

        # If version is missing, or parsed version is strictly below minimum required version
        if parsed is None or parsed < min_v:  # type: ignore
            return AuditedDependencyItem(
                name=name,
                version=version,
                is_dev=is_dev,
                severity=rule_v["severity"],  # type: ignore
                category=rule_v["category"],  # type: ignore
                issue_description=str(rule_v["issue"]),
                suggested_alternative=str(rule_v["alternative"]),
            )

    return None


def calculate_tech_health_score(
    critical_count: int,
    high_count: int,
    medium_count: int,
    low_count: int,
    total_count: int,
) -> int:
    """Calculates an architectural technology health score (0 - 100%)."""
    if total_count == 0:
        return 100

    deductions = (
        (critical_count * 25)
        + (high_count * 15)
        + (medium_count * 8)
        + (low_count * 3)
    )
    score = max(0, 100 - deductions)
    return score


def audit_dependencies_list(
    dependencies: list[tuple[str, str | None, bool]],
) -> tuple[list[AuditedDependencyItem], int, dict[str, int]]:
    """Evaluates an array of dependencies and returns flagged items, score, and counts."""
    flagged: list[AuditedDependencyItem] = []
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for name, version, is_dev in dependencies:
        item = audit_dependency(name, version, is_dev)
        if item:
            flagged.append(item)
            counts[item.severity.value] += 1

    health_score = calculate_tech_health_score(
        critical_count=counts["critical"],
        high_count=counts["high"],
        medium_count=counts["medium"],
        low_count=counts["low"],
        total_count=len(dependencies),
    )

    return flagged, health_score, counts
