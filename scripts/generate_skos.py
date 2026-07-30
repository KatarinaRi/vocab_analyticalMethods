#!/usr/bin/env python3
"""
generate_skos.py
================
Generates a SKOS Turtle file from a LinkML vocabulary YAML file.

Usage:
    python3 scripts/generate_skos.py --input vocabulary/my-vocabulary.yaml
    python3 scripts/generate_skos.py --input vocabulary/my-vocabulary.yaml --output output/my-vocabulary-raw.ttl
    python3 scripts/generate_skos.py --all   # process all YAML files in vocabulary/

Mappings:
    LinkML enum              → skos:ConceptScheme
    permissible value        → skos:Concept
    is_a:                    → skos:broader
    description:             → skos:definition
    aliases:                 → skos:altLabel
    comments:                → skos:scopeNote
    meaning:                 → skos:exactMatch + identity (no new URI minted)
    exact_mappings:          → skos:exactMatch
    broad_mappings:          → skos:broadMatch
    narrow_mappings:         → skos:narrowMatch
    related_mappings:        → skos:relatedMatch
    close_mappings:          → skos:closeMatch
    no is_a (root concept)   → skos:topConceptOf + skos:hasTopConcept
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from linkml_runtime.utils.schemaview import SchemaView
    from rdflib import Graph, URIRef, Literal, Namespace, BNode
    from rdflib.namespace import SKOS, RDF, RDFS, OWL, DCTERMS, XSD
except ImportError as e:
    print(f"Error: missing dependency — {e}")
    print("Install with: pip install linkml rdflib")
    sys.exit(1)


def get_concept_uri(pv_name, pv, default_namespace):
    """Return the URI for a permissible value."""
    if pv.meaning:
        return URIRef(str(pv.meaning))
    return URIRef(default_namespace + pv_name)


def generate_skos(input_path: str, output_path: str = None, verbose: bool = False):
    """
    Generate a SKOS Turtle file from a LinkML vocabulary YAML.

    Args:
        input_path: Path to the LinkML YAML file
        output_path: Path for the output Turtle file (optional)
        verbose: Print progress information
    """
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    if output_path is None:
        stem = input_path.stem
        output_path = input_path.parent.parent / "output" / f"{stem}-raw.ttl"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"Reading: {input_path}")

    # Load schema
    sv = SchemaView(str(input_path))
    schema = sv.schema

    # Set up RDF graph
    g = Graph()

    # Bind standard prefixes
    g.bind('skos', SKOS)
    g.bind('dcterms', DCTERMS)
    g.bind('owl', OWL)
    g.bind('rdfs', RDFS)

    # Determine base namespace from schema id
    schema_id = str(schema.id) if schema.id else "https://example.org/vocabulary/"
    if not schema_id.endswith('/'):
        schema_id += '/'

    # Bind vocabulary prefix
    VOCAB = Namespace(schema_id)
    g.bind('vocab', VOCAB)

    # Also bind default prefix if defined
    default_prefix = schema.default_prefix
    if default_prefix and default_prefix in (schema.prefixes or {}):
        prefix_uri = str(schema.prefixes[default_prefix].prefix_reference)
        TERMS = Namespace(prefix_uri)
        g.bind(default_prefix, TERMS)
        default_ns = prefix_uri
    else:
        default_ns = schema_id

    # Add owl:Ontology metadata
    ontology_uri = URIRef(str(schema.id)) if schema.id else URIRef(schema_id.rstrip('/'))
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    if schema.title:
        g.add((ontology_uri, DCTERMS.title, Literal(str(schema.title), lang='en')))
    if schema.description:
        g.add((ontology_uri, DCTERMS.description,
               Literal(str(schema.description).strip(), lang='en')))
    if schema.version:
        g.add((ontology_uri, OWL.versionInfo, Literal(str(schema.version))))
    if schema.license:
        g.add((ontology_uri, DCTERMS.license, URIRef(str(schema.license))))
    if schema.created_by:
        g.add((ontology_uri, DCTERMS.creator, URIRef(str(schema.created_by))))
    if schema.created_on:
        g.add((ontology_uri, DCTERMS.created,
               Literal(str(schema.created_on), datatype=XSD.dateTime)))
    if schema.last_updated_on:
        g.add((ontology_uri, DCTERMS.modified,
               Literal(str(schema.last_updated_on), datatype=XSD.dateTime)))

    # Process each enum → skos:ConceptScheme
    for enum_name, enum in sv.all_enums().items():

        scheme_uri = VOCAB[enum_name]
        g.add((scheme_uri, RDF.type, SKOS.ConceptScheme))
        g.add((scheme_uri, SKOS.prefLabel, Literal(enum_name, lang='en')))

        if enum.description:
            g.add((scheme_uri, SKOS.definition,
                   Literal(str(enum.description).strip(), lang='en')))

        if verbose:
            print(f"  Processing enum: {enum_name} ({len(enum.permissible_values)} values)")

        # First pass — collect all concept URIs and identify top concepts
        concept_uris = {}
        for pv_name, pv in enum.permissible_values.items():
            concept_uris[pv_name] = get_concept_uri(pv_name, pv, default_ns)

        # Second pass — generate concept triples
        for pv_name, pv in enum.permissible_values.items():
            concept_uri = concept_uris[pv_name]

            # Type
            g.add((concept_uri, RDF.type, SKOS.Concept))
            g.add((concept_uri, SKOS.inScheme, scheme_uri))

            # Notation — the LinkML key
            g.add((concept_uri, SKOS.notation, Literal(pv_name)))

            # prefLabel — use pv_name as fallback
            g.add((concept_uri, SKOS.prefLabel, Literal(pv_name, lang='en')))

            # definition from description
            if pv.description:
                g.add((concept_uri, SKOS.definition,
                       Literal(str(pv.description).strip(), lang='en')))

            # altLabel from aliases
            for alias in (pv.aliases or []):
                g.add((concept_uri, SKOS.altLabel, Literal(str(alias), lang='en')))

            # scopeNote from comments
            for comment in (pv.comments or []):
                g.add((concept_uri, SKOS.scopeNote, Literal(str(comment).strip(), lang='en')))

            # skos:broader from is_a
            if pv.is_a:
                parent_uri = concept_uris.get(pv.is_a)
                if parent_uri:
                    g.add((concept_uri, SKOS.broader, parent_uri))
                else:
                    if verbose:
                        print(f"    Warning: is_a '{pv.is_a}' not found for '{pv_name}'")
            else:
                # No parent = top concept
                g.add((concept_uri, SKOS.topConceptOf, scheme_uri))
                g.add((scheme_uri, SKOS.hasTopConcept, concept_uri))

            # If meaning: is defined — add exactMatch to external URI
            if pv.meaning:
                external_uri = URIRef(str(pv.meaning))
                # Concept is the external URI itself — add skos:exactMatch as cross-reference
                # Note: when meaning: is set, concept_uri IS the external URI
                # We also mint a cenvo: URI that exactMatches it
                own_uri = URIRef(default_ns + pv_name)
                if own_uri != concept_uri:
                    g.add((own_uri, RDF.type, SKOS.Concept))
                    g.add((own_uri, SKOS.inScheme, scheme_uri))
                    g.add((own_uri, SKOS.notation, Literal(pv_name)))
                    g.add((own_uri, SKOS.exactMatch, concept_uri))

            # exact_mappings → skos:exactMatch
            for mapping in (pv.exact_mappings or []):
                g.add((concept_uri, SKOS.exactMatch, URIRef(str(mapping))))

            # broad_mappings → skos:broadMatch
            for mapping in (pv.broad_mappings or []):
                g.add((concept_uri, SKOS.broadMatch, URIRef(str(mapping))))

            # narrow_mappings → skos:narrowMatch
            for mapping in (pv.narrow_mappings or []):
                g.add((concept_uri, SKOS.narrowMatch, URIRef(str(mapping))))

            # related_mappings → skos:relatedMatch
            for mapping in (pv.related_mappings or []):
                g.add((concept_uri, SKOS.relatedMatch, URIRef(str(mapping))))

            # close_mappings → skos:closeMatch
            for mapping in (pv.close_mappings or []):
                g.add((concept_uri, SKOS.closeMatch, URIRef(str(mapping))))

    # Serialize
    g.serialize(str(output_path), format='turtle')

    triple_count = len(g)
    if verbose:
        print(f"\nGenerated {triple_count} triples")
        print(f"Output: {output_path}")

    return str(output_path), triple_count


def main():
    parser = argparse.ArgumentParser(
        description='Generate SKOS Turtle from LinkML vocabulary YAML')
    parser.add_argument('--input', '-i',
                        help='Input LinkML YAML file')
    parser.add_argument('--output', '-o',
                        help='Output Turtle file (default: output/<name>-raw.ttl)')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Process all YAML files in vocabulary/ directory')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print progress information')
    args = parser.parse_args()

    if args.all:
        vocab_dir = Path('vocabulary')
        yaml_files = list(vocab_dir.glob('*.yaml')) + list(vocab_dir.glob('*.yml'))
        if not yaml_files:
            print("No YAML files found in vocabulary/")
            sys.exit(1)
        for yaml_file in yaml_files:
            print(f"Processing: {yaml_file}")
            output, triples = generate_skos(str(yaml_file), verbose=args.verbose)
            print(f"  -> {output} ({triples} triples)")
    elif args.input:
        output, triples = generate_skos(args.input, args.output, verbose=args.verbose)
        print(f"Generated: {output} ({triples} triples)")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
