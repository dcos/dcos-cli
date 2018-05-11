#!/usr/bin/env groovy

node('mac-hh-yosemite') {
    stage ('Pull dcos-cli repository') {
        dir('dcos-cli') {
            checkout scm
        }
    }

    stage ("Build dcos-cli MacOS Python binary") {
        dir('dcos-cli/cli') {
            sh "make binary"
            sh "dist/dcos"
        }
    }
}
