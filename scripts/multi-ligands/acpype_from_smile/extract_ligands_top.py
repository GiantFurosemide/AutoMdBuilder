# copy DONE ligands' top and pdb files to a new directory


import os
import shutil
import pandas as pd
import argparse

# Create the parser and add argument
parser = argparse.ArgumentParser(description="Copy DONE ligands' top and pdb files to a new directory.")
parser.add_argument('-f','--csv_file', type=str,default="checkdone_ONLYdone.csv", help='The CSV file to process',required=True)
# set output directory as an argument, and default name is 'for_md_system'
parser.add_argument('-o','--output_dir', type=str, default='for_md_system', help='The output directory to save the files')

# Parse the arguments
args = parser.parse_args()

# Read the CSV file
df = pd.read_csv(args.csv_file)

# Create a directory named "for_md_system"
os.makedirs(args.output_dir, exist_ok=True)

# Loop over the rows of the DataFrame
for index, row in df.iterrows():
    # Get the file paths from the current row
    itp_file_path = row['acpype_gmx_itp_out']
    pdb_file_path = row['acpype_gmx_newpdb_out']

    # Copy the files to the new directory
    shutil.copy(itp_file_path, args.output_dir)
    shutil.copy(pdb_file_path, args.output_dir)
