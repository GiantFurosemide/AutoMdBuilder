
# cp runme.sh to the directory where you want to run the simulation
# cp -v scripts/membrane_protein_amber/runme.sh ./
# cp -v scripts/membrane_protein_amber/tleap.in ./
# update pdb_in in runme.sh
# update ligand.frcmod in tleap.in



conda activate AmberTools23
pdb_in="data/add_ligand/7bw1_6_GA_6_TP.pdb"
# box size for membrane protein(in Angstrom)
box_size=176  

######################################################################################################
cp -v $pdb_in 'myprotein.pdb'
pdb_in="myprotein.pdb"
packmol_out="bilayer_${pdb_in}" 
pdb4amber_out="bilayer_pdb4amber_${pdb_in}"

# 50w
#packmol-memgen --pdb $pdb_in --lipids POPC -r 1 --distxy_fix 176  --dist_wat 55  --dims 176 176 176 --salt 0.15 --salt_c Na --salt_a Cl --ffwat tip3p --fflip lipid21 --ffprot ff19SB 
grep ATOM $pdb_in > ${pdb_in}.tmp
mv ${pdb_in}.tmp ${pdb_in}

# change np.float to np.float64 if you got internal error of amber 

# generate complex system pdb ( default concentration of NaCl is 0.15 M)
packmol-memgen --pdb $pdb_in --lipids POPC --ratio 1 --dims ${box_size} ${box_size} ${box_size} --verbose --salt --salt_c Na+ --salt_a Cl-

# packmol for re-organizing packing
grep -v amber_ter_preserve packmol.inp > packmol.inp.tmp
mv packmol.inp.tmp packmol.inp
packmol < packmol.inp

# prepare pdb for tleap (delete H)
pdb4amber -i $packmol_out -o $pdb4amber_out --nohyd

# add force field 

sed -i "s/bilayer_myprotein.pdb/${pdb4amber_out}/g" tleap.in 
tleap -f tleap.in 

conda deactivate


