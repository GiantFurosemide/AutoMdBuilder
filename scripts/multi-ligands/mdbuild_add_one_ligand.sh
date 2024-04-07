#!/bin/bash
#Author: Mu Wang 20230202 based on protocolgromacs
#Version: 1.0

# this script is only for One ligand
# INPUT:
# ${ligand}_GMX.itp 
# ${ligand}_NEW.pdb   # copy ${ligand}_GMX.itp ${ligand}_NEW.pdb (from acpype) here 
# complex.pdb         # copy receptor + ligand.pdb  here and copy to myprotein.pdb, you should make sure ligand contains H
# mdp/                # a directory with mdp files for minimization\equilibruim\production base on protocolgromacs
# (this script)

#activate acpype environment
conda activate acpype

#---------  FILE SETUP  -----------

# protein 
#PDB FILE, will be replace in the code later by $PDB (default is "complex")
FILE="myprotein" #<<<<<<<<<<<<<<<<<<<<<<<<< PUT THE PDB NAME HERE (without the extension)

# ligand
# LIGAND NAME, if you have a ligand, it will be parametrize with acpype and the ligand name will be replace by "LIG".
LIGNAME="FTY" #<<<<<<<<<<<<<<<<<<<<<<  #PUT LIGAND NAME HERE, leave it blank if no ligand.
LIGAND_LETTER='UNL' # 3-letter name in PDB files
LIGAND_LETTER_OUT=$LIGAND_LETTER # 3-letter name in out pdb file form ligand extraction of original PDB file for topology buildin by acpype  
								 # Should be same asLIGAND_LETTER in ligand_NEW.pdb
LIG_NUMBER=1

#---------  SIMU SETUP  -----------
BOXSIZE=6.0 #cubic simulation boxsiwe
BOXTYPE=cubic #Box type
NT=36 #Number of core.
WATER=tip3p #Water type
NUMBEROFREPLICAS=2 #Number of replica
FF=amber99sb-ildn #Force field
SIMULATIONTIME=3000 #Simulation time in nanosec. Will be converted in fs and modified in the mdp file.
					#If you do not need production, keep SIMULATIONTIME empty.
NACL_CONC=0.15
#  edit temperature directly in mdp file for equilibrium and production

#---------  HPC SETUP  -----------
MPI="" #If you have to submit jobs with MPI softwares like "mpirun -np 10". Add the command here
GMX=gmx #GMX command (can be "$GMX_mpi" sometimes. Just change it here
#THOSE COMMANDS 
GPU0="-gpu_id 0 -ntmpi 1 -ntomp 20 -nb gpu -bonded gpu -pin on -pinstride 0 -nstlist 100 -pinoffset 49"
GPU1="-gpu_id 1 -ntmpi 1 -ntomp 20 -nb gpu -bonded gpu -pin on -pinstride 0 -nstlist 100 -pinoffset 0"
MDRUN_CPU="$GMX mdrun -nt $NT"
MDRUN_GPU="$GMX mdrun $GPU1"
NR_MAX_WARN=20


#-------- STSTEM BUILDING --------

# make a directory 'param' for toppology files generation
mkdir param
cp $FILE".pdb" param/
cd param
# extract protein from pdb file
# just because mdanalysis ligand dose not begin with HETOM, with ATOM instead
grep 'ATOM ' "${FILE}.pdb" --color=none > receptor2.pdb
grep -v $LIGAND_LETTER receptor2.pdb > receptor.pdb
rm -rfv receptor2.pdb

### get ligand top for first ligand (delete)

# ligand 
# solution
# 1. cp ligand.pdb generated by acpype to here
# 2. cp ligand.acpype to param 
# 3. just cp ${LIGNAME}_NEW.pdb and  ${LIGNAME}_GMX.itp HERE ( use this )

### ERROR OCCUR WHEN PDB include more than One ligands. Because all atom will be treat as ONE molecular
##Extract ligand and connect
#      python_command=$(python <<EOF
#ligand_atom = []
#keepLine = []
#with open("$FILE.pdb","r") as file:
#    lines = file.readlines()
#    for line in lines:
#        if '$LIGAND_LETTER' in line[17:20]:
#            line = line[:17]+"${LIGAND_LETTER_OUT}"+line[20:]
#            keepLine.append(line)
#            ligand_atom.append(int(line[6:11]))
#        elif "CONECT" in line[0:6]:
#            idx = [int(x) for x in line.split()[1:]]
#            if any(id in idx for id in ligand_atom):
#                keepLine.append(line)
#with open("${LIGNAME}.pdb","w") as file:
#    for line in keepLine:
#        file.write(line)
#EOF
#)
    #Convert in mol2 while adding hydrogens.
    #obabel -ipdb ligand.pdb -omol2 -h > ligand.mol2
	#obabel -ipdb ${LIGNAME}.pdb -h -omol  -O ${LIGNAME}.sdf

    #use ACPYPE to create the ligand topology.
    #DISCLAMER! This is a "quick and dirty method", it has to be optimised with ACPYPE parameters of course and adapted to ligands
    #if you see strange MD behaviours.
    # You may also consider Automated Topology Builder (ATB) (webserver) Or LibParGen (webserver & standalone tools)
    #acpype -i ${LIGNAME}.sdf
    #mkdir ${LIGNAME}
    #mv ${LIGNAME}* ${LIGNAME}/
### get ligand top for first ligand ### END

# make directory for repector (protein)'s topology files genenration 
mkdir receptor
mv receptor.pdb receptor/
cd receptor

$GMX pdb2gmx -f receptor.pdb -o receptor_GMX.pdb -water $WATER -ignh -ff $FF
cd ../../
cp param/receptor/*.itp param/receptor/topol.top param/receptor/receptor_GMX.pdb .

###########################
# mannual add topol ligand 
###########################

# add '#include ligand.itp' to topol.top
cp topol.top topol.bak
cat topol.top | sed "/forcefield\.itp\"/a\
  #include \"${LIGNAME}_GMX.itp\"" > topol2.top
mv topol2.top topol.top
# add ligand info to [ system ] block in topol.top
echo "${LIGNAME}   ${LIG_NUMBER}" >> topol.top

# make position restraint for ligand
ndx=$($GMX make_ndx -f ${LIGNAME}_NEW.pdb -o ${LIGNAME}_lig_noh.ndx <<EOF
"r ${LIGAND_LETTER_OUT} & !a H*
name 3 LIG-H
q"
EOF
)	
echo "LIG-H" | $GMX genrestr -f ${LIGNAME}_NEW.pdb -o ${LIGNAME}_posre_ligand.itp -n ${LIGNAME}_lig_noh.ndx -fc 1000 1000 1000

# add position restraint to ligand.itp
echo "
        
; Include Position restraint file
#ifdef POSRES
#include \"${LIGNAME}_posre_ligand.itp\"
#endif"  >> ${LIGNAME}_GMX.itp

# extract coordination of ligands from original pdb file, then merge receptor and ligand to complex.pdb 
# for "swimming" system, ligands coodination is from acpype (ligand_NEW.pdb)
# therefore compatible with ligand_GMX.itp
grep "$LIGAND_LETTER" myprotein.pdb > all-ligand.pdb  # you should make sure all-ligand.pdb contains H
# sed -i 's/HETATM/ATOM  /g' all-ligand.pdb
grep -h ATOM receptor_GMX.pdb all-ligand.pdb > complex.pdb

######################
## set box size; add water
###################### 
$GMX editconf -f  complex.pdb -o complex_newbox.gro -box $BOXSIZE -bt $BOXTYPE
PDB=complex
$GMX solvate -cp $PDB"_newbox.gro" -cs spc216.gro -o "${PDB}_solv.gro" -p topol.top

#######################
## ADDING IONS
#######################
$GMX grompp -f mdp/ions.mdp -c $PDB"_solv.gro" -p topol.top -o ions.tpr -maxwarn $NR_MAX_WARN
echo "SOL" | $GMX genion -s ions.tpr -o $PDB"_solv_ions.gro" -p topol.top -pname NA -nname CL  -conc $NACL_CONC -neutral 


#-------- MINIMIZATION / EQUILIBRUIM / PRODUCTION / ANALYSIS -------
# for replicas
for ((i=0; i<$NUMBEROFREPLICAS; i++))
	do 
	echo ">>>>> replica_"$((i+1))
	mkdir "replica_"$((i+1))
	cd "replica_"$((i+1))
	cp -R ../mdp .
	cp ../$PDB"_solv_ions.gro" .
	cp ../topol.top .
	cp ../*.itp .


	#######################
	## MINIMISATION
	#######################
	$GMX grompp -f mdp/em.mdp -c $PDB"_solv_ions.gro" -p topol.top -o em.tpr -maxwarn $NR_MAX_WARN
	$MPI $MDRUN_CPU -v -deffnm em 


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
	$GMX grompp -f mdp/nvt_300.mdp -c results/mini/em.gro -r results/mini/em.gro  -p topol.top -o nvt_300.tpr -maxwarn $NR_MAX_WARN
	$MPI $MDRUN_GPU -deffnm nvt_300 -v 
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
	$GMX grompp -f mdp/npt.mdp -c results/nvt/nvt_300.gro -r results/nvt/nvt_300.gro -t results/nvt/nvt_300.cpt -p topol.top -o npt_ab.tpr -maxwarn $NR_MAX_WARN
	$MPI $MDRUN_GPU -deffnm npt_ab -v 

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

	$GMX grompp -f mdp/md_prod.mdp -c results/npt/npt_ab.gro -t results/npt/npt_ab.cpt -p topol.top -o "md_"$PDB"_prod.tpr" -maxwarn $NR_MAX_WARN
	$MPI $MDRUN_GPU -deffnm "md_"$PDB"_prod"  -v

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


	#####
	# TESTING DSSP Installation
	#####
	export DSSP=`which dssp`
	if [ -z "$DSSP" ]
	then
	      export DSSP=`which mkdssp`
	else
		echo "DSSP found. Good!"
	fi

	if [ -z "$DSSP" ]
	then
	      echo "DSSP SOFTWARE NOT FOUND. If you have anaconda or miniconda install, please install it with this command line:"
		  echo "conda install -c conda-forge -c salilab dssp"
		  echo "note that the name will be mkdssp"
		  echo "Trying to install it right now..."
		  conda install -y -c conda-forge -c salilab dssp
		  export DSSP=`which mkdssp`
		if [ -z "$DSSP" ]
			then
			      echo "Installation faillure..."
			else
				echo "1" |  $GMX do_dssp -s "results/prod/tpr_nowat.tpr" -f "results/prod/md_"$PDB"_clean_nowat.xtc" -o "graph/prod_"$PDB"_ss.xpm" -tu ns -dt 0.05 -ver 3
				$GMX xpm2ps -f "graph/prod_"$PDB"_ss.xpm" -o "graph/prod_"$PDB"_ss.ps" -by 10 -bx 3
			fi
	else
		echo "Protein" | $GMX do_dssp -s "results/prod/tpr_nowat.tpr" -f "results/prod/md_"$PDB"_clean_nowat.xtc" -o "graph/prod_"$PDB"_ss.xpm" -ver 3 -tu ns -dt 0.05
		$GMX xpm2ps -f "graph/prod_"$PDB"_ss.xpm" -o "graph/prod_"$PDB"_ss.ps" -by 10 -bx 3
	fi

	
fi
cd ..
done
conda deactivate