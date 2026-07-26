import os
import shutil
import subprocess
import time

import requests
from pydub import AudioSegment

from get_data import download_audio


def process_audio_source(
        url,
        openai_api_key,
        use_local_whisper=False,
        local_whisper_model="base",
        local_whisper_device="cpu",
        compression_bitrate="64k"
):
    original_audio_path = "audio_sources/audio_temp_original.mp3"
    compressed_audio_path = "audio_sources/audio_temp_compressed.mp3"

    download_audio(url, original_audio_path)
    compress_audio(original_audio_path, compressed_audio_path, bitrate=compression_bitrate)

    if use_local_whisper:
        transcription = transcribe_audio_locally(
            compressed_audio_path,
            model=local_whisper_model,
            device=local_whisper_device
        )
    else:
        transcription = transcribe_audio_via_http(compressed_audio_path, openai_api_key)

    return transcription


def compress_audio(input_path, output_path, bitrate=None):
    if bitrate is None or bitrate.lower() == "original":
        # Skip compression; just copy the file
        print("Skipping compression. Using original audio...")
        shutil.copy(input_path, output_path)
    else:
        print(f"Compressing audio to {bitrate}...")
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="mp3", bitrate=bitrate)
        print(f"Compressed audio saved to {output_path}")


def transcribe_audio_via_http(audio_path, api_key):
    """
    Transcribe the audio using OpenAI Whisper API via HTTP (cloud-based).
    """
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    url = "https://api.openai.com/v1/audio/transcriptions"

    with open(audio_path, "rb") as audio_file:
        files = {
            "file": audio_file,
            "model": (None, "whisper-1")
        }
        print("Transcribing audio using Whisper API (cloud)...")
        response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        print("Transcription (cloud) completed.")
        return response.json()["text"]
    else:
        raise Exception(f"Failed to transcribe audio: {response.status_code}, {response.text}")


def transcribe_audio_locally(audio_path, model="base", device="cpu"):
    """
    Transcribe audio using Whisper locally.
    Requires the 'whisper' CLI tool installed.
    """
    print(f"Transcribing audio locally with model={model}, device={device}...")

    output_dir = os.path.dirname(os.path.abspath(audio_path))

    start_time = time.time()
    # Example command: whisper audio.mp3 --model base --device cpu --language en
    command = [
        "whisper",
        audio_path,
        "--model", model,
        "--device", device,
        "--output_dir", output_dir,
        "--language", "en"]
    subprocess.run(command, check=True)
    end_time = time.time()

    transcription_time = end_time - start_time
    print(f"Local transcription completed in {transcription_time:.2f} seconds.")

    txt_output = os.path.join(output_dir, os.path.splitext(os.path.basename(audio_path))[0] + ".txt")
    with open(txt_output, 'r', encoding='utf-8') as f:
        transcription = f.read().strip()

    return transcription
