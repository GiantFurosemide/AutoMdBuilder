LIGAND_LETTER_LIST=(
	"UNL"
)


for my_ligname_letter in ${LIGAND_LETTER_LIST[@]};
do 
    grep -v $my_ligname_letter receptor_tmp.pdb > receptor_tmp2.pdb
    rm -rfv receptor_tmp.pdb
    mv receptor_tmp2.pdb receptor_tmp.pdb
done;
mv receptor_tmp.pdb receptor.pdb    
    
    