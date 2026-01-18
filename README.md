# A boundary hypothesis for genesis and structural stabilization

**Christopher Speciale | January 18, 2026 | Version 1.0.1**

Could physical actuality originate without antecedent actuality, with the properties of the resulting structure establishing constraints on further development?

This manuscript develops that hypothesis through explicit assumptions and mathematical examples of structural admission, finite occupancy, stabilization, and continuing activity. It also examines limits on reconstructing origins from later observations and the additional work needed for a cosmological application.

The proposed origin argument is explicit in Section 2.1: universal non-realization would require a constraint, while absolute absence has no actual properties capable of imposing one. The paper separates that argument's philosophical premise from its later mathematical results.

**[Read the complete paper (PDF)](output/pdf/boundary-hypothesis.pdf)** · [Manuscript source](manuscript/paper.md) · [Research status](docs/research-status.md) · [Reproduce the calculations](docs/reproducibility.md)

**[Read the layman's guide (PDF)](output/pdf/boundary-hypothesis-laymans-guide.pdf)** for a short, illustrated summary in plain language.

The origin claim remains conjectural. The mathematical results establish conditional compatibility of the modeled behaviors; they do not prove that absence must produce actuality or that the Big Bang occurred through this mechanism.

## Contents

| Location | Content |
|---|---|
| `manuscript/paper.md` | Complete manuscript, proofs, references, and visible verification program |
| `output/pdf/boundary-hypothesis.pdf` | Designed, self-contained paper with verification attachments |
| `output/pdf/boundary-hypothesis-laymans-guide.pdf` | Three-page plain-language summary for casual readers |
| `docs/laymans-guide.md` | Editable source of the companion summary |
| `scripts/verify.py` | Exact program reproduced in Appendix D |
| `scripts/check_manuscript.py` | Checks numbering, references, and agreement with the executable appendix |
| `scripts/audits/` | Extended calculations for quantum gain, response structure, biased packing, and past persistence |
| `scripts/build_pdf.py` | Portable PDF build with fonts supplied by Matplotlib |
| `results/` | Verification records and supplemental audit results |
| `docs/` | Scope and reproducibility documentation |

## Quick verification

Requires Python 3.10 or later.

```sh
python -m pip install -r requirements.txt
python scripts/check_manuscript.py
```

The main verification uses integer and rational arithmetic where specified, together with finite floating-point checks. It includes 70 independent exact packing integrals and 20,001 matched-history thresholds. The written proofs establish the general mathematical statements.

## Build the paper

```sh
python -m pip install -r requirements-pdf.txt
python scripts/build_pdf.py
python scripts/build_guide_pdf.py
```

The PDF contains the full argument, all eighteen numbered equations, eleven proved mathematical propositions, four appendices, and thirteen references. No separate attachment is needed to read it.

## Citation

Speciale, Christopher. *A boundary hypothesis for genesis and structural stabilization*. Research manuscript, version 1.0.1, January 18, 2026. See [CITATION.cff](CITATION.cff) for machine-readable citation metadata.
