#!/usr/bin/env python3
"""
generate_vocab_index.py
=======================
Generates a clean, SKOS-friendly index.md for a vocabulary
replacing the default gen-doc output.

The generated index includes:
  - Vocabulary metadata (title, version, license, description, creator)
  - Link to hierarchy diagram
  - Alphabetical concept index with one-line definitions
  - Concept count per enum/scheme
  - Only vocabulary content — no LinkML types, slots or classes

Usage:
    python3 scripts/generate_vocab_index.py --input vocabulary/data.yaml --output docs/index.md
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

try:
    from linkml_runtime.utils.schemaview import SchemaView
except ImportError:
    print("Error: linkml not installed. Install with: pip install linkml")
    sys.exit(1)


def generate_vocab_index(yaml_path, output_path, verbose=False):
    """
    Generate a clean vocabulary index page from a LinkML vocabulary YAML.

    Args:
        yaml_path: Path to the LinkML vocabulary YAML file
        output_path: Path for the output index.md file
        verbose: Print progress information
    """
    sv = SchemaView(str(yaml_path))
    schema = sv.schema

    title = schema.title or schema.name or "Controlled Vocabulary"
    description = str(schema.description).strip() if schema.description else ""
    version = str(schema.version) if schema.version else "—"
    license_uri = str(schema.license) if schema.license else "—"
    created_by = str(schema.created_by) if schema.created_by else "—"
    created_on = str(schema.created_on) if schema.created_on else "—"
    updated_on = str(schema.last_updated_on) if schema.last_updated_on else "—"
    schema_id = str(schema.id) if schema.id else "—"

    # Format dates nicely
    for date_str in [created_on, updated_on]:
        try:
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
        except Exception:
            pass

    if verbose:
        print(f"Generating index for: {title}")

    lines = []

    # Title
    lines.append(f"# {title}")
    lines.append("")

    # Description
    if description:
        lines.append(description)
        lines.append("")

    # Metadata table
    lines.append("## Vocabulary Metadata")
    lines.append("")
    lines.append("| Property | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| **URI** | [{schema_id}]({schema_id}) |")
    lines.append(f"| **Version** | {version} |")
    lines.append(f"| **License** | [{license_uri}]({license_uri}) |")
    lines.append(f"| **Creator** | [{created_by}]({created_by}) |")

    # Format dates
    created_display = created_on.split('T')[0] if 'T' in created_on else created_on
    updated_display = updated_on.split('T')[0] if 'T' in updated_on else updated_on
    lines.append(f"| **Created** | {created_display} |")
    lines.append(f"| **Last updated** | {updated_display} |")
    lines.append("")

    # Schema status from annotations
    if schema.annotations:
        status = schema.annotations.get('schema_status')
        if status:
            lines.append(f"> **Status:** `{status.value}`")
            lines.append("")

    # See also / related resources
    if schema.see_also:
        lines.append("## Related Resources")
        lines.append("")
        for link in schema.see_also:
            lines.append(f"- [{link}]({link})")
        lines.append("")

    # Schema overview links
    lines.append("## Schema Overview")
    lines.append("")
    lines.append("- [Concept hierarchy diagram](hierarchy.md)")
    lines.append("")

    # Process enums
    enums = sv.all_enums()
    if not enums:
        lines.append("*No enumerations defined.*")
    else:
        for enum_name, enum in enums.items():
            enum_description = str(enum.description).strip() if enum.description else ""
            concept_count = len(enum.permissible_values)

            lines.append(f"## {enum_name}")
            lines.append("")
            if enum_description:
                lines.append(enum_description)
                lines.append("")
            lines.append(f"**{concept_count} concepts** — listed alphabetically below.")
            lines.append("")

            # Alphabetical concept index
            lines.append("| Concept | Definition |")
            lines.append("| --- | --- |")

            # Sort alphabetically
            sorted_pvs = sorted(enum.permissible_values.items(),
                                key=lambda x: x[0].lower())

            for pv_name, pv in sorted_pvs:
                # Get display label
                label = pv_name
                if pv.aliases:
                    label = f"{pv_name} ({pv.aliases[0]})"

                # Get short definition
                definition = ""
                if pv.description:
                    desc = str(pv.description).strip()
                    # Truncate long definitions
                    if len(desc) > 120:
                        desc = desc[:117] + "..."
                    definition = desc

                # Link to concept page
                lines.append(f"| [{pv_name}]({pv_name}.md) | {definition} |")

            lines.append("")

            # Hierarchy summary
            lines.append("### Concept Hierarchy")
            lines.append("")

            # Build tree
            children = {}
            roots = []
            for pv_name, pv in enum.permissible_values.items():
                if pv.is_a:
                    if pv.is_a not in children:
                        children[pv.is_a] = []
                    children[pv.is_a].append(pv_name)
                else:
                    roots.append(pv_name)

            def write_tree(node, depth=0, lines=lines):
                indent = "    " * depth
                prefix = "└── " if depth > 0 else ""
                lines.append(f"{indent}{prefix}**[{node}]({node}.md)**")
                for child in sorted(children.get(node, [])):
                    write_tree(child, depth + 1, lines)

            lines.append("```")
            for root in sorted(roots):
                write_tree(root)
            lines.append("```")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated from LinkML vocabulary YAML. "
                 f"Last updated: {updated_display}.*")
    lines.append("")

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        f.write('\n')

    if verbose:
        print(f"Written to {output_path}")
        print(f"Total concepts: {sum(len(e.permissible_values) for e in enums.values())}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Generate clean vocabulary index from LinkML YAML')
    parser.add_argument('--input', '-i', required=True,
                        help='Input LinkML vocabulary YAML file')
    parser.add_argument('--output', '-o', default='docs/index.md',
                        help='Output index.md file (default: docs/index.md)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print progress information')
    args = parser.parse_args()

    generate_vocab_index(args.input, args.output, args.verbose)
    print(f"Vocabulary index written to {args.output}")


if __name__ == '__main__':
    main()
