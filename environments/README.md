# Runtime environments

The pipeline targets **Linux x86_64 + NVIDIA CUDA** for real computation. The
macOS workspace is used for Python and Nextflow contract tests only. No GPU or
Slurm execution, Linux container build, or container chemistry test has been
performed in this workspace.

## Three layers

1. Controller: Python >=3.9, Java 21, Nextflow **24.10.4**, and Apptainer (recommended)
   or Docker. Run the controller on a cluster login node with Slurm commands and
   shared-filesystem access. Keep it alive (site-approved persistent session/job).
2. GROMACS tasks: GROMACS **2024.4**, CUDA **12.4.1**, Ubuntu 22.04, FFTW,
   Python 3. The source SHA256 and amd64 CUDA base digest are pinned in
   `versions.json`, `gromacs.def`, and `Dockerfile.gromacs`.
3. Ligand parameterization: official ACPYPE **2023.10.27** image, pinned by
   amd64 manifest digest. Its bundled AmberTools dependencies are captured by
   that immutable image. Native ACPYPE installs must match and be tested separately.

Host NVIDIA driver compatibility with CUDA 12.4 must be checked on the actual
cluster. The host driver is NOT supplied by the image. Slurm controls GPU visibility;
Apptainer uses `--nv`. Do not hard-code device IDs in the scripts.

## Install the controller

Use your site's Java 21 module or managed JDK installation. The Nextflow launcher
is version pinned; its first execution downloads the matching runtime JAR:

```bash
mkdir -p "$PWD/runner"
curl -fL --retry 3 \
  https://github.com/nextflow-io/nextflow/releases/download/v24.10.4/nextflow \
  -o "$PWD/runner/nextflow"
chmod +x "$PWD/runner/nextflow"
# Verify the pinned launcher (sha256sum on Linux; shasum -a 256 on macOS):
echo "f69085f647f6c0a98c48ba5e905b10a55e04d32cfadfab2db18ae98601416c26  $PWD/runner/nextflow" | sha256sum -c -
export NXF_VER=24.10.4
export NXF_HOME="$PWD/runner/nxf-home"
export PATH="$PWD/runner:$PATH"
nextflow -version
```

For offline transfer, prepare the entire `runner/` directory online first, then
transfer it alongside a Linux JDK 21 installation appropriate to the target host.
Set `NXF_HOME` to the transferred `nxf-home` and `NXF_OFFLINE=true`. Do not transfer
the macOS JDK to Linux. The public launcher sets NXF_VER=24.10.4 itself.

## Build Apptainer images (preferred)

On a Linux x86_64 build host with network access, disk space, and appropriate
Apptainer build permissions (GPU is not needed to compile):

```bash
python3 bin/build_containers.py --outdir /absolute/path/containers --fakeroot
```

Omit `--fakeroot` if building as an authorized root user or using a site-supported
build environment. If the site disallows builds, build on another Linux machine
and transfer the completed SIFs. The script rejects nonempty output directories,
captures build logs, tests version commands and writes `images.json` containing
SHA256 checksums. A failed partial build remains for diagnosis; use a new output
directory for a new attempt.

Transfer these files together:

```text
gromacs-2024.4-cuda12.4.sif
acpype-2023.10.27.sif
images.json
```

Verify checksums on the target host before running. `launch.py` also fingerprints
SIF contents when recording a run/resume. No registry login or internet access is
needed on compute nodes once images are present.

The GROMACS recipe uses thread-MPI and portable SSE2 CPU instructions. Its CUDA
targets are specified in the recipe; A40 is SM86. For a different local GPU, use
a build containing that GPU's architecture and validate it before real execution.

## Docker alternative

```bash
docker build --platform linux/amd64 -f environments/Dockerfile.gromacs \
  -t automdbuilder-gromacs:2024.4 .
docker pull acpype/acpype@sha256:83e77ddd3def09beb1a4226aa5d95f1934afe440d448b0156e9c28ad59afdca0

python3 bin/launch.py --executor local --runtime docker \
  --samples /data/samples.csv --outdir /data/output/batch001 --work-dir /data/work/batch001 \
  --gmx-image automdbuilder-gromacs:2024.4 \
  --acpype-image acpype/acpype@sha256:83e77ddd3def09beb1a4226aa5d95f1934afe440d448b0156e9c28ad59afdca0
```

This requires the NVIDIA container runtime on a Linux GPU host. Docker Desktop
on macOS does not provide this CUDA path. For reproducible multi-host Docker use,
publish the built image to your authorized registry and use its immutable digest.
No image is pre-published by this repository.

## Native runtime

`--runtime native` is available for site-managed installations. Ensure `python3`,
`gmx` and (when needed) `acpype` are visible in noninteractive batch jobs. Every
GROMACS compute stage checks the **2024.x** version. Native mode is an explicit
escape hatch, not a claim that an arbitrary conda environment is reproducible.

## Reproducibility limits

The base images, ACPYPE image, and GROMACS source are pinned. Ubuntu packages
installed at build time follow the configured apt repositories; two builds made
at different dates are **not guaranteed bit-identical**. OS package versions are
recorded at `/opt/automdbuilder/os-packages.txt`. Reuse and verify the same SIF
artifact for an exact environment across runs, rather than rebuilding per job.

Sources: [GROMACS 2024.4 installation](https://manual.gromacs.org/documentation/2024.4/install-guide/index.html),
[ACPYPE release](https://github.com/alanwilter/acpype/releases/tag/2023.10.27),
[Nextflow installation](https://www.nextflow.io/docs/stable/install.html).
