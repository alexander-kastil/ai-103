from dotenv import load_dotenv
import os

from azure.identity import DefaultAzureCredential
from azure.ai.translation.text import TextTranslationClient
from azure.ai.translation.text.models import InputTextItem


def main():
    try:
        os.system('cls' if os.name == 'nt' else 'clear')

        load_dotenv()
        foundry_endpoint = os.getenv('FOUNDRY_ENDPOINT')

        credential = DefaultAzureCredential()
        client = TextTranslationClient(credential=credential, endpoint=foundry_endpoint)

        languages_response = client.get_supported_languages(scope="translation")
        print(f"{len(languages_response.translation)} languages supported.")
        print("(See https://learn.microsoft.com/azure/ai-services/translator/language-support#translation)")
        print("Enter a target language code for translation (for example, 'en'):")

        target_language = "xx"
        supported_language = False
        while not supported_language:
            target_language = input()
            if target_language in languages_response.translation.keys():
                supported_language = True
            else:
                print(f"{target_language} is not a supported language.")

        input_text = ""
        while input_text.lower() != "quit":
            input_text = input("Enter text to translate ('quit' to exit): ")
            if input_text != "quit":
                input_text_elements = [InputTextItem(text=input_text)]
                translation_response = client.translate(body=input_text_elements, to_language=[target_language])
                translation = translation_response[0] if translation_response else None
                if translation:
                    source_language = translation.detected_language
                    for translated_text in translation.translations:
                        print(f"'{input_text}' was translated from {source_language.language} to {translated_text.to} as '{translated_text.text}'.")

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
