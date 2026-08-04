# Vocabulary Publishing Template

A GitHub template repository for publishing SKOS controlled vocabularies
defined in LinkML YAML format. Push a vocabulary YAML — get a validated,
SKOSified Turtle file and human-readable documentation automatically.

This template is reusable by **any user**, on **any GitHub account**
(personal, organisation or enterprise), for **any SKOS vocabulary**.

---

## What this template does

Every time you push a vocabulary YAML file, GitHub Actions automatically:

1. **Validates** the YAML using `linkml-lint`
2. **Generates SKOS** Turtle from the LinkML YAML
3. **Repairs and validates** the SKOS using Skosify
4. **Validates concept URIs** — checks for collisions with other published
   vocabularies and accidental deletions of existing URIs
5. **Generates HTML documentation** with index, hierarchy and concept pages
6. **Deploys documentation** to GitHub Pages
7. **Commits generated TTL** files back to the repository

---

## Repository structure

```
.
├── .github/
│   ├── workflows/
│   │   └── publish-vocabulary.yml   ← automated pipeline (do not edit)
│   └── ISSUE_TEMPLATE/
│       └── term-request.md          ← template for community term requests
├── vocabulary/
│   └── my-vocabulary.yaml           ← [USER DEFINED] your vocabulary source
├── scripts/                         ← pipeline scripts (do not edit)
│   ├── generate_skos.py             ← generates SKOS Turtle from LinkML YAML
│   ├── generate_vocab_pages.py      ← generates HTML documentation
│   ├── skosify_vocab.py             ← validates and repairs SKOS
│   └── validate_uris.py             ← checks for URI collisions and deletions
├── output/                          ← auto-generated TTL files
│   ├── my-vocabulary-raw.ttl        ← raw SKOS (before Skosify)
│   └── my-vocabulary.ttl            ← final SKOS — use this for submission
├── docs/                            ← auto-generated documentation
├── mkdocs.yml                       ← [USER DEFINED] site name and URL
├── CHANGELOG.md                     ← [USER DEFINED] version history
└── README.md                        ← this file
```

---

## Quick start — what YOU need to define

### Step 1 — Edit `vocabulary/my-vocabulary.yaml`

This is your vocabulary source file. All fields marked `[USER DEFINED]`
must be filled in before pushing:

| Field | Description |
| --- | --- |
| `id` | Persistent URI for your vocabulary (e.g. w3id.org namespace) |
| `name` | Machine-readable name — no spaces, use hyphens |
| `title` | Human-readable vocabulary title |
| `description` | What this vocabulary covers and who it is for |
| `version` | Semantic version e.g. `"1.0.0"` |
| `license` | License URI — CC-BY 4.0 recommended |
| `created_by` | Your ORCID URI |
| `created_on` | Creation date in ISO 8601 format |
| `last_updated_on` | Last update date in ISO 8601 format |
| `modified_by` | ORCID of person who last modified |
| `annotations.schema_status` | `draft` / `review` / `stable` / `deprecated` |
| `annotations.repo_url` | Your GitHub repository URL — used for download links |
| `prefixes` | Add your vocabulary namespace prefix |
| `default_prefix` | Your prefix name (e.g. `myv`) |
| `enums` | Your vocabulary concepts — rename and fill in |

### Step 2 — Edit `mkdocs.yml`

| Field | Description |
| --- | --- |
| `site_name` | Your vocabulary name |
| `site_url` | Your GitHub Pages URL: `https://{username}.github.io/{repo-name}/` |
| `site_description` | Short description |

### Step 3 — Configure URI validation in `scripts/validate_uris.py`

Open `scripts/validate_uris.py` and update the two configuration
variables at the top of the file — **once only, when setting up
the repository**:

```python
# List of other published vocabulary TTL files to check against
# for URI collisions. Add one URL per vocabulary you publish.
# Leave empty [] for your first vocabulary.
PUBLISHED_VOCABULARIES = [
    # "https://raw.githubusercontent.com/your-username/vocab-matrix/main/output/data.ttl",
    # "https://raw.githubusercontent.com/your-username/vocab-parameter/main/output/data.ttl",
]

# URL of the previously published version of THIS vocabulary.
# Used to detect accidental URI deletions between versions.
# Points to main branch — always resolves to the last published version.
# Change only the username and repo name to match your repository.
# Never needs updating after initial setup.
PREVIOUS_VERSION_URL = \
    "https://raw.githubusercontent.com/your-username/your-repo-name/main/output/data.ttl"
```

**Important:**
- `PREVIOUS_VERSION_URL` always points to `main/output/data.ttl` — it
  automatically compares against the last published version on every push.
  You never need to update it after initial setup.
- `PUBLISHED_VOCABULARIES` — add the URL of each new vocabulary you create
  so the pipeline checks for collisions across all your vocabularies.

### Step 4 — Enable GitHub Pages

Go to your repository → **Settings** → **Pages** →
Source: `gh-pages` branch, `/ (root)` → **Save**.

### Step 5 — Push and watch

Push your vocabulary YAML — GitHub Actions runs automatically.
Check the **Actions** tab for progress.

---

## Vocabulary YAML — concept definition guide

```yaml
enums:
  MyVocabulary:
    description: Description of this concept scheme
    permissible_values:

      # Top-level concept (no is_a = no broader term)
      TopConcept:
        description: Formal definition        # → skos:definition
        aliases:
          - Preferred label                   # → skos:prefLabel (first alias)
          - Alternative name                  # → skos:altLabel
        comments:
          - Scope note — when to use this     # → skos:scopeNote

      # Child concept (is_a = has a broader concept)
      ChildConcept:
        is_a: TopConcept                      # → skos:broader
        description: Definition
        aliases:
          - Child preferred label
        meaning: https://external.org/Concept # → adopt external URI
```

### LinkML → SKOS mapping

| LinkML | SKOS | Notes |
| --- | --- | --- |
| Enum | `skos:ConceptScheme` | One scheme per enum |
| Permissible value | `skos:Concept` | One concept per value |
| `is_a:` | `skos:broader` | Hierarchical parent |
| `description:` | `skos:definition` | Formal definition |
| `aliases:` first | `skos:prefLabel` | Preferred label |
| `aliases:` rest | `skos:altLabel` | Alternative labels |
| `comments:` | `skos:scopeNote` | Usage guidance |
| `meaning:` | Adopts external URI | No new URI minted |
| `exact_mappings:` | `skos:exactMatch` | Maps to external, keeps own URI |
| `broad_mappings:` | `skos:broadMatch` | External is broader |
| `narrow_mappings:` | `skos:narrowMatch` | External is narrower |
| No `is_a:` | `skos:topConceptOf` | Root/top concept |

---

## URI validation — how it works

The `validate_uris.py` script runs automatically in the pipeline after
SKOS generation. It performs three checks:

**Check 1 — Internal uniqueness**
Verifies that no two concepts in the new TTL have the same URI.

**Check 2 — Cross-vocabulary collision**
Fetches all other published vocabularies listed in `PUBLISHED_VOCABULARIES`
and checks that no concept URI in the new vocabulary already exists in
another vocabulary. This prevents accidental URI reuse across vocabularies
sharing the same namespace.

**Check 3 — Accidental deletion**
Fetches the currently published version of this vocabulary from
`PREVIOUS_VERSION_URL` (always the `main` branch — automatically the
last published version) and checks that no existing concept URI has
been removed. Removal must always be done via deprecation
(`owl:deprecated + dcterms:isReplacedBy`), never by deleting the
concept from the YAML.

If any check fails the pipeline stops and no files are published.

---

## Versioning

Use semantic versioning (MAJOR.MINOR.PATCH):

| Version type | When to use | Example |
| --- | --- | --- |
| MAJOR (X.0.0) | Breaking changes — deprecated concepts, major restructuring | 1.0.0 → 2.0.0 |
| MINOR (1.X.0) | New concepts added — backwards compatible | 1.0.0 → 1.1.0 |
| PATCH (1.0.X) | Corrections — typos, definition improvements | 1.0.0 → 1.0.1 |

Update `version` and `last_updated_on` in the vocabulary YAML on every
release. Document changes in `CHANGELOG.md`.

**Never delete a concept URI** — use `owl:deprecated` instead.

---

## Running locally

```bash
# Install dependencies
pip install linkml rdflib skosify mkdocs mkdocs-material

# Validate
PYTHONUTF8=1 linkml-lint vocabulary/my-vocabulary.yaml

# Generate SKOS
PYTHONUTF8=1 python3 scripts/generate_skos.py \
  --input vocabulary/my-vocabulary.yaml \
  --verbose

# Skosify
python3 scripts/skosify_vocab.py \
  --input output/my-vocabulary-raw.ttl \
  --verbose

# Validate URIs
python3 scripts/validate_uris.py \
  --input output/my-vocabulary.ttl \
  --verbose

# Generate documentation
PYTHONUTF8=1 python3 scripts/generate_vocab_pages.py \
  --input vocabulary/my-vocabulary.yaml \
  --output docs/ \
  --verbose

# Preview locally
mkdocs serve

# Deploy to GitHub Pages
mkdocs gh-deploy
```

---

## Publishing your vocabulary

Once the pipeline runs successfully:

1. **Set up w3id.org redirects** — submit a PR to
   https://github.com/perma-id/w3id.org with your `.htaccess` rules
2. **Deposit on Zenodo** — upload `output/my-vocabulary.ttl` for a DOI
3. **Register in vocabulary registries:**
   - LOV: https://lov.linkeddata.es
   - BARTOC: https://bartoc.org
   - AgroPortal: https://agroportal.lirmm.fr
   - EcoPortal: https://ecoportal.lifewatch.eu

---

## Contributing new terms

To propose a new term, open a GitHub Issue using the
**Term Request** template. The editorial board will review
and respond.

---

## Reusability

This template is designed to be reusable by:
- **Any GitHub account** — personal, organisation or enterprise
- **Any user** — no credentials or account names hardcoded
- **Any SKOS vocabulary** — generic scripts work on any
  LinkML vocabulary YAML following this template structure

The only values to customise per repository are in:
- `vocabulary/my-vocabulary.yaml` — all `[USER DEFINED]` fields
- `mkdocs.yml` — `site_name`, `site_url`, `site_description`
- `scripts/validate_uris.py` — `PUBLISHED_VOCABULARIES` and
  `PREVIOUS_VERSION_URL` (username and repo name only — set once,
  never touch again)

---

## Tools used

| Tool | Purpose | License |
| --- | --- | --- |
| [LinkML](https://linkml.io) | Schema language and validators | Apache 2.0 |
| [Skosify](https://github.com/NatLibFi/Skosify) | SKOS validation and repair | MIT |
| [rdflib](https://rdflib.readthedocs.io) | RDF processing | BSD |
| [MkDocs](https://www.mkdocs.org) | Documentation generator | BSD |
| [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) | Documentation theme | MIT |

---

## License

Template code: MIT License.
Vocabulary content: license specified in vocabulary YAML header.
