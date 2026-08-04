#!/usr/bin/env python3
"""
validate_uris.py
================
Validates that newly generated SKOS concept URIs:
  1. Do not collide with URIs in other published vocabularies
  2. Do not accidentally remove URIs that existed in previous version
     (removal should always be done via deprecation, not deletion)

Usage:
    python3 scripts/validate_uris.py --input output/data.ttl
    python3 scripts/validate_uris.py --input output/data.ttl --verbose

Configuration:
    Edit the PUBLISHED_VOCABULARIES list below to include the raw GitHub
    URLs of all your other published vocabulary TTL files.
    These are checked for URI collisions.
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
# Edit this list to include all your other published vocabulary TTL files.
# Each entry is the raw GitHub URL of a vocabulary's output TTL.
# Leave empty if this is your first vocabulary.
# ===========================================================================
PUBLISHED_VOCABULARIES = [
    # Examples — uncomment and add your actual URLs:
    # "https://raw.githubusercontent.com/KatarinaRi/vocab_matrix/main/output/data.ttl",
    # "https://raw.githubusercontent.com/KatarinaRi/vocab_parameter/main/output/data.ttl",
    # "https://raw.githubusercontent.com/KatarinaRi/vocab_samplingMethod/main/output/data.ttl",
]

# URL of the previously published version of THIS vocabulary
# Used to detect accidental URI deletions
# Leave empty on first publication
PREVIOUS_VERSION_URL = \
    "https://raw.githubusercontent.com/KatarinaRi/vocab_analyticalMethods/main/output/data.ttl"


def get_concept_uris(g):
    """Get all concept URIs from an RDF graph."""
    uris = set()
    for s in g.subjects(RDF.type, SKOS.Concept):
        uris.add(str(s))
    return uris


def get_deprecated_uris(g):
    """Get all deprecated concept URIs from an RDF graph."""
    deprecated = set()
    for s in g.subjects(OWL.deprecated, None):
        deprecated.add(str(s))
    return deprecated


def load_graph_from_url(url, verbose=False):
    """Load an RDF graph from a URL. Returns None if URL is not accessible."""
    try:
        import urllib.request
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

    # Load newly generated TTL
    new_g = Graph()
    new_g.parse(str(input_path), format='turtle')
    new_uris = get_concept_uris(new_g)
    new_deprecated = get_deprecated_uris(new_g)

    if verbose:
        print(f"  Found {len(new_uris)} concepts "
              f"({len(new_deprecated)} deprecated)")

    all_passed = True

    # ── Check 1: Internal duplicates ─────────────────────────────────────────
    # rdflib deduplicates automatically so if we get here without error
    # the TTL itself has no internal duplicates — but check anyway
    print("\nCheck 1: Internal URI uniqueness...")
    uri_list = list(new_g.subjects(RDF.type, SKOS.Concept))
    uri_strings = [str(u) for u in uri_list]
    seen = set()
    internal_dupes = []
    for uri in uri_strings:
        if uri in seen:
            internal_dupes.append(uri)
        seen.add(uri)

    if internal_dupes:
        print(f"  FAILED — {len(internal_dupes)} internal duplicate URIs:")
        for uri in sorted(internal_dupes):
            print(f"    {uri}")
        all_passed = False
    else:
        print(f"  OK — {len(new_uris)} unique URIs internally")

    # ── Check 2: Collisions with other published vocabularies ─────────────────
    print("\nCheck 2: Collisions with other published vocabularies...")
    if not PUBLISHED_VOCABULARIES:
        print("  SKIPPED — no other vocabularies configured")
    else:
        existing_uris = set()
        loaded_count = 0
        for url in PUBLISHED_VOCABULARIES:
            g = load_graph_from_url(url, verbose)
            if g:
                vocab_uris = get_concept_uris(g)
                existing_uris.update(vocab_uris)
                loaded_count += 1
                if verbose:
                    print(f"    Loaded {len(vocab_uris)} concepts from {url}")

        if loaded_count == 0:
            print("  SKIPPED — no other vocabularies could be loaded")
        else:
            collisions = new_uris & existing_uris
            if collisions:
                print(f"  FAILED — {len(collisions)} URI collisions with "
                      f"existing vocabularies:")
                for uri in sorted(collisions):
                    print(f"    {uri}")
                all_passed = False
            else:
                print(f"  OK — no collisions with {len(existing_uris)} "
                      f"existing URIs across {loaded_count} vocabularies")

    # ── Check 3: Accidental URI deletions ─────────────────────────────────────
    print("\nCheck 3: Accidental URI deletions (vs previous version)...")
    if not PREVIOUS_VERSION_URL:
        print("  SKIPPED — no previous version URL configured")
    else:
        prev_g = load_graph_from_url(PREVIOUS_VERSION_URL, verbose)
        if not prev_g:
            print("  SKIPPED — previous version not accessible "
                  "(first publication or URL not reachable)")
        else:
            prev_uris = get_concept_uris(prev_g)
            prev_deprecated = get_deprecated_uris(prev_g)

            # URIs that existed before but are now missing entirely
            # (not deprecated — completely gone)
            truly_removed = (prev_uris - new_uris) - prev_deprecated

            if truly_removed:
                print(f"  FAILED — {len(truly_removed)} URIs present in "
                      f"previous version but missing in new version.")
                print("  These should be deprecated (owl:deprecated + "
                      "dcterms:isReplacedBy), not deleted:")
                for uri in sorted(truly_removed):
                    print(f"    {uri}")
                all_passed = False
            else:
                added = new_uris - prev_uris
                print(f"  OK — no URIs accidentally deleted")
                if added:
                    print(f"  INFO — {len(added)} new concepts added in "
                          f"this version")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    if all_passed:
        print("ALL CHECKS PASSED")
        print(f"  Total concepts: {len(new_uris)}")
        print(f"  Deprecated: {len(new_deprecated)}")
    else:
        print("VALIDATION FAILED — fix errors before publishing")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description='Validate concept URIs in generated SKOS TTL')
    parser.add_argument('--input', '-i', required=True,
                        help='Input SKOS Turtle file to validate')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print detailed progress information')
    args = parser.parse_args()

    passed = validate_uris(args.input, args.verbose)
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
