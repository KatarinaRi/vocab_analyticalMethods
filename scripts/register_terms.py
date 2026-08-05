#!/usr/bin/env python3
"""
register_terms.py
=================
Updates the central terms registry (terms.ttl) with concept URIs
from the newly generated vocabulary TTL.

This script:
  1. Fetches the current terms.ttl from the central terms repository
  2. Loads the newly generated vocabulary TTL
  3. Merges new concept URIs into terms.ttl
  4. Saves the updated terms.ttl locally for committing

The updated terms.ttl is then committed to the terms repository
by the GitHub Actions workflow.

===========================================================================
NOTE [USER DEFINED]: Update TERMS_REPO_RAW_URL below to point to your
central terms repository. If the repository moves (e.g. to an enterprise
GitHub account), update this URL in every vocabulary repository.
===========================================================================

Usage:
    python3 scripts/register_terms.py --input output/data.ttl
    python3 scripts/register_terms.py --input output/data.ttl --verbose
"""

import argparse
import sys
import urllib.request
from pathlib import Path

try:
    from rdflib import Graph, URIRef, Literal, Namespace
    from rdflib.namespace import SKOS, RDF, RDFS, OWL, DCTERMS, XSD
except ImportError:
    print("Error: rdflib not installed. Install with: pip install rdflib")
    sys.exit(1)

# ===========================================================================
# CONFIGURATION
# ===========================================================================

# [USER DEFINED] Raw URL of the central terms registry TTL file.
# This must be a publicly accessible raw URL.
#
# NOTE: If the terms repository moves to an enterprise GitHub account,
# update this URL in every vocabulary repository's validate_uris.py
# AND register_terms.py. Consider storing this URL in a shared config
# file or environment variable to make updates easier.
#
# Current format: https://raw.githubusercontent.com/{owner}/{repo}/main/terms.ttl
# Enterprise format: https://raw.{enterprise-host}/{owner}/{repo}/main/terms.ttl
TERMS_REPO_RAW_URL = \
    "https://raw.githubusercontent.com/KatarinaRi/chemical-exposome-terms/main/terms.ttl"

# Local path where the updated terms.ttl will be saved
# This file is then committed to the terms repository by the workflow
TERMS_OUTPUT_PATH = "terms.ttl"


def fetch_existing_terms(url, verbose=False):
    """
    Fetch the current terms.ttl from the central repository.
    Returns an empty graph if the file does not exist yet (first run).
    """
    g = Graph()
    try:
        if verbose:
            print(f"  Fetching existing terms from: {url}")
        g.parse(url, format='turtle')
        concepts = list(g.subjects(RDF.type, SKOS.Concept))
        if verbose:
            print(f"  Loaded {len(concepts)} existing concept URIs")
    except Exception as e:
        if verbose:
            print(f"  No existing terms found (first run or URL not accessible): {e}")
        # Return empty graph — this is fine on first run
    return g


def load_new_vocabulary(ttl_path, verbose=False):
    """Load the newly generated vocabulary TTL."""
    g = Graph()
    g.parse(str(ttl_path), format='turtle')
    concepts = list(g.subjects(RDF.type, SKOS.Concept))
    if verbose:
        print(f"  Loaded {len(concepts)} concepts from {ttl_path}")
    return g


def merge_terms(existing_g, new_g, verbose=False):
    """
    Merge new concept URIs into the existing terms graph.
    Only adds new concepts — never removes existing ones.
    Preserves all existing triples and adds new ones.
    """
    existing_uris = set(str(s) for s in existing_g.subjects(RDF.type, SKOS.Concept))
    new_uris = set(str(s) for s in new_g.subjects(RDF.type, SKOS.Concept))

    added = new_uris - existing_uris
    already_present = new_uris & existing_uris

    if verbose:
        print(f"  Existing concepts: {len(existing_uris)}")
        print(f"  New concepts in vocabulary: {len(new_uris)}")
        print(f"  Already registered: {len(already_present)}")
        print(f"  New to register: {len(added)}")

    if not added:
        if verbose:
            print("  No new URIs to register")
        return existing_g, added

    # Add all triples for new concepts from the vocabulary TTL
    merged_g = existing_g
    for concept_uri in added:
        uri_ref = URIRef(concept_uri)
        # Copy all triples about this concept
        for p, o in new_g.predicate_objects(uri_ref):
            merged_g.add((uri_ref, p, o))

        if verbose:
            print(f"    + Registered: {concept_uri}")

    # Copy namespace bindings from new graph
    for prefix, namespace in new_g.namespaces():
        merged_g.bind(prefix, namespace)

    return merged_g, added


def save_terms(g, output_path, verbose=False):
    """Save the updated terms graph to a Turtle file."""
    output_path = Path(output_path)
    g.serialize(str(output_path), format='turtle')
    concepts = list(g.subjects(RDF.type, SKOS.Concept))
    if verbose:
        print(f"  Saved {len(concepts)} total concept URIs to {output_path}")
    return output_path


def register_terms(input_path, verbose=False):
    """
    Main function — fetch, merge and save updated terms registry.
    Returns the number of newly registered URIs.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    if verbose:
        print(f"\nLoading new vocabulary: {input_path}")

    # 1. Fetch existing terms
    existing_g = fetch_existing_terms(TERMS_REPO_RAW_URL, verbose)

    # 2. Load new vocabulary
    new_g = load_new_vocabulary(input_path, verbose)

    # 3. Merge
    if verbose:
        print("\nMerging...")
    merged_g, added = merge_terms(existing_g, new_g, verbose)

    # 4. Save
    if verbose:
        print(f"\nSaving to {TERMS_OUTPUT_PATH}...")
    save_terms(merged_g, TERMS_OUTPUT_PATH, verbose)

    total = len(list(merged_g.subjects(RDF.type, SKOS.Concept)))
    print(f"Terms registry updated: {len(added)} new URIs added, "
          f"{total} total concept URIs")

    return len(added)


def main():
    parser = argparse.ArgumentParser(
        description='Update central terms registry with new concept URIs')
    parser.add_argument('--input', '-i', required=True,
                        help='Input SKOS Turtle file (newly generated vocabulary)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print detailed progress information')
    args = parser.parse_args()

    register_terms(args.input, args.verbose)


if __name__ == '__main__':
    main()
