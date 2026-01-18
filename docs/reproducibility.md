# Reproducing the calculations and paper

Run the following commands from the repository root with Python 3.10 or later.

## Main verification

```sh
python -m pip install -r requirements.txt
python scripts/verify.py
python scripts/check_manuscript.py
```

The first command prints the finite-check record. The manuscript check additionally verifies the eighteen equation numbers, eleven proposition and proof pairs, four appendices, thirteen cited references, summary table, and exact agreement between `scripts/verify.py` and the program printed in Appendix D. It writes `results/verification.json` and `results/manuscript-check.json`.

Exact checks use integer matrices and Python rational arithmetic. The count-law residuals and transition comparisons use floating-point arithmetic with explicit tolerances. The packing integral check directly integrates the sampling weights over ordered simplices rather than substituting the formula it checks.

## Supplemental calculations

```sh
python scripts/audits/quantum_gain.py
python scripts/audits/response_structure.py
python scripts/audits/biased_stabilization.py
python scripts/audits/past_persistence.py
```

| Calculation | Relation to the manuscript |
|---|---|
| Quantum gain | Sections 4-5: creation algebra with an internal factor, adjoint gain, count probabilities, and exact closure-time means |
| Response structure | Sections 4-5: finite stabilizer constraints, degenerate states, number preservation, continued internal activity, and competing timing laws |
| Biased stabilization | Section 6: exact parameter bounds, independent sampled integration, and the summable-exploration counterexample |
| Past persistence | Section 8: transition composition, survival bounds, matched histories, and loss of occupation-order records |

The sampled calculations use the fixed random seed recorded in each script and result file. Small floating-point differences across platforms are possible within the declared tolerances. All output paths are relative to this repository. The scripts write their records to `results/audits/`.

These supplemental checks do not expand the claims of the manuscript. In particular, they do not estimate a probability that source-free genesis is true.

## PDF build

```sh
python -m pip install -r requirements-pdf.txt
python scripts/build_pdf.py
```

The build first verifies the executable appendix, then produces `output/pdf/boundary-hypothesis.pdf`. It embeds copies of the verification program and results while retaining the complete visible listing. It also writes `results/pdf-check.json`.

Fonts come from the installed Matplotlib distribution, so the build does not require a particular operating system's fonts. Intermediate files are placed in the ignored `tmp/` directory. The paper's declared date is January 18, 2026.

The numerical and PDF structure checks do not replace visual review. Inspect a fresh render after changing the manuscript, typography, or build dependencies.
