

# copy the results gro to eqout directory
for dir in replica*; do
    gmx grompp -c $dir/results/npt/npt_ab.gro -f mdp/md_prod.mdp -p topol.top -pp processed.top
    mkdir -p ${PWD}_eqout_${dir}
    cp -rv $dir/results/npt/npt_ab.gro ${PWD}_eqout_${dir} ; cp -rv processed.top ${PWD}_eqout_${dir}/processed.itp 
    
    file_count=$(ls -1 "${PWD}_eqout_${dir}" | wc -l)
    if [ "$file_count" -eq 2 ]; 
    then 
        echo "处理完成: ${PWD}_eqout_${dir}"
    else

        echo "警告: ${PWD}_eqout_${dir} 中文件数量不是两个，跳过处理"
        rm -rfv ${PWD}_eqout_${dir}

    fi

done

