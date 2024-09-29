# acpype by mol2
obabel -ipdb DAS-jligand.pdb -omol2 -h > DAS.mol2 
acpype -i DAS.mol2 -f

# acpype by mol
obabel -ipdb DAS-jligand.pdb -omol -h > DAS.sdf  
acpype -i DAS.sdf -f

# acpype by smile,
acpype -i 'CCCC' -b 'DAS'
acpype -i "$(cat smi/dasatinib.smi)" -b 'DAS'

# obabel gen3d maybe generate error 3D coordinates
obabel -:"SCCCCCCCCCCCO" -omol2 -h --gen3d > smiles2mol_example_smiles_1.mol2 

# use acedrg to generate 3D coordinates
# -i input.smile
# -o output name GA.pdb
# 3-letter code is GAC
# will generate GA.pdb in current directory

file_in_smile="input.smile"
output_name="GA"
output_3letter_code="GAC"
acedrg -i $file_in_smile -o $output_name -r $output_3letter_code
obabel -ipdb ${output_name}.pdb -omol2  > ${output_name}.mol2
acpype -i ${output_name}.mol2

file_in_sdf="input.sdf"
output_name="GA"
output_3letter_code="GAC"
acedrg -s $file_in_sdf -o $output_name -r $output_3letter_code
obabel -ipdb ${output_name}.pdb -omol2  > ${output_name}.mol2
acpype -i ${output_name}.mol2

######### use this script to generate 3D coordinates for a ligand 20240929
input_3leter_code='ICP'
file_in_smile="${input_3leter_code}.smile"
output_name=${input_3leter_code}
output_3letter_code=${input_3leter_code}
acedrg -i $file_in_smile -o $output_name -r $output_3letter_code
obabel -ipdb ${output_name}.pdb -omol2  > ${output_name}.mol2
acpype -i ${output_name}.mol2
