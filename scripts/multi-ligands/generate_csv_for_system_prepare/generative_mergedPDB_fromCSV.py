"""
One atom group (B_structure, ex. protein or a protein with several ligand) will be placed at the center of the box. 
another atom group (A_structure, ex. small molecules or another protein) will be randomly placed inside the box,
without overlapping with B_structure within 5 angstroms(default), 
and the multiple small molecules of A_structure will not overlap within 3.5 angstroms(default).
"""

import MDAnalysis as mda
import numpy as np
from scipy.spatial.distance import cdist
import os


def update_thresholds_by_ligand(ligand_coord, threshold1, threshold2):
    distance = cdist(ligand_coord, ligand_coord)
    max_distance = np.max(distance)
    assert max_distance >= 0
    return threshold1 + max_distance, threshold2 + max_distance


def get_coordinates_with_distances_greater_than_threshold(listA, listB, threshold):
    """
    get coordinates in array A with the distances ( with array B ) greater than threshold

    :param listA:
    :param listB:
    :param threshold:
    :return: list of coordinates in array A with the distances ( with array B ) greater than threshold
    """
    # 将listA和listB中的numpy arrays合并为单个数组，以便使用cdist计算距离
    arrayA = np.vstack(listA)
    arrayB = np.vstack(listB)

    # 计算所有listA中的坐标到所有listB中的坐标的距离矩阵
    distances = cdist(arrayA, arrayB)

    # 找到距离大于阈值的坐标索引
    indices = np.where(np.all(distances > threshold, axis=1))

    assert np.min(distances[indices]) > threshold, f"error in get_coordinates_with_distances_greater_than_threshold, min distance should be greater than threshold '{threshold}', but got {np.min(distances[indices])}"

    # 获取距离大于阈值的坐标
    coordinates_with_distances_greater_than_threshold = arrayA[indices]
    return coordinates_with_distances_greater_than_threshold


def generate_random_coordinates(num_coordinates, box_size=10.0): # box_size in ns
    # 生成num_coordinates个随机坐标，范围在[0, 1)
    return (np.random.rand(num_coordinates, 3) - 0.5) * box_size


def process_lists(listC, listB, threshold1=5.0, threshold2=3.5, box_size=10.0):
    """

    :param listC: randomized coordinates of the geometric center of A ligands
    :param listB: coordinates of all atoms of B protein
    :param threshold1: the minimum distance between ligand（listC）and protein（listB）
    :param threshold2: the minimum distance between ligands in listC
    :return: filtered randomized coordinates of the geometric center of A ligands
    """

    listD = get_coordinates_with_distances_greater_than_threshold(listC, listB, threshold1)
    while len(listC) > len(listD):
        # 生成需要补充的随机坐标个数
        num_random_coordinates = len(listC) - len(listD)
        # 生成随机坐标
        listE = generate_random_coordinates(num_random_coordinates, box_size)

        # 用listC中的坐标与listB进行新一轮的距离比较
        listF = get_coordinates_with_distances_greater_than_threshold(listE, listB, threshold1)
        if len(listF) == 0:
            print(f"should generate new random coordinates, because no coordinates in listF, listE = {listE}")
            continue
        # 用listF中的坐标与listD进行新一轮的距离比较，得到合并后的新listD
        listG = get_coordinates_with_distances_greater_than_threshold(listF, listD, threshold2)
        if len(listG) == 0:
            print(f"should generate new random coordinates, because no coordinates in listG, listF = {listF}")
            continue
        listD = np.vstack((listD, listG))

        print(f"len listD = {len(listD)}")

    return listD


def translate_atoms(atom_coords, translation_vector):
    """
    Translate atomic coordinates by a translation vector.

    Args:
    atom_coords (numpy.ndarray): Array of shape (N, 3) representing atomic coordinates.
    translation_vector (numpy.ndarray): 1D array representing the translation vector.

    Returns:
    numpy.ndarray: Translated atomic coordinates.

    Example usage:
     atom_coords = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
     translation_vector = np.array([1, 1, 1])

     translated_coords = translate_atoms(atom_coords, translation_vector)

     print("Translated coordinates:")
     print(translated_coords)

    """
    translated_coords = atom_coords + translation_vector
    return translated_coords


def rotate_atoms(atom_coords, euler_angles):
    """
    Rotate atomic coordinates by Euler angles.

    Args:
    atom_coords (numpy.ndarray): Array of shape (N, 3) representing atomic coordinates.
    euler_angles (numpy.ndarray): Array of shape (3,) representing Euler angles in radians.

    Returns:
    numpy.ndarray: Rotated atomic coordinates.

    Example usage:
     atom_coords = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
     euler_angles = np.array([np.pi/4, np.pi/3, np.pi/6])

     rotated_coords = rotate_atoms(atom_coords, euler_angles)

     print("\nRotated coordinates:")
     print(rotated_coords)
    """
    # Construct rotation matrix from Euler angles
    alpha, beta, gamma = euler_angles
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(alpha), -np.sin(alpha)],
                    [0, np.sin(alpha), np.cos(alpha)]])
    R_y = np.array([[np.cos(beta), 0, np.sin(beta)],
                    [0, 1, 0],
                    [-np.sin(beta), 0, np.cos(beta)]])
    R_z = np.array([[np.cos(gamma), -np.sin(gamma), 0],
                    [np.sin(gamma), np.cos(gamma), 0],
                    [0, 0, 1]])

    # Combined rotation matrix
    R = np.dot(R_z, np.dot(R_y, R_x))

    # Rotate atomic coordinates
    rotated_coords = np.dot(atom_coords, R.T)
    return rotated_coords


def generate_merge(config_dict):

    # step 0: set output path

    ligand_pdb = config_dict["ligand_pdb"]
    input_pdb = config_dict["input_pdb"]
    output_pdb = config_dict["output_pdb"]
    segid = config_dict["segid"]

    # Step 1: Load A.pdb and B.pdb
    A_structure = mda.Universe(ligand_pdb)
    B_structure = mda.Universe(input_pdb)

    # Step 2: Define the box dimensions
    box_size = config_dict["box_size"]  # Angstroms

    # Step 3: Randomly position the 10 A proteins
    num_A_proteins = config_dict["num_A_proteins"]  # 936 94 10 20 50 (4 for PP1;10 for dasatinib)
    assert num_A_proteins > 0, "num_A_proteins should be greater than 0"
    THRESHOLD1 = config_dict["THRESHOLD1"]
    THRESHOLD2 = config_dict["THRESHOLD2"]

    THRESHOLD1, THRESHOLD2 = update_thresholds_by_ligand(A_structure.atoms.positions, THRESHOLD1, THRESHOLD2)
    print(f"threshold1, threshold2={THRESHOLD1}, {THRESHOLD2}")

    # Step 4: Place the B protein at the center
    B_protein_coords = B_structure.atoms.positions
    B_centered_coords = B_protein_coords - np.mean(B_protein_coords, axis=0)

    # Place the Geometric center of A proteins randomly
    A_positions = (np.random.rand(num_A_proteins, 3) - 0.5) * box_size
    A_positions = process_lists(A_positions, B_centered_coords, threshold1=THRESHOLD1, threshold2=THRESHOLD2,box_size=box_size)

    assert len(get_coordinates_with_distances_greater_than_threshold(A_positions, B_centered_coords,threshold=THRESHOLD1)) == len(A_positions)
    # center the ligand (A protein) at the origin (0, 0, 0)
    A_protein_coords = A_structure.atoms.positions
    A_centered_coords = A_protein_coords - np.mean(A_protein_coords, axis=0)
    A_structure.atoms.positions = A_centered_coords

    # Step 5: Create the combined structure (C.pdb)
    num_A_atoms = A_structure.atoms.positions.shape[0]
    num_B_atoms = B_structure.atoms.positions.shape[0]
    total_num_atoms = num_A_atoms * num_A_proteins + num_B_atoms

    # Create an empty array to hold the positions of all atoms in C.pdb
    C_positions = np.zeros((total_num_atoms, 3))

    # Assign positions for A structure (ligand)
    for i, position in enumerate(A_positions):
        # initialize the eular angles
        # alpha, beta, gamma: alpha,gamma: 0-2pi; beta: 0-pi
        eular_angles = np.hstack(
            [np.random.rand(1) * 2 * np.pi, np.random.rand(1) * np.pi, np.random.rand(1) * 2 * np.pi])
        #C_positions[i * num_A_atoms: (i + 1) * num_A_atoms, :] = rotate_atoms(A_structure.atoms.positions + position, eular_angles)
        C_positions[i * num_A_atoms: (i + 1) * num_A_atoms, :] = A_structure.atoms.positions + position

    # Assign positions for B structure (protein)
    C_positions[num_A_atoms * num_A_proteins:] = B_centered_coords

    # Create the combined structure (C.pdb)
    entities = []
    for i in range(num_A_proteins):
        u_copy = A_structure.copy()
        u_copy.segments.segids = segid
        temp_atom_group = u_copy.atoms
        temp_atom_group.residues.resids += i
        entities.append(temp_atom_group)
        del temp_atom_group

    for i in entities:
        print(i.segments.segids)

    entities += [B_structure.atoms]

    C_structure = mda.Merge(*entities)
    print(C_positions.shape)
    C_structure.atoms.positions = C_positions

    # step 6: Save the combined structure to C.pdb
    C_structure.atoms.write(output_pdb)
    print(f"done! output_pdb:\n > {output_pdb}")
    print(f"visualize the output_pdb by pymol & VMD:\n > pymol {output_pdb} \n > vmd {output_pdb}")

def main(ligand_info_list, MAX_TRY_NUMBER=10):

    for ligand_info in ligand_info_list:
        for merge_test in range(MAX_TRY_NUMBER):
            out_pdb = ligand_info["output_pdb"]
            try:
                generate_merge(ligand_info) 
            except ValueError as e:
                print(f"Processing ligand {ligand_info['ligand_pdb']} and protein {ligand_info['input_pdb']}")
                print(f"> {out_pdb} does not exist, and tried {merge_test+1} time(s) (MAX_TRY_NUMBER={MAX_TRY_NUMBER}")
                continue
            if os.path.isfile(out_pdb):
                break
            else:
                if merge_test >= MAX_TRY_NUMBER-1: # the last round of MAX_TRY_NUMBER
                    print(f"{out_pdb} does not exist, and reach MAX_TRY_NUMBER({MAX_TRY_NUMBER})")
                    exit()
                else: 
                    print(f"Processing ligand {ligand_info['ligand_pdb']} and protein {ligand_info['input_pdb']}")
                    print(f"> {out_pdb} does not exist, and tried {merge_test+1} time(s) (MAX_TRY_NUMBER={MAX_TRY_NUMBER}")
                    continue





if __name__ == '__main__':

    from csv_util import csv2records
    config_dict_list = csv2records('./config.csv')
    main(config_dict_list)

