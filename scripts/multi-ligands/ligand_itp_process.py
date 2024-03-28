"""
Extract [ atomtypes ] blocks from *_GMX.itp file and remove duplicates and save to atomtypes_merge.itp 

input: *_GMX.itp
output: *_GMX.itp(removed [ atomtypes ]), atomtypes_merge.itp 
"""
import glob

def process_and_remove_atomtypes(file_list, output_file):
    atomtypes_header = '[ atomtypes ]\n'
    comment_lines = set()
    data_lines = set()

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
                    file_content.append(line)  # 保留下一个区块的开始行
                elif in_atomtypes_block:
                    # 根据行的内容分类存储
                    if line.strip() == '' or line.startswith(';'):
                        if line.startswith(';'):
                            comment_lines.add(line)
                    else:
                        data_lines.add(line)
                else:
                    file_content.append(line)

        # 重写文件，移除 [ atomtypes ] 区块
        with open(file_name, 'w') as file:
            file.writelines(file_content)

    # 排序注释和数据行
    sorted_comments = sorted(list(comment_lines))
    sorted_data = sorted(list(data_lines))

    # 写入输出文件
    with open(output_file, 'w') as merge_file:
        merge_file.write(atomtypes_header)  # 写入头部
        for comment in sorted_comments:
            merge_file.write(comment)
        for data_line in sorted_data:
            merge_file.write(data_line)
        merge_file.write('\n')  # 文件末尾添加一个空行

# 示例文件列表和输出文件名
file_list = glob.glob("*_GMX.itp")
output_file = 'atomtypes_merge.itp'
process_and_remove_atomtypes(file_list, output_file)