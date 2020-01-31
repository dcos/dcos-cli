#!/usr/bin/env groovy

pipeline {
  agent none
   environment {
    GITHUB_TOKEN = credentials('gh-token-mesosphere-ci-dcos-deploy')
    APPLE_DEVACC = credentials('TEMP_APPLE_DEVELOPER_ACCOUNT')
    GOLANG_VER = "1.13.7"
    GON_VER = "0.2.2"
    SHA1_CERTIFICATE_ID = "5C99CF2B12B186C69A37BD21DFF24ACBE10560CF"
  }

  options {
    timeout(time: 6, unit: 'HOURS')
  }

  stages {
    stage("Build binaries") {
      agent {
        label "mac"
      }

      steps {
        ansiColor('xterm') {
          sh '''
              security delete-keychain jenkins-${JOB_NAME} || :
              security create-keychain -p test jenkins-${JOB_NAME}
              security unlock-keychain -p test jenkins-${JOB_NAME}
              security list-keychains -d user -s jenkins-${JOB_NAME}
              security default-keychain -s jenkins-${JOB_NAME}
              cat ${SIGNING_CERTIFICATE} > cert.p12
              security import cert.p12 -k jenkins-${JOB_NAME} -P ${SIGNING_CERTIFICATE_PASSWORD} -T /usr/bin/codesign
              security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k test jenkins-${JOB_NAME}
              xcrun altool --notarization-history 0 -u "${APPLE_DEVACC_USR}" -p "${APPLE_DEVACC_PSW}"
            '''
          sh 'security find-identity -v | grep -q ${SHA1_CERTIFICATE_ID}'
          sh '''
            bash -exc " \
              export VERSION=\"${TAG_NAME:-$GIT_COMMIT}\";
              make linux darwin windows"
          '''
          sh 'mkdir -p ${WORKSPACE}/usr/local/bin'
          sh 'wget -O /tmp/gon.zip https://github.com/mitchellh/gon/releases/download/v\${GON_VER}/gon_\${GON_VER}_macos.zip && unzip /tmp/gon.zip -d ${WORKSPACE}/usr/local/bin'
          sh '''
              export PATH=$PATH:${WORKSPACE}/usr/local/bin
              export AC_USERNAME="${APPLE_DEVACC_USR}"
              export AC_PASSWORD="${APPLE_DEVACC_PSW}"
              gon ci/release.hcl
          '''
          stash includes: 'build/**', name: 'dcos-binaries'
        }
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
