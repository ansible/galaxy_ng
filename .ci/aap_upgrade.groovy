@Library(['aap-jenkins-shared-library']) _
import steps.StepsFactory
import validation.AapqaProvisionerParameters

StepsFactory stepsFactory = new StepsFactory(this, [:], 'galaxy_ng_aap_upgrade')
Map provisionInfo = [:]
Map installInfo = [:]
Map validateInfo = [:]
List installerFlags = []
List upgradeFlags = []
Map installerVars = [:]
String pulpcore_version = ''
String automationhub_pulp_ansible_version = ''
String automationhub_pulp_container_version = ''

pipeline {
        agent {
            kubernetes {
                yaml libraryResource('pod_templates/unpriv-ansible-pod.yaml')
            }
        }
        options {
            ansiColor('xterm')
            timestamps()
            timeout(time: 18, unit: 'HOURS')
            buildDiscarder(logRotator(daysToKeepStr: '10', numToKeepStr: '50', artifactNumToKeepStr: '40'))
        }

        stages {
            stage('Set variables') {
                steps {
                    script {

                        echo "GitHub Fork: ${env.CHANGE_FORK}"
                        fork = env.CHANGE_FORK ?: 'ansible'
                        echo "${fork}"
                        echo "Branch Name: ${env.CHANGE_BRANCH}"

                        upgradeFlags.add('aapqa_private/input/install/ee_registry.yml')
                        upgradeFlags.add('input/install/flags/automationhub_content_signing.yml')
                        upgradeFlags.add('input/install/flags/automationhub_from_git.yml')
                        upgradeFlags.add('input/install/flags/automationhub_routable_hostname.yml')

                        List provisionFlags = []

                        installerFlags.add('input/install/flags/automationhub_content_signing.yml')
                        installerFlags.add('input/install/flags/automationhub_routable_hostname.yml')
                        // installerFlags.add('input/install/flags/automationhub_from_git.yml')

                        provisionFlags.add('input/provisioner/flags/domain.yml')
                        provisionFlags.add("input/provisioner/architecture/x86_64.yml")
                        provisionFlags.add('input/provisioner/flags/domain.yml')

                        validateInfo.put("provisionFlags", provisionFlags)
                        validateInfo.put("installerFlags", installerFlags)
                        validateInfo.put("upgradeFlags", upgradeFlags)
                    }
                }
            }

            stage('Get pulpcore, pulp_ansible, pulp-container versions from setup.py') {
                steps {
                    container('aapqa-ansible') {
                        script {
                            def setupPyContent = readFile('setup.py').trim()
                            def lines = setupPyContent.split('\n')
                            def dependenciesToExtract = ["pulpcore", "pulp_ansible", "pulp-container"]
                            def minimumVersions = [:]
                            lines.each { line ->
                                dependenciesToExtract.each { dependency ->
                                    if (line.contains("$dependency>=")) {
                                        def versionMatch = line =~ /$dependency>=([\d.]+)/
                                        if (versionMatch) {
                                            minimumVersions[dependency] = versionMatch[0][1]
                                        }
                                    }
                                }
                            }

                            dependenciesToExtract.each { dependency ->
                                if (minimumVersions.containsKey(dependency)) {
                                    println("Using $dependency version: ${minimumVersions[dependency]}")
                                } else {
                                    println("$dependency not found in setup.py. Using version defined in the installer")
                                }
                            }
                            if (minimumVersions.containsKey("pulpcore")){
                                pulpcore_version = minimumVersions["pulpcore"]
                            }
                            if (minimumVersions.containsKey("pulp_ansible")){
                                automationhub_pulp_ansible_version = minimumVersions["pulp_ansible"]
                            }
                            if (minimumVersions.containsKey("pulp-container")){
                                automationhub_pulp_container_version = minimumVersions["pulp-container"]
                            }
                        }
                    }
                }

            }

            stage('Setup aapqa-provisioner') {
                steps {
                    container('aapqa-ansible') {
                        script {
                            stepsFactory.aapqaSetupSteps.setup()
                        }
                    }
                }
            }

            stage('Provision') {
                steps {
                    container('aapqa-ansible') {
                        script {
                            provisionInfo = [
                                    provisionerPrefix: validateInfo.provisionPrefix,
                                    cloudVarFile     : "input/provisioner/cloud/aws.yml",
                                    scenarioVarFile  : "input/aap_scenarios/1inst_1hybr_1ahub.yml",
                            ]
                            provisionInfo = stepsFactory.aapqaOnPremProvisionerSteps.provision(provisionInfo + [
                                    provisionerVarFiles: validateInfo.get("provisionFlags") + [
                                            "input/platform/rhel88.yml",
                                    ],
                                    isPermanentDeploy  : false,
                                    registerWithRhsm   : true,
                                    runMeshScalingTests: false,
                                    runInstallerTests  : false
                            ])
                        }
                    }
                }
                post {
                    always {
                        script {
                            stepsFactory.aapqaOnPremProvisionerSteps.archiveArtifacts()
                        }
                    }
                }
            }

            stage('Fresh Install AAP 2.3') {
                steps {
                    container('aapqa-ansible') {
                        script {
                            installerFlags = validateInfo.get("installerFlags")
                            stepsFactory.aapqaAapInstallerSteps.updateBuildInformation(provisionInfo)
                            installInfo = stepsFactory.aapqaAapInstallerSteps.install(provisionInfo + [
                                aapVersionVarFile: "input/install/2.3_released.yml",
                                installerVarFiles: installerFlags + [
                                    "input/aap_scenarios/1inst_1hybr_1ahub.yml",
                                    "input/platform/rhel88.yml"
                                ]
                            ])
                        }
                    }
                }

                post {
                    always {
                        script {
                            container('aapqa-ansible') {
                                stepsFactory.aapqaAapInstallerSteps.collectAapInstallerArtifacts(provisionInfo + [
                                        archiveArtifactsSubdir: 'install'
                                ])

                                if (fileExists('artifacts/install/setup.log')) {
                                    sh """
                                        echo "Install setup log:"
                                        echo "-------------------------------------------------"
                                        cat artifacts/install/setup.log
                                        echo "-------------------------------------------------"
                                    """
                                }
                            }
                        }
                    }
                }
            }

            stage('Hub Load Data') {
                steps {
                    container('aapqa-ansible') {
                        script {
                            stepsFactory.aapqaAutomationHubSteps.setup(installInfo)
                            stepsFactory.aapqaAutomationHubSteps.runAutomationHubLoadDataTests(installInfo)
                            stepsFactory.commonSteps.saveXUnitResultsToJenkins(xunitFile: 'ah-results-load.xml')
                        }
                    }
                }
            }

            stage('Upgrade AAP 2.4') {
                steps {
                    container('aapqa-ansible') {
                        script {

                            Map ahubPipParams = [
                                    automationhub_git_url: "https://github.com/${fork}/galaxy_ng",
                                    automationhub_git_version: "${env.CHANGE_BRANCH}",
                                    automationhub_ui_download_url: "https://github.com/ansible/ansible-hub-ui/releases/download/dev/automation-hub-ui-dist.tar.gz",
                            ]
                            if (pulpcore_version != '') {
                                ahubPipParams['pulpcore_version'] = "${pulpcore_version}"
                                println("Using pulpcore version: ${pulpcore_version}")
                            }else{
                                println("pulpcore_version version not provided, using version defined in the installer")
                            }
                            if (automationhub_pulp_ansible_version != '') {
                                ahubPipParams['automationhub_pulp_ansible_version'] = "${automationhub_pulp_ansible_version}"
                                println("Using pulp_ansible version: ${automationhub_pulp_ansible_version}")
                            }else{
                                println("pulp_ansible version not provided, using version defined in the installer")
                            }
                            if (automationhub_pulp_container_version != '') {
                                ahubPipParams['automationhub_pulp_container_version'] = "${automationhub_pulp_container_version}"
                                println("Using pulp-container version: ${automationhub_pulp_container_version}")
                            }else{
                                println("pulp-container version not provided, using version defined in the installer")
                            }

                            writeYaml(
                                    file: 'input/install/ahub_pip.yml',
                                    data: ahubPipParams
                            )

                            upgradeFlags.add('input/install/ahub_pip.yml')

                            archiveArtifacts(artifacts: 'input/install/ahub_pip.yml')

                            upgradeInfo = stepsFactory.aapqaAapInstallerSteps.upgrade(provisionInfo + [
                                    aapVersionVarFile: "input/install/2.4_released.yml",
                                    upgradeVarFiles: upgradeFlags + [
                                        "input/aap_scenarios/1inst_1hybr_1ahub.yml",
                                        "input/platform/rhel88.yml"
                                    ]
                            ])
                        }
                    }
                }
                post {
                    always {
                        script {
                            container('aapqa-ansible') {
                                stepsFactory.aapqaAapInstallerSteps.collectAapInstallerArtifacts(provisionInfo + [
                                        archiveArtifactsSubdir: 'upgrade'
                                ])

                                if (fileExists('artifacts/upgrade/setup.log')) {
                                    sh """
                                        echo "Upgrade setup log:"
                                        echo "-------------------------------------------------"
                                        cat artifacts/upgrade/setup.log
                                        echo "-------------------------------------------------"
                                    """
                                }
                            }
                        }
                    }
                }
            }

            stage('Upgrade AAP devel') {
                steps {
                    container('aapqa-ansible') {
                        script {
                            upgradeFlags.add('input/install/ee/unreleased.yml')
                            upgradeInfo = stepsFactory.aapqaAapInstallerSteps.upgrade(provisionInfo + [
                                    aapVersionVarFile: "input/install/devel.yml",
                                    upgradeVarFiles: upgradeFlags + [
                                        "input/aap_scenarios/1inst_1hybr_1ahub.yml",
                                        "input/platform/rhel88.yml"
                                    ]
                            ])
                        }
                    }
                }
                post {
                    always {
                        script {
                            container('aapqa-ansible') {
                                stepsFactory.aapqaAapInstallerSteps.collectAapInstallerArtifacts(provisionInfo + [
                                        archiveArtifactsSubdir: 'upgrade'
                                ])

                                if (fileExists('artifacts/upgrade/setup.log')) {
                                    sh """
                                        echo "Upgrade setup log:"
                                        echo "-------------------------------------------------"
                                        cat artifacts/upgrade/setup.log
                                        echo "-------------------------------------------------"
                                    """
                                }
                            }
                        }
                    }
                }
            }

            stage('Hub Verify Data Tests') {
                steps {
                    container('aapqa-ansible') {
                        script {
                            upgradeFlags.add('input/install/flags/upgrade_from_aap_23.yml')
                            stepsFactory.aapqaAutomationHubSteps.setup(installInfo)
                            stepsFactory.aapqaAutomationHubSteps.runAutomationHubVerifyDataTests(installInfo + [upgradeVarFiles: upgradeFlags])
                            stepsFactory.commonSteps.saveXUnitResultsToJenkins(xunitFile: 'ah-results-verify.xml')
                        }
                    }
                }
            }

            stage('Run AutomationHub Tests') {
                steps {
                    container('aapqa-ansible') {
                        script {

                            stepsFactory.aapqaAutomationHubSteps.setup(installInfo)
                            stepsFactory.aapqaAutomationHubSteps.runAutomationHubSuite(installInfo + [ahubTestExpression: "installer_smoke_test"])
                            stepsFactory.commonSteps.saveXUnitResultsToJenkins(xunitFile: 'ah-results.xml')
                            stepsFactory.aapqaAutomationHubSteps.reportTestResults(provisionInfo + installInfo +
                                    [
                                            component: 'ahub',
                                            testType: 'api',
                                    ], "ah-results.xml")
                        }
                    }
                }
                post {
                    always {
                        container('aapqa-ansible') {
                            script {
                                stepsFactory.aapqaAutomationHubSteps.cleanup(installInfo)
                            }
                        }
                    }
                }
            }

        }

        post {
            always {
                container('aapqa-ansible') {
                    script {
                        stepsFactory.aapqaAapInstallerSteps.generateAndCollectSosReports(provisionInfo)
                    }
                }
            }
            cleanup {
                container('aapqa-ansible') {
                    script {
                        if (provisionInfo != [:]) {
                            stepsFactory.aapqaOnPremProvisionerSteps.cleanup(provisionInfo)
                        }
                    }
                }
            }
        }
    }
