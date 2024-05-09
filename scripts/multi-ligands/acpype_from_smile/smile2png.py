"""


"""


import pandas as pd
from rdkit import Chem
from rdkit.Chem import Draw


def write_log(log_string, log_file=f"{__file__.replace('.py','')}.log"):
    import datetime
    with open(log_file, "a") as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {log_string}\n")



# Read the CSV file
df = pd.read_csv('ligand_info.csv')

# Loop over the rows of the DataFrame
for index, row in df.iterrows():
    # Get the SMILES string and output name from the current row
    smiles_string = row['smile_string']
    out_name = row['out_name']

    # Create a molecule object from the SMILES string
    molecule = Chem.MolFromSmiles(smiles_string)

    # Draw the molecule and save it to a file
    try:
        Draw.MolToImageFile(molecule, f"{out_name}.png",size=(300,300))
        print(f"{out_name}.png Done!")
        write_log(f"{out_name}.png Done!")
    except OSError as e:
        print(f"{out_name}.png Failed! \n\t{e}")
        write_log(f"{out_name}.png Failed! \n\t{e}",log_file=f"{__file__.replace('.py','')}_error.log")
        continue

