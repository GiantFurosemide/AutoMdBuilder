#!/usr/bin/env python3
"""Run real Nextflow against stubs/fake CLI tools; never runs molecular dynamics."""
import argparse
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--nextflow', default='nextflow')
    p.add_argument('--outdir', required=True, type=Path)
    args = p.parse_args()
    out = args.outdir.resolve()
    if out.exists():
        p.error('Choose a new output directory')
    out.mkdir(parents=True)
    env = dict(os.environ, AUTOMDBUILDER_TEST_FAKE='1', NXF_VER='24.10.4',
               PATH=str(ROOT / 'tests/fakes') + os.pathsep + os.environ['PATH'])
    samples = ROOT / 'tests/fixtures/samples.csv'

    def run(name, sample_file=samples, extra=(), success=True, extra_env=None, result_name=None):
        result = out / (result_name or name)
        cmd = [args.nextflow, 'run', str(ROOT / 'main.nf'), '-profile', 'test', '--samples', str(sample_file),
               '--outdir', str(result), '-work-dir', str(out / 'work'), '-ansi-log', 'false', *extra]
        print('Running', name, flush=True)
        with (out / (name + '.log')).open('w') as log:
            proc = subprocess.run(cmd, cwd=out, env=dict(env, **(extra_env or {})), stdout=log,
                                  stderr=subprocess.STDOUT, timeout=300)
        if (proc.returncode == 0) != success:
            raise AssertionError(f'{name}: exit {proc.returncode}; see {out / (name + ".log")}')
        return result

    stub = run('stub', extra=['-stub-run'])
    manifests = list(stub.glob('systems/*/replica_*/system/manifest.json'))
    assert len(manifests) == 5
    assert all(json.loads(x.read_text())['status'] == 'STUB_ONLY' for x in manifests)
    assert not list(stub.rglob('*.gro'))

    real_contract = run('contract')
    manifests = list(real_contract.glob('systems/*/replica_*/system/manifest.json'))
    assert len(manifests) == 5
    records = [json.loads(x.read_text()) for x in manifests]
    assert all(x['completed_stages'] == ['em', 'nvt', 'npt'] and x['production_executed'] is False for x in records)
    assert all('FAKE' in x['gromacs_version'] for x in records)
    assert len({x['seed'] for x in records}) == 5
    for path, record in zip(manifests, records):
        for filename, digest in record['sha256'].items():
            assert hashlib.sha256((path.parent / filename).read_bytes()).hexdigest() == digest
    assert list(real_contract.glob('systems/acpype/*/system/provenance/ligands/LIG/acpype.command.log'))
    trace = sorted((real_contract / 'pipeline_info').glob('*.trace.tsv'))[-1]
    with trace.open() as handle:
        execution = list(csv.DictReader(handle, delimiter='\t'))
    assert all(row['cpus'] == '1' and row['memory'] == '1 GB' for row in execution), 'Test profile resources were overwritten'
    intervals = sorted((datetime.datetime.fromisoformat(row['start']), datetime.datetime.fromisoformat(row['complete'])) for row in execution)
    assert all(previous[1] <= following[0] for previous, following in zip(intervals, intervals[1:])), 'Local processes overlapped'
    run('resume', extra=['-resume'], result_name='contract')
    trace = sorted((real_contract / 'pipeline_info').glob('*.trace.tsv'))[-1]
    with trace.open() as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    assert len(rows) == 38 and all(row['status'] == 'CACHED' for row in rows), rows

    # A bad case must not stop unrelated valid cases; pipeline exit must still be nonzero.
    bad = out / 'bad_case'
    shutil.copytree(ROOT / 'tests/fixtures/cases/protein', bad)
    (bad / 'complex.pdb').write_text('invalid PDB\n')
    bad_json = out / 'bad_json'
    bad_json.mkdir()
    (bad_json / 'case.json').write_text('{broken json')
    failure_samples = out / 'failure.csv'
    failure_samples.write_text(f'case_id,case_dir,replicas\nbad,{bad},1\nbad_json,{bad_json},1\ngood,{ROOT / "tests/fixtures/cases/protein"},1\n')
    failure = run('failure', sample_file=failure_samples, success=False)
    assert list(failure.glob('systems/good/replica_1/system/manifest.json'))
    assert not list(failure.glob('systems/bad/**/manifest.json'))
    assert not list(failure.glob('systems/bad_json/**/manifest.json'))

    # Simulated 137 failure triggers the bounded Nextflow retry policy.
    retry = run('retry', extra_env={'AUTOMDBUILDER_FAIL_ONCE': str(out / 'fail-once.marker')})
    assert len(list(retry.glob('systems/*/replica_*/system/manifest.json'))) == 5
    assert 'Execution is retried (1)' in (out / 'retry.log').read_text()

    # Exercise the public launcher, output-protection, reporting and cross-cwd resume.
    launcher_out = out / 'launcher'
    command = [sys.executable, str(ROOT / 'bin/launch.py'), '--samples', str(samples), '--outdir', str(launcher_out),
               '--work-dir', str(out / 'launcher-work'), '--nextflow', args.nextflow, '--stub-run']
    for suffix in ([], ['--resume']):
        proc = subprocess.run(command + suffix, cwd=out, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
        assert proc.returncode == 0, proc.stdout
    assert len(list(launcher_out.glob('cases-*.csv'))) == 2
    protected = subprocess.run(command, cwd=out, env=env, capture_output=True, text=True)
    assert protected.returncode != 0 and 'nonempty' in protected.stderr
    print('PASS: stub, 38-task command contract, cached resume, failure isolation, retry, launcher protection/reporting.')


if __name__ == '__main__':
    main()
