"""Deterministic Mermaid diagram builder and architectural tier classifier."""

import html
import re

from app.schemas.diagram import DiagramEdge, DiagramNode


def sanitize_node_id(raw_name: str) -> str:
    """Sanitizes strings into valid Mermaid alphanumeric node IDs."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name.strip()).strip("_")
    if not cleaned:
        cleaned = "node"
    if cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned.lower()


def sanitize_node_label(raw_label: str) -> str:
    """Escapes quotes and HTML characters for safe Mermaid node labels."""
    safe = html.escape(raw_label.replace('"', "'").replace("\n", " ").strip())
    return safe[:60]


def classify_tier(item_name: str) -> tuple[str, str]:
    """Classifies a package or directory into an architectural tier and node type."""
    name = item_name.lower()
    if any(k in name for k in ["next", "react", "vue", "angular", "svelte", "frontend", "ui"]):
        return "Client / Frontend Tier", "frontend"
    if any(k in name for k in ["fastapi", "express", "django", "flask", "nest", "backend", "api"]):
        return "API / Service Tier", "backend"
    if any(k in name for k in ["arq", "celery", "kafka", "rabbit", "worker", "queue"]):
        return "Async Queues / Workers Tier", "queue"
    db_keys = ["postgres", "pgvector", "sqlalchemy", "mongo", "prisma", "database", "redis"]
    if any(k in name for k in db_keys):
        return "Persistence / Storage Tier", "database"
    ext_keys = ["supabase", "auth0", "firebase", "jwt", "oauth", "github", "stripe", "aws"]
    if any(k in name for k in ext_keys):
        return "Auth & External Integrations Tier", "external"
    return "Application Modules", "service"


def validate_mermaid_syntax(code: str) -> bool:
    """Validates basic syntax invariants for Mermaid flowchart definitions."""
    if not code or not isinstance(code, str):
        return False
    lines = [
        line.strip()
        for line in code.splitlines()
        if line.strip() and not line.strip().startswith("%%")
    ]
    if not lines:
        return False

    first_line = lines[0]
    if not (first_line.startswith("flowchart TD") or first_line.startswith("flowchart LR")):
        return False

    subgraph_count = sum(1 for line in lines if line.startswith("subgraph"))
    end_count = sum(1 for line in lines if line == "end")
    if subgraph_count != end_count:
        return False

    quote_count = sum(line.count('"') for line in lines)
    if quote_count % 2 != 0:
        return False

    return True


def build_deterministic_mermaid_diagram(
    project_name: str,
    dependencies: list[str],
    evidence_tags: list[str],
    top_directories: list[str],
) -> tuple[str, list[DiagramNode], list[DiagramEdge], str]:
    """Builds a deterministic multi-tier Mermaid flowchart from repository facts."""
    nodes_by_tier: dict[str, list[DiagramNode]] = {}
    registered_ids: set[str] = set()
    node_list: list[DiagramNode] = []

    def add_node(
        item_label: str,
        default_tier: str | None = None,
        node_type_override: str | None = None,
    ):
        tier, n_type = classify_tier(item_label)
        if default_tier:
            tier = default_tier
        if node_type_override:
            n_type = node_type_override

        n_id = sanitize_node_id(f"{n_type}_{item_label}")
        if n_id in registered_ids:
            return n_id

        registered_ids.add(n_id)
        node = DiagramNode(
            node_id=n_id,
            label=sanitize_node_label(item_label),
            node_type=n_type,
            subgraph=tier,
        )
        nodes_by_tier.setdefault(tier, []).append(node)
        node_list.append(node)
        return n_id

    # 1. Add top directories as high-level components if applicable
    for d in top_directories[:6]:
        if d in ["frontend", "client", "ui", "web"]:
            add_node(f"{project_name} Frontend", "Client / Frontend Tier", "frontend")
        elif d in ["backend", "app", "server", "api"]:
            add_node(f"{project_name} Backend API", "API / Service Tier", "backend")

    # 2. Add dependencies and evidence
    for dep in dependencies[:15]:
        add_node(dep)

    for ev in evidence_tags[:10]:
        add_node(ev)

    # 3. Ensure baseline nodes exist if empty
    if not node_list:
        add_node(f"{project_name} Core", "API / Service Tier", "backend")

    # 4. Synthesize Mermaid flowchart syntax
    lines: list[str] = ["flowchart TD"]
    tier_order = [
        "Client / Frontend Tier",
        "Auth & External Integrations Tier",
        "API / Service Tier",
        "Async Queues / Workers Tier",
        "Persistence / Storage Tier",
        "Application Modules",
    ]

    tier_rep_nodes: dict[str, str] = {}
    for tier in tier_order:
        if tier not in nodes_by_tier:
            continue
        nodes = nodes_by_tier[tier]
        subgraph_id = sanitize_node_id(tier)
        lines.append(f'  subgraph {subgraph_id}["{tier}"]')
        for n in nodes:
            lines.append(f'    {n.node_id}["{n.label}"]')
        lines.append("  end")
        tier_rep_nodes[tier] = nodes[0].node_id

    # 5. Connect tiers directionally
    edges: list[DiagramEdge] = []

    def connect(src_tier: str, tgt_tier: str, label: str | None = None, style: str = "solid"):
        if src_tier in tier_rep_nodes and tgt_tier in tier_rep_nodes:
            src_id = tier_rep_nodes[src_tier]
            tgt_id = tier_rep_nodes[tgt_tier]
            if src_id != tgt_id:
                edge = DiagramEdge(source_id=src_id, target_id=tgt_id, label=label, style=style)
                edges.append(edge)
                arrow = f'-->|"{label}"|' if label else "-->"
                if style == "dotted":
                    arrow = f'-.->|"{label}"|' if label else "-.->"
                lines.append(f"  {src_id} {arrow} {tgt_id}")

    connect("Client / Frontend Tier", "API / Service Tier", "HTTP / REST API")
    connect("Auth & External Integrations Tier", "API / Service Tier", "JWT / OAuth", "dotted")
    connect("API / Service Tier", "Persistence / Storage Tier", "SQL / Queries")
    connect("API / Service Tier", "Async Queues / Workers Tier", "Dispatch Jobs")
    connect("Async Queues / Workers Tier", "Persistence / Storage Tier", "Background Writes")

    mermaid_code = "\n".join(lines)
    summary = (
        f"Deterministic {len(nodes_by_tier)}-tier architecture diagram for {project_name} "
        f"incorporating {len(node_list)} components and {len(edges)} connections."
    )
    return mermaid_code, node_list, edges, summary


_EDGE_LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9_]+)(?:\s*[\[\(\{].*?[\]\)\}])?\s*"
    r"(-->|-.->|==>)(?:\s*\|\s*\"?([^|\"]+?)\"?\s*\|)?\s*"
    r"([A-Za-z0-9_]+)"
)
_NODE_DEF_RE = re.compile(
    r"^\s*([A-Za-z0-9_]+)\s*(?:\[\[|\(\(|\{\{|\[\(|\[\"|\[|\(\"?|\{)"
    r"\s*([^\n\]\)\}]+?)\s*(?:\]\]|\)\)|\}\}|\)\]|\"\]|\]|\"\)|\)|\})"
)
_SUBGRAPH_RE = re.compile(r'^\s*subgraph\s+[A-Za-z0-9_]+(?:\s*\[\s*"?([^"\]]+)"?\s*\])?')


def extract_mermaid_nodes_and_edges(
    mermaid_code: str,
) -> tuple[list[DiagramNode], list[DiagramEdge]]:
    """Derive DiagramNode and DiagramEdge objects directly from Mermaid flowchart syntax."""
    nodes_by_id: dict[str, DiagramNode] = {}
    edges: list[DiagramEdge] = []
    subgraph_stack: list[str] = []

    def ensure_node(node_id: str, raw_label: str | None = None) -> None:
        if node_id in nodes_by_id:
            if raw_label and nodes_by_id[node_id].label == node_id:
                nodes_by_id[node_id].label = raw_label[:60]
            return
        label = (raw_label or node_id).strip().strip('"')[:60]
        tier, n_type = classify_tier(label or node_id)
        current_sub = subgraph_stack[-1] if subgraph_stack else tier
        nodes_by_id[node_id] = DiagramNode(
            node_id=node_id, label=label, node_type=n_type, subgraph=current_sub
        )

    for raw_line in mermaid_code.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("%%", "flowchart ", "classDef ", "class ", "style ")):
            continue
        sub_m = _SUBGRAPH_RE.match(line)
        if sub_m:
            subgraph_stack.append((sub_m.group(1) or "Group").strip())
            continue
        if line == "end":
            if subgraph_stack:
                subgraph_stack.pop()
            continue
        edge_m = _EDGE_LINE_RE.match(line)
        if edge_m:
            src, arrow, lbl, tgt = edge_m.groups()
            ensure_node(src)
            ensure_node(tgt)
            style = "dotted" if arrow == "-.->" else "solid"
            edges.append(
                DiagramEdge(
                    source_id=src, target_id=tgt,
                    label=lbl.strip() if lbl else None, style=style,
                )
            )
            continue
        node_m = _NODE_DEF_RE.match(line)
        if node_m:
            ensure_node(node_m.group(1), node_m.group(2))

    return list(nodes_by_id.values()), edges
