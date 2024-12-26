pipeline {
	agent {
		kubernetes {
			inheritFrom 'default'
			yaml '''
      spec:
        containers:
        - name: dind
          image: docker:dind
          tty: true
          securityContext:
            allowPrivilegeEscalation: true
            privileged: true
'''
		}
	}
	stages {
		stage('Build') {
			steps {
        container('dind') {
				  echo 'Building..'
				  sh 'docker build -t pingpongelo .'
        }
			}
    }
    stage('Test') {
      steps {
        container('dind') {
				  echo 'Testing..'
				  sh 'docker run pingpongelo python tests/test_scoring.py'
				  echo 'It failed'
        }
			}
    }
    stage('Deploy') {
      steps {
        echo 'Deploying....'
			}
    }
  }
}
