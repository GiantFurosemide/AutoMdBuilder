import os
from glob import glob
import subprocess

## functions
def check_existence(file):
    if not os.path.exists(file):
        raise FileNotFoundError(f"{file} does not exist")


def check_atoms_number_gro(file:str,line_nr:int=2): # line_nr=2: the second line of gro file is the number of atoms
    with open(file, "r") as f:
        for i in range(line_nr):
            line = f.readline()
    subprocess.run(f"touch {line.strip()}.atoms_nr.txt", shell=True)
    return int(line.strip())

def judge_system_size_gro(atom_nr:int):
    if atom_nr <= 150000:
        return "10W"
    elif 150000 < atom_nr <= 250000:
        return "20W"
    elif 250000 < atom_nr <= 350000:
        return "30W"
    elif 350000 < atom_nr <= 600000:
        return "50W"
    elif 600000 < atom_nr <= 850000:
        return "80W"
    elif 850000 < atom_nr <= 1200000:
        return "100W"
    else:
        return None

########################################################################
## build md system (by ambertools)
## protein: amber19sb ; ligand:gaff2
## 12 Angstrom to the edge of the box

protein_pdb = glob("*protein_processed.pdb")[0]
ligand_mol2 = glob("*_bcc_gaff2.mol2")[0]   
ligand_frcmod = glob("*_AC.frcmod")[0]


check_existence(protein_pdb)
check_existence(ligand_mol2)
check_existence(ligand_frcmod)


cmd = f"python amber_build_system.py -p {protein_pdb} -lmol2 {ligand_mol2} -lfrcmod {ligand_frcmod}"
print(cmd)
subprocess.run(cmd, shell=True)


## md minimization equilibration production
## 1 replicas

check_existence("system.gro")
check_existence("system.top")

system_size=judge_system_size_gro(check_atoms_number_gro("system.gro",line_nr=2))

#cmd = "bash mdbuild_add_multi_ligands.sh"
#print(cmd)
#os.system(cmd)
