# ambertools23
# acpype
"""
generate system.parm7 and system.rst7 from protein.pdb and ligand.mol2 by using ambertools23
""" 

import os
import subprocess
import parmed as pmd

# add input parser
import argparse

parser = argparse.ArgumentParser(description='Generate system.parm7 system.rst7 | system.top system.gro  from protein.pdb and ligand.mol2 by using ambertools23')
parser.add_argument('-p','--protein', help='Protein pdb file', required=True)
parser.add_argument('-lmol2','--ligand_mol2', help='Ligand mol2 file', required=True)
parser.add_argument('-lfrcmod','--ligand_frcmod', help='Ligand frcmod file', required=True)
parser.add_argument('--boxsize', help='Box size', default=100)
parser.add_argument('--ion_concentration', help='Ion concentration', default=150)

args = parser.parse_args()

# Input
#protein = "/media/muwang/新加卷/muwang/database/PDBBIND_PLUS/amber/1bju_protein.pdb"
#ligand_001 = "/media/muwang/新加卷/muwang/database/PDBBIND_PLUS/amber/1bju_ligand.mol2"
protein = args.protein
ligand_001 = args.ligand_mol2
boxsize = 100  # angstrom
ion_concentration = 150  # mM

# Output
ligand_001_out_frcmod = args.ligand_frcmod
# ligand_001_out_mol2 = os.path.basename(ligand_001).replace('.mol2', '.antechamber.mol2')
protein_tleap_corrected = os.path.basename(protein).replace('.pdb', '_pdb4amber_corrected.pdb')

# amber output
parm7_out = 'system.parm7'
rst7_out = 'system.rst7'
# gromacs output
top_out = 'system.top'
gro_out = 'system.gro'

## Ligand process
#if not os.path.exists(ligand_001_out_frcmod,):
#    subprocess.run([
#        'antechamber',
#        '-i', ligand_001,
#        '-fi', 'mol2',
#        '-o', ligand_001 + '.tmp',
#        '-fo', 'mol2',
#        '-c', 'bcc',
#        '-s', '2'
#    ])
#
#    subprocess.run([
#        'parmchk2',
#        '-i', ligand_001 + '.tmp',
#        '-f', 'mol2',
#        '-o', ligand_001_out_frcmod,
#        '-s', 'gaff2'
#    ])
#
#    os.rename(ligand_001 + '.tmp', ligand_001_out_mol2)

# Protein process
subprocess.run([
    'pdb4amber',
    '-i', protein,
    '-o', protein_tleap_corrected,
    '--nohyd',
    '--reduce'
])

# TLEAP: Protein processing
with open('leap_protein_process.in', 'w') as f:
    f.write(f"""source leaprc.protein.ff14SB
mol = loadpdb {protein_tleap_corrected}
savepdb mol {protein_tleap_corrected}
quit
""")

subprocess.run(['tleap', '-f', 'leap_protein_process.in'])

# TLEAP: Complex processing
with open('leap.in', 'w') as f:
    f.write(f"""source leaprc.protein.ff19SB
source leaprc.gaff2
source leaprc.water.tip3p
loadamberparams {ligand_001_out_frcmod}

mol = loadpdb {protein_tleap_corrected}
lig1 = loadmol2 {ligand_001}
complex = combine {{mol lig1}}

#set complex box{{ {boxsize} {boxsize} {boxsize} }}

addions complex Na+ 0
addions complex Cl- 0
addions complex Na+ {ion_concentration}
addions complex Cl- {ion_concentration}

charge complex


#setBox complex centers {boxsize}
solvatebox complex TIP3PBOX 12.0

saveamberparm complex {parm7_out} {rst7_out}
quit
""")

subprocess.run(['tleap', '-f', 'leap.in'])
print("parm7 and rst7 generated: ", parm7_out, rst7_out)

print("Ambertools23 and acpype requied.")


# convert to gromacs
system = pmd.load_file(parm7_out, rst7_out)
system.save(top_out, overwrite=True)
print("top file generated: ", top_out)
system.save(gro_out, overwrite=True)
print("gro file generated: ", gro_out)
