#!/usr/bin/env python3
"""
generate_vocab_pages.py
=======================
Generates complete SKOS-oriented documentation for a LinkML vocabulary.
Replaces gen-doc output with clean, vocabulary-focused pages.

Generated pages:
  - docs/index.md          — vocabulary homepage with metadata + alphabetical index
  - docs/hierarchy.md      — Mermaid class diagram of concept hierarchy
  - docs/{ConceptName}.md  — one page per concept with full SKOS properties

This script is vocabulary-agnostic — it works on any LinkML YAML following
the vocabulary template structure.

Usage:
    python3 scripts/generate_vocab_pages.py --input vocabulary/data.yaml --output docs/
    python3 scripts/generate_vocab_pages.py --input vocabulary/data.yaml --output docs/ --verbose
"""

import argparse
import os
import sys
import re
from pathlib import Path

try:
    from linkml_runtime.utils.schemaview import SchemaView
except ImportError:
    print("Error: linkml not installed. Install with: pip install linkml")
    sys.exit(1)


# ── Helpers ──────────────────────────────────────────────────────────────────

def clean_description(text):
    """Clean up description text — remove extra whitespace."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()


def format_date(date_str):
    """Format ISO date string to readable date."""
    if not date_str:
        return "—"
    s = str(date_str)
    if 'T' in s:
        s = s.split('T')[0]
    return s


def get_status_badge(status):
    """Return a Markdown badge for vocabulary status."""
    badges = {
        'draft':      '🟡 Draft',
        'review':     '🔵 Under Review',
        'stable':     '🟢 Stable',
        'deprecated': '🔴 Deprecated',
    }
    return badges.get(str(status).lower(), f'`{status}`')


def safe_filename(name):
    """Convert a concept name to a safe filename."""
    return ''.join(c if c.isalnum() or c in '-_' else '_' for c in name)


# ── Build concept tree ────────────────────────────────────────────────────────

def build_tree(enum):
    """Build parent→children mapping and identify root concepts."""
    children = {}
    roots = []
    for pv_name, pv in enum.permissible_values.items():
        if pv.is_a:
            if pv.is_a not in children:
                children[pv.is_a] = []
            children[pv.is_a].append(pv_name)
        else:
            roots.append(pv_name)
    return roots, children


def render_tree_text(node, children, depth=0):
    """Render concept hierarchy as indented text tree."""
    lines = []
    indent = "    " * depth
    prefix = "└── " if depth > 0 else ""
    lines.append(f"{indent}{prefix}[{node}]({safe_filename(node)}.md)")
    for child in sorted(children.get(node, [])):
        lines.extend(render_tree_text(child, children, depth + 1))
    return lines


# ── Generate index.md ─────────────────────────────────────────────────────────

def generate_index(sv, output_dir, verbose=False):
    """Generate vocabulary homepage."""
    schema = sv.schema
    title = schema.title or schema.name or "Controlled Vocabulary"
    description = clean_description(schema.description)
    version = str(schema.version) if schema.version else "—"
    license_uri = str(schema.license) if schema.license else None
    created_by = str(schema.created_by) if schema.created_by else None
    schema_id = str(schema.id) if schema.id else None
    created_on = format_date(schema.created_on)
    updated_on = format_date(schema.last_updated_on)

    # Get status from annotations
    status = None
    funding = None
    if schema.annotations:
        s = schema.annotations.get('schema_status')
        if s:
            status = s.value
        f = schema.annotations.get('funding')
        if f:
            funding = clean_description(f.value)

    lines = []

    # Title
    lines.append(f"# {title}")
    lines.append("")

    # Status badge
    if status:
        lines.append(f"**Status:** {get_status_badge(status)}")
        lines.append("")

    # Description
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

    # Funding
    if funding:
        lines.append(f"> *{funding}*")
        lines.append("")

    # Related resources
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
    lines.append("| Turtle (SKOS) | Machine-readable SKOS vocabulary | [Download TTL](../output/data.ttl) |")
    lines.append("| YAML (LinkML) | Source vocabulary definition | [View YAML](../vocabulary/data.yaml) |")
    lines.append("")

    # Navigation
    lines.append("## Browse the Vocabulary")
    lines.append("")
    lines.append("- [📊 Concept hierarchy diagram](hierarchy.md)")
    lines.append("")

    # Per enum section
    enums = sv.all_enums()
    total_concepts = sum(len(e.permissible_values) for e in enums.values())
    lines.append(f"This vocabulary contains **{total_concepts} concepts**")
    if len(enums) > 1:
        lines.append(f" across {len(enums)} concept schemes.")
    else:
        lines.append(".")
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
        lines.append(f"**{concept_count} concepts**")
        lines.append("")

        # Alphabetical index table
        lines.append("#### Alphabetical index")
        lines.append("")
        lines.append("| Concept | Alternative labels | Definition |")
        lines.append("| --- | --- | --- |")

        for pv_name in sorted(enum.permissible_values.keys()):
            pv = enum.permissible_values[pv_name]
            alt_labels = ", ".join(str(a) for a in (pv.aliases or [])[:2])
            definition = clean_description(pv.description)
            if len(definition) > 100:
                definition = definition[:97] + "..."
            fn = safe_filename(pv_name)
            lines.append(f"| [{pv_name}]({fn}.md) | {alt_labels} | {definition} |")

        lines.append("")

        # Hierarchy tree
        lines.append("#### Concept hierarchy")
        lines.append("")
        lines.append("```")
        for root in sorted(roots):
            lines.extend(render_tree_text(root, children))
        lines.append("```")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Documentation generated automatically from LinkML vocabulary source. "
                 f"Last updated: {updated_on}.*")

    # Write
    output_path = Path(output_dir) / "index.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    if verbose:
        print(f"  Written: {output_path}")
    return output_path


# ── Generate hierarchy.md ─────────────────────────────────────────────────────

def generate_hierarchy(sv, output_dir, verbose=False):
    """Generate Mermaid class diagram of concept hierarchy."""
    schema = sv.schema
    title = schema.title or schema.name or "Vocabulary"

    lines = []
    lines.append(f"# {title} — Concept Hierarchy")
    lines.append("")
    lines.append("Arrows point from broader (parent) to narrower (child) concepts.")
    lines.append("")

    enums = sv.all_enums()

    for enum_name, enum in enums.items():
        if len(enums) > 1:
            lines.append(f"## {enum_name}")
            lines.append("")

        lines.append("```mermaid")
        lines.append("classDiagram")

        added = set()
        relationships = []

        for pv_name, pv in enum.permissible_values.items():
            # Get display label — use first alias if available
            label = pv_name
            if pv.aliases:
                label = str(pv.aliases[0])
            # Escape quotes in label
            label = label.replace('"', "'")

            safe = safe_filename(pv_name)
            if safe not in added:
                lines.append(f'    class {safe}["{label}"]')
                # Make it clickable
                lines.append(f'    click {safe} href "../{safe}/"')
                added.add(safe)

            if pv.is_a:
                safe_parent = safe_filename(pv.is_a)
                parent_pv = enum.permissible_values.get(pv.is_a)
                parent_label = pv.is_a
                if parent_pv and parent_pv.aliases:
                    parent_label = str(parent_pv.aliases[0])
                parent_label = parent_label.replace('"', "'")

                if safe_parent not in added:
                    lines.append(f'    class {safe_parent}["{parent_label}"]')
                    lines.append(f'    click {safe_parent} href "../{safe_parent}/"')
                    added.add(safe_parent)

                relationships.append(f"    {safe_parent} <|-- {safe}")

        lines.extend(relationships)
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("[← Back to vocabulary index](index.md)")

    output_path = Path(output_dir) / "hierarchy.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    if verbose:
        print(f"  Written: {output_path}")
    return output_path


# ── Generate individual concept pages ─────────────────────────────────────────

def generate_concept_page(pv_name, pv, enum, enum_name, sv, output_dir, verbose=False):
    """Generate a single concept page."""
    schema = sv.schema
    schema_id = str(schema.id) if schema.id else ""

    # Determine concept URI
    if pv.meaning:
        concept_uri = str(pv.meaning)
        uri_source = "adopted"  # meaning: → external URI adopted directly
    else:
        # Minted URI
        default_prefix = schema.default_prefix or ""
        prefix_uri = ""
        if default_prefix and schema.prefixes and default_prefix in schema.prefixes:
            prefix_uri = str(schema.prefixes[default_prefix].prefix_reference)
        concept_uri = f"{prefix_uri}{pv_name}" if prefix_uri else f"{schema_id}/{pv_name}"
        uri_source = "minted"

    # Preferred label
    pref_label = pv_name
    if pv.aliases:
        pref_label = str(pv.aliases[0])

    # Alternative labels (all aliases after the first)
    alt_labels = [str(a) for a in (pv.aliases or [])[1:]]

    # Broader concept
    broader = pv.is_a

    # Children (narrower concepts)
    narrower = []
    for other_name, other_pv in enum.permissible_values.items():
        if other_pv.is_a == pv_name:
            narrower.append(other_name)

    # Definition and scope note
    definition = clean_description(pv.description)
    scope_notes = [clean_description(c) for c in (pv.comments or []) if c]

    # Mappings
    exact_mappings = [str(m) for m in (pv.exact_mappings or [])]
    broad_mappings = [str(m) for m in (pv.broad_mappings or [])]
    narrow_mappings = [str(m) for m in (pv.narrow_mappings or [])]
    related_mappings = [str(m) for m in (pv.related_mappings or [])]
    close_mappings = [str(m) for m in (pv.close_mappings or [])]

    lines = []

    # Title
    lines.append(f"# {pref_label}")
    lines.append("")

    # Concept URI
    lines.append("## Concept Information")
    lines.append("")
    lines.append("| | |")
    lines.append("| --- | --- |")
    lines.append(f"| **Notation** | `{pv_name}` |")

    if uri_source == "adopted":
        lines.append(f"| **Concept URI** | [{concept_uri}]({concept_uri}) |")
        lines.append(f"| **URI source** | Adopted from external vocabulary (`meaning:`) |")
    else:
        lines.append(f"| **Concept URI** | [{concept_uri}]({concept_uri}) |")
        lines.append(f"| **URI source** | Minted in this vocabulary |")

    lines.append(f"| **Preferred label** | {pref_label} |")
    if alt_labels:
        lines.append(f"| **Alternative labels** | {' · '.join(alt_labels)} |")
    lines.append(f"| **Part of** | [{enum_name}](index.md) |")
    lines.append("")

    # Definition
    if definition:
        lines.append("## Definition")
        lines.append("")
        lines.append(definition)
        lines.append("")

    # Scope notes
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
        broader_fn = safe_filename(broader)
        lines.append(f"**Broader concept:** [{broader}]({broader_fn}.md)")
        lines.append("")
    else:
        lines.append("**Broader concept:** *(top concept — no broader term)*")
        lines.append("")

    if narrower:
        lines.append("**Narrower concepts:**")
        lines.append("")
        for n in sorted(narrower):
            n_fn = safe_filename(n)
            n_pv = enum.permissible_values.get(n)
            n_label = n
            if n_pv and n_pv.aliases:
                n_label = str(n_pv.aliases[0])
            lines.append(f"- [{n_label}]({n_fn}.md) (`{n}`)")
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
            lines.append(f"| **Adopted from** (`meaning:`) | [{concept_uri}]({concept_uri}) |")
            lines.append("| --- | --- |")
            lines.append("")
            lines.append("> This concept directly adopts an external URI. "
                         "The concept identity IS the external URI.")
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
    lines.append(f"[← Back to {enum_name} index](index.md) · "
                 f"[📊 Hierarchy diagram](hierarchy.md)")

    # Write
    fn = safe_filename(pv_name)
    output_path = Path(output_dir) / f"{fn}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    return output_path


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_all(yaml_path, output_dir, verbose=False):
    """Generate all vocabulary documentation pages."""
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

    # 1. Generate index
    if verbose:
        print("Generating index.md...")
    generate_index(sv, output_dir, verbose)

    # 2. Generate hierarchy diagram
    if verbose:
        print("Generating hierarchy.md...")
    generate_hierarchy(sv, output_dir, verbose)

    # 3. Generate individual concept pages
    enums = sv.all_enums()
    total = sum(len(e.permissible_values) for e in enums.values())
    if verbose:
        print(f"Generating {total} concept pages...")

    count = 0
    for enum_name, enum in enums.items():
        for pv_name, pv in enum.permissible_values.items():
            generate_concept_page(
                pv_name, pv, enum, enum_name, sv, output_dir, verbose=False)
            count += 1

    if verbose:
        print(f"  Generated {count} concept pages")

    print(f"Done — {count + 2} pages written to {output_dir}/")
    return count


def main():
    parser = argparse.ArgumentParser(
        description='Generate SKOS-oriented vocabulary documentation from LinkML YAML')
    parser.add_argument('--input', '-i', required=True,
                        help='Input LinkML vocabulary YAML file')
    parser.add_argument('--output', '-o', default='docs',
                        help='Output directory for documentation (default: docs)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print progress information')
    args = parser.parse_args()

    generate_all(args.input, args.output, args.verbose)


if __name__ == '__main__':
    main()
