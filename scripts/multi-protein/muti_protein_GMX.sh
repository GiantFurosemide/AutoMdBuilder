

ORI_PDB="complex.pdb"

gmx make_ndx -f $ORI_PDB -o index.ndx << INPUT
keep 0
a 187-2947
name 1 chain_A
a 2948-7958
name 2 chain_B
r GX1
name 3 ligands_GX1
q
INPUT

# new pdb start from atomid 1
echo chain_A | gmx editconf -f $ORI_PDB -n index.ndx -o chain_A.pdb -label A
echo chain_B | gmx editconf -f $ORI_PDB -n index.ndx -o chain_B.pdb -label B
#echo ligands_GX1 | gmx editconf -f $ORI_PDB -n index.ndx -o chain_Z.pdb -label Z


cat chain_*.pdb | grep ATOM > combined.pdb
gmx pdb2gmx -f combined.pdb -o combined.gro -ignh -p  topol.top