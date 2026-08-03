#!/usr/bin/env python3
"""
generate_vocab_pages.py
=======================
Generates complete SKOS-oriented documentation for a LinkML vocabulary.
Replaces gen-doc output with clean, vocabulary-focused pages.

Generated pages:
  - docs/index.md              — vocabulary homepage with metadata + alphabetical index
  - docs/hierarchy.md          — concept hierarchy split per top-level concept
  - docs/alphabetical.md       — all concepts A-Z with definitions
  - docs/{ConceptName}.md      — one page per concept with full SKOS properties

Usage:
    python3 scripts/generate_vocab_pages.py --input vocabulary/data.yaml --output docs/
    python3 scripts/generate_vocab_pages.py --input vocabulary/data.yaml --output docs/ --verbose
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from linkml_runtime.utils.schemaview import SchemaView
except ImportError:
    print("Error: linkml not installed. Install with: pip install linkml")
    sys.exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_description(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()


def format_date(date_str):
    if not date_str:
        return "—"
    s = str(date_str)
    return s.split('T')[0] if 'T' in s else s


def get_status_badge(status):
    badges = {
        'draft':      '🟡 Draft',
        'review':     '🔵 Under Review',
        'stable':     '🟢 Stable',
        'deprecated': '🔴 Deprecated',
    }
    return badges.get(str(status).lower(), f'`{status}`')


def safe_filename(name):
    return ''.join(c if c.isalnum() or c in '-_' else '_' for c in name)


def build_tree(enum):
    """Build parent->children mapping and identify root concepts."""
    children = {}
    roots = []
    for pv_name, pv in enum.permissible_values.items():
        if pv.is_a:
            if pv.is_a not in children:
                children[pv.is_a] = []
            children[pv.is_a].append(pv_name)
        else:
            roots.append(pv_name)
    return sorted(roots), children


def get_pref_label(pv_name, pv):
    """Get preferred label — first alias or the key itself."""
    if pv.aliases:
        return str(pv.aliases[0])
    return pv_name


def render_tree_text(node, children, pvs, depth=0):
    """Render concept hierarchy as indented Markdown link tree."""
    lines = []
    indent = "    " * depth
    prefix = "└── " if depth > 0 else ""
    pv = pvs.get(node)
    label = get_pref_label(node, pv) if pv else node
    fn = safe_filename(node)
    lines.append(f"{indent}{prefix}[{label}]({fn}.md) `{node}`")
    for child in sorted(children.get(node, [])):
        lines.extend(render_tree_text(child, children, pvs, depth + 1))
    return lines


def get_all_descendants(node, children):
    """Get all descendants of a node recursively."""
    result = []
    for child in children.get(node, []):
        result.append(child)
        result.extend(get_all_descendants(child, children))
    return result


# ── Generate index.md ─────────────────────────────────────────────────────────

def generate_index(sv, yaml_path, output_dir, verbose=False):
    schema = sv.schema
    title = schema.title or schema.name or "Controlled Vocabulary"
    description = clean_description(schema.description)
    version = str(schema.version) if schema.version else "—"
    license_uri = str(schema.license) if schema.license else None
    created_by = str(schema.created_by) if schema.created_by else None
    schema_id = str(schema.id) if schema.id else None
    created_on = format_date(schema.created_on)
    updated_on = format_date(schema.last_updated_on)

    # Annotations
    status = None
    funding = None
    repo_url = None
    if schema.annotations:
        s = schema.annotations.get('schema_status')
        if s:
            status = s.value
        f = schema.annotations.get('funding')
        if f:
            funding = clean_description(f.value)
        r = schema.annotations.get('repo_url')
        if r:
            repo_url = str(r.value).rstrip('/')

    stem = Path(yaml_path).stem

    lines = []
    lines.append(f"# {title}")
    lines.append("")

    if status:
        lines.append(f"**Status:** {get_status_badge(status)}")
        lines.append("")

    if description:
        lines.append(description)
        lines.append("")

    # Metadata table
    lines.append("## Vocabulary Information")
    lines.append("")
    lines.append("| | |")
    lines.append("| --- | --- |")
    if schema_id:
        lines.append(f"| **Persistent URI** | [{schema_id}]({schema_id}) |")
    lines.append(f"| **Version** | {version} |")
    if license_uri:
        lines.append(f"| **License** | [{license_uri}]({license_uri}) |")
    if created_by:
        lines.append(f"| **Creator** | [{created_by}]({created_by}) |")
    lines.append(f"| **Created** | {created_on} |")
    lines.append(f"| **Last updated** | {updated_on} |")
    lines.append("")

    if funding:
        lines.append(f"> *{funding}*")
        lines.append("")

    if schema.see_also:
        lines.append("**Related resources:**")
        for link in schema.see_also:
            link_str = str(link)
            lines.append(f"- [{link_str}]({link_str})")
        lines.append("")

    # Downloads
    lines.append("## Downloads")
    lines.append("")
    lines.append("| Format | Description | Link |")
    lines.append("| --- | --- | --- |")
    if repo_url:
        lines.append(f"| Turtle (SKOS) | Machine-readable SKOS vocabulary | [Download TTL]({repo_url}/raw/main/output/{stem}.ttl) |")
        lines.append(f"| YAML (LinkML) | Source vocabulary definition | [View YAML]({repo_url}/blob/main/vocabulary/{stem}.yaml) |")
    else:
        lines.append(f"| Turtle (SKOS) | Machine-readable SKOS vocabulary | `output/{stem}.ttl` |")
        lines.append(f"| YAML (LinkML) | Source vocabulary definition | `vocabulary/{stem}.yaml` |")
    lines.append("")

    # Navigation
    lines.append("## Browse the Vocabulary")
    lines.append("")
    lines.append("- [📊 Concept hierarchy — by branch](hierarchy.md)")
    lines.append("- [🔤 All concepts — alphabetical](alphabetical.md)")
    lines.append("")

    # Summary per enum
    enums = sv.all_enums()
    total_concepts = sum(len(e.permissible_values) for e in enums.values())
    lines.append(f"This vocabulary contains **{total_concepts} concepts**.")
    lines.append("")

    for enum_name, enum in enums.items():
        enum_desc = clean_description(enum.description)
        concept_count = len(enum.permissible_values)
        roots, children = build_tree(enum)

        lines.append(f"### {enum_name}")
        lines.append("")
        if enum_desc:
            lines.append(enum_desc)
            lines.append("")
        lines.append(f"**{concept_count} concepts** — "
                     f"[browse alphabetically](alphabetical.md) · "
                     f"[view hierarchy](hierarchy.md)")
        lines.append("")

    lines.append("---")
    lines.append(f"*Last updated: {updated_on}.*")

    output_path = Path(output_dir) / "index.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    if verbose:
        print(f"  Written: {output_path}")
    return output_path


# ── Generate hierarchy.md ─────────────────────────────────────────────────────

def generate_hierarchy(sv, output_dir, verbose=False):
    """
    Generate hierarchy page with one Mermaid diagram per top-level concept.
    This keeps diagrams small and readable.
    """
    schema = sv.schema
    title = schema.title or schema.name or "Vocabulary"

    lines = []
    lines.append(f"# {title} — Concept Hierarchy")
    lines.append("")
    lines.append("The hierarchy is split by top-level concept for readability. "
                 "Click any concept to view its full detail page.")
    lines.append("")
    lines.append("[← Back to index](index.md) · [🔤 Alphabetical view](alphabetical.md)")
    lines.append("")

    enums = sv.all_enums()

    for enum_name, enum in enums.items():
        if len(enums) > 1:
            lines.append(f"## {enum_name}")
            lines.append("")

        roots, children = build_tree(enum)
        pvs = enum.permissible_values

        # One diagram per root concept
        for root in roots:
            root_pv = pvs.get(root)
            root_label = get_pref_label(root, root_pv) if root_pv else root
            root_desc = clean_description(root_pv.description) if root_pv else ""
            descendants = get_all_descendants(root, children)

            lines.append(f"### {root_label}")
            if root_desc:
                short_desc = root_desc[:150] + "..." if len(root_desc) > 150 else root_desc
                lines.append(f"*{short_desc}*")
            lines.append("")
            lines.append(f"**{len(descendants)} narrower concepts**")
            lines.append("")

            # Mermaid diagram for this branch only
            lines.append("```mermaid")
            lines.append("classDiagram")
            lines.append(f'    %% Branch: {root_label}')

            added = set()
            relationships = []

            # Add root node
            safe_root = safe_filename(root)
            lines.append(f'    class {safe_root}["{root_label}"]')
            lines.append(f'    click {safe_root} href "../{safe_root}/"')
            added.add(safe_root)

            # Add all descendants
            all_nodes = [root] + descendants
            for node in all_nodes:
                pv = pvs.get(node)
                if not pv:
                    continue
                label = get_pref_label(node, pv).replace('"', "'")
                safe_node = safe_filename(node)

                if safe_node not in added:
                    lines.append(f'    class {safe_node}["{label}"]')
                    lines.append(f'    click {safe_node} href "../{safe_node}/"')
                    added.add(safe_node)

                if pv.is_a and pv.is_a in all_nodes:
                    safe_parent = safe_filename(pv.is_a)
                    relationships.append(f"    {safe_parent} <|-- {safe_node}")

            lines.extend(relationships)
            lines.append("```")
            lines.append("")

            # Also show as text tree for readability
            lines.append("<details>")
            lines.append(f"<summary>Show as text tree</summary>")
            lines.append("")
            lines.append("```")
            lines.extend(render_tree_text(root, children, pvs))
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    lines.append("---")
    lines.append("[← Back to index](index.md) · [🔤 Alphabetical view](alphabetical.md)")

    output_path = Path(output_dir) / "hierarchy.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    if verbose:
        print(f"  Written: {output_path}")
    return output_path


# ── Generate alphabetical.md ──────────────────────────────────────────────────

def generate_alphabetical(sv, output_dir, verbose=False):
    """Generate alphabetical listing of all concepts."""
    schema = sv.schema
    title = schema.title or schema.name or "Vocabulary"

    lines = []
    lines.append(f"# {title} — All Concepts (A–Z)")
    lines.append("")
    lines.append("[← Back to index](index.md) · [📊 Hierarchy view](hierarchy.md)")
    lines.append("")

    enums = sv.all_enums()

    # Collect all concepts across all enums
    all_concepts = []
    for enum_name, enum in enums.items():
        for pv_name, pv in enum.permissible_values.items():
            all_concepts.append((pv_name, pv, enum_name, enum))

    # Sort alphabetically by preferred label
    all_concepts.sort(key=lambda x: get_pref_label(x[0], x[1]).lower())

    # Letter index
    letters = sorted(set(get_pref_label(c[0], c[1])[0].upper()
                         for c in all_concepts if get_pref_label(c[0], c[1])))
    lines.append("**Jump to:** " + " · ".join(f"[{l}](#{l.lower()})" for l in letters))
    lines.append("")
    lines.append(f"**Total: {len(all_concepts)} concepts**")
    lines.append("")

    # Group by first letter
    current_letter = None
    for pv_name, pv, enum_name, enum in all_concepts:
        pref_label = get_pref_label(pv_name, pv)
        first_letter = pref_label[0].upper()

        if first_letter != current_letter:
            current_letter = first_letter
            lines.append(f"## {current_letter}")
            lines.append("")

        fn = safe_filename(pv_name)
        definition = clean_description(pv.description)
        if len(definition) > 150:
            definition = definition[:147] + "..."

        alt_labels = [str(a) for a in (pv.aliases or [])[1:3]]
        alt_str = f" *(also: {', '.join(alt_labels)})*" if alt_labels else ""

        # Broader concept
        broader_str = ""
        if pv.is_a:
            broader_pv = enum.permissible_values.get(pv.is_a)
            broader_label = get_pref_label(pv.is_a, broader_pv) if broader_pv else pv.is_a
            broader_fn = safe_filename(pv.is_a)
            broader_str = f" › [{broader_label}]({broader_fn}.md)"

        lines.append(f"### [{pref_label}]({fn}.md){alt_str}")
        lines.append("")
        if broader_str:
            lines.append(f"*Broader:{broader_str}*")
            lines.append("")
        if definition:
            lines.append(definition)
            lines.append("")
        lines.append(f"`{pv_name}`")
        lines.append("")

    lines.append("---")
    lines.append("[← Back to index](index.md) · [📊 Hierarchy view](hierarchy.md)")

    output_path = Path(output_dir) / "alphabetical.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    if verbose:
        print(f"  Written: {output_path}")
    return output_path


# ── Generate individual concept pages ─────────────────────────────────────────

def generate_concept_page(pv_name, pv, enum, enum_name, sv, output_dir):
    """Generate a single concept detail page."""
    schema = sv.schema
    schema_id = str(schema.id) if schema.id else ""

    # Get default prefix URI
    default_prefix = schema.default_prefix or ""
    prefix_uri = ""
    if default_prefix and schema.prefixes and default_prefix in schema.prefixes:
        prefix_uri = str(schema.prefixes[default_prefix].prefix_reference)

    # Determine concept URI and source
    if pv.meaning:
        concept_uri = str(pv.meaning)
        uri_source = "adopted"
    else:
        concept_uri = f"{prefix_uri}{pv_name}" if prefix_uri else f"{schema_id}/{pv_name}"
        uri_source = "minted"

    pref_label = get_pref_label(pv_name, pv)
    alt_labels = [str(a) for a in (pv.aliases or [])[1:]]
    broader = pv.is_a
    definition = clean_description(pv.description)
    scope_notes = [clean_description(c) for c in (pv.comments or []) if c]

    # Find narrower concepts
    narrower = []
    for other_name, other_pv in enum.permissible_values.items():
        if other_pv.is_a == pv_name:
            narrower.append((other_name, other_pv))
    narrower.sort(key=lambda x: get_pref_label(x[0], x[1]).lower())

    # Mappings
    exact_mappings = [str(m) for m in (pv.exact_mappings or [])]
    broad_mappings = [str(m) for m in (pv.broad_mappings or [])]
    narrow_mappings = [str(m) for m in (pv.narrow_mappings or [])]
    related_mappings = [str(m) for m in (pv.related_mappings or [])]
    close_mappings = [str(m) for m in (pv.close_mappings or [])]

    lines = []
    lines.append(f"# {pref_label}")
    lines.append("")

    # Concept information table
    lines.append("## Concept Information")
    lines.append("")
    lines.append("| | |")
    lines.append("| --- | --- |")
    lines.append(f"| **Notation** | `{pv_name}` |")
    lines.append(f"| **Preferred label** | {pref_label} |")
    if alt_labels:
        lines.append(f"| **Alternative labels** | {' · '.join(alt_labels)} |")
    if uri_source == "adopted":
        lines.append(f"| **Concept URI** | [{concept_uri}]({concept_uri}) |")
        lines.append(f"| **URI type** | Adopted from external vocabulary |")
    else:
        lines.append(f"| **Concept URI** | [{concept_uri}]({concept_uri}) |")
        lines.append(f"| **URI type** | Minted in this vocabulary |")
    lines.append(f"| **Part of** | [{enum_name}](index.md) |")
    lines.append("")

    # Definition
    if definition:
        lines.append("## Definition")
        lines.append("")
        lines.append(definition)
        lines.append("")

    # Scope note
    if scope_notes:
        lines.append("## Scope Note")
        lines.append("")
        for note in scope_notes:
            lines.append(f"> {note}")
        lines.append("")

    # Hierarchy
    lines.append("## Hierarchy")
    lines.append("")

    if broader:
        broader_pv = enum.permissible_values.get(broader)
        broader_label = get_pref_label(broader, broader_pv) if broader_pv else broader
        broader_fn = safe_filename(broader)
        lines.append(f"**Broader concept:** [{broader_label}]({broader_fn}.md) `{broader}`")
    else:
        lines.append("**Broader concept:** *(top concept — no broader term)*")
    lines.append("")

    if narrower:
        lines.append(f"**Narrower concepts ({len(narrower)}):**")
        lines.append("")
        for n_name, n_pv in narrower:
            n_label = get_pref_label(n_name, n_pv)
            n_fn = safe_filename(n_name)
            n_def = clean_description(n_pv.description)
            if len(n_def) > 80:
                n_def = n_def[:77] + "..."
            lines.append(f"- [{n_label}]({n_fn}.md) `{n_name}` — {n_def}")
        lines.append("")
    else:
        lines.append("**Narrower concepts:** *(leaf concept — no narrower terms)*")
        lines.append("")

    # Mappings
    has_mappings = (uri_source == "adopted" or exact_mappings or broad_mappings
                    or narrow_mappings or related_mappings or close_mappings)

    if has_mappings:
        lines.append("## Mappings to External Vocabularies")
        lines.append("")

        if uri_source == "adopted":
            lines.append(f"**Adopted from** (`meaning:`) — this concept directly adopts an external URI:")
            lines.append(f"> [{concept_uri}]({concept_uri})")
            lines.append("")

        if exact_mappings:
            lines.append("**Exact matches** (`skos:exactMatch`) — "
                         "equivalent concept in external vocabulary, own URI kept:")
            for m in exact_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")

        if broad_mappings:
            lines.append("**Broad matches** (`skos:broadMatch`) — "
                         "external concept is broader than this concept:")
            for m in broad_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")

        if narrow_mappings:
            lines.append("**Narrow matches** (`skos:narrowMatch`) — "
                         "external concept is narrower than this concept:")
            for m in narrow_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")

        if close_mappings:
            lines.append("**Close matches** (`skos:closeMatch`) — "
                         "similar but not identical external concept:")
            for m in close_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")

        if related_mappings:
            lines.append("**Related matches** (`skos:relatedMatch`) — "
                         "related external concept:")
            for m in related_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")

    # Footer navigation
    lines.append("---")
    lines.append("")
    lines.append(f"[← Back to index](index.md) · "
                 f"[📊 Hierarchy](hierarchy.md) · "
                 f"[🔤 Alphabetical](alphabetical.md)")

    fn = safe_filename(pv_name)
    output_path = Path(output_dir) / f"{fn}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return output_path


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_all(yaml_path, output_dir, verbose=False):
    yaml_path = Path(yaml_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"Loading: {yaml_path}")

    sv = SchemaView(str(yaml_path))
    schema = sv.schema
    title = schema.title or schema.name or "Vocabulary"

    if verbose:
        print(f"Vocabulary: {title}")

    # 1. Index page
    if verbose:
        print("Generating index.md...")
    generate_index(sv, yaml_path, output_dir, verbose)

    # 2. Hierarchy page
    if verbose:
        print("Generating hierarchy.md...")
    generate_hierarchy(sv, output_dir, verbose)

    # 3. Alphabetical page
    if verbose:
        print("Generating alphabetical.md...")
    generate_alphabetical(sv, output_dir, verbose)

    # 4. Individual concept pages
    enums = sv.all_enums()
    total = sum(len(e.permissible_values) for e in enums.values())
    if verbose:
        print(f"Generating {total} concept pages...")

    count = 0
    for enum_name, enum in enums.items():
        for pv_name, pv in enum.permissible_values.items():
            generate_concept_page(pv_name, pv, enum, enum_name, sv, output_dir)
            count += 1

    if verbose:
        print(f"  Generated {count} concept pages")

    print(f"Done — {count + 3} pages written to {output_dir}/")
    return count


def main():
    parser = argparse.ArgumentParser(
        description='Generate SKOS-oriented vocabulary documentation from LinkML YAML')
    parser.add_argument('--input', '-i', required=True,
                        help='Input LinkML vocabulary YAML file')
    parser.add_argument('--output', '-o', default='docs',
                        help='Output directory (default: docs)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print progress information')
    args = parser.parse_args()

    generate_all(args.input, args.output, args.verbose)


if __name__ == '__main__':
    main()
