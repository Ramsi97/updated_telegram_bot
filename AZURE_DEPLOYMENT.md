# ☁️ Azure Deployment Guide (Student Credits)

This guide will help you deploy your Telegram Bot to Azure using **Web App for Containers**. This is the best method for your FastAPI bot.

## Prerequisites
1.  **Azure Student Account**: Make sure you have activated your credits at [azure.microsoft.com/free/students](https://azure.microsoft.com/free/students/).
2.  **Azure CLI**: Install it on your machine ([Instructions here](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)).

---

## 🏗️ Step 1: Create Azure Resources
Open your terminal and run these commands:

1.  **Login to Azure**:
    ```bash
    az login
    ```

2.  **Create a Resource Group**:
    ```bash
    az group create --name BotResourceGroup --location eastus
    ```

3.  **Create an Azure Container Registry (ACR)**: 
    *(Choose a unique name instead of `mybotregistry`)*
    ```bash
    az acr create --resource-group BotResourceGroup --name mybotregistry --sku Basic
    ```

---

## 📤 Step 2: Build and Push your Docker Image

### Option A: Build in the Cloud (Recommended)
This is faster and avoids upload issues with large images. It builds directly in Azure.
1.  **Build in Azure**:
    *(Replace `nationald` with your registry name)*
    ```bash
    az acr build --registry nationald --image national-id-bot:latest .
    ```

### Option B: Build Locally and Push
1.  **Login to your Registry**:
    ```bash
    az acr login --name nationald
    ```

2.  **Build Locally**:
    ```bash
    docker build -t national-id-bot .
    ```

3.  **Tag your local image**:
    ```bash
    docker tag national-id-bot nationald.azurecr.io/national-id-bot:latest
    ```

4.  **Push the image**:
    ```bash
    docker push nationald.azurecr.io/national-id-bot:latest
    ```

---

## 🌐 Step 3: Create the Web App
1.  **Create an App Service Plan** (Free/B1 tier for students):
    ```bash
    az appservice plan create --name BotServicePlan --resource-group BotResourceGroup --sku B1 --is-linux
    ```

2.  **Create the Web App**:
    ```bash
    az webapp create --resource-group BotResourceGroup --plan BotServicePlan --name my-unique-bot-app --deployment-container-image-name mybotregistry.azurecr.io/national-id-bot:v1
    ```

---

## ⚙️ Step 4: Final Configuration
1.  **Enable Admin Access for ACR** (So the web app can pull the image):
    ```bash
    az acr update -n mybotregistry --admin-enabled true
    ```

2.  **Set Environment Variables**:
    Go to the **Azure Portal** -> Your Web App -> **Configuration** -> **New application setting**. Add the following:
    - `TELEGRAM_TOKEN`: (Your bot token)
    - `WEBHOOK_URL`: `https://my-unique-bot-app.azurewebsites.net`
    - `REQUIRED_GROUP_ID`: (Your group ID)

3.  **Set the Port**:
    Add another setting: `WEBSITES_PORT` with value `8000`.

---

## 🔗 Step 5: Update Telegram Webhook
Visit this URL in your browser to tell Telegram to send updates to Azure:
`https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://my-unique-bot-app.azurewebsites.net/webhook`

---
✅ **Done!** Your bot is now running in the cloud.
