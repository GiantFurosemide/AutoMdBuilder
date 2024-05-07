


# write a function to write log conveniently by inputting a string
# with format: [2021-01-01 12:00:00] log_string
def write_log(log_string, log_file=f"{__file__.replace('.py','')}.log"):
    import datetime
    with open(log_file, "a") as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {log_string}\n")

# file_in_smile="input.smile"
# output_name="GA"
# output_3letter_code="GAC"
# acedrg -i $file_in_smile -o $output_name -r $output_3letter_code
# obabel -ipdb ${output_name}.pdb -omol2  > ${output_name}.mol2
# acpype -i ${output_name}.mol2
def acpype_from_smile(smile_string, output_name, output_3letter_code):
    import os
    cmd = f"acedrg -i '{smile_string}' -o {output_name} -r {output_3letter_code}"
    write_log(cmd)
    os.system(cmd)
    cmd = f"obabel -ipdb {output_name}.pdb -omol2 -h > {output_name}.mol2"
    write_log(cmd)
    os.system(cmd)
    cmd = f"acpype -i {output_name}.mol2"
    write_log(cmd)
    os.system(cmd)

# read the csv file with columns(no header): smile, name, 3letter_code by pandas
def acpype_from_smile_csv(file):
    import pandas as pd
    #df = pd.read_csv(file, header=None, names=['ID','smile_string', 'out_name', '3letter_code','acpype_dir_out','acedrg_tmp_out','acpype_cif_out','acpype_pdb_out'])
    df = pd.read_csv(file)
    for record in df.to_dict(orient='records'):
        acpype_from_smile(record['smile_string'], record['out_name'], record['3letter_code'])

# write a function to convert a int (< 46656) to a 3-letter code. each letter is A-Z or 0-9
def int_to_3letter_code(num):
    import string
    # 46656 = 36^3
    # check if num is less than 46656
    if num >= 46656:
        raise ValueError("num should be less than 46656 (36*36*36)")
    letters = string.ascii_uppercase + string.digits
    return letters[num // (36*36)] + letters[(num // 36) % 36] + letters[num % 36]

# read a csv file with columns(no header): ID, smile_string. convert the index of each row to a 3-letter code. 
# save the 3-letter code to a new column'out_name' and a new column'3letter_code'. and save as a new csv file.
def add_3letter_code(csv_in, csv_out="output.csv"):
    import pandas as pd
    df = pd.read_csv(csv_in, header=None, names=[ 'ID','smile_string'])
    df['out_name'] = df.index.map(int_to_3letter_code)
    df['3letter_code'] = df['out_name'].map(lambda x: x.upper())
    df['acpype_dir_out'] = df['out_name'].map(lambda x: x+".acpype")
    df['acedrg_tmp_out'] = df['out_name'].map(lambda x: x+"_TMP")
    df['acpype_cif_out'] = df['out_name'].map(lambda x: x+".cif")
    df['acpype_pdb_out'] = df['out_name'].map(lambda x: x+".pdb")
    write_log(f"add 3-letter code to {csv_in} and save to {csv_out}")
    df.to_csv(csv_out, index=False)

if __name__ == "__main__":
    
    # input.csv has columns: ID, smile_string
    # ouput.csv has columns: ID, smile_string, out_name, 3letter_code
    add_3letter_code("test_acpype.csv", "output.csv") 

    # generate pdb and ligand.acpype
    acpype_from_smile_csv("output.csv")
    print(f"\n> check output.csv and {__file__.replace('.py','')}.log for details.")


