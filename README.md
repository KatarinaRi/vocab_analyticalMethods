# Vocabulary Publishing Template

A GitHub template repository for publishing SKOS controlled vocabularies
defined in LinkML YAML format. Push a vocabulary YAML — get a validated,
SKOSified Turtle file and human-readable documentation automatically.

---

## What this template does

Every time you push a vocabulary YAML file to this repository, GitHub Actions
automatically:

1. **Validates** the YAML using `linkml-lint`
2. **Generates SKOS** Turtle from the LinkML YAML (Python script)
3. **Repairs and validates** the SKOS using Skosify
4. **Generates HTML documentation** using `gen-doc` + MkDocs
5. **Deploys documentation** to GitHub Pages
6. **Commits generated TTL** files back to the repository

---

## Repository structure

```
.
├── .github/
│   └── workflows/
│       └── publish-vocabulary.yml   ← GitHub Actions pipeline
├── vocabulary/
│   └── my-vocabulary.yaml           ← your LinkML vocabulary YAML (edit this)
├── scripts/
│   ├── generate_skos.py             ← SKOS generation script
│   ├── skosify_vocab.py             ← Skosify wrapper
│   └── fix_tables.py                ← MkDocs table fix
├── output/                          ← generated TTL files (auto-generated)
│   ├── my-vocabulary-raw.ttl        ← raw SKOS (before Skosify)
│   └── my-vocabulary.ttl            ← final SKOS (after Skosify) ← USE THIS
├── docs/                            ← generated HTML documentation (auto-generated)
├── mkdocs.yml                       ← MkDocs configuration
├── CHANGELOG.md                     ← version history
└── README.md                        ← this file
```

---

## Quick start

### 1. Use this template

Click **Use this template** on GitHub to create your own repository.

### 2. Edit the vocabulary YAML

Open `vocabulary/my-vocabulary.yaml` and:
- Fill in the header fields (id, title, description, license, creator etc.)
- Define your vocabulary concepts in the `enums` section
- Use `is_a:` for hierarchy, `aliases:` for alternative labels,
  `description:` for definitions, `meaning:` for external URI adoption

### 3. Configure MkDocs

Edit `mkdocs.yml`:
- Set `site_name` to your vocabulary name
- Set `site_url` to your GitHub Pages URL

### 4. Enable GitHub Pages

Go to your repository → Settings → Pages → Source: `gh-pages` branch, `/ (root)`

### 5. Push and watch

Push your vocabulary YAML — GitHub Actions will run automatically.
Check the Actions tab for progress.

---

## LinkML vocabulary YAML structure

```yaml
# Required header fields
id: https://w3id.org/your-namespace/vocabulary/my-vocabulary
name: my-vocabulary
title: My Controlled Vocabulary
description: >-
  What this vocabulary covers and who it is for.
version: "1.0.0"
license: https://creativecommons.org/licenses/by/4.0/
created_by: https://orcid.org/0000-0000-0000-0000
created_on: "2026-01-01T00:00:00Z"
last_updated_on: "2026-01-01T00:00:00Z"

prefixes:
  linkml: https://w3id.org/linkml/
  # add your namespace prefixes here

default_prefix: myv   # prefix for minted URIs
imports:
  - linkml:types

enums:
  MyVocabulary:
    description: Description of this concept scheme
    permissible_values:

      TopConcept:
        description: Definition of the top concept
        aliases:
          - Alternative name

      ChildConcept:
        is_a: TopConcept          # → skos:broader
        description: Definition
        aliases:
          - Alternative name
        comments:
          - Scope note — when to use this vs other concepts
        meaning: https://external-vocab.org/ChildConcept  # adopt external URI
```

### LinkML → SKOS mapping

| LinkML property | SKOS property | Notes |
|----------------|---------------|-------|
| Enum | `skos:ConceptScheme` | One scheme per enum |
| Permissible value | `skos:Concept` | One concept per value |
| `is_a:` | `skos:broader` | Hierarchy |
| `description:` | `skos:definition` | Formal definition |
| `aliases:` | `skos:altLabel` | Alternative labels |
| `comments:` | `skos:scopeNote` | Usage guidance |
| `meaning:` | `skos:exactMatch` + identity | Adopts external URI |
| `exact_mappings:` | `skos:exactMatch` | Maps to external, keeps own URI |
| `broad_mappings:` | `skos:broadMatch` | External is broader |
| No `is_a:` | `skos:topConceptOf` | Root concept |

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
PYTHONUTF8=1 gen-doc vocabulary/my-vocabulary.yaml -d ./docs -f markdown
python3 scripts/fix_tables.py --dir docs

# Preview documentation locally
mkdocs serve

# Deploy to GitHub Pages
mkdocs gh-deploy
```

---

## Output files

After the pipeline runs:

| File | Description | Use for |
|------|-------------|---------|
| `output/my-vocabulary-raw.ttl` | Raw SKOS (before Skosify) | Debugging |
| `output/my-vocabulary.ttl` | Final SKOS (after Skosify) | Submission to registries |
| `docs/` | HTML documentation | GitHub Pages |

### Submit to vocabulary registries

Once your vocabulary is published, you can register it in:

- **LOV** (Linked Open Vocabularies) — https://lov.linkeddata.es
- **BARTOC** — https://bartoc.org
- **AgroPortal** — https://agroportal.lirmm.fr
- **EcoPortal** — https://ecoportal.lifewatch.eu
- **vocabs.repo.cz** — https://vocabs.repo.cz (Czech Republic)

Submit the `output/my-vocabulary.ttl` file.

---

## w3id.org persistent URIs

To make your vocabulary URIs persistent via w3id.org:

1. Fork https://github.com/perma-id/w3id.org
2. Create `.htaccess` redirect rules for your namespace
3. Submit a pull request

```apache
RewriteEngine on

# Vocabulary TTL for RDF clients
RewriteCond %{HTTP_ACCEPT} text/turtle
RewriteRule ^vocabulary/my-vocabulary$
  https://raw.githubusercontent.com/your-username/your-repo/main/output/my-vocabulary.ttl
  [R=303,L]

# HTML for browsers
RewriteRule ^vocabulary/my-vocabulary$
  https://your-username.github.io/your-repo/
  [R=303,L]
```

---

## Tools used

| Tool | Purpose | License |
|------|---------|---------|
| [LinkML](https://linkml.io) | Schema language and generators | Apache 2.0 |
| [Skosify](https://github.com/NatLibFi/Skosify) | SKOS validation and repair | MIT |
| [rdflib](https://rdflib.readthedocs.io) | RDF processing | BSD |
| [MkDocs](https://www.mkdocs.org) | Documentation site generator | BSD |
| [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) | Documentation theme | MIT |

---

## Contributing vocabulary terms

To propose a new term:

1. Open a GitHub Issue using the **Term Request** template
2. Provide: term name, definition, broader concept, references
3. The editorial board will review and respond
4. Approved terms are added to the YAML and the pipeline runs automatically

---

## License

The vocabulary publishing template code is released under the MIT License.
Vocabulary content is released under the license specified in the vocabulary YAML header.
