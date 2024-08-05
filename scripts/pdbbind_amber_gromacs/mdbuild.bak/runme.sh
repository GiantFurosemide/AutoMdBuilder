
my_work_root=$PWD
my_log=$my_work_root/runme.log

echo -e "[ $(date) ] start" > $my_log
cd $my_work_root
for i in structures/*;
do
    # copy data and scripts
    
    cp -v -r $i ./projects/

    tmp_dir=./projects/$(basename $i)
    cp -v scripts/*.py $tmp_dir
    cp -v scripts/*.sh $tmp_dir
    cp -v -r scripts/mdp $tmp_dir/
    
    # run the scripts
    cd $tmp_dir
    echo -e "[ $(date) $tmp_dir build start] " >> $my_log
    python runme.py
    echo -e "[ $(date) $tmp_dir build end] " >> $my_log
    
    echo -e "[ $(date) $tmp_dir processing start] " >> $my_log
    source mdbuild_add_multi_ligands.sh
    echo -e "[ $(date) $tmp_dir processing end] " >> $my_log
    
    cd $my_work_root
done
cd $my_work_root


#for i in projects/*;
#do
#    # run the scripts
#    cd $i
#    echo -e "[ $(date) $i processing start] " >> $my_log
#    source mdbuild_add_multi_ligands.sh
#    echo -e "[ $(date) $i processing end] " >> $my_log
#    cd $my_work_root
#done
#cd $my_work_root