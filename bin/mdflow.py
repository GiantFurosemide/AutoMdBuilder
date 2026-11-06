#!/usr/bin/env python3
"""Task implementations for AutoMdBuilder. Python stdlib; no shell execution.

Each command writes a NEW task-local directory. Original case inputs and previous
Nextflow task outputs are never edited. See docs/nextflow/README.zh-CN.md.
"""
import argparse
import base64
import collections
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

LOG = logging.getLogger('mdflow')
SAFE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')
PROTEIN = set(('ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL '
               'HID HIE HIP CYX CYM ASH GLH LYN').split())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    with Path(path).open() as handle:
        return json.load(handle)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def local_file(root, relative):
    require(isinstance(relative, str) and relative, 'Expected a nonempty relative file path')
    root = Path(root).resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root), f'Input path escapes case directory: {relative}')
    require(path.is_file() and path.stat().st_size > 0, f'Missing/empty input: {relative}')
    return path


def new_output(out, source=None):
    out = Path(out)
    require(not out.exists(), f'Refusing to overwrite output directory: {out}')
    if source:
        shutil.copytree(source, out)
    else:
        out.mkdir(parents=True)
    return out.resolve()


def execute(argv, cwd, name, stdin='', timeout=None):
    cwd = Path(cwd)
    LOG.info('%s: %s', cwd.name, shlex.join([str(x) for x in argv]))
    with (cwd / 'commands.jsonl').open('a') as handle:
        handle.write(json.dumps({'argv': [str(x) for x in argv], 'log': name + '.command.log'}) + '\n')
    env = dict(os.environ, GMX_MAXBACKUP='-1')
    with (cwd / (name + '.command.log')).open('w') as log:
        result = subprocess.run([str(x) for x in argv], cwd=cwd, input=stdin, text=True,
                                stdout=log, stderr=subprocess.STDOUT, timeout=timeout, env=env)
    if result.returncode:
        tail = (cwd / (name + '.command.log')).read_text(errors='replace')[-5000:]
        LOG.error('%s failed (exit %s):\n%s', name, result.returncode, tail)
        raise subprocess.CalledProcessError(result.returncode, argv)
    return (cwd / (name + '.command.log')).read_text(errors='replace')


def gmx_version(gmx, out):
    text = execute([gmx, '--version'], out, 'gromacs-version', timeout=60)
    match = re.search(r'GROMACS version:\s*(\S+)', text)
    require(match and re.match(r'^2024(?:\.\d+)?(?:$|[-_])', match.group(1)),
            'GROMACS 2024.x is required; inspect gromacs-version.command.log')
    return match.group(1)


def pdb_atoms(path):
    atoms = []
    models = 0
    for line in Path(path).read_text().splitlines():
        if line.startswith('MODEL'):
            models += 1
        if line[:6].strip() not in ('ATOM', 'HETATM'):
            continue
        require(len(line) >= 54, f'Malformed PDB record: {line}')
        require(line[16] == ' ', f'Unresolved alternate conformation: {line[:27]}')
        xyz = [float(line[a:b]) for a, b in ((30, 38), (38, 46), (46, 54))]
        require(all(math.isfinite(v) for v in xyz), 'Nonfinite PDB coordinates')
        atoms.append({'line': line, 'name': line[12:16].strip(), 'resname': line[17:20].strip(),
                      'reskey': (line[21], line[22:26], line[26]), 'xyz': xyz})
    require(models <= 1, 'Multiple PDB MODELs: supply one explicit model')
    require(atoms, f'No atoms in {path}')
    return atoms


def validate_settings(settings):
    require(settings['forcefield'] in ('amber99sb-ildn', 'amber99sb', 'amber03'),
            'v0.1 supports built-in Amber protein force fields: amber99sb-ildn, amber99sb, amber03')
    require(settings['water'] == 'tip3p', 'v0.1 validates TIP3P only')
    for key in ('padding_nm', 'temperature_k', 'nvt_ps', 'npt_ps', 'dt_ps', 'em_tolerance'):
        settings[key] = float(settings[key])
        require(math.isfinite(settings[key]) and settings[key] > 0, f'{key} must be finite and positive')
    settings['salt_molar'] = float(settings['salt_molar'])
    require(math.isfinite(settings['salt_molar']) and settings['salt_molar'] >= 0, 'salt_molar must be >= 0')
    require(0 < settings['dt_ps'] <= 0.002, 'dt_ps must be <= 0.002 (no HMR support)')
    require(float(settings['em_steps']).is_integer() and int(settings['em_steps']) > 0,
            'em_steps must be a positive integer')
    settings['em_steps'] = int(settings['em_steps'])
    for stage in ('nvt', 'npt'):
        steps = settings[stage + '_ps'] / settings['dt_ps']
        require(abs(steps - round(steps)) < 1e-6, f'{stage}_ps must be divisible by dt_ps')
        settings[stage + '_steps'] = int(round(steps))


def validate(args):
    root = Path(args.source).resolve()
    spec = read_json(root / 'case.json')
    require(isinstance(spec, dict), 'case.json must be a JSON object')
    require(spec.get('schema_version') == 1, 'case.json requires schema_version: 1')
    require(set(spec) <= {'schema_version', 'structure', 'ligands', 'box_nm'}, 'Unknown case.json field')
    settings = json.loads(base64.b64decode(args.settings))
    validate_settings(settings)
    structure = local_file(root, spec.get('structure'))
    ligands = spec.get('ligands', [])
    require(isinstance(ligands, list), 'ligands must be an array')
    spec['ligands'] = ligands
    ids, resnames = set(), set()
    hashes = {'case.json': sha256(root / 'case.json'), spec['structure']: sha256(structure)}
    for lig in ligands:
        require(set(lig) <= {'id', 'resname', 'count', 'mode', 'itp', 'mol2', 'charge', 'atom_type', 'charge_method'},
                f'Unknown ligand fields: {lig}')
        require(isinstance(lig.get('id'), str) and SAFE.fullmatch(lig['id']) and lig['id'] not in ids,
                'Ligand ids must be unique safe identifiers')
        require(re.fullmatch(r'[A-Z0-9]{1,3}', lig.get('resname', '')) and
                lig['resname'] not in resnames and lig['resname'] not in PROTEIN,
                'Each ligand type needs a unique 1-3 character PDB resname, different from protein')
        require(type(lig.get('count')) is int and lig['count'] > 0, 'Ligand count must be a positive integer')
        require(lig.get('mode') in ('itp', 'acpype'), 'Ligand mode must be itp or acpype')
        path_key = 'itp' if lig['mode'] == 'itp' else 'mol2'
        source = local_file(root, lig.get(path_key))
        hashes[lig[path_key]] = sha256(source)
        if lig['mode'] == 'acpype':
            require(type(lig.get('charge')) is int, 'ACPYPE requires an explicitly specified integer net charge')
            lig.setdefault('atom_type', 'gaff2')
            lig.setdefault('charge_method', 'bcc')
            require(lig['atom_type'] in ('gaff', 'gaff2'), 'Unsupported ACPYPE atom_type')
            require(lig['charge_method'] in ('bcc', 'user'), 'Supported charge_method: bcc or user')
        ids.add(lig['id'])
        resnames.add(lig['resname'])
    atoms = pdb_atoms(structure)
    protein = [a for a in atoms if a['resname'] not in resnames]
    require(protein, 'A protein is required')
    unknown = sorted({a['resname'] for a in protein if a['resname'] not in PROTEIN})
    require(not unknown, f'Unlisted non-protein residues {unknown}: remove explicitly or declare as ligands; no silent deletion')
    # Repeated atom names within a residue indicate duplicate structures/unresolved conformers.
    for key, group in group_residues(protein).items():
        names = [a['name'] for a in group]
        require(len(names) == len(set(names)), f'Duplicate protein atom names in residue {key}')
    for lig in ligands:
        selected = [a for a in atoms if a['resname'] == lig['resname']]
        require(len(group_residues(selected)) == lig['count'], f"{lig['id']}: residue count != declared count")
    if 'box_nm' in spec:
        box = spec['box_nm']
        require(isinstance(box, list) and len(box) == 3 and all(isinstance(x, (int, float)) and math.isfinite(x) and x > 0 for x in box),
                'box_nm must contain three positive lengths in nm')
        for axis in range(3):
            span = (max(a['xyz'][axis] for a in atoms) - min(a['xyz'][axis] for a in atoms)) / 10
            require(box[axis] >= span + 2 * settings['padding_nm'], 'Explicit box is too small for configured solvent padding')
    out = new_output(args.out)
    shutil.copyfile(structure, out / 'input.pdb')
    # Keep TER records between chains; do not pass ligand records or CONECT records to pdb2gmx.
    protein_lines = []
    for line in structure.read_text().splitlines():
        if line.startswith('TER'):
            protein_lines.append('TER')
        elif line[:6].strip() in ('ATOM', 'HETATM') and line[17:20].strip() not in resnames:
            protein_lines.append('ATOM  ' + line[6:])
    (out / 'protein_input.pdb').write_text('\n'.join(protein_lines) + '\nEND\n')
    for lig in ligands:
        key = 'itp' if lig['mode'] == 'itp' else 'mol2'
        target = f"{lig['id']}.input.{key}"
        shutil.copyfile(local_file(root, lig[key]), out / target)
        lig['input_file'] = target
    write_json(out / 'state.json', {'schema_version': 1, 'case_id': args.case_id,
               'spec': spec, 'settings': settings, 'input_sha256': hashes, 'simulation_executed': False})


def group_residues(atoms):
    result = collections.OrderedDict()
    for atom in atoms:
        result.setdefault(atom['reskey'], []).append(atom)
    return result


def parse_itp(path):
    """Accept a standalone ACPYPE molecule, rejecting implicit include dependencies."""
    global_lines, molecule_lines, atomtypes = [], [], {}
    atoms, molecules = [], []
    section = None
    allowed = {'atomtypes', 'moleculetype', 'atoms', 'bonds', 'pairs', 'angles', 'dihedrals', 'constraints', 'exclusions'}
    for raw in Path(path).read_text().splitlines():
        clean = raw.split(';', 1)[0].strip()
        require(not clean.startswith('#'), f'{path}: external includes/macros are not supported; supply standalone ACPYPE ITP')
        match = re.fullmatch(r'\[\s*(\w+)\s*\]', clean)
        if match:
            section = match.group(1)
            require(section in allowed, f'{path}: unsupported topology section {section}')
        elif clean:
            fields = clean.split()
            if section == 'atomtypes':
                require(len(fields) >= 6, 'Malformed atomtypes row')
                require(fields[0] not in atomtypes or atomtypes[fields[0]] == fields, 'Conflicting atomtypes within ligand')
                atomtypes[fields[0]] = fields
            elif section == 'moleculetype':
                require(len(fields) == 2 and SAFE.fullmatch(fields[0]), 'Invalid moleculetype')
                molecules.append(fields[0])
            elif section == 'atoms':
                require(len(fields) >= 8, f'{path}: explicit masses required in [ atoms ]')
                require(all(math.isfinite(float(fields[i])) for i in (6, 7)), 'Nonfinite charge/mass')
                require(float(fields[7]) > 0, 'Massless/virtual-site atoms are outside v0.1 scope')
                atoms.append(fields)
        if section != 'atomtypes':
            molecule_lines.append(raw)
        else:
            global_lines.append(raw)
    require(len(molecules) == 1 and atoms, f'{path}: expected exactly one molecule and nonempty atoms')
    require([int(a[0]) for a in atoms] == list(range(1, len(atoms) + 1)), 'ITP atom numbering must be contiguous from 1')
    require(len({a[4] for a in atoms}) == len(atoms), 'Ligand atom names must be unique for unambiguous mapping')
    require(len({a[2] for a in atoms}) == 1, 'Each ligand molecule must be one residue')
    charge = sum(float(a[6]) for a in atoms)
    require(abs(charge - round(charge)) < 0.02, f'Noninteger ligand charge: {charge}')
    return molecules[0], atoms, atomtypes, molecule_lines


def canonical_atomtype(fields):
    def normalize(token):
        try:
            return float(token)
        except ValueError:
            return token
    return tuple(normalize(t) for t in fields)


def prepare_ligands(args):
    out = new_output(args.out)
    source = Path(args.source).resolve()
    state = read_json(source / 'state.json')
    all_atoms = pdb_atoms(source / 'input.pdb')
    all_types, molecule_names, coord_lines, prepared = {}, set(), [], []
    for lig in state['spec']['ligands']:
        ligand_dir = out / lig['id']
        ligand_dir.mkdir()
        input_file = source / lig['input_file']
        if lig['mode'] == 'acpype':
            require(shutil.which('acpype'), 'ACPYPE executable missing: use the ACPYPE container/profile')
            version = execute(['acpype', '-v'], ligand_dir, 'acpype-version', timeout=60)
            require('2023.10.27' in version, 'ACPYPE 2023.10.27 is required by this environment contract')
            shutil.copyfile(input_file, ligand_dir / 'input.mol2')
            execute(['acpype', '-i', 'input.mol2', '-b', lig['id'], '-n', lig['charge'],
                     '-a', lig['atom_type'], '-c', lig['charge_method'], '-o', 'gmx'], ligand_dir, 'acpype')
            itp = ligand_dir / (lig['id'] + '.acpype') / (lig['id'] + '_GMX.itp')
            require(itp.is_file(), f'ACPYPE did not produce {itp.name}')
        else:
            itp = input_file
        provenance = out / 'ligand_provenance' / lig['id']
        provenance.mkdir(parents=True)
        shutil.copyfile(input_file, provenance / input_file.name)
        shutil.copyfile(itp, provenance / 'parameterized.itp')
        for log in ligand_dir.glob('*.log'):
            shutil.copyfile(log, provenance / log.name)
        for journal in ligand_dir.glob('*.jsonl'):
            shutil.copyfile(journal, provenance / journal.name)
        name, atoms, types, body = parse_itp(itp)
        require(name not in molecule_names, f'Duplicate ligand moleculetype {name}')
        molecule_names.add(name)
        require(all(a[3] == lig['resname'] for a in atoms), f"{lig['id']}: ITP residue name differs from declared PDB resname")
        if lig['mode'] == 'acpype':
            require(abs(sum(float(a[6]) for a in atoms) - lig['charge']) < 0.02, 'ACPYPE net charge mismatch')
        for key, fields in types.items():
            require(key not in all_types or canonical_atomtype(fields) == canonical_atomtype(all_types[key]),
                    f'Conflicting definitions of ligand atom type {key}; resolve parameters upstream')
            all_types[key] = fields
        residues = group_residues([a for a in all_atoms if a['resname'] == lig['resname']])
        for reskey, group in residues.items():
            by_name = {a['name']: a for a in group}
            names = [a[4] for a in atoms]
            require(len(by_name) == len(group) and set(by_name) == set(names),
                    f"{lig['id']} residue {reskey}: PDB/ITP atoms differ (including H); "
                    f"missing={sorted(set(names)-set(by_name))}, extra={sorted(set(by_name)-set(names))}")
            coord_lines.extend('ATOM  ' + by_name[n]['line'][6:] for n in names)
        restraint = ['[ position_restraints ]', '; ai funct fcx fcy fcz']
        restraint.extend(f'{a[0]} 1 1000 1000 1000' for a in atoms if float(a[7]) > 2.1)
        (out / (lig['id'] + '_posre.itp')).write_text('\n'.join(restraint) + '\n')
        body += ['#ifdef POSRES', f'#include "{lig["id"]}_posre.itp"', '#endif']
        (out / (lig['id'] + '.itp')).write_text('\n'.join(body) + '\n')
        prepared.append({'id': lig['id'], 'moleculetype': name, 'count': lig['count'],
                         'atoms_per_molecule': len(atoms), 'itp_sha256': sha256(itp), 'mode': lig['mode']})
    (out / 'ligand_atomtypes.itp').write_text('[ atomtypes ]\n' + '\n'.join(' '.join(all_types[k]) for k in sorted(all_types)) + '\n')
    (out / 'ligand_coordinates.pdb').write_text('\n'.join(coord_lines) + '\n')
    write_json(out / 'ligands.json', prepared)


def protein_topology(args):
    out = new_output(args.out, args.source)
    state = read_json(out / 'state.json')
    state['gromacs_version'] = gmx_version(args.gmx, out)
    s = state['settings']
    execute([args.gmx, 'pdb2gmx', '-f', 'protein_input.pdb', '-o', 'protein.pdb', '-p', 'topol.top',
             '-i', 'posre.itp', '-ff', s['forcefield'], '-water', s['water'], '-ignh'], out, 'pdb2gmx', timeout=600)
    require((out / 'topol.top').is_file() and (out / 'protein.pdb').is_file(), 'pdb2gmx output missing')
    write_json(out / 'state.json', state)


def assemble(args):
    out = new_output(args.out, args.source)
    ligdir = Path(args.ligands)
    prepared = read_json(ligdir / 'ligands.json')
    for path in ligdir.glob('*.itp'):
        require(not (out / path.name).exists(), f'Ligand/protein topology filename collision: {path.name}')
        shutil.copyfile(path, out / path.name)
    if (ligdir / 'ligand_provenance').exists():
        shutil.copytree(ligdir / 'ligand_provenance', out / 'ligand_provenance')
    top = (out / 'topol.top').read_text()
    if prepared:
        marker = re.search(r'^\s*#include\s+"[^"]+/forcefield\.itp".*$', top, re.M)
        require(marker, 'Cannot locate forcefield include in protein topology')
        top = top[:marker.end()] + '\n#include "ligand_atomtypes.itp"\n' + top[marker.end():]
        marker = re.search(r'^\s*\[\s*system\s*\]', top, re.M)
        require(marker, 'Missing [ system ] section')
        includes = '\n'.join(f'#include "{lig["id"]}.itp"' for lig in prepared) + '\n\n'
        top = top[:marker.start()] + '\n' + includes + top[marker.start():]
        require(re.search(r'\[\s*molecules\s*\]', top), 'Missing [ molecules ] section')
        top = top.rstrip() + '\n' + '\n'.join(f'{lig["moleculetype"]} {lig["count"]}' for lig in prepared) + '\n'
    (out / 'topol.top').write_text(top)
    protein = [a['line'] for a in pdb_atoms(out / 'protein.pdb')]
    ligands = (ligdir / 'ligand_coordinates.pdb').read_text().splitlines()
    (out / 'complex.pdb').write_text('\n'.join(protein + ligands) + '\nEND\n')
    state = read_json(out / 'state.json')
    state['ligands'] = prepared
    write_json(out / 'state.json', state)


def solvate(args):
    out = new_output(args.out, args.source)
    gmx_version(args.gmx, out)
    state = read_json(out / 'state.json')
    box = state['spec'].get('box_nm')
    cmd = [args.gmx, 'editconf', '-f', 'complex.pdb', '-o', 'boxed.gro', '-bt', 'cubic', '-c']
    cmd += ['-box', *box] if box else ['-d', state['settings']['padding_nm']]
    execute(cmd, out, 'editconf')
    execute([args.gmx, 'solvate', '-cp', 'boxed.gro', '-cs', 'spc216.gro', '-o', 'solvated.gro', '-p', 'topol.top'], out, 'solvate')
    gro_count(out / 'solvated.gro')


def render_mdp(template, destination, settings, seed=1):
    values = dict(settings, seed=seed)
    text = Path(template).read_text()
    for key in re.findall(r'@([a-z_]+)@', text):
        require(key in values, f'Unknown MDP template placeholder {key}')
        text = text.replace('@' + key + '@', str(values[key]))
    Path(destination).write_text(text)


def ions(args):
    out = new_output(args.out, args.source)
    gmx_version(args.gmx, out)
    state = read_json(out / 'state.json')
    render_mdp(Path(args.mdps) / 'ions.mdp', out / 'ions.mdp', state['settings'])
    execute([args.gmx, 'grompp', '-f', 'ions.mdp', '-c', 'solvated.gro', '-p', 'topol.top', '-o', 'ions.tpr', '-maxwarn', 0], out, 'ions-grompp')
    execute([args.gmx, 'genion', '-s', 'ions.tpr', '-o', 'ionized.gro', '-p', 'topol.top',
             '-pname', 'NA', '-nname', 'CL', '-neutral', '-conc', state['settings']['salt_molar'], '-seed', 2024],
            out, 'genion', stdin='SOL\n')
    state['atom_count'] = gro_count(out / 'ionized.gro')
    write_json(out / 'state.json', state)


def gro_count(path):
    lines = Path(path).read_text().splitlines()
    require(len(lines) >= 3, f'Truncated GRO: {path}')
    n = int(lines[1].strip())
    require(n > 0 and len(lines) == n + 3, f'GRO atom count/line count mismatch: {path}')
    box = [float(x) for x in lines[-1].split()]
    require(len(box) in (3, 9) and all(math.isfinite(x) for x in box) and min(box[:3]) > 0,
            f'Invalid box in {path}')
    for line in lines[2:-1]:
        xyz = [float(line[a:b]) for a, b in ((20, 28), (28, 36), (36, 44))]
        require(all(math.isfinite(x) for x in xyz), f'Nonfinite coordinates in {path}')
    return n


def validate_run_log(path, stage, steps, tolerance):
    text = Path(path).read_text(errors='replace')
    require(not re.search(r'LINCS WARNING|SHAKE did not converge|Fatal error|\bnan\b', text, re.I),
            f'{stage}: numerical instability/error in {path}')
    if stage == 'em':
        match = re.search(r'converged to Fmax\s*<\s*([\d.eE+-]+)', text)
        require(match and float(match.group(1)) <= tolerance * 1.0001,
                'EM did not meet the requested force tolerance; inspect em.log, do not continue blindly')
    else:
        pairs = re.findall(r'Step\s+Time\s*\n\s*(\d+)\s+([\d.eE+-]+)', text)
        require(pairs and int(pairs[-1][0]) >= steps, f'{stage} stopped before requested step {steps}')
        require('Finished mdrun' in text, f'{stage} lacks normal completion marker')


def run_stage(args):
    out = new_output(args.out, args.source)
    state = read_json(out / 'state.json')
    state['gromacs_version'] = gmx_version(args.gmx, out)
    state.update(replica=args.replica, seed=args.seed)
    s, stage = state['settings'], args.stage
    render_mdp(Path(args.mdps) / (stage + '.mdp'), out / (stage + '.mdp'), s, args.seed)
    coord = {'em': 'ionized.gro', 'nvt': 'em.gro', 'npt': 'nvt.gro'}[stage]
    cmd = [args.gmx, 'grompp', '-f', stage + '.mdp', '-c', coord, '-p', 'topol.top',
           '-o', stage + '.tpr', '-po', stage + '.resolved.mdp', '-maxwarn', 0]
    if stage != 'em':
        cmd += ['-r', 'em.gro']
    if stage == 'npt':
        cmd += ['-t', 'nvt.cpt']
    execute(cmd, out, stage + '-grompp')
    cmd = [args.gmx, 'mdrun', '-deffnm', stage, '-ntmpi', 1, '-ntomp', args.cpus, '-pin', 'auto']
    if args.gpu and stage != 'em':
        # Let CUDA_VISIBLE_DEVICES / Slurm select the device. PME/update remain portable on CPU.
        cmd += ['-nb', 'gpu', '-pme', 'cpu', '-bonded', 'auto', '-update', 'cpu']
    else:
        cmd += ['-nb', 'cpu', '-pme', 'cpu', '-bonded', 'cpu', '-update', 'cpu']
    execute(cmd, out, stage + '-mdrun')
    count = gro_count(out / (stage + '.gro'))
    require(count == state['atom_count'], f'{stage}: unexpected atom-count change')
    validate_run_log(out / (stage + '.log'), stage, s.get(stage + '_steps', s['em_steps']), s['em_tolerance'])
    if stage != 'em':
        require((out / (stage + '.cpt')).stat().st_size > 0, 'Missing checkpoint')
        terms = 'Temperature\n' if stage == 'nvt' else 'Temperature\nPressure\nDensity\n'
        execute([args.gmx, 'energy', '-f', stage + '.edr', '-o', stage + '.qc.xvg'], out, stage + '-energy', stdin=terms + '\n')
    state['simulation_executed'] = True
    state.setdefault('completed_stages', []).append(stage)
    write_json(out / 'state.json', state)


def export_system(args):
    # Export into a fresh directory; flattened topology is self-contained and has POSRES disabled.
    source = Path(args.source).resolve()
    state = read_json(source / 'state.json')
    require(state.get('completed_stages') == ['em', 'nvt', 'npt'], 'Cannot export an incomplete system')
    out = new_output(args.out)
    staging = out / '_prepare'
    shutil.copytree(source, staging)
    gmx_version(args.gmx, staging)
    render_mdp(Path(args.mdps) / 'handoff.mdp', staging / 'handoff.mdp', state['settings'])
    execute([args.gmx, 'grompp', '-f', 'handoff.mdp', '-c', 'npt.gro', '-t', 'npt.cpt',
             '-p', 'topol.top', '-pp', 'system.top', '-o', 'handoff_check.tpr', '-maxwarn', 0], staging, 'handoff-grompp')
    top = (staging / 'system.top').read_text()
    require(not re.search(r'^\s*#\s*(include|if)', top, re.M), 'Export topology is not fully expanded')
    require('[ position_restraints ]' not in top, 'Unexpected active position restraints in exported topology')
    for old, new in [('npt.gro', 'equilibrated.gro'), ('npt.cpt', 'equilibrated.cpt'),
                     ('npt.tpr', 'equilibration.tpr'), ('system.top', 'system.top'), ('em.gro', 'restraint_reference.gro')]:
        shutil.copyfile(staging / old, out / new)
    provenance = out / 'provenance'
    provenance.mkdir()
    if (staging / 'ligand_provenance').exists():
        shutil.copytree(staging / 'ligand_provenance', provenance / 'ligands')
    for pattern in ('*.mdp', '*.log', '*.xvg', '*.jsonl', 'state.json'):
        for path in staging.glob(pattern):
            shutil.copyfile(path, provenance / path.name)
    # Retain original includes for re-equilibration / custom restraints; portable handoff uses system.top.
    topology = out / 'topology'
    topology.mkdir()
    for pattern in ('*.itp', 'topol.top'):
        for path in staging.glob(pattern):
            shutil.copyfile(path, topology / path.name)
    shutil.rmtree(staging)
    manifest = dict(state, artifact_schema='automdbuilder.system.v1', status='equilibrated',
                    production_executed=False, scientific_equilibration_verified=False,
                    files={'coordinates': 'equilibrated.gro', 'topology': 'system.top',
                           'checkpoint': 'equilibrated.cpt', 'equilibration_tpr': 'equilibration.tpr',
                           'restraint_reference': 'restraint_reference.gro'},
                    notes=['Numerical completion checks passed; scientific equilibration requires review.',
                           'Checkpoint comes from restrained NPT; choose a new protocol explicitly downstream.',
                           'system.top has POSRES disabled; equilibration.tpr retains the NPT protocol.'])
    manifest['sha256'] = {str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write_json(out / 'manifest.json', manifest)


def stub(args):
    out = new_output(args.out)
    state = read_json(Path(args.source) / 'state.json')
    state.update(simulation_executed=False, status='STUB_ONLY', replica=args.replica, seed=args.seed)
    write_json(out / 'state.json', state)
    if args.stage == 'export':
        write_json(out / 'manifest.json', dict(state, artifact_schema='automdbuilder.system.v1',
                                              production_executed=False, files={}))
        (out / 'STUB_ONLY.txt').write_text('Workflow wiring test. No molecular dynamics executed. No usable system.\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'ligands', 'protein', 'assemble', 'solvate', 'ions', 'run', 'export', 'stub'):
        p = sub.add_parser(name)
        p.add_argument('--source', required=True, type=Path)
        p.add_argument('--out', required=True, type=Path)
        p.add_argument('--gmx', default='gmx', help='One executable name/path, no shell arguments')
        p.add_argument('--mdps', type=Path)
        p.add_argument('--stage', choices=('em', 'nvt', 'npt', 'ligands', 'protein', 'assembled', 'solvated', 'ionized', 'export'))
        p.add_argument('--replica', type=int, default=1)
        p.add_argument('--seed', type=int, default=1)
        p.add_argument('--cpus', type=int, default=1)
        p.add_argument('--gpu', action='store_true')
        p.add_argument('--case-id')
        p.add_argument('--settings')
        p.add_argument('--ligands', type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    commands = {'validate': validate, 'ligands': prepare_ligands, 'protein': protein_topology,
                'assemble': assemble, 'solvate': solvate, 'ions': ions, 'run': run_stage,
                'export': export_system, 'stub': stub}
    try:
        require(args.source.is_dir(), f'Input directory missing: {args.source}')
        require(args.cpus > 0 and args.replica > 0 and 0 < args.seed < 2147483647, 'Invalid cpus/replica/seed')
        commands[args.command](args)
    except subprocess.CalledProcessError as exc:
        code = exc.returncode if exc.returncode >= 0 else 128 - exc.returncode
        return code if code in (137, 140, 143) else 1
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        LOG.error('%s: %s', args.command, exc)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
