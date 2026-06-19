# Project Upgrade: Gen AI Vision Chat to Azure AI Foundry

## Overview

This project migrates from standalone Azure OpenAI setup to **Azure AI Foundry** with project-scoped authentication and model management.

## Current State

- **Services**: Azure OpenAI (Chat completions), Azure AI Vision (Image Analysis)
- **Authentication**: DefaultAzureCredential with separate endpoints
- **SDK**: `azure-ai-projects`, `openai`
- **Config Vars**: `PROJECT_CONNECTION`, `MODEL_DEPLOYMENT`

## Migration to Azure AI Foundry

### Status: ✅ ALREADY COMPATIBLE

This project **already uses Azure AI Foundry SDK** (`azure-ai-projects`). Minor updates needed for optimal integration:

### Current Code Structure

```python
from azure.ai.projects import AIProjectClient
from openai import AzureOpenAI

project_client = AIProjectClient(
    credential=DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True
    ),
    endpoint=project_endpoint,
)

openai_client = project_client.get_openai_client(api_version="2024-10-21")
```

## Recommended Updates

### 1. Update Environment Configuration

**Current .env**:

```
PROJECT_CONNECTION=<connection-string>
MODEL_DEPLOYMENT=<deployment-name>
```

**New .env (Preferred)**:

```
PROJECT_ENDPOINT=https://pro-code-agents-resource.services.ai.azure.com/api/projects/pro-code-agents
MODEL_DEPLOYMENT=gpt-4o
```

### 2. Simplify Authentication

**Current**:

```python
credential=DefaultAzureCredential(
    exclude_environment_credential=True,
    exclude_managed_identity_credential=True
)
```

**Recommended**:

```python
credential=DefaultAzureCredential()
```

The simplified version is more flexible and handles environment variables better.

### 3. Add Image Analysis Integration

Enhance the chat app to analyze images using Foundry's vision capabilities:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import os
from pathlib import Path
import base64

def load_image_as_base64(image_path: str) -> str:
    """Load image and convert to base64 for API transmission."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image_with_context(project_client, image_path: str, user_question: str):
    """Analyze image and answer questions about it."""

    openai_client = project_client.get_openai_client(api_version="2024-10-21")

    # Load image as base64
    image_data = load_image_as_base64(image_path)

    response = openai_client.chat.completions.create(
        model=os.environ["MODEL_DEPLOYMENT"],
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant in a grocery store that sells fruit. You provide detailed answers about produce in images."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_question},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ]
    )

    return response.choices[0].message.content
```

## Model Deployment Requirements

### Required Model Deployment

- **Model**: `gpt-4-turbo` or `gpt-4o` (supports vision)
- **Deployment Name**: Set in `MODEL_DEPLOYMENT` environment variable
- **API Version**: `2024-10-21` or later (supports vision)

### Deployment Steps (Azure Portal or CLI)

1. Navigate to Azure AI Foundry portal
2. Go to your project → Models + Endpoints
3. Deploy a vision-capable model (GPT-4 Turbo with Vision or GPT-4o)
4. Note the deployment name
5. Set `MODEL_DEPLOYMENT` environment variable

### Example Deployment Command (CLI)

```bash
az cognitiveservices account deployment create \
  --resource-group <resource-group> \
  --name <foundry-resource> \
  --deployment-id gpt-4o-vision \
  --model-name gpt-4o \
  --model-version "2024-08-06"
```

## Step-by-Step Migration

1. **Update Dependencies**:

   ```bash
   pip install --upgrade azure-ai-projects azure-identity openai
   ```

2. **Update Environment Variables**:

   - Replace `PROJECT_CONNECTION` with `PROJECT_ENDPOINT`
   - Ensure `MODEL_DEPLOYMENT` points to a vision-capable model

3. **Update Code** (if not already using PROJECT_ENDPOINT):

   ```python
   project_endpoint = os.getenv("PROJECT_ENDPOINT")

   project_client = AIProjectClient(
       endpoint=project_endpoint,
       credential=DefaultAzureCredential()
   )
   ```

4. **Add Vision Integration** (optional):

   - Use the code example above to add image analysis
   - Pass image paths from the command line

5. **Deploy Model**:
   - Ensure a vision-capable model is deployed in your Foundry project
   - Verify the deployment name matches `MODEL_DEPLOYMENT` environment variable

## Example Usage - Updated

```python
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

def main():
    os.system('cls' if os.name=='nt' else 'clear')

    try:
        # Load configuration
        load_dotenv()
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        # Initialize project client
        project_client = AIProjectClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential()
        )

        # Get OpenAI client from project
        openai_client = project_client.get_openai_client(api_version="2024-10-21")

        # System message
        system_message = "You are an AI assistant in a grocery store that sells fruit. You provide detailed answers to questions about produce."

        # Interactive loop
        while True:
            prompt = input("\nAsk a question about the image\n(or type 'quit' to exit)\n")
            if prompt.lower() == "quit":
                break
            elif len(prompt) == 0:
                print("Please enter a question.\n")
            else:
                # Get response from model
                response = openai_client.chat.completions.create(
                    model=model_deployment,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )

                print(f"\nResponse: {response.choices[0].message.content}\n")

    except Exception as ex:
        print(f"Error: {ex}")

if __name__ == "__main__":
    main()
```

## Troubleshooting

### Model Not Found

- **Error**: "The deployment 'gpt-4o' could not be found"
- **Solution**: Check your model deployment name in Foundry portal
- Ensure the model is deployed and available

### Vision Not Supported

- **Error**: "Vision is not supported by this model"
- **Solution**: Use GPT-4 Turbo with Vision or GPT-4o
- Update to API version 2024-10-21 or later

### Authentication Issues

- **Error**: "DefaultAzureCredential authentication failed"
- **Solution**: Run `az login` first
- Verify you have access to the Foundry project

## Related Resources

- [Azure AI Foundry Quickstart](https://learn.microsoft.com/en-us/azure/ai-foundry/quickstarts/get-started-code)
- [Azure OpenAI Vision Guide](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/vision)
- [Azure AI Projects SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-projects-readme)

## Notes

- This project is **already Foundry-compatible**
- Focus on updating environment variables and model deployment
- Vision requires a capable model deployment (GPT-4o or Turbo with Vision)
- Consider adding image analysis features to enhance the application
