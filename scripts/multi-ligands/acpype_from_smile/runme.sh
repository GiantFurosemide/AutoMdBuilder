

# convert smile to pdb(by acedrg) and topology file(by acpype)
# read input.csv and write output.csv
conda activate acpype
python acpype_from_smile.py
conda deactivate

# caluculate mass and logP, then visualize mass and logP
# read output.csv and write ligand_info.csv
conda activate my-rdkit-env
python smile2mass_log.py

# check if topology file and pdb file are generated correctly
# read ligand_info.csv and write 3 checkdone_*.csv
python check_done_ligand.py

# convert smiles to png to visualize ligand
# read ligand_info.csv 
python smile2png.py
conda deactivate

# pack files
mkdir acpype_file/
mkdir acedrg_file/
mkdir pdb_file/
mkdir mol2_file/
mkdir png_file/
mkdir cif_file/
mkdir acpype_file/

mv ./???.acpype   acpype_file/
mv ./???_TMP      acedrg_file/
mv ./???.pdb      pdb_file/
mv ./???.mol2     mol2_file/
mv ./???.png      png_file/
mv ./???.cif      cif_file/
mv ./.acpype_tmp* acpype_file/

# extract ligands top and pdb for md system building 
cp checkdone_ONLYdone.csv acpype_file
cp extract_ligands_top.py acpype_file
cd acpype_file
FOR_MD_SYS='for_md_system'
python extract_ligands_top.py -f checkdone_ONLYdone.csv -o $FOR_MD_SYS
mv $FOR_MD_SYS ../
rm -r extract_ligands_top.py
cd -


# if chechdone_ONLYnot_done is not empty, change file name to input.csv and run from start
