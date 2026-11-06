process MINIMIZE {
    tag "${meta.id}/replica_${meta.replica}"
    container params.gmx_container
    cpus params.cpus
    input:
    tuple val(meta), path(state, stageAs: 'input_state')
    path driver
    path mdps, stageAs: 'templates'
    output:
    tuple val(meta), path('em')
    script:
    """
    python3 ${driver} run --stage em --source input_state --out em --mdps templates --gmx '${params.gmx}' --cpus ${task.cpus} --replica ${meta.replica} --seed ${meta.seed}
    """
    stub:
    """
    python3 ${driver} stub --stage em --source input_state --out em --replica ${meta.replica} --seed ${meta.seed}
    """
}

process EQUILIBRATE_NVT {
    tag "${meta.id}/replica_${meta.replica}"
    label 'dynamics'
    cpus params.cpus
    container params.gmx_container
    input:
    tuple val(meta), path(state, stageAs: 'input_state')
    path driver
    path mdps, stageAs: 'templates'
    output:
    tuple val(meta), path('nvt')
    script:
    """
    python3 ${driver} run --stage nvt --source input_state --out nvt --mdps templates --gmx '${params.gmx}' --cpus ${task.cpus} ${params.gpu ? '--gpu' : ''} --replica ${meta.replica} --seed ${meta.seed}
    """
    stub:
    """
    python3 ${driver} stub --stage nvt --source input_state --out nvt --replica ${meta.replica} --seed ${meta.seed}
    """
}

process EQUILIBRATE_NPT {
    tag "${meta.id}/replica_${meta.replica}"
    label 'dynamics'
    cpus params.cpus
    container params.gmx_container
    input:
    tuple val(meta), path(state, stageAs: 'input_state')
    path driver
    path mdps, stageAs: 'templates'
    output:
    tuple val(meta), path('npt')
    script:
    """
    python3 ${driver} run --stage npt --source input_state --out npt --mdps templates --gmx '${params.gmx}' --cpus ${task.cpus} ${params.gpu ? '--gpu' : ''} --replica ${meta.replica} --seed ${meta.seed}
    """
    stub:
    """
    python3 ${driver} stub --stage npt --source input_state --out npt --replica ${meta.replica} --seed ${meta.seed}
    """
}

process EXPORT_SYSTEM {
    tag "${meta.id}/replica_${meta.replica}"
    container params.gmx_container
    publishDir "${params.outdir}/systems/${meta.id}/replica_${meta.replica}", mode: 'copy', overwrite: false
    input:
    tuple val(meta), path(state, stageAs: 'input_state')
    path driver
    path mdps, stageAs: 'templates'
    output:
    tuple val(meta), path('system')
    script:
    """
    python3 ${driver} export --source input_state --out system --mdps templates --gmx '${params.gmx}'
    """
    stub:
    """
    python3 ${driver} stub --source input_state --out system --stage export --replica ${meta.replica} --seed ${meta.seed}
    """
}
