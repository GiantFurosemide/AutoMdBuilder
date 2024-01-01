# AutoMdBuilder

Homemade scripts based on  [protocolGromacs](https://github.com/tubiana/protocolGromacs), for automatically md system building.

## 1. Installation

Please visit following links for more information about installation.

* [gromacs](https://manual.gromacs.org/current/install-guide/index.html)
* [protocolGromacs](https://github.com/tubiana/protocolGromacs)

## 2. Directory Structure

![directory_structure](imgs/directory_structure.png)

## 3. Usage

The working directory is 'projects/'. The script 'runme.sh' will first check PDB files in 'projects/structures', then create new directories under 'projects/projects' for each structure, and perform MD system building, minimization, NVT equilibration, NPT equilibration, and so on, as set up in 'scripts/protocolgromacs_001'.

1. Refine PDB files and copy them to 'projects/structures'.
2. Update parameters for GROMACS in 'scripts/protocolgromacs_001':
   a. 'scripts/protocolgromacs_001/runGromacs.sh'
   b. 'scripts/protocolgromacs_001/mdp/*.mdp'
3. Change the directory to 'projects/'.
4. Run the script 'runme.sh'.

## 4. TODO

* update automatically center atom selection, for example by centroid.
* update supporting for multiple ligands
* update logging
