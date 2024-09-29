######################################

echo -e "run in rosetta mpi docker"
echo -e "usage: "
echo -e " cp this script to pdb files dir"
echo -e " source runme_fastrelex.sh"

# number of output s
NSTRCTS=1
ROSETTA_OUT_PDB_DIR='rosetta_out_pdb'
ROSETTA_MY_LOG='rosetta.log'
######################################
mkdir $ROSETTA_OUT_PDB_DIR

cat > fast_relax.xml <<EOF

<ROSETTASCRIPTS>
    <SCOREFXNS>
        <ScoreFunction name="ref15" weights="ref2015"/>
    </SCOREFXNS>
    <MOVERS>
        <FastRelax name="fast_relax" scorefxn="ref15" repeats="5"/>
    </MOVERS>
    <PROTOCOLS>
        <Add mover="fast_relax"/>
    </PROTOCOLS>
    <OUTPUT scorefxn="ref15"/>
</ROSETTASCRIPTS>


EOF



function rosetta_fastrelax(){
	mpirun -n 32 --use-hwthread-cpus --allow-run-as-root rosetta_scripts -s $1 -parser:protocol fast_relax.xml -nstruct $NSTRCTS -out:pdb  -out:path:pdb $ROSETTA_OUT_PDB_DIR >> $ROSETTA_MY_LOG
}

for i in ./*.pdb;
do
	echo -e "[$(date)] start processing -> $i"
	rosetta_fastrelax $i
	echo -e "[$(date)] end processing -> $i"
done