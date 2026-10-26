from pathlib import Path
from typing import Optional

import structlog
import yaml

from app.analyzers.dependencies.base import BaseDependencyParser, DependencyMetadata

logger = structlog.get_logger(__name__)


def parse_dockerfile(
    content: str,
    file_path: str = "Dockerfile",
) -> list[DependencyMetadata]:
    """Parses base images and build stages from Dockerfile."""
    dependencies: list[DependencyMetadata] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line.upper().startswith("FROM "):
            continue

        parts = [p for p in line[5:].strip().split() if not p.startswith("--")]
        if not parts:
            continue

        img_spec = parts[0].strip()
        if img_spec.lower() in ("scratch", ""):
            continue

        stage_name: Optional[str] = None
        if len(parts) >= 3 and parts[1].upper() == "AS":
            stage_name = parts[2].strip().lower()

        is_dev = False
        if stage_name:
            is_dev = any(dev_token in stage_name for dev_token in ("build", "test", "dev", "lint"))

        if ":" in img_spec:
            pkg_name, version = img_spec.split(":", 1)
        else:
            pkg_name, version = img_spec, "latest"

        dependencies.append(
            DependencyMetadata(
                name=pkg_name.strip().lower(),
                version=version.strip(),
                source_file=file_path,
                is_dev=is_dev,
            )
        )

    logger.info("dockerfile_parsed", file_path=file_path, count=len(dependencies))
    return dependencies


def parse_docker_compose(
    content: str,
    file_path: str = "docker-compose.yml",
) -> list[DependencyMetadata]:
    """Parses service images and build targets from docker-compose.yml."""
    dependencies: list[DependencyMetadata] = []
    try:
        data = yaml.safe_load(content)
    except Exception as exc:
        logger.error("docker_compose_parse_failed", file_path=file_path, error=str(exc))
        return []

    if not isinstance(data, dict):
        return []

    services = data.get("services", {})
    if not isinstance(services, dict):
        return []

    for service_name, service_config in services.items():
        if not isinstance(service_config, dict):
            continue

        image = service_config.get("image")
        if image and isinstance(image, str):
            clean_img = image.strip()
            if ":" in clean_img:
                pkg_name, version = clean_img.split(":", 1)
            else:
                pkg_name, version = clean_img, "latest"

            dependencies.append(
                DependencyMetadata(
                    name=pkg_name.strip().lower(),
                    version=version.strip(),
                    source_file=file_path,
                    is_dev=False,
                )
            )
        elif "build" in service_config:
            dependencies.append(
                DependencyMetadata(
                    name=str(service_name).strip().lower(),
                    version="local-build",
                    source_file=file_path,
                    is_dev=False,
                )
            )

    logger.info("docker_compose_parsed", file_path=file_path, count=len(dependencies))
    return dependencies


def parse_github_actions_workflow(
    content: str,
    file_path: str,
) -> list[DependencyMetadata]:
    """Parses external GitHub Actions used in workflow steps."""
    dependencies: list[DependencyMetadata] = []
    seen: set[tuple[str, str]] = set()

    try:
        data = yaml.safe_load(content)
    except Exception as exc:
        logger.error("github_actions_parse_failed", file_path=file_path, error=str(exc))
        return []

    if not isinstance(data, dict):
        return []

    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return []

    for _, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue

        steps = job_config.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                if uses and isinstance(uses, str):
                    clean_uses = uses.strip()
                    if clean_uses.startswith("./") or clean_uses.startswith("docker://"):
                        continue
                    if "@" in clean_uses:
                        action_name, version = clean_uses.split("@", 1)
                    else:
                        action_name, version = clean_uses, "latest"

                    pair = (action_name.strip().lower(), version.strip())
                    if pair not in seen:
                        seen.add(pair)
                        dependencies.append(
                            DependencyMetadata(
                                name=pair[0],
                                version=pair[1],
                                source_file=file_path,
                                is_dev=True,
                            )
                        )

    logger.info("github_actions_parsed", file_path=file_path, count=len(dependencies))
    return dependencies


class InfraDependencyParser(BaseDependencyParser):
    """Deterministic parser for infrastructure, container, and CI/CD configurations."""

    def parse(self, content_str: str, file_path: str) -> list[DependencyMetadata]:
        """Dispatches configuration content to the appropriate specialized parser."""
        normalized_path = Path(file_path).as_posix().lower()
        if "workflows" in normalized_path:
            return parse_github_actions_workflow(content_str, file_path=file_path)
        if "compose" in normalized_path:
            return parse_docker_compose(content_str, file_path=file_path)
        return parse_dockerfile(content_str, file_path=file_path)
