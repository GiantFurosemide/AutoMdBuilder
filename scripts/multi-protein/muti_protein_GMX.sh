
ORI_PDB="File.pdb"

gmx make_ndx -f $ORI_PDB -o index.ndx << INPUT
a 1-100
name 16 chain_A
a 101-200
name 17 chain_B
q
INPUT

gmx editconf -f $ORI_PDB -n index.ndx -o chain_A.pdb -label A
gmx editconf -f $ORI_PDB -n index.ndx -o chain_B.pdb -label B

cat chain_A.pdb chain_B.pdb > combined.pdb
gmx pdb2gmx -f combined.pdb -o combined.gro -p topol.top