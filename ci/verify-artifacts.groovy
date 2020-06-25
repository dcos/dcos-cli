#!/usr/bin/env groovy

def GITHUB_TOKEN = string(credentialsId: 'd146870f-03b0-4f6a-ab70-1d09757a51fc', variable: 'GITHUB_TOKEN')
def SLACK_TOKEN = string(credentialsId: '8b793652-f26a-422f-a9ba-0d1e47eb9d89', variable: 'SLACK_TOKEN')


pipeline {
  agent none

  options {
    timeout(time: 6, unit: 'HOURS')
  }

  stages {
    stage('Verify artifacts') {
      parallel {
        stage("Verify Linux artifacts") {
          agent { label 'py36' }

          steps {
            withCredentials([GITHUB_TOKEN]) {
              sh '''
                bash -exc " \
                  cd ci; \
                  python3 -m venv env; \
                  source env/bin/activate; \
                  pip install -r requirements.txt; \
                  ./verify-artifacts.py"
              '''
            }
          }
        }

        stage("Verify macOS artifacts") {
          agent { label 'mac-hh-yosemite' }
          steps {
            withCredentials([GITHUB_TOKEN]) {
              sh '''
                bash -exc " \
                  cd ci; \
                  python3 -m venv env; \
                  source env/bin/activate; \
                  pip install -r requirements.txt; \
                  ./verify-artifacts.py"
              '''
            }
          }
        }

        stage("Verify Windows artifacts") {
          agent {
            node {
              label 'windows'
              customWorkspace 'C:\\windows\\workspace'
            }
          }

          steps {
            withCredentials([GITHUB_TOKEN]) {
              bat '''
                bash -exc " \
                  cd ci; \
                  python -m venv env; \
                  env/Scripts/python -m pip install -U pip; \
                  env/Scripts/pip install -r requirements.txt; \
                  env/Scripts/python ./verify-artifacts.py"
              '''
            }
          }
        }
      }
    }
  }

  post {
    failure {
      withCredentials([SLACK_TOKEN]) {
        slackSend (
          channel: "#dcos-cli-ci",
          color: "danger",
          message: "CLI artifacts verification failed... :crying:\n${env.RUN_DISPLAY_URL}",
          teamDomain: "mesosphere",
          token: "${env.SLACK_TOKEN}",
        )
      }
    }
  }
}
