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
            string(credentialsId: "3f0dbb48-de33-431f-b91c-2366d2f0e1cf", variable: "AWS_ACCESS_KEY_ID"),
            string(credentialsId: "f585ec9a-3c38-4f67-8bdb-79e5d4761937", variable: "AWS_SECRET_ACCESS_KEY"),
        ]) {
            sh '''
              bash -exc " \
                env; \
                cd scripts; \
                python -m venv env; \
                source env/bin/activate; \
                pip install -r requirements.txt; \
                ./release_tag.py"
            '''
        }
      }
    }
  }
}
