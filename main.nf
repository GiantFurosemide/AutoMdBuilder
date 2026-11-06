nextflow.enable.dsl = 2

import groovy.json.JsonSlurper
import groovy.json.JsonOutput

include { VALIDATE_CASE; LIGAND_PARAMETERS; PROTEIN_TOPOLOGY; ASSEMBLE_SYSTEM; SOLVATE; ADD_IONS } from './modules/build'
include { MINIMIZE; EQUILIBRATE_NVT; EQUILIBRATE_NPT; EXPORT_SYSTEM } from './modules/equilibrate'

workflow {
    if (params.help) {
        log.info 'AutoMdBuilder 0.1: use python3 bin/launch.py --help; see docs/nextflow/README.zh-CN.md'
        return
    }
    if (!params.samples) error 'Missing --samples CSV (columns: case_id,case_dir,replicas)'
    if (!(params.gmx ==~ /[A-Za-z0-9_\/.+ -]+/)) error 'gmx must be a single executable name/path without shell metacharacters'
    if (!params.gpu && !workflow.stubRun && !workflow.profile.tokenize(',').contains('test'))
        error 'Choose slurm/local_gpu, or use test with -stub-run for a no-GPU dry run.'
    if (workflow.profile.tokenize(',').any { it in ['apptainer', 'docker'] } && (!params.gmx_container || !params.acpype_container))
        error 'Container profiles require both --gmx_container and --acpype_container.'

    def settings = [forcefield: params.forcefield, water: params.water,
        padding_nm: params.padding_nm, salt_molar: params.salt_molar,
        temperature_k: params.temperature_k, nvt_ps: params.nvt_ps, npt_ps: params.npt_ps,
        dt_ps: params.dt_ps, em_steps: params.em_steps, em_tolerance: params.em_tolerance,
        runtime_images: [gromacs: params.gmx_container, acpype: params.acpype_container]]
    def encoded = JsonOutput.toJson(settings).bytes.encodeBase64().toString()
    def driver = Channel.value(file("${projectDir}/bin/mdflow.py"))
    def mdps = Channel.value(file(params.mdp_dir, checkIfExists: true))
    def samplesFile = file(params.samples, checkIfExists: true)
    def seen = new HashSet()
    cases = Channel.fromPath(samplesFile).splitCsv(header: true).map { row ->
        def id = row.case_id?.trim()
        if (!id || !(id ==~ /[A-Za-z0-9][A-Za-z0-9_.-]{0,79}/) || !seen.add(id))
            error "Invalid or duplicate case_id: ${id}"
        def replicas = row.replicas?.trim() ?: '1'
        if (!(replicas ==~ /[1-9][0-9]*/) || replicas.toInteger() > 10000)
            error "Invalid replicas for ${id}: ${replicas}"
        if (!row.case_dir?.trim()) error "Missing case_dir for ${id}"
        def src = file(samplesFile.parent.resolve(row.case_dir.trim()).normalize(), checkIfExists: true)
        tuple([id: id, replicas: replicas.toInteger()], src)
    }.ifEmpty { error 'Samples CSV contains no cases' }

    VALIDATE_CASE(cases, driver, encoded)
    validated = VALIDATE_CASE.out.map { meta, directory ->
        // Read only validated metadata; a malformed case.json fails its own task,
        // rather than throwing in the controller and cancelling unrelated cases.
        def state = new JsonSlurper().parse(directory.resolve('state.json').toFile())
        tuple(meta + [acpype: state.spec.ligands.any { it.mode == 'acpype' }], directory)
    }
    LIGAND_PARAMETERS(validated, driver)
    PROTEIN_TOPOLOGY(validated, driver)
    ASSEMBLE_SYSTEM(PROTEIN_TOPOLOGY.out.join(LIGAND_PARAMETERS.out), driver)
    SOLVATE(ASSEMBLE_SYSTEM.out, driver)
    ADD_IONS(SOLVATE.out, driver, mdps)
    replicas = ADD_IONS.out.flatMap { meta, state ->
        (1..meta.replicas).collect { replica ->
            def digest = java.security.MessageDigest.getInstance('SHA-256').digest("${params.seed}:${meta.id}:${replica}".bytes)
            def seed = (new BigInteger(1, digest).mod(BigInteger.valueOf(2147483646L))).intValue() + 1
            tuple(meta + [replica: replica, seed: seed], state)
        }
    }
    MINIMIZE(replicas, driver, mdps)
    EQUILIBRATE_NVT(MINIMIZE.out, driver, mdps)
    EQUILIBRATE_NPT(EQUILIBRATE_NVT.out, driver, mdps)
    EXPORT_SYSTEM(EQUILIBRATE_NPT.out, driver, mdps)
}
