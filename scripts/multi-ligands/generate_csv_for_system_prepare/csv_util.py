import pandas as pd

# convert dataframe to records
def df2records(df:pd.DataFrame)->list:
    return df.to_dict(orient='records')

# convert records to dataframe
def records2df(records:list)->pd.DataFrame:
    return pd.DataFrame.from_records(records)

# convert dataframe to csv
def df2csv(df:pd.DataFrame, csv_path:str):
    df.to_csv(csv_path, index=False)

# convert csv to dataframe
def csv2df(csv_path:str)->pd.DataFrame:
    return pd.read_csv(csv_path)

# convert csv to records
def csv2records(csv_path:str)->list:
    return csv2df(csv_path).to_dict(orient='records')

# convert records to csv
def records2csv(records:list, csv_path:str):
    df = records2df(records)
    df2csv(df, csv_path)



if __name__ == "__main__":
    config_dict_list = [
    {
        # ligand structure, from acepype , contains atom H
        "ligand_pdb": '/media/muwang/新加卷/muwang/work/md_build/projects/ZYK/structure/complex/GA_NEW.pdb',
        # protein structure
        "input_pdb": '/media/muwang/新加卷/muwang/work/md_build/projects/ZYK/structure/complex/3D4N_mutated_maestro_coot-29-282.pdb', # protein
        # output pdb path
        "output_pdb": '/media/muwang/新加卷/muwang/work/md_build/projects/ZYK/structure/complex/output/3D4N_mutated_maestro_coot-29-282-GA6-10w.pdb',
        # number of ligand you want to insert
        "num_A_proteins": 6,
        # box size in Angstrom 
        "box_size": 100,
        # the minimum distance between ligand and protein
        "THRESHOLD1": 5.5,
        # the minimum distance between ligands
        "THRESHOLD2": 5.5,
        # chain name for ligand
        "segid": "AAA"
    },
    {
        # ligand structure, from acepype , contains atom H
        "ligand_pdb": '/media/muwang/新加卷/muwang/work/md_build/projects/ZYK/structure/complex/TP_NEW.pdb',
        # protein structure
        "input_pdb": '/media/muwang/新加卷/muwang/work/md_build/projects/ZYK/structure/complex/output/3D4N_mutated_maestro_coot-29-282-GA6-10w.pdb', # protein
        # output pdb path
        "output_pdb": '/media/muwang/新加卷/muwang/work/md_build/projects/ZYK/structure/complex/output/3D4N_mutated_maestro_coot-29-282-GA6-TP6-10w.pdb',
        # number of ligand you want to insert
        "num_A_proteins": 6,
        # box size in Angstrom 
        "box_size": 100,
        # the minimum distance between ligand and protein
        "THRESHOLD1": 5.5,
        # the minimum distance between ligands
        "THRESHOLD2": 5.5,
        # chain name for ligand
        "segid": "AAB"
    }

    ]

    records2csv(config_dict_list, 'config.csv')

    ligand_info_list = [
    {
        'LIGNAME':"FTY",
        'LIGAND_LETTER':"UNL",
        'LIGAND_LETTER_OUT':"UNL",
        'LIG_NUMBER':2,
    },

    ]

    records2csv(ligand_info_list, 'ligand_info.csv')
