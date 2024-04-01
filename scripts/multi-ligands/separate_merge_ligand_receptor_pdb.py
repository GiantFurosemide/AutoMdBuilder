"""
0. pdb_fixer convert non_standatd_residue
1. separate ligand from complex pdb file, and save protein and ligand to individual pdb file.
2. send individual ligand to ACPYPE to generate GROMACS topology files and new pdb file
3. record number of ligands in complex pdb file.
4. merge protein and NEW ligand pdb file to generate new complex pdb file.
"""
from Bio.PDB import *
import os
import pandas as pd
from Bio.PDB import PDBParser, PDBIO, Select, Structure, Model, Chain
from Bio.PDB.Polypeptide import is_aa


############################################################################################################
# seperate to protien and ligand

# input
pdb_data_file="data/src-PP1-3-10w-new.pdb"

# output
protein_pdb_file="protein_raw.pdb"
ligand_pdb_file="all_ligands_raw.pdb"

class ProteinSelect(Select):
    def accept_residue(self, residue):
        return 1 if is_aa(residue.get_resname(), standard=True) else 0

class LigandSelect(Select):
    def accept_residue(self, residue):
        return 0 if is_aa(residue.get_resname(), standard=True) else 1


# Parse the original PDB file
parser = PDBParser(QUIET=True)
structure = parser.get_structure('original', pdb_data_file)

# Select the protein and save to a new PDB file
io = PDBIO()
io.set_structure(structure)
io.save(protein_pdb_file, ProteinSelect())

# Select the ligands and save to a new PDB file
io.save(ligand_pdb_file, LigandSelect())

############################################################################################################
# separate ligand and record ligand meta data

# input
# pdb_data_file="data/src-PP1-3-10w-new.pdb"
pdb_data_file = ligand_pdb_file
pdb_data_name = "ligands"
out_dir = "data"
out_ligand_prefix = "ligand"
default_chain_name = "X"
# output
out_meta_data = []  # [{residue_name:, residue_id:,out_pdb_path:}, ...]
out_meta_data_csv = f"{out_dir}/ligand_meta_data.csv"

# 创建 PDBParser 对象
parser = PDBParser(QUIET=True)

# 读取 PDB 文件

structure = parser.get_structure(pdb_data_name, pdb_data_file)

# 创建 PDBIO 对象
io = PDBIO()
# for pdb from md ANALYSIS
for model in structure:
    # 遍历模型中的链
    for chain in model:
        # 遍历链中的残基
        for residue in chain:
            # 检查残基是否为小分子
            print(residue.resname)
            if not is_aa(residue.resname, standard=True):
                # 获取小分子的名字
                residue_name = residue.resname
                print(residue_name)
                # 如果不存在对应的文件夹，则创建
                _tmp_out_dir = os.path.join(out_dir, residue_name)
                if not os.path.exists(_tmp_out_dir):
                    os.makedirs(_tmp_out_dir)
                # 创建一个新的 Structure 对象
                new_structure = Structure.Structure('new_structure')
                # 将小分子添加到新的结构中
                new_structure.add(Model.Model(0))
                new_structure[0].add(Chain.Chain(default_chain_name))
                new_structure[0][default_chain_name].add(residue)
                # 将新的结构写入 PDB 文件
                io.set_structure(new_structure)
                io.save(f'{out_dir}/{residue_name}/{out_ligand_prefix}_{residue_name}_{residue.id[1]}.pdb')
                out_meta_data.append({"residue_name": residue_name, "residue_id": residue.id[1],
                                      "out_pdb_path": f'{out_dir}/{residue_name}/{out_ligand_prefix}_{residue_name}_{residue.id[1]}.pdb'})

pd.DataFrame(out_meta_data).to_csv(out_meta_data_csv, index=False)

############################################################################################################
# separate ligand and record ligand meta data
