#!/usr/bin/env python3
"""
generate_hierarchy_diagram.py
=============================
Generates a Mermaid class diagram showing the SKOS concept hierarchy
from a SKOSified TTL file or directly from a LinkML vocabulary YAML.

The diagram shows:
  - skos:broader / skos:narrower relationships as inheritance arrows
  - Top concepts as root nodes
  - Concept labels (prefLabel or notation)

Usage:
    # From SKOS TTL file
    python3 scripts/generate_hierarchy_diagram.py --input output/data.ttl --output docs/hierarchy.md

    # From LinkML YAML directly (uses is_a: hierarchy)
    python3 scripts/generate_hierarchy_diagram.py --yaml vocabulary/data.yaml --output docs/hierarchy.md
"""

import argparse
import sys
from pathlib import Path

try:
    from rdflib import Graph, URIRef, Literal, Namespace
    from rdflib.namespace import SKOS, RDF, RDFS
except ImportError:
    print("Error: rdflib not installed. Install with: pip install rdflib")
    sys.exit(1)


def sanitize_id(uri_or_str):
    """Convert a URI or string to a valid Mermaid node ID."""
    s = str(uri_or_str)
    # Take the last part of a URI
    if '/' in s:
        s = s.split('/')[-1]
    if '#' in s:
        s = s.split('#')[-1]
    # Replace non-alphanumeric characters
    s = ''.join(c if c.isalnum() or c == '_' else '_' for c in s)
    return s


def get_label(g, concept_uri):
    """Get the best available label for a concept."""
    # Try prefLabel first
    for lang in ['en', None]:
        for label in g.objects(concept_uri, SKOS.prefLabel):
            if lang is None or (hasattr(label, 'language') and label.language == lang):
                return str(label)
    # Try notation
    for notation in g.objects(concept_uri, SKOS.notation):
        return str(notation)
    # Fall back to last part of URI
    return sanitize_id(concept_uri)


def generate_from_ttl(input_path, output_path, max_depth=None, verbose=False):
    """Generate hierarchy diagram from a SKOS TTL file."""
    g = Graph()
    g.parse(str(input_path), format='turtle')

    if verbose:
        print(f"Loaded {len(g)} triples from {input_path}")

    # Get all concepts
    concepts = list(g.subjects(RDF.type, SKOS.Concept))
    if not concepts:
        print("Warning: no skos:Concept found in TTL file")
        return

    # Get all broader/narrower relationships
    relationships = []
    for s, p, o in g.triples((None, SKOS.broader, None)):
        if s in concepts:
            relationships.append((o, s))  # parent -> child

    # Get top concepts (no broader)
    has_broader = set(s for s, p, o in g.triples((None, SKOS.broader, None)))
    top_concepts = [c for c in concepts if c not in has_broader]

    if verbose:
        print(f"Found {len(concepts)} concepts, {len(relationships)} relationships, {len(top_concepts)} top concepts")

    # Get scheme info
    schemes = list(g.subjects(RDF.type, SKOS.ConceptScheme))
    scheme_label = "Concept Hierarchy"
    if schemes:
        for label in g.objects(schemes[0], SKOS.prefLabel):
            scheme_label = str(label)
            break

    # Build Mermaid diagram
    lines = []
    lines.append("```mermaid")
    lines.append("classDiagram")
    lines.append(f"    %% {scheme_label}")
    lines.append("")

    # Add relationships
    added_concepts = set()
    for parent, child in relationships:
        parent_id = sanitize_id(parent)
        child_id = sanitize_id(child)
        parent_label = get_label(g, parent)
        child_label = get_label(g, child)

        # Add class definitions
        if parent_id not in added_concepts:
            lines.append(f"    class {parent_id}[\"{parent_label}\"]")
            added_concepts.add(parent_id)
        if child_id not in added_concepts:
            lines.append(f"    class {child_id}[\"{child_label}\"]")
            added_concepts.add(child_id)

        # Add inheritance arrow (child inherits from parent = narrower than parent)
        lines.append(f"    {parent_id} <|-- {child_id}")

    # Add any orphan concepts not in relationships
    for concept in concepts:
        cid = sanitize_id(concept)
        if cid not in added_concepts:
            label = get_label(g, concept)
            lines.append(f"    class {cid}[\"{label}\"]")
            added_concepts.add(cid)

    lines.append("```")

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {scheme_label} — Concept Hierarchy\n\n")
        f.write("This diagram shows the hierarchical relationships between concepts.\n")
        f.write("Arrows point from broader (parent) to narrower (child) concepts.\n\n")
        f.write('\n'.join(lines))
        f.write('\n')

    if verbose:
        print(f"Written to {output_path}")

    return output_path


def generate_from_yaml(yaml_path, output_path, verbose=False):
    """Generate hierarchy diagram directly from LinkML vocabulary YAML."""
    try:
        from linkml_runtime.utils.schemaview import SchemaView
    except ImportError:
        print("Error: linkml not installed. Install with: pip install linkml")
        sys.exit(1)

    sv = SchemaView(str(yaml_path))
    schema = sv.schema

    lines = []
    lines.append("```mermaid")
    lines.append("classDiagram")
    lines.append(f"    %% {schema.title or schema.name}")
    lines.append("")

    added = set()

    for enum_name, enum in sv.all_enums().items():
        lines.append(f"    %% --- {enum_name} ---")

        for pv_name, pv in enum.permissible_values.items():
            # Get display label
            label = pv_name
            if pv.aliases:
                label = str(pv.aliases[0])

            # Sanitize IDs
            safe_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in pv_name)

            if safe_name not in added:
                lines.append(f'    class {safe_name}["{label}"]')
                added.add(safe_name)

            if pv.is_a:
                safe_parent = ''.join(c if c.isalnum() or c == '_' else '_' for c in pv.is_a)
                parent_pv = enum.permissible_values.get(pv.is_a)
                parent_label = pv.is_a
                if parent_pv and parent_pv.aliases:
                    parent_label = str(parent_pv.aliases[0])

                if safe_parent not in added:
                    lines.append(f'    class {safe_parent}["{parent_label}"]')
                    added.add(safe_parent)

                lines.append(f"    {safe_parent} <|-- {safe_name}")

        lines.append("")

    lines.append("```")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    title = schema.title or schema.name or "Vocabulary"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {title} — Concept Hierarchy\n\n")
        f.write("This diagram shows the hierarchical relationships between concepts ")
        f.write("using arrows from broader (parent) to narrower (child) concepts.\n\n")
        f.write('\n'.join(lines))
        f.write('\n')

    if verbose:
        print(f"Written to {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Generate Mermaid hierarchy diagram from SKOS TTL or LinkML YAML')
    parser.add_argument('--input', '-i',
                        help='Input SKOS Turtle file')
    parser.add_argument('--yaml', '-y',
                        help='Input LinkML vocabulary YAML file (alternative to --input)')
    parser.add_argument('--output', '-o', default='docs/hierarchy.md',
                        help='Output Markdown file (default: docs/hierarchy.md)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print progress information')
    args = parser.parse_args()

    if args.yaml:
        generate_from_yaml(args.yaml, args.output, args.verbose)
        print(f"Hierarchy diagram written to {args.output}")
    elif args.input:
        generate_from_ttl(args.input, args.output, verbose=args.verbose)
        print(f"Hierarchy diagram written to {args.output}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
