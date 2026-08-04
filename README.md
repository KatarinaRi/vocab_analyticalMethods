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
4. **Generates HTML documentation** with index, hierarchy and concept pages
5. **Deploys documentation** to GitHub Pages
6. **Commits generated TTL** files back to the repository

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
│   ├── generate_skos.py
│   ├── generate_vocab_pages.py
│   └── skosify_vocab.py
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

### Step 3 — Enable GitHub Pages

Go to your repository → **Settings** → **Pages** →
Source: `gh-pages` branch, `/ (root)` → **Save**.

### Step 4 — Push and watch

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

The only account-specific values are in `vocabulary/my-vocabulary.yaml`
(`created_by`, `repo_url`) and `mkdocs.yml` (`site_url`) —
update these for your own vocabulary.

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
