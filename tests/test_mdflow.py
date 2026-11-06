"""Boundary tests for inputs, topology mapping, scientific gates and fallback."""
import argparse
import base64
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'bin' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


md = load('mdflow')
launch = load('launch')
SETTINGS = dict(forcefield='amber99sb-ildn', water='tip3p', padding_nm=1.2, salt_molar=0.15,
                temperature_k=303.15, nvt_ps=500.0, npt_ps=500.0, dt_ps=0.002,
                em_steps=50000, em_tolerance=1000.0)


class InputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.case = self.root / 'case'
        shutil.copytree(ROOT / 'tests/fixtures/cases/ligand', self.case)

    def validate(self, out='validated'):
        args = argparse.Namespace(source=self.case, out=self.root / out, case_id='test',
                                  settings=base64.b64encode(json.dumps(SETTINGS).encode()).decode())
        md.validate(args)
        return args.out

    def change_spec(self, **kwargs):
        spec = md.read_json(self.case / 'case.json')
        spec.update(kwargs)
        md.write_json(self.case / 'case.json', spec)

    def test_valid_input_does_not_modify_original(self):
        before = {p.name: md.sha256(p) for p in self.case.iterdir()}
        out = self.validate()
        self.assertEqual(before, {p.name: md.sha256(p) for p in self.case.iterdir()})
        self.assertEqual(md.read_json(out / 'state.json')['settings']['nvt_steps'], 250000)

    def test_count_mismatch(self):
        spec = md.read_json(self.case / 'case.json')
        spec['ligands'][0]['count'] = 5
        self.change_spec(ligands=spec['ligands'])
        with self.assertRaisesRegex(ValueError, 'count'):
            self.validate()

    def test_unknown_residue_is_not_silently_removed(self):
        p = self.case / 'complex.pdb'
        p.write_text(p.read_text().replace('ALA', 'HOH'))
        with self.assertRaisesRegex(ValueError, 'Unlisted'):
            self.validate()

    def test_altloc_rejected(self):
        p = self.case / 'complex.pdb'
        text = p.read_text()
        p.write_text(text[:16] + 'A' + text[17:])
        with self.assertRaisesRegex(ValueError, 'alternate'):
            self.validate()

    def test_path_escape_rejected(self):
        shutil.copyfile(self.case / 'complex.pdb', self.root / 'outside.pdb')
        self.change_spec(structure='../outside.pdb')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.validate()

    def test_small_box_rejected(self):
        self.change_spec(box_nm=[1, 1, 1])
        with self.assertRaisesRegex(ValueError, 'too small'):
            self.validate()

    def test_existing_output_not_overwritten(self):
        self.validate()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            self.validate()

    def test_ligand_atom_reordering(self):
        p = self.case / 'complex.pdb'
        lines = p.read_text().splitlines()
        lines[6], lines[7] = lines[7], lines[6]
        p.write_text('\n'.join(lines) + '\n')
        validated = self.validate()
        md.prepare_ligands(argparse.Namespace(source=validated, out=self.root / 'params'))
        atoms = md.pdb_atoms(self.root / 'params/ligand_coordinates.pdb')
        self.assertEqual([a['name'] for a in atoms], ['C1', 'H1', 'C1', 'H1'])
        self.assertIn('1000', (self.root / 'params/LIG_posre.itp').read_text())

    def test_missing_hydrogen_fails_mapping(self):
        p = self.case / 'complex.pdb'
        p.write_text('\n'.join(line for line in p.read_text().splitlines() if ' H1 ' not in line) + '\n')
        validated = self.validate()
        with self.assertRaisesRegex(ValueError, 'atoms differ'):
            md.prepare_ligands(argparse.Namespace(source=validated, out=self.root / 'params'))

    def test_non_standalone_itp_rejected(self):
        p = self.case / 'LIG.itp'
        p.write_text(p.read_text() + '#include "missing.itp"\n')
        with self.assertRaisesRegex(ValueError, 'includes/macros'):
            md.parse_itp(p)

    def test_conflicting_atomtypes_rejected(self):
        p = self.case / 'LIG.itp'
        p.write_text(p.read_text().replace('c3 c3 12.01 0 A 0.34 0.45',
                                         'c3 c3 12.01 0 A 0.34 0.45\nc3 c3 12.01 0 A 0.34 0.99'))
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            md.parse_itp(p)

    def add_second_ligand(self, conflict=False):
        spec = md.read_json(self.case / 'case.json')
        spec['ligands'].append(dict(id='LG2', resname='LG2', count=1, mode='itp', itp='LG2.itp'))
        self.change_spec(ligands=spec['ligands'])
        text = (self.case / 'LIG.itp').read_text().replace('LIG', 'LG2')
        if conflict:
            text = text.replace('0.34 0.45', '0.34 0.99')
        (self.case / 'LG2.itp').write_text(text)
        pdb = self.case / 'complex.pdb'
        ligand_lines = [a['line'].replace('LIG', 'LG2') for a in md.pdb_atoms(pdb)
                        if a['resname'] == 'LIG'][:2]
        pdb.write_text(pdb.read_text().replace('END\n', '\n'.join(ligand_lines) + '\nEND\n'))

    def test_multiple_ligand_types_share_atomtypes(self):
        self.add_second_ligand()
        validated = self.validate()
        out = self.root / 'params'
        md.prepare_ligands(argparse.Namespace(source=validated, out=out))
        self.assertEqual(len(md.read_json(out / 'ligands.json')), 2)
        self.assertEqual(len(md.pdb_atoms(out / 'ligand_coordinates.pdb')), 6)
        self.assertEqual((out / 'ligand_atomtypes.itp').read_text().count('c3 c3'), 1)

    def test_different_ligands_cannot_redefine_atomtype(self):
        self.add_second_ligand(conflict=True)
        validated = self.validate()
        with self.assertRaisesRegex(ValueError, 'Conflicting definitions'):
            md.prepare_ligands(argparse.Namespace(source=validated, out=self.root / 'params'))

    def test_acpype_requires_explicit_charge(self):
        shutil.copyfile(ROOT / 'tests/fixtures/cases/acpype/LIG.mol2', self.case / 'LIG.mol2')
        self.change_spec(ligands=[dict(id='LIG', resname='LIG', count=2, mode='acpype', mol2='LIG.mol2')])
        with self.assertRaisesRegex(ValueError, 'net charge'):
            self.validate()

    def test_invalid_timestep(self):
        with self.assertRaisesRegex(ValueError, 'dt_ps'):
            md.validate_settings(dict(SETTINGS, dt_ps=0.004))

    def test_noninteger_steps(self):
        with self.assertRaisesRegex(ValueError, 'divisible'):
            md.validate_settings(dict(SETTINGS, nvt_ps=0.001))

    def test_em_must_converge(self):
        p = self.root / 'em.log'
        p.write_text('Steepest Descents did not converge in 50000 steps\n')
        with self.assertRaisesRegex(ValueError, 'force tolerance'):
            md.validate_run_log(p, 'em', 50000, 1000)

    def test_em_converged(self):
        p = self.root / 'em.log'
        p.write_text('Steepest Descents converged to Fmax < 1000 in 200 steps\n')
        md.validate_run_log(p, 'em', 50000, 1000)

    def test_incomplete_dynamics_rejected(self):
        p = self.root / 'npt.log'
        p.write_text('Step Time\n100 0.2\nFinished mdrun\n')
        with self.assertRaisesRegex(ValueError, 'before requested'):
            md.validate_run_log(p, 'npt', 250000, 1000)

    def test_lincs_warning_rejected(self):
        p = self.root / 'npt.log'
        p.write_text('LINCS WARNING\nStep Time\n250000 500\nFinished mdrun\n')
        with self.assertRaisesRegex(ValueError, 'instability'):
            md.validate_run_log(p, 'npt', 250000, 1000)

    def test_finished_dynamics(self):
        p = self.root / 'npt.log'
        p.write_text('Step Time\n250000 500\nFinished mdrun\n')
        md.validate_run_log(p, 'npt', 250000, 1000)

    def test_template_and_fixed_seed(self):
        s = SETTINGS.copy()
        md.validate_settings(s)
        md.render_mdp(ROOT / 'assets/mdp/nvt.mdp', self.root / 'nvt.mdp', s, 123)
        text = (self.root / 'nvt.mdp').read_text()
        self.assertIn('gen-seed = 123', text)
        self.assertNotIn('@', text)

    def test_gromacs_version_gate(self):
        with patch.object(md, 'execute', return_value='GROMACS version: 2025.1'):
            with self.assertRaisesRegex(ValueError, '2024'):
                md.gmx_version('gmx', self.root)


class ExecutorTests(unittest.TestCase):
    def test_prefers_slurm(self):
        with patch.object(launch, 'has_slurm', return_value=True), patch.object(launch, 'has_gpu', return_value=True):
            self.assertEqual(launch.select_executor('auto', 'gpu'), 'slurm')

    def test_local_fallback(self):
        with patch.object(launch, 'has_slurm', return_value=False), patch.object(launch, 'has_gpu', return_value=True):
            self.assertEqual(launch.select_executor('auto', 'gpu'), 'local_gpu')

    def test_no_hardware_does_not_run(self):
        with patch.object(launch, 'has_slurm', return_value=False), patch.object(launch, 'has_gpu', return_value=False):
            with self.assertRaisesRegex(ValueError, 'No reachable'):
                launch.select_executor('auto', 'gpu')

    def test_explicit_slurm_does_not_fallback(self):
        with patch.object(launch, 'has_slurm', return_value=False), patch.object(launch, 'has_gpu', return_value=True):
            with self.assertRaisesRegex(ValueError, 'Slurm'):
                launch.select_executor('slurm', 'gpu')

    def test_stub_without_hardware(self):
        self.assertEqual(launch.select_executor('auto', 'gpu', True), 'test')


if __name__ == '__main__':
    unittest.main()
