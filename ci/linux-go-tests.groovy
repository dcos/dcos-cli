#!/usr/bin/env groovy

node("mesos") {
    stage ('Pull dcos-cli repository') {
        dir('dcos-cli') {
            checkout scm
        }
    }

    dir('dcos-cli') {
        stage ("Test dcos-cli Go project") {
            sh "make test"
        }
    }
}
