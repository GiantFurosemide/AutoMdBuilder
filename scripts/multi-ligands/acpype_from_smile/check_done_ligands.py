"""
check if topology of ligands generated successfully
input: 
    csv file with columns:
        ID,
        smile_string,
        out_name,
        3letter_code,
        acpype_dir_out,
        acedrg_tmp_out,
        acedrg_cif_out,
        acedrg_pdb_out
output:
    csv file with columns:
        ID,
        smile_string,
        out_name,
        3letter_code,
        acpype_dir_out,
        acedrg_tmp_out,
        acedrg_cif_out,
        acedrg_pdb_out,
        acpype_gmx_itp_out,
        acpype_gmx_newpdb_out,
"""

def write_log(log_string, log_file=f"{__file__.replace('.py','')}.log"):
    import datetime
    with open(log_file, "a") as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {log_string}\n")


# check if file exists and not empty
def check_file_exist_and_not_empty(file):
    import os
    if not os.path.exists(file):
        return False
    if os.path.getsize(file) == 0:
        return False
    return True

# check if topology of ligands generated successfully
def check_done_ligands(csv_in, csv_out_all="checkdone_all.csv",csv_out_done="checkdone_ONLYdone.csv",csv_out_not_done="checkdone_ONLYnot_done.csv"):
    import pandas as pd
    df = pd.read_csv(csv_in)

    df['acpype_gmx_itp_out_path'] = df['acpype_dir_out']+'/'+df['acpype_gmx_itp_out']
    df['acpype_gmx_newpdb_out_path'] =  df['acpype_dir_out']+'/'+df['acpype_gmx_newpdb_out'] 
    
    df['if_exist_acpype_gmx_itp_out'] = df['acpype_gmx_itp_out_path'].map(check_file_exist_and_not_empty)
    df['if_exist_acpype_gmx_itp_out'] = df['acpype_gmx_newpdb_out_path'].map(check_file_exist_and_not_empty)

    # output bool by input two bools with operator 'and'
    df['if_done'] = df['if_exist_acpype_gmx_itp_out'] & df['if_exist_acpype_gmx_itp_out']

    
    #write_log(f"check if topology of ligands generated successfully")
    df.to_csv(csv_out_all, index=False)
    df_done = df[df['if_done']]
    df_not_done = df[~df['if_done']]
    df_done.to_csv(csv_out_done, index=False)
    df_not_done.to_csv(csv_out_not_done, index=False)
    print(f"check results in \n\t>{csv_out_all} \n\t>{csv_out_done} \n\t>{csv_out_not_done}")

if __name__ == "__main__":
    input_csv = "output.csv" #  (at least)with columns: ID, smile_string, out_name, 3letter_code, acpype_dir_out, acpype_gmx_itp_out, acpype_gmx_newpdb_out
    check_done_ligands(input_csv)