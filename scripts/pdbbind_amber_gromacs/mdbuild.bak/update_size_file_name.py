"""
read atom size from [size].atom.txt and update the size in the directory name.
"""


from glob import glob
import os
import subprocess


def check_existence(file):
    if not os.path.exists(file):
        raise FileNotFoundError(f"{file} does not exist")


def check_atoms_number_gro(file:str,line_nr:int=2): # line_nr=2: the second line of gro file is the number of atoms
    with open(file, "r") as f:
        for i in range(line_nr):
            line = f.readline()
    subprocess.run(f"touch {line.strip()}.atoms_nr.txt", shell=True)
    return int(line.strip())


def judge_system_size_gro(atom_nr:int):
    if atom_nr <= 150000:
        return "10W"
    elif 150000 < atom_nr <= 250000:
        return "20W"
    elif 250000 < atom_nr <= 350000:
        return "30W"
    elif 350000 < atom_nr <= 600000:
        return "50W"
    elif 600000 < atom_nr <= 850000:
        return "80W"
    elif 850000 < atom_nr <= 1200000:
        return "100W"
    else:
        return None


# read atom size from [size].atom.txt and update the size in the directory name.
def update_size_file_name(dir_path:str):
    """
    input: dir_path, for example PDB_complexR1_1ua4_10w, will update dir name of example 'PDB_complexR1_1ua4_10w' and 'PDB_complexR1_1ua4_10w_eqout_replica_*'.
    """
    try:
        atom_size = int(os.path.basename(glob(f"{dir_path}/*.atoms_nr.txt")[0]).split(".")[0])
    except IndexError:
        exit(f"no atoms_nr.txt file in {dir_path}")
    atom_size_str = judge_system_size_gro(atom_size)

    dir_name = os.path.dirname(dir_path)
    base_name = os.path.basename(dir_path)
    eqout_replicas_paths = glob(f"{dir_name}/{base_name}_eqout_replica_*")
    assert len(eqout_replicas_paths) > 0
    eqout_replicas_paths.append(dir_path)

    def update_dir_name(dir_path:str, change_to_atom_size_str:str):
        dir_name = os.path.dirname(dir_path)
        base_name = os.path.basename(dir_path)

        original_atom_size_str_list = base_name.split("_")
        
        if len(original_atom_size_str_list) == 4: # like PDB_complexR1_1ua4_10w
            original_atom_size_str = original_atom_size_str_list[-1]
        elif len(original_atom_size_str_list) == 7: # like PDB_complexR1_1ua4_10w_eqout_replica_1
            original_atom_size_str = original_atom_size_str_list[3]
        else:
            raise ValueError(f"unexpected dir name: {dir_path}")

        new_dir_name = os.path.join(dir_name,base_name.replace(f"_{original_atom_size_str}", f"_{change_to_atom_size_str.lower()}")) 

        return new_dir_name
    
    new_dir_name = update_dir_name(dir_path, atom_size_str)
    new_eqout_replicas_paths = [update_dir_name(path, atom_size_str) for path in eqout_replicas_paths]
    

    assert len(eqout_replicas_paths) == len(new_eqout_replicas_paths) 
    for old, new in zip(eqout_replicas_paths, new_eqout_replicas_paths):
        os.rename(old, new)
        print(f"rename {old} -> {new}")
    return {"old":eqout_replicas_paths, "new":new_eqout_replicas_paths}


if __name__ == "__main__":
    updated_list = {}
    for dir_path in glob("projects/*_eqout_replica_1"):
        # get path of dir which already generated processed.itp
        dir_path = dir_path.replace("_eqout_replica_1", "")
        change_dict = update_size_file_name(dir_path)
        updated_list[dir_path] = change_dict
    
    import json
    with open("updated_size_file_name.json", "w") as f:
        json.dump(updated_list, f, indent=4)

        
        