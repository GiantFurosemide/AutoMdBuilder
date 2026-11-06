# Validation record — 2026-11-06

Environment: macOS arm64, Python 3.9.6, temporary Java 21 and Nextflow 24.10.4.
The workstation has neither cluster access nor a usable CUDA GPU/container engine.
The original repository base is `6a307cba357e2615e7bb8918b3c8869ec74827e0`.

## Tests

| Check | Evidence / expected result |
|---|---|
| Python boundary/unit tests | 28 tests: paths, schema fields, ligand copies, atom mapping, shared/conflicting atomtypes, explicit charge, timestep, EM/MD gates, version gate, executor selection |
| Nextflow stub execution | Three cases, five replicas; 38 tasks; all outputs explicitly STUB_ONLY, no GRO files |
| External-command contract | Real Nextflow processes call opt-in fake GROMACS/ACPYPE; all stages, export files, checksums and ligand provenance are checked |
| Resume | All 38 successful tasks are CACHED on an unchanged rerun |
| Serial local execution | Trace start/complete intervals do not overlap across process types |
| Resource profiles | Test tasks use 1 CPU/1 GB; dynamic profile values are not lost during configuration merging |
| Failure isolation | Invalid PDB and malformed case JSON fail independently; a valid case completes; overall exit is nonzero |
| Retry | A simulated exit 137 produces one retry, followed by successful completion |
| Public launcher | Stub launch, resume, case summary files, refusal to overwrite a nonempty output directory |
| Hardware absence | Auto mode exits before real submission when neither Slurm nor NVIDIA GPU is available |
| Slurm submission contract | Fake scheduler executes stubs through Nextflow's actual Slurm executor; 10 job scripts use partition gpu; only NVT/NPT request `--gres=gpu:a40:1`, each with 8 CPUs |
| Static checks | Python AST parse and Git whitespace check |

Reproduce without a GPU:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tests/run_workflow_tests.py --nextflow /path/to/nextflow --outdir tests/output/new-run
python3 tests/test_slurm_submission.py --nextflow /path/to/nextflow --outdir tests/output/new-slurm-run
```

The scripts refuse existing output directories. Test outputs are git-ignored.
GitHub Actions repeats these software checks; it does not claim GPU/MD validation.

## What has NOT been validated

- Building the Linux GROMACS container, loading CUDA, or running on a real A40.
- Real Slurm accounting, partition policy, GRES spelling, wall-time termination,
  Apptainer bind configuration, driver compatibility or filesystem performance.
- Actual ACPYPE/AmberTools parameterization, real GROMACS preprocessing and dynamics.
- Scientific validity of a ligand force field, protein protonation, initial poses,
  numerical behavior on a real molecular system, or adequacy of equilibration.

The container source archive SHA256 and upstream linux/amd64 image digests were
retrieved and pinned, but this is **not** a successful container-build test.

Before scaling up, perform the small real-system acceptance run described in
README.zh-CN.md §8 on the target cluster. The software test fixtures are synthetic
and must never be used as chemical test cases or supplied as scientific results.
