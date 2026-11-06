process VALIDATE_CASE {
    tag "${meta.id}"
    container params.gmx_container
    input:
    tuple val(meta), path(source, stageAs: 'source')
    path driver
    val settings
    output:
    tuple val(meta), path('validated')
    script:
    """
    python3 ${driver} validate --source source --out validated --case-id ${meta.id} --settings ${settings}
    """
    stub:
    """
    python3 ${driver} validate --source source --out validated --case-id ${meta.id} --settings ${settings}
    """
}

process LIGAND_PARAMETERS {
    tag "${meta.id}"
    container { meta.acpype ? params.acpype_container : params.gmx_container }
    input:
    tuple val(meta), path(validated, stageAs: 'validated')
    path driver
    output:
    tuple val(meta), path('ligands')
    script:
    """
    python3 ${driver} ligands --source validated --out ligands
    """
    stub:
    """
    python3 ${driver} stub --source validated --out ligands --stage ligands
    """
}

process PROTEIN_TOPOLOGY {
    tag "${meta.id}"
    container params.gmx_container
    input:
    tuple val(meta), path(validated, stageAs: 'validated')
    path driver
    output:
    tuple val(meta), path('protein')
    script:
    """
    python3 ${driver} protein --source validated --out protein --gmx '${params.gmx}'
    """
    stub:
    """
    python3 ${driver} stub --source validated --out protein --stage protein
    """
}

process ASSEMBLE_SYSTEM {
    tag "${meta.id}"
    container params.gmx_container
    input:
    tuple val(meta), path(protein, stageAs: 'protein'), path(ligands, stageAs: 'ligands')
    path driver
    output:
    tuple val(meta), path('assembled')
    script:
    """
    python3 ${driver} assemble --source protein --ligands ligands --out assembled --gmx '${params.gmx}'
    """
    stub:
    """
    python3 ${driver} stub --source protein --out assembled --stage assembled
    """
}

process SOLVATE {
    tag "${meta.id}"
    container params.gmx_container
    input:
    tuple val(meta), path(state, stageAs: 'input_state')
    path driver
    output:
    tuple val(meta), path('solvated')
    script:
    """
    python3 ${driver} solvate --source input_state --out solvated --gmx '${params.gmx}'
    """
    stub:
    """
    python3 ${driver} stub --source input_state --out solvated --stage solvated
    """
}

process ADD_IONS {
    tag "${meta.id}"
    container params.gmx_container
    input:
    tuple val(meta), path(state, stageAs: 'input_state')
    path driver
    path mdps, stageAs: 'templates'
    output:
    tuple val(meta), path('ionized')
    script:
    """
    python3 ${driver} ions --source input_state --out ionized --mdps templates --gmx '${params.gmx}'
    """
    stub:
    """
    python3 ${driver} stub --source input_state --out ionized --stage ionized
    """
}
