#!/usr/bin/env python3
"""Check Nextflow's generated Slurm directives using a fake scheduler and stubs."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nextflow', default='nextflow')
    parser.add_argument('--outdir', required=True, type=Path)
    args = parser.parse_args()
    out = args.outdir.resolve()
    if out.exists():
        parser.error('Choose a fresh output directory')
    out.mkdir(parents=True)
    (out / 'samples.csv').write_text('case_id,case_dir,replicas\nprotein,' + str(ROOT / 'tests/fixtures/cases/protein') + ',1\n')
    (out / 'test.config').write_text("executor.pollInterval = '100 ms'\nexecutor.queueStatInterval = '100 ms'\nexecutor.submitRateLimit = '100 sec'\n")
    env = dict(os.environ, AUTOMDBUILDER_TEST_SCHEDULER='1', NXF_VER='24.10.4',
               PATH=str(ROOT / 'tests/fakes/slurm') + os.pathsep + os.environ['PATH'])
    cmd = [args.nextflow, 'run', str(ROOT / 'main.nf'), '-profile', 'slurm', '-stub-run',
           '--samples', str(out / 'samples.csv'), '--outdir', str(out / 'results'),
           '-work-dir', str(out / 'work'), '-c', str(out / 'test.config'), '-ansi-log', 'false']
    with (out / 'scheduler.log').open('w') as handle:
        result = subprocess.run(cmd, cwd=out, env=env, stdout=handle, stderr=subprocess.STDOUT, timeout=180)
    assert result.returncode == 0, (out / 'scheduler.log').read_text()
    scripts = list((out / 'work').glob('*/*/.command.run'))
    assert len(scripts) == 10, len(scripts)
    gpu_jobs = []
    for path in scripts:
        text = path.read_text()
        assert '#SBATCH -p gpu' in text or '#SBATCH --partition gpu' in text, text[:2000]
        if '--gres=gpu:a40:1' in text:
            gpu_jobs.append(text)
    assert len(gpu_jobs) == 2, len(gpu_jobs)
    assert all('EQUILIBRATE_NVT' in x or 'EQUILIBRATE_NPT' in x for x in gpu_jobs)
    assert all('#SBATCH --cpus-per-task 8' in x or '#SBATCH -c 8' in x for x in gpu_jobs), gpu_jobs
    assert (out / 'results/systems/protein/replica_1/system/STUB_ONLY.txt').is_file()
    print('PASS: 10 Slurm job scripts; partition gpu; exactly NVT and NPT request one A40.')


if __name__ == '__main__':
    main()
