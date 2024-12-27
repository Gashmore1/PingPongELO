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
		DATABASE_CONFIG = credentials('conf_test.json')
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
				  sh "docker run pingpongelo -v $DATABASE_CONFIG:/home/app/conf_test.json python -m unittest tests/test_scoring.py"
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
