#!/usr/bin/env groovy

pipeline {
  agent none

  options {
    timeout(time: 6, unit: 'HOURS')
  }

  stages {
    stage("Build binaries") {
      agent { label 'mesos-ubuntu' }

      steps {
          sh 'make core-download'
          sh 'make core-bundle'
          sh 'GO_BUILD_TAGS=corecli make linux darwin windows'
          stash includes: 'build/linux/**', name: 'dcos-linux'
          stash includes: 'build/darwin/**', name: 'dcos-darwin'
          stash includes: 'build/windows/**', name: 'dcos-windows'
      }
    }

    stage("Launch DC/OS cluster") {
      agent { label 'py36' }

      steps {
        withCredentials([
          [$class: 'AmazonWebServicesCredentialsBinding',
          credentialsId: 'a20fbd60-2528-4e00-9175-ebe2287906cf',
          accessKeyVariable: 'AWS_ACCESS_KEY_ID',
          secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'],
          [$class: 'StringBinding',
          credentialsId: '0b513aad-e0e0-4a82-95f4-309a80a02ff9',
          variable: 'DCOS_TEST_INSTALLER_URL'],
          [$class: 'FileBinding',
          credentialsId: '23743034-1ac4-49f7-b2e6-a661aee2d11b',
          variable: 'DCOS_TEST_SSH_KEY_PATH'],
          [$class: 'StringBinding',
          credentialsId: 'ca159ad3-7323-4564-818c-46a8f03e1389',
          variable: 'DCOS_TEST_LICENSE']
        ]) {
            sh '''
              bash -exc " \
                cd tests; \
                python3 -m venv env; \
                source env/bin/activate; \
                pip install -r requirements.txt; \
                flake8 integration; \
                ./launch_cluster.py ${DCOS_TEST_INSTALLER_URL}"
            '''
            stash includes: 'tests/test_cluster.env.sh', name: 'test-cluster'
        }
      }
    }

    stage('Run integration tests') {
      parallel {
        stage("Run Linux integration tests") {
          agent { label 'py36' }

          steps {
              unstash 'test-cluster'
              unstash 'dcos-linux'

              sh '''
                bash -exc " \
                  PATH=$PWD/build/linux:$PATH; \
                  cd tests; \
                  dcos cluster remove --all; \
                  python3 -m venv env; \
                  source env/bin/activate; \
                  source test_cluster.env.sh; \
                  pip install -U pip; \
                  pip install -r requirements.txt; \
                  pytest integration"
              '''
          }
        }

        stage("Run macOS integration tests") {
          agent { label 'mac-hh-yosemite' }

          steps {
              unstash 'test-cluster'
              unstash 'dcos-darwin'

              sh '''
                bash -exc " \
                  export LC_ALL=en_US.UTF-8; \
                  export PYTHONIOENCODING=utf-8; \
                  PATH=$PWD/build/darwin:$PATH; \
                  cd tests; \
                  dcos cluster remove --all; \
                  python3 -m venv env; \
                  source env/bin/activate; \
                  source test_cluster.env.sh; \
                  pip install -U pip; \
                  pip install -r requirements.txt; \
                  pytest integration"
              '''
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
              unstash 'test-cluster'
              unstash 'dcos-windows'

              bat '''
                bash -exc " \
                  export PYTHONIOENCODING=utf-8; \
                  PATH=$PWD/build/windows:$PATH; \
                  cd tests; \
                  dcos cluster remove --all; \
                  source test_cluster.env.sh; \
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
}
