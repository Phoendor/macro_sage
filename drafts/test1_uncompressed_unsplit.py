import os

import requests


def _required_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    return api_key


def download_audio(url, output_path):
    """Download audio file from the given URL."""
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, "wb") as file_handle:
            file_handle.write(response.content)
        print(f"Audio file downloaded to {output_path}")
    else:
        raise Exception(f"Failed to download audio: {response.status_code}")


def transcribe_audio_via_http(audio_path):
    """Transcribe the audio using OpenAI Whisper API via HTTP."""
    headers = {"Authorization": f"Bearer {_required_api_key()}"}
    url = "https://api.openai.com/v1/audio/transcriptions"

    with open(audio_path, "rb") as audio_file:
        files = {"file": audio_file, "model": (None, "whisper-1")}
        print("Transcribing audio using Whisper...")
        response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        print("Transcription completed.")
        return response.json()["text"]
    raise Exception(f"Failed to transcribe audio: {response.status_code}, {response.text}")


def summarize_text(text):
    """Summarize the transcribed text using OpenAI GPT API."""
    headers = {"Authorization": f"Bearer {_required_api_key()}"}
    url = "https://api.openai.com/v1/chat/completions"

    prompt = "Summarize the following content in a concise and clear manner:\n\n" f"{text}"
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    }

    print("Summarizing text...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("Summarization completed.")
        return response.json()["choices"][0]["message"]["content"].strip()
    raise Exception(f"Failed to summarize text: {response.status_code}, {response.text}")


def main():
    audio_url = (
        "https://d3ctxlq1ktw2nl.cloudfront.net/staging/2024-3-11/"
        "b5a137a6-b707-b738-c090-616e1ae4a712.mp3"
    )
    audio_path = "audio.mp3"

    try:
        download_audio(audio_url, audio_path)
    except Exception as exc:
        print(f"Error during audio download: {exc}")
        return

    try:
        transcription = transcribe_audio_via_http(audio_path)
    except Exception as exc:
        print(f"Error during transcription: {exc}")
        return

    try:
        summary = summarize_text(transcription)
        print("\nSummary:\n", summary)
    except Exception as exc:
        print(f"Error during summarization: {exc}")


if __name__ == "__main__":
    main()
