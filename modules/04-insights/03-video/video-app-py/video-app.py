import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    load_dotenv()
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    model_deployment = os.getenv('MODEL_DEPLOYMENT')

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )

    client = OpenAI(
        base_url=endpoint,
        api_key=token_provider,
    )

    # Generate a video from a text prompt
    print("Generating video from text prompt...")
    video = client.videos.create(
        model=model_deployment,
        prompt="A peaceful mountain lake at sunrise with mist rising from the water",
        size="1280x720",
        seconds='4',
    )
    print(f"Job ID: {video.id}")
    video = poll_video_status(client, video.id)

    if video.status == "completed":
        download_video(client, video.id, "text_video.mp4")
    else:
        print(f"Video generation failed with status: {video.status}")

    # Generate a video from a reference image (if available)
    ref_image = "reference.png"
    if os.path.exists(ref_image):
        print(f"\nGenerating video from reference image '{ref_image}'...")
        with open(ref_image, "rb") as img:
            video = client.videos.create(
                model=model_deployment,
                prompt="The scene comes to life with gentle movement and ambient lighting",
                size="1280x720",
                seconds='4',
                input_reference=img,
            )
        print(f"Job ID: {video.id}")
        video = poll_video_status(client, video.id)
        if video.status == "completed":
            download_video(client, video.id, "image_video.mp4")
    else:
        print(f"\nSkipping image-based video ('{ref_image}' not found).")


def poll_video_status(client, video_id):
    video = client.videos.retrieve(video_id)
    while video.status not in ["completed", "failed", "cancelled"]:
        print(f"  Status: {video.status} — waiting 20 seconds...")
        time.sleep(20)
        video = client.videos.retrieve(video_id)
    print(f"  Final status: {video.status}")
    return video


def download_video(client, video_id, filename):
    print(f"Downloading video to '{filename}'...")
    content = client.videos.download_content(video_id, variant="video")
    content.write_to_file(filename)
    print(f"Saved: {filename}")


if __name__ == "__main__":
    main()
