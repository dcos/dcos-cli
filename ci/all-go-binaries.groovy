#!/usr/bin/env groovy

node("mesos") {
    stage ('Pull dcos-cli repository') {
        dir('dcos-cli') {
            checkout scm
        }
    }

    dir('dcos-cli') {
        stage ("Build dcos-cli Go binaries") {
            sh "make linux darwin windows"
        }
    }
}
