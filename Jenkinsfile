pipeline {
    agent any

    environment {
        // Azure Configuration Details
        ACR_REGISTRY     = "internalauditreg.azurecr.io"
        IMAGE_NAME       = "internal-audit-app"
        RESOURCE_GROUP   = "internal-audit-app"
        ACA_APP_NAME     = "internal-audit-app"
        
        // Dynamically captures short Git Commit Hash for clean image versioning
        IMAGE_TAG        = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
    }

    stages {
        stage('Checkout') {
            steps {
                // Pulls your latest code using your SSH Deploy Key
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Building production Docker image with tag: ${IMAGE_TAG}..."
                // Builds and tags the image directly for your remote ACR registry
                sh "docker build -t ${ACR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('Push to Azure Container Registry (ACR)') {
            steps {
                // Securely logs into your ACR using your stored Jenkins credentials
                withCredentials([usernamePassword(credentialsId: 'azure-acr-credentials', usernameVariable: 'ACR_USER', passwordVariable: 'ACR_PASS')]) {
                    echo "Logging into Azure Container Registry..."
                    sh "docker login ${ACR_REGISTRY} -u ${ACR_USER} -p ${ACR_PASS}"
                    
                    echo "Pushing image to ACR..."
                    sh "docker push ${ACR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
                }
            }
        }

        stage('Deploy to Azure Container Apps (ACA)') {
            steps {
                // We bind BOTH your ACR login credentials AND your local Jenkins .env file secret
                withCredentials([
                    usernamePassword(credentialsId: 'azure-acr-credentials', usernameVariable: 'ACR_USER', passwordVariable: 'ACR_PASS'),
                    file(credentialsId: 'app-env-file', variable: 'ENV_FILE')
                ]) {
                    script {
                        // 1. This script reads your Jenkins secret file, strips newlines, 
                        // and formats it into a single clean line: KEY1=VAL1 KEY2=VAL2
                        def parsedEnvVars = sh(script: "cat ${ENV_FILE} | xargs | tr '\\n' ' '", returnStdout: true).trim()
                        
                        echo "Deploying to ACA and updating environment configurations dynamically..."
                        
                        // 2. We pass that variable string straight into the --set-env-vars flag
                        sh """
                        az containerapp update \
                        --name ${ACA_APP_NAME} \
                        --resource-group ${RESOURCE_GROUP} \
                        --image ${ACR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} \
                        --registry-server ${ACR_REGISTRY} \
                        --registry-username ${ACR_USER} \
                        --registry-password ${ACR_PASS} \
                        --set-env-vars ${parsedEnvVars}
                        """
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline executed perfectly. Your production FastAPI application is now live on ACA!"
            // Housekeeping: Removes the local image variant on the VM to prevent disk bloating
            sh "docker rmi ${ACR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} || true"
        }
        failure {
            echo "Pipeline failed. Please check the build logs above for troubleshooting details."
        }
    }
}