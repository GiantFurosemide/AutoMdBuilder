## usage ##
# 1.check pdb files and move them into ROOT/projects/structures
# 2.cd to ROOT/projects, make sure this script is in ROOT/projects and zip_output.sh is in ROOT/projects/projects
# 3.run this script
## usage ##


# check .pdb files in the projects/strucutres/ directory, then build new directories for each .pdb file in projects/projects directory
# then copy scripts/protocolgromacs_001 to each new directory
# then copy .pdb file to protocolgromacs_001 in each new directory, and rename it to myprotein.pdb after copying and saving the original file name as a backup.
workdir=$(pwd)
protocolgromacs_RUN=protocolgromacs_001 # the name of the script to run. in $ROOT/scripts
log_file=${workdir}/runme.log

# check if the log file exists, if not, create it

if [ ! -f $log_file ]; then
    touch $log_file
fi

# initialize the projects directory
cd $workdir
for file in structures/*.pdb; do
    filename=$(basename $file)
    filename="${filename%.*}"
    mkdir -p projects/$filename
    cp -rv ../scripts/$protocolgromacs_RUN projects/$filename
    cp -rv structures/$filename.pdb projects/$filename/$protocolgromacs_RUN/myprotein.pdb
    cp -rv structures/$filename.pdb projects/$filename/$protocolgromacs_RUN/$filename.pdb
done

# then run the protocolgromacs_001 script runGromacs.sh in each new directory
cd $workdir
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
    cd $workdir
done

cd projects
source zip_output.sh
cd $workdir