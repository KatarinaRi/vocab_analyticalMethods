#!/usr/bin/env python3
"""
generate_vocab_pages.py
=======================
Generates complete SKOS-oriented documentation for a LinkML vocabulary.

Generated pages:
  - docs/index.md              — vocabulary homepage with metadata
  - docs/browse.md             — tabbed view: Alphabetical | Hierarchy
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
    if pv and pv.aliases:
        return str(pv.aliases[0])
    return pv_name

def get_all_descendants(node, children):
    result = []
    for child in children.get(node, []):
        result.append(child)
        result.extend(get_all_descendants(child, children))
    return result


# ── HTML tree renderer ────────────────────────────────────────────────────────

def render_html_tree(node, children, pvs, depth=0):
    """Render concept hierarchy as nested HTML list with clickable links."""
    pv = pvs.get(node)
    label = get_pref_label(node, pv)
    fn = safe_filename(node)
    definition = clean_description(pv.description) if pv else ""
    short_def = (definition[:80] + "...") if len(definition) > 80 else definition

    lines = []
    lines.append('<li>')
    lines.append(f'  <a href="{fn}.md"><strong>{label}</strong></a>')
    lines.append(f'  <small><code>{node}</code></small>')
    if short_def:
        lines.append(f'  <br/><small style="color:#666">{short_def}</small>')

    node_children = sorted(children.get(node, []))
    if node_children:
        lines.append('<ul>')
        for child in node_children:
            lines.extend(render_html_tree(child, children, pvs, depth + 1))
        lines.append('</ul>')
    lines.append('</li>')
    return lines


# ── Generate alphabetical content (reusable) ──────────────────────────────────

def generate_alphabetical_content(enums, indent=""):
    """Generate alphabetical listing as Markdown lines."""
    lines = []
    all_concepts = []
    for enum_name, enum in enums.items():
        for pv_name, pv in enum.permissible_values.items():
            all_concepts.append((pv_name, pv, enum_name, enum))

    all_concepts.sort(key=lambda x: get_pref_label(x[0], x[1]).lower())

    letters = sorted(set(get_pref_label(c[0], c[1])[0].upper()
                         for c in all_concepts if get_pref_label(c[0], c[1])))
    lines.append(indent + "**Jump to:** " +
                 " · ".join(f"[{l}](#{l.lower()})" for l in letters))
    lines.append("")
    lines.append(indent + f"**Total: {len(all_concepts)} concepts**")
    lines.append("")

    current_letter = None
    for pv_name, pv, enum_name, enum in all_concepts:
        pref_label = get_pref_label(pv_name, pv)
        first_letter = pref_label[0].upper()

        if first_letter != current_letter:
            current_letter = first_letter
            lines.append(indent + f"### {current_letter}")
            lines.append("")

        fn = safe_filename(pv_name)
        definition = clean_description(pv.description)
        if len(definition) > 120:
            definition = definition[:117] + "..."

        alt_labels = [str(a) for a in (pv.aliases or [])[1:3]]
        alt_str = f" *(also: {', '.join(alt_labels)})*" if alt_labels else ""

        broader_str = ""
        if pv.is_a:
            broader_pv = enum.permissible_values.get(pv.is_a)
            broader_label = get_pref_label(pv.is_a, broader_pv) if broader_pv else pv.is_a
            broader_fn = safe_filename(pv.is_a)
            broader_str = f"*Broader: [{broader_label}]({broader_fn}.md)*  \n"

        lines.append(indent + f"**[{pref_label}]({fn}.md)**{alt_str} `{pv_name}`")
        lines.append("")
        if broader_str:
            lines.append(indent + broader_str.strip())
            lines.append("")
        if definition:
            lines.append(indent + definition)
            lines.append("")

    return lines


# ── Generate hierarchy content (reusable) ─────────────────────────────────────

def generate_hierarchy_content(enums, indent=""):
    """Generate hierarchy HTML trees as Markdown lines."""
    lines = []
    for enum_name, enum in enums.items():
        if len(enums) > 1:
            lines.append(indent + f"### {enum_name}")
            lines.append("")

        roots, children = build_tree(enum)
        pvs = enum.permissible_values

        for root in roots:
            root_pv = pvs.get(root)
            root_label = get_pref_label(root, root_pv) if root_pv else root
            root_desc = clean_description(root_pv.description) if root_pv else ""
            descendants = get_all_descendants(root, children)

            lines.append(indent + f"#### {root_label}")
            lines.append("")
            if root_desc:
                short = root_desc[:120] + "..." if len(root_desc) > 120 else root_desc
                lines.append(indent + f"*{short}*")
                lines.append("")
            lines.append(indent + f"**{len(descendants)} narrower concepts**")
            lines.append("")

            lines.append('<ul class="vocab-tree">')
            lines.extend(render_html_tree(root, children, pvs, depth=0))
            lines.append('</ul>')
            lines.append("")

    return lines


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

    status = None
    funding = None
    repo_url = None
    if schema.annotations:
        s = schema.annotations.get('schema_status')
        if s: status = s.value
        f = schema.annotations.get('funding')
        if f: funding = clean_description(f.value)
        r = schema.annotations.get('repo_url')
        if r: repo_url = str(r.value).rstrip('/')

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

    enums = sv.all_enums()
    total_concepts = sum(len(e.permissible_values) for e in enums.values())

    lines.append("## Browse the Vocabulary")
    lines.append("")
    lines.append(f"This vocabulary contains **{total_concepts} concepts**.")
    lines.append("")
    lines.append("[📖 Browse — Alphabetical & Hierarchy](browse.md)")
    lines.append("")

    lines.append("---")
    lines.append(f"*Last updated: {updated_on}.*")

    output_path = Path(output_dir) / "index.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    if verbose:
        print(f"  Written: {output_path}")
    return output_path


# ── Generate browse.md (tabbed: Alphabetical | Hierarchy) ─────────────────────

def generate_browse(sv, output_dir, verbose=False):
    """Generate combined browse page with two tabs."""
    schema = sv.schema
    title = schema.title or schema.name or "Vocabulary"
    enums = sv.all_enums()

    lines = []
    lines.append(f"# {title} — Browse")
    lines.append("")
    lines.append("[← Back to index](index.md)")
    lines.append("")

    # Tab 1: Alphabetical
    lines.append('=== "🔤 Alphabetical"')
    lines.append("")
    alpha_lines = generate_alphabetical_content(enums, indent="    ")
    for l in alpha_lines:
        lines.append("    " + l if l.strip() and not l.startswith('<') else l)
    lines.append("")

    # Tab 2: Hierarchy
    lines.append('=== "📊 Hierarchy"')
    lines.append("")
    lines.append("    Click any concept name to view its full detail page.")
    lines.append("")
    hier_lines = generate_hierarchy_content(enums, indent="    ")
    for l in hier_lines:
        lines.append("    " + l if l.strip() and not l.startswith('<') else l)
    lines.append("")

    output_path = Path(output_dir) / "browse.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    if verbose:
        print(f"  Written: {output_path}")
    return output_path


# ── Generate individual concept pages ─────────────────────────────────────────

def generate_concept_page(pv_name, pv, enum, enum_name, sv, output_dir):
    schema = sv.schema
    schema_id = str(schema.id) if schema.id else ""

    default_prefix = schema.default_prefix or ""
    prefix_uri = ""
    if default_prefix and schema.prefixes and default_prefix in schema.prefixes:
        prefix_uri = str(schema.prefixes[default_prefix].prefix_reference)

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

    narrower = []
    for other_name, other_pv in enum.permissible_values.items():
        if other_pv.is_a == pv_name:
            narrower.append((other_name, other_pv))
    narrower.sort(key=lambda x: get_pref_label(x[0], x[1]).lower())

    exact_mappings = [str(m) for m in (pv.exact_mappings or [])]
    broad_mappings = [str(m) for m in (pv.broad_mappings or [])]
    narrow_mappings = [str(m) for m in (pv.narrow_mappings or [])]
    related_mappings = [str(m) for m in (pv.related_mappings or [])]
    close_mappings = [str(m) for m in (pv.close_mappings or [])]

    lines = []
    lines.append(f"# {pref_label}")
    lines.append("")

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

    if definition:
        lines.append("## Definition")
        lines.append("")
        lines.append(definition)
        lines.append("")

    if scope_notes:
        lines.append("## Scope Note")
        lines.append("")
        for note in scope_notes:
            lines.append(f"> {note}")
        lines.append("")

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

    has_mappings = (uri_source == "adopted" or exact_mappings or broad_mappings
                    or narrow_mappings or related_mappings or close_mappings)

    if has_mappings:
        lines.append("## Mappings to External Vocabularies")
        lines.append("")
        if uri_source == "adopted":
            lines.append("**Adopted from** (`meaning:`) — this concept directly adopts an external URI:")
            lines.append(f"> [{concept_uri}]({concept_uri})")
            lines.append("")
        if exact_mappings:
            lines.append("**Exact matches** (`skos:exactMatch`) — equivalent concept, own URI kept:")
            for m in exact_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")
        if broad_mappings:
            lines.append("**Broad matches** (`skos:broadMatch`) — external concept is broader:")
            for m in broad_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")
        if narrow_mappings:
            lines.append("**Narrow matches** (`skos:narrowMatch`) — external concept is narrower:")
            for m in narrow_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")
        if close_mappings:
            lines.append("**Close matches** (`skos:closeMatch`) — similar but not identical:")
            for m in close_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")
        if related_mappings:
            lines.append("**Related matches** (`skos:relatedMatch`) — related external concept:")
            for m in related_mappings:
                lines.append(f"- [{m}]({m})")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"[← Back to index](index.md) · [📖 Browse](browse.md)")

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

    if verbose: print("Generating index.md...")
    generate_index(sv, yaml_path, output_dir, verbose)

    if verbose: print("Generating browse.md (tabbed)...")
    generate_browse(sv, output_dir, verbose)

    enums = sv.all_enums()
    total = sum(len(e.permissible_values) for e in enums.values())
    if verbose: print(f"Generating {total} concept pages...")

    count = 0
    for enum_name, enum in enums.items():
        for pv_name, pv in enum.permissible_values.items():
            generate_concept_page(pv_name, pv, enum, enum_name, sv, output_dir)
            count += 1

    if verbose: print(f"  Generated {count} concept pages")
    print(f"Done — {count + 2} pages written to {output_dir}/")
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
