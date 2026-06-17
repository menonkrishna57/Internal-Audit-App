pipeline {
    agent any

    environment {
        // Defines the name of your Docker image
        IMAGE_NAME = "internal-audit-app"
        CONTAINER_NAME = "fastapi-audit-server"
        PORT_MAPPING = "8000:8000"
    }

    stages {
        stage('Checkout') {
            steps {
                // Pulls your latest code from the GitHub repository using your Deploy Key
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Building Docker image: ${IMAGE_NAME}..."
                // Builds the image using the local Dockerfile you provided
                sh "docker build -t ${IMAGE_NAME}:latest ."
            }
        }

        stage('Deploy Container') {
            steps {
                echo "Deploying container..."
                script {
                    // 1. Stop and remove the old container if it's already running
                    try {
                        sh "docker stop ${CONTAINER_NAME}"
                        sh "docker rm ${CONTAINER_NAME}"
                    } catch (Exception e) {
                        echo "No existing container found to stop. Proceeding to fresh deployment."
                    }
                    
                    // 2. Run the new container in detached mode (-d)
                    // It connects to the host network so it can communicate directly with Qdrant on port 6333
                    sh "docker run -d --name ${CONTAINER_NAME} -p ${PORT_MAPPING} ${IMAGE_NAME}:latest"
                }
            }
        }

        stage('Verify Health Check') {
            steps {
                echo "Verifying application deployment status..."
                // Gives the Uvicorn server 5 seconds to fully initialize
                sleep time: 5, unit: 'SECONDS'
                // Pings the container internally to make sure it's actively responding
                sh "docker ps | grep ${CONTAINER_NAME}"
            }
        }
    }

    post {
        success {
            echo "Pipeline executed perfectly. Your FastAPI application is now live on port 8000!"
        }
        failure {
            echo "Pipeline failed. Please review the build or deployment logs above."
        }
    }
}