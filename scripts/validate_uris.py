#!/usr/bin/env python3
"""
validate_uris.py
================
Validates that newly generated SKOS concept URIs:
  1. Do not collide with URIs already registered in the central terms registry
  2. Do not accidentally remove URIs that existed in the previous version
     (removal must always be done via deprecation, not deletion)

===========================================================================
NOTE [USER DEFINED]: Update TERMS_REGISTRY_URL below to point to your
central terms repository. If the repository moves (e.g. to an enterprise
GitHub account), update this URL in every vocabulary repository.
===========================================================================

Usage:
    python3 scripts/validate_uris.py --input output/data.ttl
    python3 scripts/validate_uris.py --input output/data.ttl --verbose
"""

import argparse
import sys
from pathlib import Path

try:
    from rdflib import Graph, URIRef
    from rdflib.namespace import SKOS, RDF, OWL
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
# update this URL here AND in register_terms.py in every vocabulary
# repository. Consider storing this URL as a GitHub Actions variable
# or organisation secret to make updates easier across repositories.
#
# Current format: https://raw.githubusercontent.com/{owner}/{repo}/main/terms.ttl
# Enterprise format: https://raw.{enterprise-host}/{owner}/{repo}/main/terms.ttl
TERMS_REGISTRY_URL = \
    "https://raw.githubusercontent.com/KatarinaRi/chemical-exposome-terms/main/terms.ttl"

# [USER DEFINED] Raw URL of the previously published version of THIS vocabulary.
# Points to main branch — always resolves to the last published version.
# Change only the username and repo name to match your repository.
# Set once on initial setup — never needs updating after that.
PREVIOUS_VERSION_URL = \
    "https://raw.githubusercontent.com/KatarinaRi/your-repo-name/main/output/data.ttl"


def get_concept_uris(g):
    """Get all concept URIs from an RDF graph."""
    return set(str(s) for s in g.subjects(RDF.type, SKOS.Concept))


def get_deprecated_uris(g):
    """Get all deprecated concept URIs from an RDF graph."""
    return set(str(s) for s in g.subjects(OWL.deprecated, None))


def load_graph_from_url(url, verbose=False):
    """Load an RDF graph from a URL. Returns None if not accessible."""
    try:
        if verbose:
            print(f"    Loading: {url}")
        g = Graph()
        g.parse(url, format='turtle')
        return g
    except Exception as e:
        if verbose:
            print(f"    Could not load {url}: {e}")
        return None


def validate_uris(input_path, verbose=False):
    """
    Validate concept URIs in the generated TTL file.
    Returns True if all checks pass, False if any check fails.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        return False

    if verbose:
        print(f"Loading new vocabulary: {input_path}")

    new_g = Graph()
    new_g.parse(str(input_path), format='turtle')
    new_uris = get_concept_uris(new_g)
    new_deprecated = get_deprecated_uris(new_g)

    if verbose:
        print(f"  Found {len(new_uris)} concepts "
              f"({len(new_deprecated)} deprecated)")

    all_passed = True

    # Check 1: Internal duplicates
    print("\nCheck 1: Internal URI uniqueness...")
    uri_list = [str(u) for u in new_g.subjects(RDF.type, SKOS.Concept)]
    seen = set()
    internal_dupes = []
    for uri in uri_list:
        if uri in seen:
            internal_dupes.append(uri)
        seen.add(uri)

    if internal_dupes:
        print(f"  FAILED - {len(internal_dupes)} internal duplicate URIs:")
        for uri in sorted(internal_dupes):
            print(f"    {uri}")
        all_passed = False
    else:
        print(f"  OK - {len(new_uris)} unique URIs internally")

    # Check 2: Collision with central terms registry
    print("\nCheck 2: Collision with central terms registry...")
    registry_g = load_graph_from_url(TERMS_REGISTRY_URL, verbose)

    if registry_g is None:
        print("  SKIPPED - terms registry not accessible "
              "(first vocabulary or URL not reachable)")
    else:
        registry_uris = get_concept_uris(registry_g)

        # Load previous version to exclude own already-registered URIs
        prev_g = load_graph_from_url(PREVIOUS_VERSION_URL, verbose)
        own_previous_uris = get_concept_uris(prev_g) if prev_g else set()

        # Collision = URI in registry but NOT from this vocabulary's own history
        collisions = (new_uris & registry_uris) - own_previous_uris

        if collisions:
            print(f"  FAILED - {len(collisions)} URI collisions with "
                  f"central terms registry:")
            for uri in sorted(collisions):
                print(f"    {uri}")
            all_passed = False
        else:
            new_to_register = new_uris - registry_uris
            print(f"  OK - no collisions found")
            print(f"  INFO - {len(new_to_register)} new URIs will be "
                  f"registered in terms registry")

    # Check 3: Accidental URI deletions
    print("\nCheck 3: Accidental URI deletions (vs previous version)...")
    prev_g = load_graph_from_url(PREVIOUS_VERSION_URL, verbose)

    if prev_g is None:
        print("  SKIPPED - previous version not accessible "
              "(first publication or URL not reachable)")
    else:
        prev_uris = get_concept_uris(prev_g)
        prev_deprecated = get_deprecated_uris(prev_g)
        truly_removed = (prev_uris - new_uris) - prev_deprecated

        if truly_removed:
            print(f"  FAILED - {len(truly_removed)} URIs present in "
                  f"previous version but missing in new version.")
            print("  Use owl:deprecated + dcterms:isReplacedBy instead "
                  "of deleting:")
            for uri in sorted(truly_removed):
                print(f"    {uri}")
            all_passed = False
        else:
            added = new_uris - prev_uris
            print(f"  OK - no URIs accidentally deleted")
            if added:
                print(f"  INFO - {len(added)} new concepts added")

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL CHECKS PASSED")
        print(f"  Total concepts: {len(new_uris)}")
        print(f"  Deprecated: {len(new_deprecated)}")
    else:
        print("VALIDATION FAILED - fix errors before publishing")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description='Validate concept URIs against central terms registry')
    parser.add_argument('--input', '-i', required=True,
                        help='Input SKOS Turtle file to validate')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print detailed progress information')
    args = parser.parse_args()

    passed = validate_uris(args.input, args.verbose)
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
