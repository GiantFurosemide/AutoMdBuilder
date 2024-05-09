# 
# line 60 need all liand name 
# line 118-147 loop 
import os

# generate ligand_info 

def  generate_single_ligand_info_file(lig_dict,output_name):
    
    cmd = f"""
# generated by ligand_info_prepare.py
# ligand
# LIGAND NAME, if you have a ligand, it will be parametrize with acpype and the ligand name will be replace by "LIG".
LIGNAME="{lig_dict['LIGNAME']}" #<<<<<<<<<<<<<<<<<<<<<<  #PUT LIGAND NAME HERE, leave it blank if no ligand.
LIGAND_LETTER='{lig_dict['LIGAND_LETTER']}' # 3-letter name in PDB files
LIGAND_LETTER_OUT='{lig_dict['LIGAND_LETTER_OUT']}' # 3-letter name in out pdb file form ligand extraction of original PDB file for topology buildin by acpype  
LIG_NUMBER={lig_dict['LIG_NUMBER']}

    """
    #os.system('mkdir ligand_info')
    with open(output_name,'w') as file_out:
        file_out.write(cmd)

def generate_ligands_info_file(lig_dict_list,output_dir='./ligand_info')-> list:
    
    number_of_ligands = len(lig_dict_list)
    os.system(f"mkdir {output_dir}")
    ligand_info_file_path = []
    if number_of_ligands >=1:
        for i in range(number_of_ligands):
            ligand_info = lig_dict_list[i]
            ligand_out_path = os.path.join(output_dir,f"ligand_{i+1}.sh") 
            generate_single_ligand_info_file(ligand_info,ligand_out_path)
            ligand_info_file_path.append(ligand_out_path)
    else:
        print('no ligand to be processed')
    assert len(ligand_info_file_path) == len(lig_dict_list)
    return ligand_info_file_path
# generate ligand_config.sh
def generate_ligand_config_sh(lig_path_list,out_name='./ligand_config.sh'):

    with open(out_name,'w') as o_file:
        o_file.write("# generated by ligand_info_prepare.py\n")
        o_file.write("LIGAND_INFO_LIST=(\n")
        for i in lig_path_list:
            o_file.write(f"\t\"{i}\"\n")
        o_file.write(")\n")
    
    print(f"Done! wrote into {out_name}")


# generate generate_pure_protein_pdb.sh


def extract_ligand_letter(lig_info_list:list)->list:
    lig_letter_list = []
    for lig_info_dict in lig_info_list:
        lig_letter_list.append(lig_info_dict['LIGAND_LETTER'])
    assert len(lig_letter_list) == len(lig_info_list)
    return lig_letter_list

def generate_pure_protein_pdb_sh(ligand_letter_list,out_file='./generate_pure_protein_pdb.sh'):
    cmd = """

for my_ligname_letter in ${LIGAND_LETTER_LIST[@]};
do 
    grep -v $my_ligname_letter receptor_tmp.pdb > receptor_tmp2.pdb
    rm -rfv receptor_tmp.pdb
    mv receptor_tmp2.pdb receptor_tmp.pdb
done;
mv receptor_tmp.pdb receptor.pdb    
    
    """    

    with open(out_file,'w') as o_file:
        o_file.write("LIGAND_LETTER_LIST=(\n")
        for i in ligand_letter_list:
            o_file.write(f"\t\"{i}\"\n")
        o_file.write(")\n") 
        o_file.write(cmd)
    
    print(f"Done! wrote into {out_file}")
    


if __name__ == "__main__":

# ligand dict
# may add from csv files
    from csv_util import csv2records
    ligand_info_list = csv2records('ligand_info.csv')
# generate ligand_info 
    output_dir = "./ligand_info"
    ligand_info_path_list = generate_ligands_info_file(ligand_info_list,output_dir=output_dir)

# generate ligand_config.sh
    out_name='./ligand_config.sh'
    generate_ligand_config_sh(ligand_info_path_list,out_name=out_name)

# generate generate_pure_protein_pdb.sh
    out_name='./generate_pure_protein_pdb.sh'
    lig_letter_list = extract_ligand_letter(ligand_info_list)
    generate_pure_protein_pdb_sh(lig_letter_list,out_file=out_name)




