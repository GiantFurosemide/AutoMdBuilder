#!/usr/bin/env python3
"""Select Slurm or a serial local NVIDIA-GPU executor, then launch Nextflow.

Run on the cluster login node for Slurm. This is not an SSH submission service.
Use --stub-run on a computer with neither Slurm nor GPU.
"""
import argparse
import csv
import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger('launch')


def probe(argv):
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def has_slurm(partition):
    return all(shutil.which(x) for x in ('sbatch', 'squeue', 'scancel', 'sinfo')) and bool(
        probe(['sinfo', '-h', '-p', partition, '-o', '%P']))


def has_gpu():
    if os.environ.get('CUDA_VISIBLE_DEVICES') in ('', '-1', 'NoDevFiles'):
        return False
    return bool(shutil.which('nvidia-smi') and probe(['nvidia-smi', '--query-gpu=uuid', '--format=csv,noheader']))


def select_executor(requested, partition, stub=False):
    if stub:
        return 'test'
    if requested in ('auto', 'slurm') and has_slurm(partition):
        return 'slurm'
    if requested == 'slurm':
        raise ValueError(f'Slurm is not reachable / partition {partition!r} is not visible')
    if requested in ('auto', 'local') and has_gpu():
        return 'local_gpu'
    raise ValueError('No reachable Slurm and no visible NVIDIA GPU. Use --stub-run for wiring tests; no real MD was launched.')


def hash_inputs(samples):
    """Fingerprint contents for safe output-directory reuse, including case dependencies."""
    h = hashlib.sha256(samples.read_bytes())
    with samples.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError('Empty samples CSV')
    for row in rows:
        case = (samples.parent / row['case_dir'].strip()).resolve()
        if not case.is_dir():
            raise ValueError(f'Missing case directory: {case}')
        for path in sorted(case.rglob('*')):
            if path.is_file():
                h.update(str(path.relative_to(case)).encode())
                with path.open('rb') as f:
                    for block in iter(lambda: f.read(1024 * 1024), b''):
                        h.update(block)
    return h.hexdigest()


def summarize(samples, outdir, stamp):
    """Report every requested replica, including cases with no downstream output."""
    with samples.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    with (outdir / ('cases-' + stamp + '.csv')).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['case_id', 'replica', 'status', 'manifest'])
        writer.writeheader()
        for row in rows:
            for replica in range(1, int(row.get('replicas') or 1) + 1):
                manifest = outdir / 'systems' / row['case_id'] / f'replica_{replica}' / 'system/manifest.json'
                status = json.loads(manifest.read_text()).get('status', 'INVALID') if manifest.is_file() else 'NOT_COMPLETED'
                writer.writerow(dict(case_id=row['case_id'], replica=replica, status=status,
                                     manifest=str(manifest.relative_to(outdir)) if manifest.is_file() else ''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', required=True, type=Path)
    parser.add_argument('--outdir', required=True, type=Path, help='Fresh output directory; --resume required to reuse')
    parser.add_argument('--work-dir', type=Path, default=Path('work'))
    parser.add_argument('--executor', choices=('auto', 'slurm', 'local'), default='auto')
    parser.add_argument('--runtime', choices=('apptainer', 'docker', 'native'), default='apptainer')
    parser.add_argument('--gmx-image', help='Absolute path to GROMACS SIF, or Docker image digest')
    parser.add_argument('--acpype-image', help='Absolute path to ACPYPE SIF, or Docker image digest')
    parser.add_argument('--partition', default='gpu')
    parser.add_argument('--gres', default='gpu:a40:1')
    parser.add_argument('--params-file', type=Path, help='Nextflow JSON/YAML protocol parameters')
    parser.add_argument('--config', type=Path, help='Site config, e.g. Slurm account/resource limits')
    parser.add_argument('--nextflow', default='nextflow')
    parser.add_argument('--resume', action='store_true', help='Resume from this output directory’s Nextflow cache')
    parser.add_argument('--stub-run', action='store_true', help='No GROMACS/ACPYPE/GPU; output marked STUB_ONLY')
    parser.add_argument('--plan', action='store_true', help='Print command without launching or creating output')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    try:
        samples, outdir = args.samples.resolve(), args.outdir.resolve()
        if not samples.is_file():
            raise ValueError(f'Missing samples file: {samples}')
        selected = select_executor(args.executor, args.partition, args.stub_run)
        runtime = 'native' if args.stub_run else args.runtime
        if runtime != 'native' and not shutil.which(runtime):
            raise ValueError(f'{runtime} is not installed; choose native only with a verified environment')
        if runtime != 'native' and (not args.gmx_image or not args.acpype_image):
            raise ValueError('Both --gmx-image and --acpype-image are required for container execution')
        if runtime == 'apptainer':
            for path in (args.gmx_image, args.acpype_image):
                if not Path(path).is_absolute() or not Path(path).is_file():
                    raise ValueError('Use existing absolute SIF paths, visible on every Slurm node')
        nextflow = shutil.which(args.nextflow)
        if not nextflow:
            raise ValueError('Nextflow not found; see environments/README.md (requires Java 17-21)')
        nextflow = str(Path(nextflow).resolve())
        for option in (args.params_file, args.config):
            if option and not option.is_file():
                raise ValueError(f'Missing configuration file: {option}')
        profile = 'standard' if runtime == 'native' else runtime
        cmd = [nextflow, 'run', str(ROOT / 'main.nf'), '-profile', f'{selected},{profile}',
               '--samples', str(samples), '--outdir', str(outdir), '-work-dir', str(args.work_dir.resolve()),
               '--partition', args.partition, '--gpu_gres', args.gres]
        if args.params_file:
            cmd += ['-params-file', str(args.params_file.resolve())]
        if args.config:
            cmd += ['-c', str(args.config.resolve())]
        if runtime != 'native':
            cmd += ['--gmx_container', args.gmx_image, '--acpype_container', args.acpype_image]
        if args.stub_run:
            cmd += ['-stub-run']
        if args.resume:
            cmd += ['-resume']
        fingerprint = {'inputs': hash_inputs(samples), 'stub': args.stub_run,
                       'parameters': hashlib.sha256(args.params_file.read_bytes()).hexdigest() if args.params_file else None,
                       'config': hashlib.sha256(args.config.read_bytes()).hexdigest() if args.config else None,
                       'gmx_image': args.gmx_image, 'acpype_image': args.acpype_image}
        source_hash = hashlib.sha256()
        for folder in ('bin', 'modules', 'assets', 'conf'):
            for path in sorted((ROOT / folder).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts:
                    source_hash.update(path.read_bytes())
        source_hash.update((ROOT / 'main.nf').read_bytes())
        source_hash.update((ROOT / 'nextflow.config').read_bytes())
        fingerprint['pipeline_source'] = source_hash.hexdigest()
        if runtime == 'apptainer':
            for key, filename in [('gmx_sif_sha256', args.gmx_image), ('acpype_sif_sha256', args.acpype_image)]:
                digest = hashlib.sha256()
                with open(filename, 'rb') as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b''):
                        digest.update(block)
                fingerprint[key] = digest.hexdigest()
        marker = outdir / 'run_inputs.json'
        if outdir.exists() and any(outdir.iterdir()):
            if not args.resume or not marker.is_file():
                raise ValueError('Output directory is nonempty; use a new directory or --resume for the same inputs')
            if json.loads(marker.read_text()) != fingerprint:
                raise ValueError('Inputs/config/images changed: use a NEW --outdir')
        elif args.resume:
            raise ValueError('--resume requires an existing output directory from this launcher')
        LOG.info('Selected %s + %s; local execution is serial across all stages', selected, runtime)
        LOG.info('Command: %s', shlex.join(cmd))
        if args.plan:
            return 0
        outdir.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(fingerprint, indent=2) + '\n')
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (outdir / ('launch-' + stamp + '.json')).write_text(json.dumps({'argv': cmd, 'executor': selected,
             'runtime': runtime, 'utc': stamp}, indent=2) + '\n')
        # Keep .nextflow cache with this run; resume works even when caller changes directory.
        env = dict(os.environ, NXF_VER='24.10.4')
        result = subprocess.run(cmd, cwd=outdir, env=env)
        summarize(samples, outdir, stamp)
        write_status = {'exit_code': result.returncode, 'success': result.returncode == 0,
                        'stub_only': args.stub_run, 'trace_directory': 'pipeline_info'}
        (outdir / ('status-' + stamp + '.json')).write_text(json.dumps(write_status, indent=2) + '\n')
        return result.returncode
    except (ValueError, OSError, KeyError) as exc:
        LOG.error('%s', exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())
