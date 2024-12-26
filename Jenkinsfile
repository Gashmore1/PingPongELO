pipeline {
		agent {
				kubernetes {
						inheritFrom 'default'
						yaml '''
						spec:
							containers:
							- name: docker-build
								image: docker:dind
						'''
				}
		}

		stages {
        stage('Build') {
            steps {
                echo 'Building..'
								sh 'ls .'
								sh 'pwd'
								sh 'docker'
            }
        }
        stage('Test') {
            steps {
                echo 'Testing..'
            }
        }
        stage('Deploy') {
            steps {
                echo 'Deploying....'
						}
        }
    }
}
