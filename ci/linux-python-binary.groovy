#!/usr/bin/env groovy

node('py35') {
    ws ('/workspace') {
        stage ('Pull dcos-cli repository') {
            dir('dcos-cli') {
                checkout scm
            }
        }

        dir('dcos-cli/cli') {
            stage ("Build dcos-cli Linux Python binary") {
                sh "make binary"
                sh "dist/dcos"
            }
        }
    }
}
