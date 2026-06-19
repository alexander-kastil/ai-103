import os
import requests
import base64
from dotenv import load_dotenv

# Add references
from azure.identity import DefaultAzureCredential

def main(): 

    try: 
        # Get configuration settings 
        load_dotenv()
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")
        api_version = os.getenv("API_VERSION")

        print("Configuration:")
        print(f"  Endpoint: {project_endpoint}")
        print(f"  Model: {model_deployment}")
        print(f"  API Version: {api_version}\n")

        # Initialize prompts
        system_message = "You are an AI assistant for a produce supplier company."
        prompt = "Who was calling, and what did they want?"

        print("Getting a response ...\n")

        # Load local audio file
        print(f"Prompt: {prompt}\n")
        audio_file = os.path.join(os.path.dirname(__file__), "avocados.mp3")
        
        if not os.path.exists(audio_file):
            print(f"Error: Audio file not found at {audio_file}")
            return
            
        print(f"Loading local audio file: avocados.mp3")
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        audio_data = base64.b64encode(audio_bytes).decode('utf-8')
        print(f"Audio data encoded: {len(audio_data)} chars\n")

        # Use direct HTTP with bearer token
        from azure.identity import get_bearer_token_provider
        
        token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")
        token = token_provider()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Construct models endpoint from project endpoint
        resource_url = project_endpoint.split('/api/')[0]
        api_url = f"{resource_url}/models/chat/completions?api-version={api_version}"
        
        payload = {
            "model": model_deployment,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "input_audio", "input_audio": {"data": audio_data, "format": "mp3"}}
                ]}
            ]
        }
        
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("Response:")
            print(result['choices'][0]['message']['content'])
        else:
            print(f"Error ({response.status_code}): {response.text}")

    except Exception as ex:
        print(f"Error: {ex}")

    except Exception as ex:
        print(ex)


if __name__ == '__main__': 
    main()