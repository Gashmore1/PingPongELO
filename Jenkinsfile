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
	environment {
		DATABASE_CONFIG = credentials('testing_credentials')
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
				  sh "docker run -v $DATABASE_CONFIG:/home/app/conf_test.json pingpongelo python -m unittest tests/test_scoring.py"
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
