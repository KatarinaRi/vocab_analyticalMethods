#!/usr/bin/env python3
"""
skosify_vocab.py
================
Validates and repairs a SKOS Turtle file using Skosify.

Skosify does the following:
  - Adds missing skos:narrower from skos:broader (and vice versa)
  - Marks top concepts (skos:hasTopConcept / skos:topConceptOf)
  - Detects and reports SKOS integrity violations:
      * Concepts with no prefLabel
      * Cycles in the hierarchy
      * Orphan concepts
      * Missing skos:inScheme
  - Converts non-SKOS RDF to SKOS where possible

Usage:
    python3 scripts/skosify_vocab.py --input output/my-vocabulary-raw.ttl
    python3 scripts/skosify_vocab.py --input output/my-vocabulary-raw.ttl --output output/my-vocabulary.ttl
    python3 scripts/skosify_vocab.py --all   # process all raw TTL files in output/
"""

import argparse
import sys
from pathlib import Path

try:
    import skosify
except ImportError:
    print("Error: skosify not installed.")
    print("Install with: pip install skosify")
    sys.exit(1)

try:
    from rdflib import Graph
except ImportError:
    print("Error: rdflib not installed.")
    print("Install with: pip install rdflib")
    sys.exit(1)


def run_skosify(input_path: str, output_path: str = None, verbose: bool = False):
    """
    Validate and repair a SKOS Turtle file using Skosify.

    Args:
        input_path: Path to the raw SKOS Turtle file
        output_path: Path for the output repaired Turtle file
        verbose: Print progress information
    """
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    # Derive output path if not specified
    if output_path is None:
        stem = input_path.stem
        # Remove -raw suffix if present
        if stem.endswith('-raw'):
            stem = stem[:-4]
        output_path = input_path.parent / f"{stem}.ttl"

    output_path = Path(output_path)

    if verbose:
        print(f"Running Skosify on: {input_path}")

    # Load the RDF graph
    voc = skosify.skosify(
        str(input_path),
        narrower=True,           # add missing skos:narrower from skos:broader
        transitive=False,        # do not add transitive relations (inferred by reasoner)
        mark_top_concepts=True,  # add skos:topConceptOf / skos:hasTopConcept
        eliminate_redundancy=True,  # remove redundant broader/narrower
        break_cycles=True,       # detect and break cycles in hierarchy
        keep_related=False,      # do not add skos:related between siblings
        cleanup_classes=True,    # remove unused owl:Class declarations
        cleanup_properties=True, # remove unused property declarations
    )

    # Serialize repaired vocabulary
    voc.serialize(str(output_path), format='turtle')

    triple_count = len(voc)
    if verbose:
        print(f"Skosify complete: {triple_count} triples")
        print(f"Output: {output_path}")

    return str(output_path), triple_count


def main():
    parser = argparse.ArgumentParser(
        description='Validate and repair SKOS Turtle using Skosify')
    parser.add_argument('--input', '-i',
                        help='Input raw SKOS Turtle file')
    parser.add_argument('--output', '-o',
                        help='Output repaired Turtle file')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Process all *-raw.ttl files in output/ directory')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print progress information')
    args = parser.parse_args()

    if args.all:
        output_dir = Path('output')
        raw_files = list(output_dir.glob('*-raw.ttl'))
        if not raw_files:
            print("No *-raw.ttl files found in output/")
            sys.exit(1)
        for raw_file in raw_files:
            print(f"Processing: {raw_file}")
            output, triples = run_skosify(str(raw_file), verbose=args.verbose)
            print(f"  -> {output} ({triples} triples)")
    elif args.input:
        output, triples = run_skosify(args.input, args.output, args.verbose)
        print(f"Skosified: {output} ({triples} triples)")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
