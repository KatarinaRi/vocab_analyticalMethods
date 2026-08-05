# Analytical Methods Vocabulary

A controlled vocabulary of analytical methods used for chemical analysis
in environmental monitoring samples. Developed within the
[PARC project](https://www.eu-parc.eu) (Partnership for the Assessment
of Risks from Chemicals).

---

## Overview

| | |
| --- | --- |
| **Persistent URI** | https://w3id.org/chemical-exposome/vocabulary/analytical-methods |
| **Version** | 2.1.0 |
| **Status** | 🟡 Draft |
| **License** | [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| **Creator** | [Katarína Řiháčková](https://orcid.org/0000-0003-0222-801x) (Masaryk University) |
| **Created** | 2026-01-01 |
| **Last updated** | 2026-07-30 |
| **Funding** | Horizon Europe, PARC project, grant No 101057014 |

---

## Documentation and downloads

| Resource | Link |
| --- | --- |
| **Browse online** | [GitHub Pages documentation](https://katarinari.github.io/vocab_analyticalMethods/) |
| **Concept hierarchy** | [Hierarchy view](https://katarinari.github.io/vocab_analyticalMethods/hierarchy) |
| **Download SKOS TTL** | [output/data.ttl](output/data.ttl) |
| **Source YAML** | [vocabulary/data.yaml](vocabulary/data.yaml) |
| **Zenodo DOI** | [PLACEHOLDER — add after Zenodo deposit] |

---

## Scope

This vocabulary provides a standardised set of terms for describing
analytical methods used in environmental monitoring. It covers:

- **Spectroscopy** — Atomic Absorption (AAS), Atomic Emission (AES),
  Atomic Fluorescence (AFS), ICP, X-ray Fluorescence (XRF), NMR, UV-Vis
- **Mass Spectrometry** — ICP-MS, GC-MS, LC-MS, IC-MS, SFC-MS with
  full coverage of ionisation modes (EI, NCI, CI, APPI, APCI) and
  resolution variants (MS, MS/MS, HRMS, HRMS/MS)
- **Chromatography** — Gas (GC), Liquid (HPLC, UPLC), Ion (IC)
  with detection variants (DAD, FLD, UV, ECD, FID etc.)
- **Mixed methods** — Chromatography coupled to ICP-MS (LC, GC, IC),
  LC-IR, LC-NMR
- **Other** — Spectrophotometry, Colorimetry, Electrophoresis

The vocabulary currently contains **[PLACEHOLDER — number] concepts**
organised in a hierarchy with [PLACEHOLDER — number] top-level categories.

---

## Alignment

This vocabulary is aligned with:

- **PARC deliverable D9.4-1** — [PLACEHOLDER — add reference]
- **[PLACEHOLDER — add other relevant standards or vocabularies]**

---

## How to use this vocabulary

### In data annotation

Reference concept URIs in your data:

```
https://w3id.org/chemical-exposome/term/GFAAS
https://w3id.org/chemical-exposome/term/GCMS
https://w3id.org/chemical-exposome/term/ICPMS
```

### In a LinkML schema

Reference concepts via `meaning:` in your schema enums:

```yaml
enums:
  AnalyticalMethod:
    permissible_values:
      GFAAS:
        meaning: https://w3id.org/chemical-exposome/term/GFAAS
      GCMS:
        meaning: https://w3id.org/chemical-exposome/term/GCMS
```

### In RDF/SPARQL

```sparql
PREFIX cenvo: <https://w3id.org/chemical-exposome/term/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

# Find all GC-MS methods
SELECT ?method ?label WHERE {
    ?method skos:broader+ cenvo:GCMS ;
            skos:prefLabel ?label .
}
```

---

## Provenance

### Development

[PLACEHOLDER — describe how the vocabulary was developed,
e.g. based on which sources, expert review process, etc.]

### Contributors

| Name | ORCID | Role | Institution |
| --- | --- | --- | --- |
| Katarína Řiháčková | [0000-0003-0222-801x](https://orcid.org/0000-0003-0222-801x) | Conceptualization, Data curation | Masaryk University |
| [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |

### Funding

This vocabulary was developed within the PARC project (Partnership for
the Assessment of Risks from Chemicals), funded by the European Union
under Horizon Europe grant agreement No 101057014.

### Citation

If you use this vocabulary in your work, please cite:

> [PLACEHOLDER — add citation after Zenodo deposit]
> Řiháčková, K. et al. (2026). Analytical Methods Vocabulary (v2.1.0).
> Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX

---

## Versioning and changelog

See [CHANGELOG.md](CHANGELOG.md) for a full history of changes.

This vocabulary follows [semantic versioning](https://semver.org/):
- **MAJOR** — breaking changes (deprecated concepts, restructuring)
- **MINOR** — new concepts added
- **PATCH** — corrections and improvements

**Concept URIs are permanent** — once minted, a URI never changes.
Retired concepts are deprecated with `owl:deprecated`, not deleted.

---

## Contributing

To propose a new term or report an error, open a GitHub Issue
using the [Term Request](.github/ISSUE_TEMPLATE/term-request.md) template.

Please provide:
- Proposed term name and definition
- Why the term is needed
- Broader concept (parent in hierarchy)
- References or sources
- Any equivalent terms in external vocabularies

All proposals are reviewed by the editorial board before publication.

---

## Technical notes

This vocabulary is published using the
[vocab-template](https://github.com/KatarinaRi/vocab-template)
pipeline. The source is a LinkML YAML file which is automatically
converted to SKOS Turtle, validated, and published to GitHub Pages
on every push.

| File | Description |
| --- | --- |
| `vocabulary/data.yaml` | Source vocabulary in LinkML YAML format |
| `output/data-raw.ttl` | Raw SKOS Turtle (before Skosify validation) |
| `output/data.ttl` | Final SKOS Turtle — use this for submission to registries |

---

## License

This vocabulary is released under the
[Creative Commons Attribution 4.0 International License (CC-BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

You are free to share and adapt this vocabulary for any purpose,
provided you give appropriate credit.
