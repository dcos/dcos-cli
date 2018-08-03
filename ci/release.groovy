#!/usr/bin/env groovy

@Library('sec_ci_libs@v2-latest') _

pipeline {
  agent none

  options {
    timeout(time: 2, unit: 'HOURS')
  }

  stages {
    stage("Release binaries in S3") {
      agent { label 'py35' }

      steps {
        withCredentials([
            string(credentialsId: "8b793652-f26a-422f-a9ba-0d1e47eb9d89", variable: "SLACK_API_TOKEN"),
            string(credentialsId: "e270aa3f-4825-480c-a3ec-18a541c4e2d1",variable: "AWS_ACCESS_KEY_ID"),
            string(credentialsId: "cd616d55-78eb-45de-b7a8-e5bc5ccce4c7",variable: "AWS_SECRET_ACCESS_KEY"),
        ]) {
            sh '''
              bash -exc " \
                env; \
                cd scripts; \
                python -m venv env; \
                source env/bin/activate; \
                pip install --upgrade pip setuptools; \
                pip install -r requirements.txt; \
                ./release_tag.py"
            '''
        }
      }
    }
  }
}
