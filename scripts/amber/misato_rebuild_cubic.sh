# input: production.top, production.rst from misato database
# output: complex.pdb, complex.parm7, complex.rst7
# guess only one ligand and with MOL as name


cat > convert2pdb.in <<EOF
trajin production.rst
trajout production.pdb
run
EOF
cpptraj -p production.top -i convert2pdb.in

cat production.pdb | grep MOL > ligand.pdb
#cat production.pdb | grep -v WAT | grep -v Cl- | grep Na+ > protein.pdb
grep -v -e "Na+" -e "Cl-" -e "WAT" -e "MOL" production.pdb > protein.pdb

antechamber -i ligand.pdb -fi pdb -o ligand.mol2 -fo mol2 -c bcc -s 2
parmchk2 -i ligand.mol2 -f mol2 -o ligand.frcmod

cat > tleap.in <<EOF
source leaprc.protein.ff14SB
source leaprc.gaff2
source leaprc.water.tip3p

# Load the protein and ligand files
protein = loadpdb protein.pdb
ligand = loadmol2 ligand.mol2

# Load the ligand parameters
loadamberparams ligand.frcmod

# Combine the protein and ligand
complex = combine {protein ligand}

# Add a cubic water box with a minimum distance of 12 Å
#solvatebox complex TIP3PBOX 12.0

# Create a cubic water box with fixed size of 100 Å
solvatebox complex TIP3PBOX {100.0 100.0 100.0}


# Add 150mM NaCl and neutralize the system
# addions2 complex Na+ Cl- 150 
addions complex Na+ 0
addions complex Cl- 0

# Save the new topology and coordinate files
saveamberparm complex complex.parm7 complex.rst7
savepdb complex complex.pdb

quit

EOF
tleap -f tleap.in