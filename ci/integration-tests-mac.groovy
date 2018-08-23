#!/usr/bin/env groovy

pipeline {
  agent none

  options {
    timeout(time: 6, unit: 'HOURS')
  }

  stages {
    stage("Run macOS integration tests") {
      agent { label 'mac-hh-yosemite' }

      steps {
        withCredentials([
          [$class: 'AmazonWebServicesCredentialsBinding',
          credentialsId: 'a20fbd60-2528-4e00-9175-ebe2287906cf',
          accessKeyVariable: 'AWS_ACCESS_KEY_ID',
          secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'],
          [$class: 'FileBinding',
          credentialsId: '23743034-1ac4-49f7-b2e6-a661aee2d11b',
          variable: 'DCOS_TEST_SSH_KEY_PATH'],
          [$class: 'StringBinding',
          credentialsId: '9273e717-5f3d-4e6b-9163-146f99470b43',
          variable: 'DCOS_TEST_INSTALLER_URL'],
          [$class: 'StringBinding',
          credentialsId: 'ca159ad3-7323-4564-818c-46a8f03e1389',
          variable: 'DCOS_TEST_LICENSE'],
          [$class: 'UsernamePasswordMultiBinding',
          credentialsId: '323df884-742b-4099-b8b7-d764e5eb9674',
          usernameVariable: 'DCOS_TEST_ADMIN_USERNAME',
          passwordVariable: 'DCOS_TEST_ADMIN_PASSWORD']
        ]) {
          sh '''
            bash -exc " \
              env; \
              cd scripts; \
              python3 -m venv env; \
              source env/bin/activate; \
              export LC_ALL=en_US.UTF-8; \
              export PYTHONIOENCODING=utf-8; \
              pip install --upgrade pip; \
              pip install -r requirements.txt; \
              dcos cluster remove --all; \
              ./run_integration_tests.py --e2e-backend=dcos_launch"
          '''
        }
      }
    }
  }
}
