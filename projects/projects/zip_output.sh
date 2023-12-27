#!/bin/bash

# 获取当前工作目录
work_dir=$(pwd)

# 遍历所有文件夹
for folder in $work_dir/*; do
  if [ -d "$folder" ]; then
    # 在每个文件夹中查找以protocolgromacs_开头的子文件夹
    protocolgromacs_folders=("$folder"/protocolgromacs_*eqout*)
    
    if [ ${#protocolgromacs_folders[@]} -gt 0 ]; then
      # 获取文件夹的名称（不包含路径）
      folder_name=$(basename "$folder")
      
      # 遍历protocolgromacs子文件夹
      for protocolgromacs_folder in "${protocolgromacs_folders[@]}"; do
        # 创建新的子文件夹，以原文件夹的名称命名
        new_folder="$folder/$folder_name"
        mkdir "$new_folder"
        
        # 获取protocolgromacs子文件夹中的文件数量
        file_count=$(ls -1 "$protocolgromacs_folder" | wc -l)
        
        # 判断protocolgromacs子文件夹中是否有且仅有两个文件
        if [ "$file_count" -eq 2 ]; then
          # 复制protocolgromacs子文件夹中的两个文件到新的子文件夹
          cp -r "$protocolgromacs_folder" "$new_folder"
          
          # 打包新的子文件夹为.zip文件
          cd $folder
          zip -r "$folder_name.zip" "$folder_name"
          cd - 
          
          echo "处理完成: $protocolgromacs_folder"
        else
          echo "警告: $protocolgromacs_folder 中文件数量不是两个，跳过处理"
        fi
      done
    fi
  fi
done

echo "脚本执行完毕"
