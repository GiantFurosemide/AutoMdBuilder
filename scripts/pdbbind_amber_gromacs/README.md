
# Requirment

* ambertools23
* acpype
* gromacs
* parmed
* python 3.11
* amber (optional)

# Workflow Overview

* step0 input files:
  * pdbbind
    * protein: XXXX_protein.pdb
    * ligand: XXXX_ligand.mol2
* step1 generate ligand topology and force flied information by acpype:
  * input:
    * ligand: XXXX_ligand.mol2
  * output:
    * ligand:XXXX_ligand_bcc_gaff2.mol2
    * ligand:XXXX_ligand_AC.frcmod
* step2 pre-process protein file:
  * pdbfixer_process.py::pdbfixer_processor()
    * input:
      * protein: XXXX_protein.pdb
    * output:
      * protein:XXXX_protein_processed.pdb
* step3 organize input files for md system buiding:
  * create a directory in mdbuild.bak/structures, fo example PDB_complexR1_XXXX_10w, which contains:
    * input:
      * protein:XXXX_protein_processed.pdb
      * ligand:XXXX_ligand_bcc_gaff2.mol2
      * ligand:XXXX_ligand_AC.frcmod
  * change directory to mdbuild.bak/ , run "source runme.sh"
  * runme.sh will copy PDB_complexR1_XXXX_10w to mdbuild.bak/projects
  * runme.sh will copy mdbuild.bak/scripts/* to mdbuild.bak/projects/PDB_complexR1_XXXX_10w
  * runme.sh will run amber_build_system.py for md sytem building
  * runme.sh will run mdbuild_add_multi_ligands.sh for minimization/equilibration/production and output files wraping
    * output files( .gro and .itp) will be stored in for examplemdbuild.bak/projects/PDB_complexR1_XXXX_10w_eqout_replica_*
* step4 update md system size
  * by defaut, every case was named as "10w", a md system with about 10,000 atoms, before its md system built.
  * cd mdbuild.bak/, run "python update_size_file_name.py"
  * update_size_file_name.py will check atoms number of .gro file, and update cases directory name
    * for example: mdbuild.bak/projects/PDB_complexR1_XXXX_10w -> mdbuild.bak/projects/PDB_complexR1_XXXX_50w

# File Structure

├── mdbuild.bak
│   ├── projects
│   ├── runme.sh
│   ├── scripts
│   │   ├── amber_build_system.py
│   │   ├── mdbuild_add_multi_ligands.sh
│   │   ├── mdp
│   │   │   ├── em.mdp
│   │   │   ├── ions.mdp
│   │   │   ├── md_nvt.mdp
│   │   │   ├── md_prod.mdp
│   │   │   ├── npt.mdp
│   │   │   └── nvt_300.mdp
│   │   ├── packup.sh
│   │   └── runme.py
│   ├── structures
│   │   ├── PDB_complexR1_1ai4_10w
│   │   │   ├── 1ai4_ligand_AC.frcmod
│   │   │   ├── 1ai4_ligand_bcc_gaff2.mol2
│   │   │   └── 1ai4_protein_processed.pdb
│   │   ├── PDB_complexR1_1ai5_10w
│   │   │   ├── 1ai5_ligand_AC.frcmod
│   │   │   ├── 1ai5_ligand_bcc_gaff2.mol2
│   │   │   └── 1ai5_protein_processed.pdb
│   └── update_size_file_name.py
├── pdbfixer_process.py
└── README.md

* pdbfixer_process.py: script to process protein files (add missing atoms/PH/convert non-standard amino acid) based on OPENMM.
* mdbuild.bak/structures: initial topology and coordinates file for building MD system. each subdirectory (PDB_complexR1_1ai4_10w for example) is an indenpendent case.
* mdbuild.bak/projects: subdirectories in mdbuild.bak/structures will be copy to here. md building related scripts will be copied to each subdirectory and start building.
* mdbuild.bak/scripts: md building related scripts
* mdbuild.bak/scripts/amber_build_system.py: read ligand.mol2,ligand.frcmod and protein.pdb, generate system.parm7, system.rst7 ( and system.gro system.top) for further minimization/equilibration/production. amber_build_system.py perform system preparetion by tleap of amber.
* mdbuild.bak/scripts/mdbuild_add_multi_ligands.sh: read system.gro system.top and start minimization/equilibration/production. based on gromacs 2024
* mdbuild.bak/scripts/packup.sh: pack up .gro and .top files outputed from mdbuild_add_multi_ligands.sh for submision to HPC512
* mdbuild.bak/scripts/runme.py: script integrated amber_build_system.py,mdbuild_add_multi_ligands.sh for workflow control.
* mdbuild.bak/scripts/mdp: mdp files of gromacs for minimization/equilibration/production.
* mdbuild.bak/runme.sh: main script to start all processes.
