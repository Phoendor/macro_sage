import os

import requests
from pydub import AudioSegment


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


def compress_audio(input_path, output_path, bitrate="64k"):
    """Compress audio to reduce file size."""
    print("Compressing audio...")
    audio = AudioSegment.from_file(input_path)
    audio.export(output_path, format="mp3", bitrate=bitrate)
    print(f"Compressed audio saved to {output_path}")


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


def split_text(text, max_tokens=8000):
    """Split text into smaller chunks based on token limits."""
    print("Splitting text into smaller chunks...")
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        current_length += len(word) + 1
        if current_length > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = len(word) + 1
        current_chunk.append(word)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    print(f"Split text into {len(chunks)} chunks.")
    return chunks


def summarize_text_chunk(chunk):
    """Summarize a single chunk of text using GPT."""
    headers = {"Authorization": f"Bearer {_required_api_key()}"}
    url = "https://api.openai.com/v1/chat/completions"
    prompt = "Summarize the following content in a concise and clear manner:\n\n" f"{chunk}"
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    }

    print("Summarizing text chunk...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    raise Exception(f"Failed to summarize text chunk: {response.status_code}, {response.text}")


def summarize_text(text):
    """Summarize the transcribed text by processing it in chunks."""
    chunks = split_text(text)
    summaries = []

    for index, chunk in enumerate(chunks):
        print(f"Processing chunk {index + 1}/{len(chunks)}...")
        summary = summarize_text_chunk(chunk)
        summaries.append(summary)

    print("Combining chunk summaries...")
    return " ".join(summaries)


def main():
    audio_url = (
        "https://dcs-spotify.megaphone.fm/"
        "ALFINVESTMENTSTRATEGYBV4832558841.mp3"
    )
    original_audio_path = "audio.mp3"
    compressed_audio_path = "compressed_audio.mp3"

    try:
        download_audio(audio_url, original_audio_path)
    except Exception as exc:
        print(f"Error during audio download: {exc}")
        return

    try:
        compress_audio(original_audio_path, compressed_audio_path)
    except Exception as exc:
        print(f"Error during audio compression: {exc}")
        return

    try:
        transcription = transcribe_audio_via_http(compressed_audio_path)
    except Exception as exc:
        print(f"Error during transcription: {exc}")
        return

    try:
        summary = summarize_text(transcription)
        print("\nFinal Summary:\n", summary)
    except Exception as exc:
        print(f"Error during summarization: {exc}")


if __name__ == "__main__":
    main()
