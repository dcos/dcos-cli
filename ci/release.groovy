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
          sh '''
            bash -exc " \
              export VERSION=\"${TAG_NAME:-$GIT_COMMIT}\";
              export GO_BUILD_TAGS=\"corecli\";
              make core-download;
              make core-bundle;
              make linux darwin windows"
          '''
          stash includes: 'build/**', name: 'dcos-binaries'
      }
    }

    stage("Release binaries to S3") {
      when {
        anyOf {
          branch 'master'
          expression { env.TAG_NAME != null }
        }
      }

      agent { label 'py36' }

      steps {
        withCredentials([
            string(credentialsId: "8b793652-f26a-422f-a9ba-0d1e47eb9d89", variable: "SLACK_API_TOKEN"),
            string(credentialsId: "e270aa3f-4825-480c-a3ec-18a541c4e2d1",variable: "AWS_ACCESS_KEY_ID"),
            string(credentialsId: "cd616d55-78eb-45de-b7a8-e5bc5ccce4c7",variable: "AWS_SECRET_ACCESS_KEY"),
        ]) {
            unstash 'dcos-binaries'

            sh '''
              bash -exc " \
                cd ci; \
                python -m venv env; \
                source env/bin/activate; \
                pip install --upgrade pip setuptools; \
                pip install -r requirements.txt; \
                ./release.py"
            '''
        }
      }
    }
  }
}
