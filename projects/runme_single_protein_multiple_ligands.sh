## usage ##
# 0.update mdp files in ROOT/projects/scripts/protocolgromacs_multiple_ligands/mdp
# 1.check data and scripts files and move them into ROOT/projects/structures/case1, case2, case3, etc.
# 2.cd to ROOT/projects, make sure this script is in ROOT/projects 
# 3.run this script
## usage ##


# check .pdb files in the projects/strucutres/ directory, then build new directories for each .pdb file in projects/projects directory
# then copy scripts/protocolgromacs_001 to each new directory
# then copy .pdb file to protocolgromacs_001 in each new directory, and rename it to myprotein.pdb after copying and saving the original file name as a backup.
workdir=$(pwd)  # AutoMDbuilder/projects/
protocolgromacs_RUN=protocolgromacs_multiple_ligands # the name of the script to run. in $ROOT/scripts
log_file=${workdir}/runme.log

# check if the log file exists, if not, create it

if [ ! -f $log_file ]; then
    touch $log_file
fi

# initialize the projects directory
cd $workdir # AutoMDbuilder/projects/
for data_dir in structures/*; do
    data_dir_name=$(basename $data_dir)
    #filename="${filename%.*}"
    mkdir -p projects/$data_dir_name
    cp -rv ../scripts/$protocolgromacs_RUN projects/$data_dir_name
    # complex.pdb ligand_GMX.tip ligand_NEW.pdb
    cp -rv $data_dir/* projects/$data_dir_name/$protocolgromacs_RUN/
    for pdb_file in $data_dir/*.pdb;
    do
        cp -v $pdb_file projects/$data_dir_name/$protocolgromacs_RUN/myprotein.pdb
    done;
done;

# then run the protocolgromacs_001 script runGromacs.sh in each new directory
cd $workdir # AutoMDbuilder/projects/
for file in structures/*.pdb; do
    filename=$(basename $file)
    filename="${filename%.*}"
    cd projects/$filename/$protocolgromacs_RUN
    source ./runGromacs.sh

    # copy the results gro to eqout directory
    for dir in replica*; do
        gmx grompp -c $dir/results/npt/npt_ab.gro -f mdp/md_prod.mdp -p topol.top -pp processed.top
        mkdir -p ${PWD}_eqout_${dir}
        cp -rv $dir/results/npt/npt_ab.gro ${PWD}_eqout_${dir} && cp -rv processed.top ${PWD}_eqout_${dir} 
    done
    # copy the processed.top to the eqout directory
    for dir in replica*; do
        cp -rv processed.top ${PWD}_eqout_${dir} 
    done
    cd $workdir # AutoMDbuilder/projects/
done

cd $workdir # AutoMDbuilder/projects/
for data_dir in structures/*; do
    data_dir_name=$(basename $data_dir)
    cd projects/$data_dir_name/$protocolgromacs_RUN
    cp -rv ../$workdir/scripts/packup.sh .  # will be used in mdbuild_add_multi_ligands.sh
    python ligand_info_prepare.py
    source mdbuild_add_multi_ligands.sh
    #source ./runGromacs.sh

    ## copy the results gro to eqout directory
    #for dir in replica*; do
    #    gmx grompp -c $dir/results/npt/npt_ab.gro -f mdp/md_prod.mdp -p topol.top -pp processed.top
    #    mkdir -p ${PWD}_eqout_${dir}
    #    cp -rv $dir/results/npt/npt_ab.gro ${PWD}_eqout_${dir} && cp -rv processed.top ${PWD}_eqout_${dir} 
    #done
    ## copy the processed.top to the eqout directory
    #for dir in replica*; do
    #    cp -rv processed.top ${PWD}_eqout_${dir} 
    #done
done

#cd projects
#source zip_output.sh
cd $workdir