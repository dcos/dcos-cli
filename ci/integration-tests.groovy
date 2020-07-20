#!/usr/bin/env groovy

@Library("sec_ci_libs@v2-latest") _

def master_branches = ["master", ] as String[]

def credentials = [
        [$class           : 'AmazonWebServicesCredentialsBinding',
         credentialsId    : 'a20fbd60-2528-4e00-9175-ebe2287906cf',
         accessKeyVariable: 'AWS_ACCESS_KEY_ID',
         secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'],
        [$class       : 'FileBinding',
         credentialsId: '23743034-1ac4-49f7-b2e6-a661aee2d11b',
         variable     : 'CLI_TEST_SSH_KEY_PATH'],
        [$class       : 'StringBinding',
         credentialsId: '0b513aad-e0e0-4a82-95f4-309a80a02ff9',
         variable     : 'DCOS_TEST_INSTALLER_URL'],
        [$class       : 'StringBinding',
         credentialsId: 'ca159ad3-7323-4564-818c-46a8f03e1389',
         variable     : 'DCOS_TEST_LICENSE'],
        [$class          : 'UsernamePasswordMultiBinding',
         credentialsId   : '323df884-742b-4099-b8b7-d764e5eb9674',
         usernameVariable: 'DCOS_TEST_DEFAULT_CLUSTER_USERNAME',
         passwordVariable: 'DCOS_TEST_DEFAULT_CLUSTER_PASSWORD']
]

pipeline {
  agent { label 'mesos' }

  options {
    timeout(time: 6, unit: 'HOURS')
  }

  stages {
    stage('Check authorization') {
      when {
        expression { env.CHANGE_ID != null }
      }

      steps {
        user_is_authorized([] as String[], '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#dcos-cli-ci')
      }
    }

    stage("Build binaries") {
      agent { label 'mesos-ubuntu' }

      steps {
          sh 'make linux darwin windows'
          stash includes: 'build/linux/**', name: 'dcos-linux'
          stash includes: 'build/darwin/**', name: 'dcos-darwin'
          stash includes: 'build/windows/**', name: 'dcos-windows'
      }
    }

    stage("Launch AWS Cluster") {
      steps {
          retry(5) {
              withCredentials(credentials) {
                  script {
                      master_ip = sh(script: 'cd scripts && ./launch_aws_cluster.sh', returnStdout: true).trim()
                  }
                  stash includes: 'scripts/**/*', name: 'terraform'
              }
          }
      }
    }

    stage("Run Linux integration tests") {
      agent { label 'py36' }

      steps {
          unstash 'dcos-linux'

          withEnv(["DCOS_TEST_DEFAULT_CLUSTER_HOST=${master_ip}"]) {
              withCredentials(credentials) {
                  sh '''
                    bash -exc " \
                      export DCOS_CLI_EXPERIMENTAL_AUTOINSTALL_PACKAGE_CLIS=1; \
                      PATH=$PWD/build/linux:$PATH; \
                      cd tests; \
                      dcos cluster remove --all; \
                      python3 -m venv env; \
                      source env/bin/activate; \
                      pip install -U pip; \
                      pip install -r requirements.txt; \
                      pytest integration --junitxml=tests.xml"
                  '''
              }
          }
      }
      post {
          always {
              junit 'tests/tests.xml'
          }
      }
    }

    stage("Run macOS integration tests") {
      agent { label 'mac-hh-yosemite' }

      steps {
          unstash 'dcos-darwin'

          withEnv(["DCOS_TEST_DEFAULT_CLUSTER_HOST=${master_ip}"]) {
              withCredentials(credentials) {
                  sh '''
                    bash -exc " \
                      export LC_ALL=en_US.UTF-8; \
                      export PYTHONIOENCODING=utf-8; \
                      export DCOS_CLI_EXPERIMENTAL_AUTOINSTALL_PACKAGE_CLIS=1; \
                      PATH=$PWD/build/darwin:$PATH; \
                      cd tests; \
                      dcos cluster remove --all; \
                      python3 -m venv env; \
                      source env/bin/activate; \
                      pip install -U pip; \
                      pip install -r requirements.txt; \
                      pytest integration"
                  '''
              }
          }
      }
    }

    stage("Run Windows integration tests") {
      agent {
        node {
          label 'windows'
          customWorkspace 'C:\\windows\\workspace'
        }
      }

      steps {
          unstash 'dcos-windows'

          withEnv(["DCOS_TEST_DEFAULT_CLUSTER_HOST=${master_ip}"]) {
              withCredentials(credentials) {
                  bat '''
                    bash -exc " \
                      export PYTHONIOENCODING=utf-8; \
                      export DCOS_CLI_EXPERIMENTAL_AUTOINSTALL_PACKAGE_CLIS=1; \
                      PATH=$PWD/build/windows:$PATH; \
                      cd tests; \
                      dcos cluster remove --all; \
                      python -m venv env; \
                      env/Scripts/python -m pip install -U pip; \
                      env/Scripts/pip install -r requirements.txt; \
                      env/Scripts/pytest -vv integration"
                  '''
              }
          }
      }
    }
  }

  post {
        cleanup {
            echo 'Delete AWS Cluster'
            unstash 'terraform'
            withCredentials(credentials) {
                sh('''
                  cd scripts && \
                  export AWS_REGION="us-east-1" && \
                  export TF_INPUT=false && \
                  export TF_IN_AUTOMATION=1 && \
                  ./terraform destroy -auto-approve -no-color 1> /dev/null''')
            }
        }
  }
}
