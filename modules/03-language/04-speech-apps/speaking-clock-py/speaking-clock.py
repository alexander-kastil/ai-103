import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI


def print_banner(title: str) -> None:
	print("\n" + "=" * 80)
	print(title)
	print("=" * 80)


def main() -> None:
	root = Path(__file__).resolve().parent
	load_dotenv()
	ai_service_endpoint = os.getenv("AI_SERVICE_ENDPOINT")
	ai_service_key = os.getenv("AI_SERVICE_KEY")
	transcribe_model = os.getenv("TRANSCRIBE_MODEL_DEPLOYMENT")
	speak_model = os.getenv("SPEAK_MODEL_DEPLOYMENT")

	print_banner("Speaking Clock - Azure AI Foundry")

	# Validate endpoint: must be Azure OpenAI/Foundry endpoint (openai.azure.com)
	if not ai_service_endpoint or ".openai.azure.com" not in ai_service_endpoint:
		print("Error: AI_SERVICE_ENDPOINT must be your Azure OpenAI/Foundry endpoint (…openai.azure.com)")
		print("Current endpoint:", ai_service_endpoint or "<not set>")
		print("Update your .env to the OpenAI endpoint shown in Foundry → Model Deployments → Keys and Endpoint.")
		return

	# Initialize Azure OpenAI client
	client = AzureOpenAI(
		api_key=ai_service_key,
		api_version="2024-10-01-preview",
		azure_endpoint=ai_service_endpoint,
	)

	# Get spoken input
	command = transcribe_command(client, root, transcribe_model)
	if command.lower() == "what time is it?":
		tell_time(client, root, speak_model)
	else:
		print("\nCommand not recognized. Expected: 'What time is it?'")


def transcribe_command(client: AzureOpenAI, root: Path, model_deployment: str) -> str:
	"""Transcribe speech from audio file using deployed model."""
	command = ""

	# Check audio file exists
	audio_file = root / "time.wav"
	if not audio_file.exists():
		print(f"Error: Audio file not found at {audio_file}")
		return command

	# Transcribe using Azure OpenAI
	print("Transcribing audio...")
	try:
		with open(audio_file, "rb") as f:
			transcript = client.audio.transcriptions.create(
				model=model_deployment,
				file=f,
				language="en",
			)
		command = transcript.text
		print(f"Recognized: {command}")
	except FileNotFoundError:
		print(f"Error: Could not open audio file {audio_file}")
	except Exception as e:
		print(f"Transcription error: {str(e)}")
		print("Hint: Ensure the deployment name exists under your OpenAI resource and matches TRANSCRIBE_MODEL_DEPLOYMENT.")
		print("Foundry path: OpenAI resource → Model Deployments → Deployment name (e.g., gpt-4o-transcribe)")

	return command


def tell_time(client: AzureOpenAI, root: Path, speak_model: str) -> None:
	"""Synthesize current time as speech using deployed TTS model."""
	now = datetime.now()
	response_text = f"The time is {now.hour}:{now.minute:02d}"

	# Synthesize using Azure OpenAI TTS
	output_file = root / "output.wav"
	print("\nSynthesizing speech...")
	try:
		response = client.audio.speech.create(
			model=speak_model,
			voice="alloy",
			input=response_text,
		)
		# Write binary content to file
		with open(output_file, "wb") as f:
			f.write(response.content)
		print(f"Spoken output saved to {output_file}")
	except Exception as e:
		print(f"Synthesis error: {str(e)}")
		print(f"Note: Deploy '{speak_model}' model (tts or tts-hd) in Azure AI Foundry")

	# Print the response
	print(f"Text response: {response_text}")


if __name__ == "__main__":
	main()