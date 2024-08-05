import os
from glob import glob

from pdbfixer import PDBFixer
from openmm.app import PDBFile


from openmm.app import *
from openmm import *
from openmm.unit import *
from sys import stdout


# in/out file
file_in_pdb = "/media/muwang/新加卷/muwang/database/PDBBIND_PLUS/v2020/PDBbind_v2020_refined/refined-set/1bju/1bju_protein.pdb"
out_dir = 'processed_pdb/refined_set'
# out_dir = 'processed_pdb/other_PL'
file_out_pdb = os.path.join(out_dir, os.path.basename(file_in_pdb).replace('.pdb', '_processed.pdb'))

# prcessing by pdbfixer

def pdbfixer_processor(file_in_pdb,file_out_pdb,chain_id_keep_start=1,ph=7.0):
    """
    process pdb file by pdbfixer, ONLY KEEP 1ST CHAIN.
    add missing residues, atoms, hydrogens, remove heterogens, nonstandard residues
    output file is a pdb file, only keep protein


    :param file_in_pdb: str, input pdb file
    :param file_out_pdb: str, output pdb file
    :param chain_id_keep_start: int, the chain id start to remove, default is 1,means keep 1st chain('chain 0')
    """
    try:
        fixer = PDBFixer(filename=file_in_pdb)
        fixer.findMissingResidues()
        fixer.findNonstandardResidues()
        fixer.replaceNonstandardResidues()
        fixer.removeHeterogens(True)
        fixer.findMissingAtoms()
        fixer.addMissingAtoms()
        fixer.addMissingHydrogens(ph)
#        numChains = len(list(fixer.topology.chains()))
#        if numChains > chain_id_keep_start:
#            fixer.removeChains(range(chain_id_keep_start, numChains))

        
        # fixer.addSolvent(fixer.topology.getUnitCellDimensions())
        PDBFile.writeFile(fixer.topology, fixer.positions, open(file_out_pdb , 'w'))
        print(f'Processing {file_in_pdb} done!')
        print(f'Output file is {file_out_pdb}')
    except Exception as e:
        print(f'Error: {e}')
        print(f'Error in processing {file_in_pdb}')
        return False
    else:
        return True

def pdbfixer_processor_first_chain(file_in_pdb,file_out_pdb,chain_id_keep_start=1,ph=7.0):
    """
    process pdb file by pdbfixer, ONLY KEEP 1ST CHAIN.
    add missing residues, atoms, hydrogens, remove heterogens, nonstandard residues
    output file is a pdb file, only keep protein


    :param file_in_pdb: str, input pdb file
    :param file_out_pdb: str, output pdb file
    :param chain_id_keep_start: int, the chain id start to remove, default is 1,means keep 1st chain('chain 0')
    """
    try:
        fixer = PDBFixer(filename=file_in_pdb)
        fixer.findMissingResidues()
        fixer.findNonstandardResidues()
        fixer.replaceNonstandardResidues()
        fixer.removeHeterogens(True)
        fixer.findMissingAtoms()
        fixer.addMissingAtoms()
        fixer.addMissingHydrogens(ph)
        numChains = len(list(fixer.topology.chains()))
        if numChains > chain_id_keep_start:
            fixer.removeChains(range(chain_id_keep_start, numChains))

        
        # fixer.addSolvent(fixer.topology.getUnitCellDimensions())
        PDBFile.writeFile(fixer.topology, fixer.positions, open(file_out_pdb , 'w'))
        print(f'Processing {file_in_pdb} done!')
        print(f'Output file is {file_out_pdb}')
    except Exception as e:
        print(f'Error: {e}')
        print(f'Error in processing {file_in_pdb}')
        return False
    else:
        return True
    
def pdbfixer_processor_for_system(file_in_pdb,
                                  file_out_pdb,
                                  ph=7.0,
                                  boxSize=10,  # nm
                                  #water_model='tip3p',
                                  positiveIon='Na+',
                                  negativeIon='Cl-',
                                  ionicStrength=0.15,  # Molar
                                  ):
    """
    process pdb file by pdbfixer, only keep 1st chain
    output file is a system pdb file, with solvent, ions, etc.
    :param file_in_pdb: str, input pdb file
    :param file_out_pdb: str, output pdb file
    :param chain_id_keep_start: int, the chain id start to remove, default is 1,means keep 1st chain('chain 0')
    """
    try:

        fixer = PDBFixer(filename=file_in_pdb)
        fixer.findMissingResidues()
        fixer.findNonstandardResidues()
        fixer.replaceNonstandardResidues()
        fixer.removeHeterogens(True)
        fixer.findMissingAtoms()
        fixer.addMissingAtoms()
        fixer.addMissingHydrogens(ph)
        fixer.addSolvent(boxSize=Vec3(boxSize,boxSize,boxSize)*unit.nanometers, 
                    #model=water_model,
                    positiveIon=positiveIon,
                    negativeIon=negativeIon,
                    ionicStrength=ionicStrength*unit.molar,)
        PDBFile.writeFile(fixer.topology, fixer.positions, open(file_out_pdb , 'w'))
        print(f'Processing {file_in_pdb} done!')
        print(f'Output file is {file_out_pdb}')
    except Exception as e:
        print(f'Error: {e}')
        print(f'Error in processing {file_in_pdb}')
        return False
    else:
        return fixer
    
if __name__ == '__main__':

    #file_in_pdb = "/media/muwang/新加卷/muwang/database/PDBBIND_PLUS/v2020/PDBbind_v2020_refined/refined-set/1bju/1bju_protein.pdb"
    #out_dir = 'processed_pdb/refined_set'
    #out_dir = 'processed_pdb/other_PL'
    #file_out_pdb = os.path.join(out_dir, os.path.basename(file_in_pdb).replace('.pdb', '_processed.pdb'))
    #pdbfixer_processor(file_in_pdb,file_out_pdb,chain_id_keep_start=1,ph=7.0)

    #file_out_pdb = os.path.join(out_dir, os.path.basename(file_in_pdb).replace('.pdb', '_processed_system.pdb'))
    #fixer=pdbfixer_processer_for_system(file_in_pdb=file_in_pdb,file_out_pdb=file_out_pdb,boxSize=10)  # nm

    import datetime

    for pdb_file in glob("v2020/PDBbind_v2020_refined/refined-set/????/*_protein.pdb"):
        out_dir = 'processed_pdb/refined_set'
        file_out_pdb = os.path.join(out_dir, os.path.basename(pdb_file).replace('.pdb', '_processed.pdb'))
        
        if os.path.exists(file_out_pdb):
            print(f"{datetime.datetime.now()} Processing {file_out_pdb} done!")
            continue
        
        pdbfixer_processor(pdb_file,file_out_pdb,chain_id_keep_start=1,ph=7.0)
        print(f"{datetime.datetime.now()} Processing {file_out_pdb} done!")
    
    for pdb_file in glob('v2020/PDBbind_v2020_other_PL/v2020-other-PL/????/*_protein.pdb'):
        out_dir = 'processed_pdb/other_PL'
        file_out_pdb = os.path.join(out_dir, os.path.basename(pdb_file).replace('.pdb', '_processed.pdb'))
        
        if os.path.exists(file_out_pdb):
            print(f"{datetime.datetime.now()} Processing {file_out_pdb} done!")
            continue
        
        pdbfixer_processor(pdb_file,file_out_pdb,chain_id_keep_start=1,ph=7.0)
        print(f"{datetime.datetime.now()} Processing {file_out_pdb} done!")