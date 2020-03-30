#!/usr/bin/env groovy

@Library("sec_ci_libs@v2-latest") _

def master_branches = ["master", ] as String[]

pipeline {
  agent none

  options {
    timeout(time: 6, unit: 'HOURS')
  }

  stages {
    stage("Authorization") {
      steps {
        user_is_authorized(master_branches, "8b793652-f26a-422f-a9ba-0d1e47eb9d89", "#mesosphere-dev")
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

    stage("Launch DC/OS cluster") {
      agent { label 'py36' }

      steps {
        withCredentials([
          [$class: 'AmazonWebServicesCredentialsBinding',
          credentialsId: 'mesosphere-ci-marathon',
          accessKeyVariable: 'AWS_ACCESS_KEY_ID',
          secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'],
          [$class: 'FileBinding',
          credentialsId: '23743034-1ac4-49f7-b2e6-a661aee2d11b',
          variable: 'DCOS_TEST_SSH_KEY_PATH']
        ]) {
            sh '''
              bash -exc " \
                cd tests; \
                python3 -m venv env; \
                source env/bin/activate; \
                pip install -r requirements.txt; \
                flake8 integration; \
                export DCOS_TEST_VARIANT=open; \
                ./launch_cluster.py https://downloads.dcos.io/dcos/testing/master/dcos_generate_config.sh"
            '''
            stash includes: 'tests/test_cluster.env.sh', name: 'test-cluster'
        }
      }
    }

    stage("Run Linux integration tests") {
      agent { label 'py36' }

      steps {
          unstash 'test-cluster'
          unstash 'dcos-linux'

          sh '''
            bash -exc " \
              export DCOS_CLI_EXPERIMENTAL_AUTOINSTALL_PACKAGE_CLIS=1; \
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
              export DCOS_CLI_EXPERIMENTAL_AUTOINSTALL_PACKAGE_CLIS=1; \
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
              export DCOS_CLI_EXPERIMENTAL_AUTOINSTALL_PACKAGE_CLIS=1; \
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
