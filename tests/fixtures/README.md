These are **synthetic software-contract fixtures**, not chemically meaningful
structures. Use them only with `-stub-run`, unit tests, or the explicit test
executables in `tests/fakes/`. Never use them for real parameterization or MD.

The fixtures exercise pure protein, preparameterized ligand copies, and ACPYPE
dispatch. A real cluster acceptance test must use an independently validated
protein/ligand case, not these fixtures.
