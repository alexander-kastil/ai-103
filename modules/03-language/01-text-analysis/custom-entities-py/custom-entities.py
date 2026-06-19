import os
import re
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential


def print_banner(title: str) -> None:
	print("\n" + "=" * 80)
	print(title)
	print("=" * 80)


def main() -> None:
	root = Path(__file__).resolve().parent
	load_dotenv()
	AI_SERVICE_ENDPOINT = os.getenv("AI_SERVICE_ENDPOINT")
	AI_SERVICE_KEY = os.getenv("AI_SERVICE_KEY")
	MODEL_VERSION = os.getenv("MODEL_VERSION") or "latest"

	if not AI_SERVICE_ENDPOINT or not AI_SERVICE_KEY:
		raise RuntimeError(
			"Missing AI_SERVICE_ENDPOINT or AI_SERVICE_KEY. Set them in your .env file or environment variables."
		)

	if MODEL_VERSION != "latest" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", MODEL_VERSION):
		print(f"Warning: MODEL_VERSION '{MODEL_VERSION}' is not valid; using 'latest'.")
		MODEL_VERSION = "latest"

	client = TextAnalyticsClient(endpoint=AI_SERVICE_ENDPOINT, credential=AzureKeyCredential(AI_SERVICE_KEY))

	ads_dir = root.parent / "ads"
	for path in sorted(ads_dir.glob("*.txt")):
		text = path.read_text(encoding="utf-8").strip()
		print_banner(f"Processing: {path.name}")

		results = client.recognize_entities(
			documents=[{"id": path.stem, "text": text, "language": "en"}],
			model_version=MODEL_VERSION,
		)
		for result in results:
			if result.is_error:
				print(f"Error: {result.error.code} - {result.error.message}")
				continue
			for entity in result.entities:
				print(f"- {entity.text} | {entity.category}", end="")
				if entity.subcategory:
					print(f"/{entity.subcategory}", end="")
				print(f" | confidence={entity.confidence_score}")


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		print("\nInterrupted.")
