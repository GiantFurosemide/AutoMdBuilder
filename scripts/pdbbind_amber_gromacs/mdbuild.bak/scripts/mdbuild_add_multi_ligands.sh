#!/bin/bash
#Author: Mu Wang 20230202 based on protocolgromacs
#Version: 1.0

# INPUT:
# ${ligand}_GMX.itp 
# ${ligand}_NEW.pdb   # copy ${ligand}_GMX.itp ${ligand}_NEW.pdb (from acpype) here 
# complex.pdb         # copy receptor + ligand.pdb  here and copy to myprotein.pdb, you should make sure ligand contains H
# mdp/                # a directory with mdp files for minimization\equilibruim\production base on protocolgromacs
# (this script)



#---------  FILE SETUP  -----------

log_file=$PWD/mdbuild_add_multi_ligands.log

#---------  SIMU SETUP  -----------
NUMBEROFREPLICAS=1
SIMULATIONTIME=0.2
NT=32
#  edit temperature directly in mdp file for equilibrium and production

#---------  HPC SETUP  -----------
MPI="" #If you have to submit jobs with MPI softwares like "mpirun -np 10". Add the command here
GMX=gmx #GMX command (can be "$GMX_mpi" sometimes. Just change it here
#THOSE COMMANDS 
#GPU0="-gpu_id 0 -ntmpi 1 -ntomp 20 -nb gpu -bonded gpu -pin on -pinstride 0 -nstlist 100 -pinoffset 49"
GPU1="-gpu_id 1 -ntmpi 1 -ntomp 20 -nb gpu -bonded gpu -pin on -pinstride 0 -nstlist 100 -pinoffset 0"
MDRUN_CPU="$GMX mdrun -nt $NT"
MDRUN_GPU="$GMX mdrun $GPU1"
NR_MAX_WARN=100
#-------- clean -----------
rm -rfv param
#rm -rfv complex.pdb
#rm -rfv topol.top
rm -rfv replica_*
echo -e "[ $(date) ] start" >> $log_file


#-------- STSTEM BUILDING --------


#-------- MINIMIZATION / EQUILIBRUIM / PRODUCTION / ANALYSIS -------
# for replicas
replica_work_dir=$PWD
for ((i=0; i<$NUMBEROFREPLICAS; i++))
	do 
	cd $replica_work_dir
	echo ">>>>> replica_"$((i+1))
	echo ">>>>> replica_"$((i+1))" start" >> $log_file
	mkdir "replica_"$((i+1))
	cd "replica_"$((i+1))
	echo -e "[ $(date) ] cd replica_$((i+1))" >> $log_file
	cp -R ../mdp .
	cp ../system.gro .
	cp ../system.top topol.top 
	


	#######################
	## MINIMISATION
	#######################
	echo -e "[ $(date) ] start minimization" >> $log_file
	$GMX grompp -f mdp/em.mdp -c system.gro -p topol.top -o em.tpr -maxwarn $NR_MAX_WARN
	$MPI $MDRUN_CPU -v -deffnm em 
	echo -e "[ $(date) ] end minimization" >> $log_file

	#Cleaning
	mkdir -p results/mini
	mkdir -p gro
	mkdir graph
	mv em* results/mini/
	mv mdout.mdp results/mini/
	mv *.gro gro/
	#potential energy graph
	$GMX energy -f results/mini/em.edr -o graph/mini_"$PDB"_pot.xvg << INPUT
Potential
INPUT

	#######################
	## temperature (300K by default)
	#######################
	echo -e "[ $(date) ] start temperature" >> $log_file
	$GMX grompp -f mdp/nvt_300.mdp -c results/mini/em.gro -r results/mini/em.gro  -p topol.top -o nvt_300.tpr -maxwarn $NR_MAX_WARN
	$MPI $MDRUN_GPU -deffnm nvt_300 -v 
	echo -e "[ $(date) ] end temperature" >> $log_file
	#temperature_graph

	#cleaning
	mkdir -p results/nvt
	mv nvt* results/nvt/ 2> /dev/null
	mv mdout.mdp results/nvt/

	#Temparture graph
	$GMX energy -f results/nvt/nvt_300.edr -o graph/temperature_nvt_300.xvg << INPUT
Temperature
INPUT

	#######################
	## Pression
	#######################
	echo -e "[ $(date) ] start pression" >> $log_file
	$GMX grompp -f mdp/npt.mdp -c results/nvt/nvt_300.gro -r results/nvt/nvt_300.gro -t results/nvt/nvt_300.cpt -p topol.top -o npt_ab.tpr -maxwarn $NR_MAX_WARN
	$MPI $MDRUN_GPU -deffnm npt_ab -v 
	echo -e "[ $(date) ] end pression" >> $log_file
	#cleaning
	mkdir -p results/npt
	mv npt* results/npt/ 2> /dev/null
	mv mdout.mdp results/npt_ab/
	#Pression and density graph
	$GMX energy -f results/npt/npt_ab.edr -o graph/npt_"$PDB"_pressure.xvg << INPUT
Pressure
INPUT
	$GMX energy -f results/npt/npt_ab.edr -o graph/npt_"$PDB"_volume.xvg << INPUT
Volume
INPUT
	$GMX energy -f results/npt/npt_ab.edr -o graph/npt_"$PDB"_potential.xvg << INPUT
Potential
INPUT

	#######################
	## Production 
	#######################
	
	#Setup simulationtime
if [ ! -z "$SIMULATIONTIME" ]
then
	python_command=$(python <<EOF
import re
restep = re.compile("nsteps *= *(\d*)")
redt = re.compile("dt *= *(\d*.\d*)")
dt = 0
simulationtime = float($SIMULATIONTIME) *1000 #Time in ps
outputLines = []
with open("mdp/md_prod.mdp",'r') as f:
    mdp = f.readlines()
    #find first the timestep
    for line in mdp: 
        dtmatch = redt.match(line)
        if dtmatch:
            dt = float(dtmatch.group(1))
            break
    for line in mdp:
        stepmatch = restep.match(line)
        if stepmatch and float(dt) > 0:
            nsteps = int(simulationtime)/dt
            line = "nsteps            = {}        ; {} * {} = {} ps or {} ns\n".format(int(nsteps),dt,nsteps, dt*nsteps, simulationtime/1000)
        outputLines.append(line)
    with open("mdp/md_prod.mdp",'w') as f:
        for line in outputLines:
            f.write(line)
EOF
)          
	echo -e "[ $(date) ] production start " >> $log_file
	$GMX grompp -f mdp/md_prod.mdp -c results/npt/npt_ab.gro -t results/npt/npt_ab.cpt -p topol.top -o "md_"$PDB"_prod.tpr" -maxwarn $NR_MAX_WARN
	$MPI $MDRUN_GPU -deffnm "md_"$PDB"_prod"  -v
	echo -e "[ $(date) ]  production end" >> $log_file
	mkdir -p results/prod
	mv md_* results/prod 2> /dev/null
	mv mdout.mdp results/prod/

	echo "backbone backbone" | $GMX rms -s "results/prod/md_"$PDB"_prod.tpr" -f "results/prod/md_"$PDB"_prod.trr" -o graph/prod_"$PDB"_rmsd.xvg -tu ns

	cd results/prod

	echo "Protein System" | $GMX trjconv -s "md_"$PDB"_prod.tpr" -f "md_"$PDB"_prod.trr" -o "md_"$PDB"_clean_temp.xtc" -pbc nojump -ur compact -center

	echo "Protein System" | $GMX trjconv -s "md_"$PDB"_prod.tpr" -f "md_"$PDB"_clean_temp.xtc" -o "md_"$PDB"_clean_full.xtc" -fit rot+trans

	echo "Protein non-Water" | $GMX trjconv -s "md_"$PDB"_prod.tpr" -f "md_"$PDB"_clean_temp.xtc" -o "md_"$PDB"_clean_nowat.xtc" -fit rot+trans

	echo "Protein non-Water" | $GMX trjconv -s "md_"$PDB"_prod.tpr" -f "md_"$PDB"_clean_temp.xtc" -o "md_"$PDB"_clean_nowat.pdb" -pbc nojump -ur compact -center -b 0 -e 0

	rm "md_"$PDB"_clean_temp.pdb"
	
	echo "non-Water" | $GMX convert-tpr -s "md_"$PDB"_prod.tpr" -o tpr_nowat.tpr
	
	# Create a smooth trajectory
	echo "Protein" | $GMX -s tpr_nowat.tpr -f "md_"$PDB"_clean_nowat.xtc" -ol "md_"$PDB"_clean_nowat_filtered.xtc" -all -fit



	cd ../../
	#Final graph
	echo "backbone backbone" | $GMX rms -s "results/prod/tpr_nowat.tpr" -f "results/prod/md_"$PDB"_clean_nowat.xtc" -o "graph/prod_"$PDB"_rmsd_ca.xvg" -tu ns
	echo "protein protein" | $GMX rms -s "results/prod/tpr_nowat.tpr" -f "results/prod/md_"$PDB"_clean_nowat.xtc" -o "graph/prod_"$PDB"_rmsd_all.xvg" -tu ns
	echo "backbone" | $GMX gyrate -s "results/prod/tpr_nowat.tpr" -f "results/prod/md_"$PDB"_clean_nowat.xtc" -o "graph/prod_"$PDB"_gyrate.xvg"

	echo "backbone" | $GMX rmsf -s "results/prod/tpr_nowat.tpr" -f "results/prod/md_"$PDB"_clean_nowat.xtc" -o "graph/prod_"$PDB"_rmsf_ref.xvg" -res
	
fi
cp topol.top ..
cd ..
done

# packing up results

source packup.sh

