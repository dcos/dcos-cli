#!/usr/bin/env groovy

/**
 * This Jenkinsfile runs a set of parallel builders for the dcos-cli across
 * multiple platforms (linux/mac/windows).
 *
 * One set of builders builds the CLI into a binary on each platform. The other
 * set of builders runs integration tests on each platform. Under the hood, the
 * integration test builders use `dcos_launch` to create the DC/OS clusters for
 * each platform to run their tests against. Unfortunately, `dcos_luanch` only
 * works reliably on Linux, so we use a single linux instance to create all of
 * the clusters and separate linux/mac/windows instances to run the actual
 * tests.
 */

/**
 * These are the platforms we are building against.
 */
def platforms = ["linux", "mac", "windows"]

/**
 * This generates the `dcos_launch` config for a particular build.
 */
def generateConfig(deploymentName, templateUrl) {
    return """
---
launch_config_version: 1
deployment_name: ${deploymentName}
template_url: ${templateUrl}
provider: aws
aws_region: us-west-2
template_parameters:
    KeyName: default
    AdminLocation: 0.0.0.0/0
    PublicSlaveInstanceCount: 1
    SlaveInstanceCount: 1
"""
}


/**
 * This class abstracts away the functions required to create a test cluster
 * for each of our platforms.
 */
class TestCluster implements Serializable {
    WorkflowScript script
    String platform
    int createAttempts

    TestCluster(WorkflowScript script, String platform) {
        this.script = script
        this.platform = platform
        this.createAttempts = 0
    }

    /**
     * Creates a new DC/OS cluster for the given platform using `dcos_launch`.
     */
    def launch_create() {
        script.sh "./dcos-launch create -c ${platform}_config.yaml -i ${platform}_cluster_info.json"
    }

    /**
     * Waits for a cluster previously created with `dcos_launch` to come online.
     */
    def launch_wait() {
        script.sh "./dcos-launch wait -i ${platform}_cluster_info.json"
    }

    /**
     * Deletes a cluster previously created using `dcos_launch`.
     */
    def launch_delete() {
        script.sh "./dcos-launch delete -i ${platform}_cluster_info.json"
    }

    /**
     * Creates a new test cluster for the given platform.
     *
     * It first creates a custom config file with a new deployment name that
     * matches the given platform and then uses `launch_create()` to actually
     * create the cluster.
     */
    def create() {
        script.sh "rm -rf ${platform}_config.yaml"
        script.sh "rm -rf ${platform}_cluster_info.json"

        script.writeFile([
            "file": "${platform}_config.yaml",
            "text" : script.generateConfig(
                "dcos-cli-${platform}-${script.env.BRANCH_NAME}-${script.env.BUILD_ID}-${createAttempts}",
                "${script.env.CF_TEMPLATE_URL}")])

        launch_create()

        createAttempts++
    }

    /**
     * Blocks until a test cluster successfully comes online or a user
     * interrupts the build.
     *
     * Under the hood, `launch_create()` will be re-executed anytime a previous
     * creation attempt fails. The only way to exit this loop is to either
     * create a cluster successfully, or interrupt the build manually.
     */
    def block() {
        while (true) {
            try {
                launch_wait()
                break
            } catch(InterruptedException e) {
                destroy()
                script.echo("Build interrupted. Exiting...")
                throw e
            } catch(Exception e) {
                destroy()
                if (createAttempts < 3) {
                    create()
                } else {
                    script.echo("Maximum number of creation attempts exceeded. Exiting...")
                    throw e
                }
            }
        }
    }

    /**
     * Destroys a test cluster previously created using `create()`.
     */
    def destroy() {
        launch_delete()
    }

    /**
     * Retreives the URL of a cluster previously created using `create()`.
     */
    def getDcosUrl() {
        /* In the future, consider doing the following with jq instead of
           inline python (however, jq is not installed on our windows machines
           at the moment). */
        script.sh """
            ./dcos-launch describe -i ${platform}_cluster_info.json \
            | python -c \
                'import sys, json; \
                 contents = json.load(sys.stdin); \
                 print(contents["masters"][0]["public_ip"], end="")' \
            > ${platform}_dcos_url"""

        return script.readFile("${platform}_dcos_url")
    }
}


/**
 * This function returns a closure that prepares binary builds for a specific
 * platform on a specific node in a specific workspace.
 */
def binaryBuilder(String platform, String nodeId, String workspace = null) {
    return { Closure _body ->
        def body = _body

        return {
            node(nodeId) {
                if (!workspace) {
                    workspace = "${env.WORKSPACE}"
                }

                ws (workspace) {
                    stage ('Cleanup workspace') {
                        deleteDir()
                    }

                    stage ("Unstash dcos-cli repository") {
                        unstash('dcos-cli')
                    }

                    body()
                }
            }
        }
    }
}


/**
 * This function returns a closure that prepares a test environment for a
 * specific platform on a specific node in a specific workspace.
 */
def testBuilder(String platform, String nodeId, String workspace = null) {
    return { Closure _body ->
        def body = _body

        return {
            def destroyCluster = true
            def cluster = new TestCluster(this, platform)

            try {
                stage ("Create ${platform} cluster") {
                    cluster.create()
                }

                stage ("Wait for ${platform} cluster") {
                    cluster.block()
                }

                def dcosUrl = cluster.getDcosUrl()

                node(nodeId) {
                    if (!workspace) {
                        workspace = "${env.WORKSPACE}"
                    }

                    ws (workspace) {
                        stage ('Cleanup workspace') {
                            deleteDir()
                        }

                        stage ("Unstash dcos-cli repository") {
                            unstash('dcos-cli')
                        }

                        withCredentials(
                            [[$class: 'FileBinding',
                             credentialsId: '1c206779-acc0-4844-97f6-7b3ed081a456',
                             variable: 'DCOS_SNAKEOIL_CRT_PATH'],
                            [$class: 'FileBinding',
                             credentialsId: '23743034-1ac4-49f7-b2e6-a661aee2d11b',
                             variable: 'CLI_TEST_SSH_KEY_PATH']]) {

                            withEnv(["DCOS_URL=${dcosUrl}"]) {
                                try {
                                    body()
                                } catch (Exception e) {
                                    echo(
                                        "Build failed. The DC/OS cluster at" +
                                        " ${dcosUrl} will remain temporarily" +
                                        " active so you can debug what went" +
                                        " wrong.")
                                    destroyCluster = false
                                    throw e
                                }
                            }
                        }
                    }
                }

            } finally {
                if (destroyCluster) {
                    stage ("Destroy ${platform} cluster") {
                        try { cluster.destroy() }
                        catch (Exception e) {}
                    }
                }
            }
        }
    }
}

/**
 * These are the builds that can be run in parallel.
 */
def builders = [:]


builders['linux-binary'] = binaryBuilder('linux', 'py35', '/workspace')({
    stage ("Build dcos-cli binary") {
        dir('dcos-cli/cli') {
            sh "make binary"
            sh "dist/dcos"
        }
    }
})


builders['mac-binary'] = binaryBuilder('mac', 'mac')({
    stage ("Build dcos-cli binary") {
        dir('dcos-cli/cli') {
            sh "make binary"
            sh "dist/dcos"
        }
    }
})


builders['windows-binary'] = binaryBuilder('windows', 'windows')({
    stage ("Build dcos-cli binary") {
        dir('dcos-cli/cli') {
            bat 'bash -c "make binary"'
            bat 'dist\\dcos.exe'
        }
    }
})


builders['linux-tests'] = testBuilder('linux', 'py35', '/workspace')({
    stage ("Run dcos-cli tests") {
        sh '''
           rm -rf ~/.dcos; \
           grep -q "^.* dcos.snakeoil.mesosphere.com$" /etc/hosts && \
           sed -iold "s/^.* dcos.snakeoil.mesosphere.com$/${DCOS_URL} dcos.snakeoil.mesosphere.com/" /etc/hosts || \
           echo ${DCOS_URL} dcos.snakeoil.mesosphere.com >> /etc/hosts'''

        dir('dcos-cli/cli') {
            sh '''
               export PYTHONIOENCODING=utf-8; \
               dcos cluster setup ${DCOS_URL} --insecure --username=${DCOS_ADMIN_USERNAME} --password-env=DCOS_ADMIN_PASSWORD; \
               dcos config set core.timeout 5; \
               dcos config set core.reporting false; \
               unset DCOS_URL; \
               make test-binary'''
        }
    }
})


builders['mac-tests'] = testBuilder('mac', 'mac')({
    stage ("Run dcos-cli tests") {
        sh '''
           rm -rf ~/.dcos; \
           cp /etc/hosts hosts.local; \
           grep -q "^.* dcos.snakeoil.mesosphere.com$" hosts.local && \
           sed -iold "s/^.* dcos.snakeoil.mesosphere.com$/${DCOS_URL} dcos.snakeoil.mesosphere.com/" hosts.local || \
           echo ${DCOS_URL} dcos.snakeoil.mesosphere.com >> hosts.local; \
           sudo cp ./hosts.local /etc/hosts'''

        dir('dcos-cli/cli') {
            sh '''
               export PYTHONIOENCODING=utf-8; \
               dcos cluster setup ${DCOS_URL} --insecure --username=${DCOS_ADMIN_USERNAME} --password-env=DCOS_ADMIN_PASSWORD; \
               dcos config set core.timeout 5; \
               dcos config set core.reporting false; \
               unset DCOS_URL; \
               make test-binary'''
        }
    }
})


builders['windows-tests'] = testBuilder('windows', 'windows', 'C:\\windows\\workspace')({
    stage ("Run dcos-cli tests") {
        bat '''
            bash -c "rm -rf ~/.dcos"'''

        bat 'echo %DCOS_URL% dcos.snakeoil.mesosphere.com >> C:\\windows\\system32\\drivers\\etc\\hosts'

        dir('dcos-cli/cli') {
            bat '''
                bash -c " \
                export PYTHONIOENCODING=utf-8; \
                dcos cluster setup ${DCOS_URL} --insecure --username=${DCOS_ADMIN_USERNAME} --password-env=DCOS_ADMIN_PASSWORD; \
                dcos config set core.timeout 5; \
                dcos config set core.reporting false; \
                unset DCOS_URL; \
                make test-binary"'''
        }
    }
})


/**
 * This node bootstraps everything including creating all the test clusters,
 * starting the builders, and finally destroying all the clusters once they
 * are done.
 */
node('py35') {
    stage ('Cleanup workspace') {
        deleteDir()
    }

    stage ('Update node') {
        sh 'pip install requests'
    }

    stage ('Download dcos-launch') {
        sh 'wget https://downloads.dcos.io/dcos-test-utils/bin/linux/dcos-launch'
        sh 'chmod a+x dcos-launch'
    }

    stage ('Pull dcos-cli repository') {
        dir('dcos-cli') {
            checkout scm
        }
    }

    stage ('Stash dcos-cli repository') {
        stash(['includes': 'dcos-cli/**', name: 'dcos-cli'])
    }

    withCredentials(
        [[$class: 'AmazonWebServicesCredentialsBinding',
         credentialsId: '7155bd15-767d-4ae3-a375-e0d74c90a2c4',
         accessKeyVariable: 'AWS_ACCESS_KEY_ID',
         secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'],
        [$class: 'StringBinding',
         credentialsId: 'fd1fe0ae-113d-4096-87b2-15aa9606bb4e',
         variable: 'CF_TEMPLATE_URL'],
        [$class: 'UsernamePasswordMultiBinding',
         credentialsId: '323df884-742b-4099-b8b7-d764e5eb9674',
         usernameVariable: 'DCOS_ADMIN_USERNAME',
         passwordVariable: 'DCOS_ADMIN_PASSWORD']]) {

        parallel builders
    }
}
