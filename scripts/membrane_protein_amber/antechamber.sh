# make force field for lignad


# 0. antechamber to generate topoly and force field
# 这里，-i LIG.pdb指定了输入文件（你的小分子的PDB文件）
# -o LIG.mol2指定了输出文件（生成的mol2文件）
# -c bcc指定了电荷计算方法（这里使用了AM1-BCC方法）
# -s 2指定了状态（这里是2，表示两个单独的步骤：首先使用sqm计算AM1电荷，然后使用bcc调整这些电荷）123。

antechamber -i LIG.pdb -fi pdb -o LIG.mol2 -fo mol2 -c bcc -s 2

# 1. check missing force field info by parmchk2
parmchk2 -i LIG.mol2 -f mol2 -o LIG.frcmod


# update tleap.in for tleep
# add this:
# loadamberparams LIG.frcmod
