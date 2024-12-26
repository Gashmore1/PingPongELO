pipeline {
	agent {
		kubernetes {
			inheritFrom 'default'
			yaml '''
      spec:
        containers:
        - name: dind
          image: docker:dind
					securityContext:
						allowPrivilegeEscalation: true
						privileged: true
'''
		}
	}
	stages {
		stage('Build') {
			steps {
				echo 'Building..'
				sh 'docker build -t pingpongelo .'
      }
    }
    stage('Test') {
      steps {
				echo 'Testing..'
				sh 'docker run pingpongelo python tests/test_scoring.py'
				echo 'It failed'
      }
    }
    stage('Deploy') {
      steps {
        echo 'Deploying....'
			}
    }
  }
}
