from dotenv import load_dotenv
import os

from azure.identity import DefaultAzureCredential
import azure.cognitiveservices.speech as speech_sdk


def main():
    try:
        os.system('cls' if os.name == 'nt' else 'clear')

        load_dotenv()
        foundry_endpoint = os.getenv('FOUNDRY_ENDPOINT')

        credential = DefaultAzureCredential()

        translation_cfg = speech_sdk.translation.SpeechTranslationConfig(
            token_credential=credential,
            endpoint=foundry_endpoint
        )
        translation_cfg.speech_recognition_language = 'en-US'
        translation_cfg.add_target_language('fr')
        translation_cfg.add_target_language('es')
        translation_cfg.add_target_language('hi')
        audio_in_cfg = speech_sdk.AudioConfig(use_default_microphone=True)
        translator = speech_sdk.translation.TranslationRecognizer(
            translation_config=translation_cfg,
            audio_config=audio_in_cfg
        )
        print(f"Ready to translate from {translation_cfg.speech_recognition_language}")

        speech_cfg = speech_sdk.SpeechConfig(
            token_credential=credential,
            endpoint=foundry_endpoint
        )
        voices = {
            "fr": "fr-FR-HenriNeural",
            "es": "es-ES-ElviraNeural",
            "hi": "hi-IN-MadhurNeural"
        }
        print("Ready to use speech service.")

        print("\nSpeak now...")
        translation_results = translator.recognize_once_async().get()
        print(f"Translating '{translation_results.text}'")

        translations = translation_results.translations
        for language in translations:
            print(f"{language}: '{translations[language]}'")
            speech_cfg.speech_synthesis_voice_name = voices.get(language)
            audio_out_cfg = speech_sdk.audio.AudioOutputConfig(use_default_speaker=True)
            speech_synthesizer = speech_sdk.SpeechSynthesizer(speech_cfg, audio_out_cfg)
            speak = speech_synthesizer.speak_text_async(translations[language]).get()
            if speak.reason != speech_sdk.ResultReason.SynthesizingAudioCompleted:
                print(speak.reason)

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()
