#!/usr/bin/env python

"""
Genertate 3d pdb files by scedrg when input a .smi file from zinc database

# requirement: acedrg and parallel in cmd
"""


import os
import pandas as pd
from datetime import datetime
import argparse

def make_cmd(zinc_smile_file,cmd_file = 'acedrg.sh'):
    """
    read .smi file from zinc database and write the acedrg command to a file.
    then write the file name od the output of acedrg  to a csv file.
    """
    
    file_name = zinc_smile_file.split('/')[-1].split('.')[0]
    # out csv file
    csv_out = file_name + '_out.csv'

    df = pd.read_csv(zinc_smile_file,sep=' ')
    # df have two columns: 'SMILES''ZINC_ID' 
    columns = df.columns
    with open(cmd_file, 'w') as f:      
        for i in range(len(df)):
            smi = df[columns[0]][i]  # 'colomns[0]' is 'smiles'
            zinc_id = str(df[columns[1]][i]).strip()   # 'colomns[1]' is 'zinc_id'
            #cmd = f'obabel -:"{smi}" -O {zinc_id}.pdbqt'
            cmd = f"acedrg -i '{smi.strip()}' -o '{'_'.join([file_name,zinc_id])}' \n"
            print(f"[{datetime.now()}] writing <{cmd.strip()}> to {cmd_file}")
            f.write(cmd)
    
    df['acedrg_name'] = [f"{file_name}_{str(i).strip()}" for i in df[columns[1]]]
    df.to_csv(csv_out,index=False)
    print(f"[{datetime.now()}] writing <{csv_out}>")
    return csv_out

def clean_acdrg_output(csv_file,acedrg_output_dir='./acedrg_output'):
    """
    read the csv file to get 'acedrg_name', then organise acedrg output to acedrg_output_di.
    """
    df = pd.read_csv(csv_file)
    for i in range(len(df)):
        acedrg_name =  df['acedrg_name'][i]
        smi_filename = acedrg_name.split('_')[0]
        #zinc_id:str = acedrg_name.split('_')[1]

        pdb_file = f"{acedrg_name}.pdb"
        cif_file = f"{acedrg_name}.cif"
        acedrg_tmp_file = f"{acedrg_name}_TMP"

        out_dir = os.path.join(acedrg_output_dir,smi_filename,acedrg_name)
        if not os.path.exists(out_dir):
            os.system(f"mkdir -p {out_dir}")
        
        os.system(f"mv -v {pdb_file} {out_dir}")
        os.system(f"rm -rfv {cif_file} {out_dir}")
        os.system(f"rm -rfv {acedrg_tmp_file} {out_dir}") 

    return df
        
def main():
    parser = argparse.ArgumentParser(description='Convert SMILES to cmd file for acedrg')
    parser.add_argument('-smi','--smi_file', help='SMILES file',required=True)
    parser.add_argument('-ocmd','--cmd_file', help='Command file',required=True)
    parser.add_argument('-oacedrg','--out_acedrg_dir',default='./acedrg_output', help='Output directory of acedrg',required=False)
    args = parser.parse_args()

    csv_file = make_cmd(args.smi_file, args.cmd_file)

    # use parallel to run the acedrg command
    os.system(f"parallel :::: {args.cmd_file}")

    clean_acdrg_output(csv_file,args.out_acedrg_dir)



if __name__ == '__main__':
#    smi_file = 'AAAC.smi'
#    cmd_file = smi_file+".cmd"
#    make_cmd(smi_file,cmd_file=cmd_file)

    main()
