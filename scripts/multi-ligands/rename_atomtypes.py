"""
get atomtype name and mass from itp files name and mass from itp files
Extract [ atomtypes ] blocks from *_GMX.itp file and remove duplicates and save to atomtypes_merge.itp. 

input: 
    *_GMX.itp,
    atomtypes.atp
output: 
    *_GMX.itp(removed [ atomtypes ]), atomtypes_merge.itp file to append to atomtypes.atp
    atomtypes.atp.extend
    atomtypes_group_tuples.pickle
"""
import glob

def process_and_remove_atomtypes(file_list:list,output_file='atomtypes_merge.itp'):
    #atomtypes_header = '[ atomtypes ]\n'
    comment_lines = []  #set((info_line, file_name),...) ; info_line is data line or comment line; file_name is which *_GMX.itp it belongs
    data_lines = []  #set((info_line, file_name),...)

    # 处理每个文件
    for file_name in file_list:
        file_content = []
        in_atomtypes_block = False
        with open(file_name, 'r') as file:
            for line in file:
                # 检测到 [ atomtypes ] 区块的开始
                if '[ atomtypes ]' in line:
                    in_atomtypes_block = True
                # 检测到下一个区块的开始，结束当前区块的处理
                elif line.startswith('[') and in_atomtypes_block:
                    in_atomtypes_block = False
                    file_content.append((line,file_name))  # 保留下一个区块的开始行
                elif in_atomtypes_block:
                    # 根据行的内容分类存储
                    if line.strip() == '' or line.startswith(';'):
                        if line.startswith(';'):
                            comment_lines.append((line,file_name))
                    else:
                        data_lines.append((line,file_name))
                else:
                    file_content.append((line,file_name))

        # 重写文件，移除 [ atomtypes ] 区块
        # with open(file_name, 'w') as file:
        #   file.writelines(file_content)

    # 排序注释和数据行
    sorted_comments = sorted(group_tuples(comment_lines).keys())
    data_lines_dict = group_tuples(data_lines)
    sorted_data = sorted(data_lines_dict.keys())

    
    return sorted_comments, sorted_data, data_lines_dict

def write_merge_atomtype(sorted_comments,sorted_data,data_lines_dict,output_file='atomtypes_merge.itp'):
    # 写入输出文件
    with open(output_file, 'w') as merge_file:
        merge_file.write('[ atomtypes ]\n')  # 写入头部
        for comment in sorted_comments:
            merge_file.write(comment[0])
        for data_line in sorted_data:
            for itp_filename in data_lines_dict[data_line]:
                merge_file.write(f";{itp_filename}\n")  # 每行后添加一个换行符
            merge_file.write(data_line)
        merge_file.write('\n')  # 文件末尾添加一个空行



from collections import defaultdict
def group_tuples(tuples_list:list)->dict:
    """
    group tuples by the first element of each tuple

    input:
        tuples_list = [('a', 1), ('b', 2), ('a', 3), ('c', 4), ('b', 5)]
    output:
        dict{'a': [1, 3], 'b': [2, 5], 'c': [4]}    
    example usage
    tuples_list = [('a', 1), ('b', 2), ('a', 3), ('c', 4), ('b', 5)]
    grouped_dict = group_tuples(tuples_list)
    print(grouped_dict)
    """

    grouped_dict = defaultdict(list)
    for t in tuples_list:
        grouped_dict[t[0]].append(t[1])
    return dict(grouped_dict)


def split_line_atomtype(line:str,comment_delimiter:str=';')->tuple:
    """
    parse a line in [ atomtypes ] block
    input:
        string line = 'C1    12    12.01100    0.000    A    3.399    0.077    0.000'
    output:
        list ['C1', '12', '12.01100', '0.000', 'A', '3.399', '0.077', '0.000'], string comment = '; 3.399    0.077    0.000'
    """
    # atomtype, mass, charge, sigma, epsilon, comment = line.split()
    if comment_delimiter in line:
        result =  line.split(';')
        if len(result) > 1 and result[0] == '':
            comment = line
        else:
            comment= f"{comment_delimiter}"+" ".join(result[1:])
        return result[0].split(),comment
    else:
        return line.split(), None

def parse_line_atomtype(line:str)->dict:
    """
    parse a line in [ atomtypes ] block
    input:
        string line = 'oh       oh          0.00000  0.00000   A     3.24287e-01   3.89112e-01'
    output:
        dict{'name': 'oh', 'bond_type': 'oh', 'mass': '0.00000', 'charge': '0.00000', 'ptype': 'A', 'sigma': '3.24287e-01', 'epsilon': '3.89112e-01', 'comment': None}
        
    """
    data, comment = split_line_atomtype(line)
    
    assert len(data) == 7, f"Error: \n >'{line}'\n is not a valid atomtype line"
    return {'name':' '+data[0]+' ',
            'bond_type':' '+data[1]+' ',
            'mass':data[2],     
            'charge':data[3],  
            'ptype':data[4],   
            'sigma':data[5],         
            'epsilon':data[6],
            'comment':comment,
            'raw_line':line
            }

def replace_atomtype(
        sorted_comments:list,
        sorted_data:list, 
        data_lines_dict:dict,
        input_atomtype_atp:str='atomtypes.atp', 
        output_file_atomtypes_merge_itp:str='atomtypes_merge.itp',
        output_file_atomtypes_atp:str='atomtypes.atp.extend',
        ):
    import pandas as pd
    record_list = []
    for line in sorted_data:
        record_list.append(parse_line_atomtype(line))
    df = pd.DataFrame(record_list)
    # generate new column 'new_name' based on row index(by int_to_3letter_code)
    df['new_name'] = df.index.map(int_to_3letter_code)
    # update new_name in df by concatenating first letter of 'atomtype' and 'new_name'
    df['new_name'] = df['name'].str[1] + df['new_name']
    df.to_csv("df.csv")

    ####################output####################
    # write updated atomtypes_merge.itp file

    sorted_data_renamed = [row['raw_line'].replace(row['name'],row['new_name']) for i, row in df.iterrows()]
    for old,new in zip(sorted_data,sorted_data_renamed):
        data_lines_dict[new] = data_lines_dict[old]
    write_merge_atomtype(sorted_comments, 
                         sorted_data_renamed, 
                         data_lines_dict, 
                         output_file=output_file_atomtypes_merge_itp)


    # generate new atomtype.atp file
    for_name_mass_new_atomname = [row['new_name']for i,row in df.iterrows()]
    for_name_mass_old_atomname = [row['name'] for i, row in df.iterrows()]
    for_name_mass_file_name = [data_lines_dict[row['raw_line']][0] for i, row in df.iterrows()]
    name_mass = get_atomtype_name_mass(for_name_mass_new_atomname,for_name_mass_old_atomname,for_name_mass_file_name)
    extend_atomtypes_atp(name_mass,input_atomtype_atp,output_file_atomtypes_atp)

    # replace atomtype name in itp files
    for i, row in df.iterrows():
        for itp_file in data_lines_dict[row['raw_line']]:
            # replace atomtype name in itp_file
            replace_itp_atomtype(itp_file, row['raw_line'], row['name'], row['new_name'])
        
def extend_atomtypes_atp(name_mass:list,intput_file_atp:str='atomtypes.atp',output_file_atomtypes_merge_itp:str='atomtypes.atp.extend'):
    
    # append atomtypes_merge.itp to atomtypes.atp
    with open(intput_file_atp, 'r') as file:
        lines = file.readlines()
    with open(output_file_atomtypes_merge_itp, 'w') as file:
        file.writelines(lines)
        file.write('\n')
        for new_name, mass in name_mass:
            file.write(f"{new_name}    {mass}\n")
        print(f"> append {len(name_mass)} atomtypes to {output_file_atomtypes_merge_itp}")

def get_atomtype_name_mass(new_name_list:list,old_name_list:list,file_list:list)->list:
    """
    get atomtype name and mass from itp files
    """
    name_mass = []
    assert len(new_name_list) == len(old_name_list) == len(file_list), "Error: length of new_name_list, old_name_list, file_list should be the same"
    for new_name, old_name, itp_file in  zip(new_name_list,old_name_list,file_list):
        atoms_lines = read_itp_atoms(itp_file)
        atoms_record_list = [parse_line_atoms(i) for i in atoms_lines]
        for record in atoms_record_list:
            if record['type'] == old_name and (new_name, record['mass']) not in name_mass:
                name_mass.append((new_name, record['mass']))

    return name_mass


# read itp file and parse lines in [atom] section
def read_itp_atoms(itp_file:str)->list: # in order
    """
    read atoms block in itp file, return a list of atoms lines
    """
    with open(itp_file, 'r') as file:
        lines = file.readlines()
    in_atoms_block = False
    atoms_lines = []
    for line in lines:
        if '[ atoms ]' in line:
            in_atoms_block = True
        elif line.startswith('[') and in_atoms_block:
            in_atoms_block = False
        elif in_atoms_block:
            if line.strip() == '' or line.startswith(';'):
                pass
            else:
                atoms_lines.append(line)
        else:
            pass
    return atoms_lines

def parse_line_atoms(line:str)->dict:
    """
    parse a line in [ atomtypes ] block
    input:
        string line = '1    o     1   AAZ    O1    1    -0.585100     16.00000 ; qtot -0.585'
    output:
        dict{'nr': '1', 'type': 'o', 'resnr': '1', 'residue': 'AAZ', 'atom': 'O1', 'cgnr': '1', 'charge': '-0.585100', 'mass': '16.00000', 'comment': 'qtot -0.585'}
        
    """
    data, comment = split_line_atomtype(line)
    
    assert len(data) == 8, f"Error: \n >'{line}'\n is not a valid atoms line"
    return {'nr':data[0],
            'type':' '+data[1]+' ',
            'resnr':data[2],     
            'residue':data[3],  
            'atom':data[4],   
            'cgnr':data[5],   
            'charge':data[6],         
            'mass':data[7],
            'comment':comment,
            'raw_line':line
            }


def replace_itp_atomtype(itp_file:str, original_data_line:str,old_name:str, new_name:str):
    """
    write new *GMX.itp file with replaced atomtype name
    """
    with open(itp_file, 'r') as file:
        lines = file.readlines()
    with open(itp_file, 'w') as file:
        for line in lines:
            if line.startswith(original_data_line.strip()) or old_name in line:
                file.write(line.replace(old_name, new_name))
            else:
                file.write(line)



def int_to_3letter_code(num):
    import string
    # 46656 = 36^3
    # check if num is less than 46656
    if num >= 46656:
        raise ValueError("num should be less than 46656 (36*36*36)")
    letters = string.ascii_uppercase + string.digits
    return letters[num // (36*36)] + letters[(num // 36) % 36] + letters[num % 36]



if __name__ == "__main__":
    
    # 0. merge all atomtypes in *_GMX.itp files
    # input
    #   all *_GMX.itp files
    # output: 
    #   atomtypes_merge.itp file
    #   atomtypes_group_tuples.pickle file ; record atomtype info and which *_GMX.itp file it belongs
    #                                      ; dict{'atomtype_line': ['itp_file1', 'itp_file2', ...]}

    # 示例文件列表和输出文件名
    file_list = glob.glob("*_GMX.itp")
    output_file = 'atomtypes_merge.itp'
    # sorted_comments : list of comment lines ['; comments1 ',...]
    # sorted_data: list of atomtype lines ['C1    12    12.01100    0.000    A    3.399    0.077    0.000',...]
    # data_lines_dict: dict{'atomtype_line': ['itp_file1', 'itp_file2', ...]}
    sorted_comments, sorted_data, data_lines_dict=process_and_remove_atomtypes(file_list, output_file)
    
    import pickle
    with open('atomtypes_group_tuples.pickle', 'wb') as f:
        pickle.dump(data_lines_dict, f)

    # 1 rename atoms with same name but different sigma & epsilon
    replace_atomtype(sorted_comments,sorted_data,data_lines_dict)
