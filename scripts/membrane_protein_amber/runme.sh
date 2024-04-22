
pdb_in="data/7bw1_mutated_maestro.pdb" # membrane 
cp -v $pdb_in 'myprotein.pdb'
pdb_in="myprotein.pdb"
#packmol_out="bilayer_myprotein.pdb"

# 50w
#packmol-memgen --pdb $pdb_in --lipids POPC -r 1 --distxy_fix 176  --dist_wat 55  --dims 176 176 176 --salt 0.15 --salt_c Na --salt_a Cl --ffwat tip3p --fflip lipid21 --ffprot ff19SB 
grep ATOM $pdb_in > ${pdb_in}.tmp
mv ${pdb_in}.tmp ${pdb_in}

# change np.float to np.float64
packmol-memgen --pdb $pdb_in --lipids POPC --ratio 1 --dims 176 176 176 --verbose

grep -v amber_ter_preserve packmol.inp > packmol.inp.tmp
mv packmol.inp.tmp packmol.inp
packmol < packmol.inp

# add force field 
tleap -f tleap.in


