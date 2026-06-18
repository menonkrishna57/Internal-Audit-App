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
                withCredentials([usernamePassword(credentialsId: 'container-registry', usernameVariable: 'ACR_USER', passwordVariable: 'ACR_PASS')]) {
                    echo "Logging into Azure Container Registry..."
                    sh "docker login ${ACR_REGISTRY} -u ${ACR_USER} -p ${ACR_PASS}"
                    
                    echo "Pushing image to ACR..."
                    sh "docker push ${ACR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
                }
            }
        }

        stage('Deploy to Azure Container Apps (ACA)') {
            steps {
                withCredentials([
                    usernamePassword(credentialsId: 'azure-acr-credentials', usernameVariable: 'ACR_USER', passwordVariable: 'ACR_PASS'),
                    usernamePassword(credentialsId: 'azure-sp-credentials', usernameVariable: 'AZURE_CLIENT_ID', passwordVariable: 'AZURE_CLIENT_SECRET'),
                    file(credentialsId: 'app-env-file', variable: 'ENV_FILE')
                ]) {
                    script {
                        echo "Authenticating with Azure and deploying dynamically..."
                        
                        // Clean up the environment file variables into a flat string
                        def parsedEnvVars = sh(
                            script: "cat \${ENV_FILE} | tr '\\n' ' ' | tr '\\r' ' ' | xargs", 
                            returnStdout: true
                        ).trim()
                        
                        env.PARSED_ENV_VARS = parsedEnvVars
                        
                        // Define your Azure Tenant ID here
                        env.AZURE_TENANT_ID = "27c62613-4d10-47aa-bb1f-4e00a75c6a37" // <== Paste your actual tenantId from the JSON block

                        sh '''
                        # 1. Authenticate Azure CLI using the Service Principal
                        az login --service-principal \
                          -u "${AZURE_CLIENT_ID}" \
                          -p "${AZURE_CLIENT_SECRET}" \
                          --tenant "${AZURE_TENANT_ID}"

                        # 2. Link your private ACR registry to the Container App
                        az containerapp registry set \
                          --name "${ACA_APP_NAME}" \
                          --resource-group "${RESOURCE_GROUP}" \
                          --server "${ACR_REGISTRY}" \
                          --username "${ACR_USER}" \
                          --password "${ACR_PASS}"

                        # 3. Update the container app deployment with the new image and env vars
                        az containerapp update \
                          --name "${ACA_APP_NAME}" \
                          --resource-group "${RESOURCE_GROUP}" \
                          --image "${ACR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" \
                          --set-env-vars ${PARSED_ENV_VARS}
                        '''
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