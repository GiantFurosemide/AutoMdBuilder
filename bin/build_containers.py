#!/usr/bin/env python3
"""Build a portable GROMACS SIF and pull the pinned ACPYPE SIF on Linux amd64."""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', required=True, type=Path)
    parser.add_argument('--fakeroot', action='store_true', help='Use only if supported by this site')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    try:
        if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'AMD64'):
            raise ValueError('Build on Linux x86_64, then transfer SIFs to the cluster. GPU is not needed to compile.')
        if not shutil.which('apptainer'):
            raise ValueError('Apptainer is required')
        out = args.outdir.resolve()
        if out.exists() and any(out.iterdir()):
            raise ValueError('Output directory must be empty; existing images are never overwritten')
        out.mkdir(parents=True, exist_ok=True)
        versions = json.loads((ROOT / 'environments/versions.json').read_text())
        images = {'gromacs': out / 'gromacs-2024.4-cuda12.4.sif', 'acpype': out / 'acpype-2023.10.27.sif'}
        commands = [
            ['apptainer', 'build'] + (['--fakeroot'] if args.fakeroot else []) + [str(images['gromacs']), str(ROOT / 'environments/gromacs.def')],
            ['apptainer', 'pull', str(images['acpype']), 'docker://' + versions['acpype_image']],
        ]
        for i, cmd in enumerate(commands):
            logging.info('Running %s; log: build-%s.log', cmd, i)
            with (out / f'build-{i}.log').open('w') as handle:
                subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, check=True)
        for name, executable in [('gromacs', 'gmx'), ('acpype', 'acpype')]:
            subprocess.run(['apptainer', 'exec', str(images[name]), executable, '--version' if name == 'gromacs' else '-v'], check=True)
        manifest = {'versions': versions, 'images': {}}
        for name, path in images.items():
            h = hashlib.sha256()
            with path.open('rb') as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                    h.update(chunk)
            manifest['images'][name] = {'file': path.name, 'sha256': h.hexdigest()}
        (out / 'images.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(out / 'images.json')
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        logging.error('%s', exc)
        return 1


if __name__ == '__main__':
    sys.exit(main())
