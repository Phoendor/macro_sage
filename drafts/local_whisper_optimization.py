import os
import shutil
import get_data
import subprocess
import time
import tiktoken
from pydub import AudioSegment

def download_audio(url, output_path):
    """Download audio file from the given URL."""
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"Audio file downloaded to {output_path}")
    else:
        raise Exception(f"Failed to download audio: {response.status_code}")


def compress_audio(input_path, output_path, bitrate="64k"):
    """
    Compress audio to reduce file size, unless bitrate is None or "original".
    In that case, simply copy the file to output_path, effectively skipping compression.
    """
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

    start_time = time.time()
    # Example command: whisper audio.mp3 --model base --device cpu --language en
    command = [
        "whisper", audio_path,
        "--model", model,
        "--device", device,
        "--language", "en"
    ]
    subprocess.run(command, check=True)
    end_time = time.time()

    transcription_time = end_time - start_time
    print(f"Local transcription completed in {transcription_time:.2f} seconds.")

    # Whisper CLI typically generates a .txt file with the same prefix as audio_path
    txt_output = audio_path.rsplit('.', 1)[0] + ".txt"
    with open(txt_output, 'r', encoding='utf-8') as f:
        transcription = f.read().strip()

    return transcription


def fetch_text_from_url(url):
    """
    Fetch textual content from a given URL (e.g., for articles or blog posts).
    Adjust as needed for specific site formatting or scraping logic.
    """
    response = requests.get(url)
    if response.status_code == 200:
        print(f"Fetched text content from {url}")
        # Basic approach: just return raw HTML or text.
        # If the page is HTML, you might parse or extract <p> tags for clarity.
        # For now, let's just return the entire text content.
        return response.text
    else:
        raise Exception(f"Failed to fetch text from URL: {response.status_code}")


def split_text_into_token_chunks(text, max_chunk_size=3000, overlap_ratio=0.1):
    """
    Split text into chunks of up to max_chunk_size tokens.
    Overlap the next chunk by overlap_ratio (e.g., 10%) to maintain context.
    """
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    tokens = encoding.encode(text)

    overlap = int(max_chunk_size * overlap_ratio)
    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + max_chunk_size, len(tokens))
        chunk = encoding.decode(tokens[start:end])
        chunks.append(chunk)

        if end >= len(tokens):
            break
        # Move 'start' forward but preserve overlap
        start = end - overlap

    return chunks


def summarize_text_chunk(chunk, api_key, max_tokens=512, temperature=0.3):
    """
    Summarize a single chunk of text using GPT via HTTP.
    Temperature is set to 0.3 for more factual consistency.
    """
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    url = "https://api.openai.com/v1/chat/completions"

    prompt = f"""Read and summarize the following text in the given structured format:

Asset name: (e.g., USD, EUR, SEK, CEE FX)
Asset class: (e.g., currencies, stocks, metals, energy)
Author's view asset future price direction: (e.g., Up, Down, or Stable)
Rationale: Key reasons for the expected price direction, including:
 - Relevant economic data and market trends
 - Central bank policies and messaging
 - Geopolitical influences or external factors
 - Any specific forecasts, resistance/support levels, or anticipated events

Focus on thorough reasoning while maintaining brevity and clarity (~300-500 words).

{chunk}
"""

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    print("Summarizing text chunk...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        raise Exception(f"Failed to summarize text chunk: {response.status_code}, {response.text}")


def consolidate_summaries(summaries, api_key, max_tokens=700, temperature=0.3):
    """
    Consolidate multiple intermediate summaries into one final cohesive summary.
    Mention that chunks may overlap so GPT can remove redundancies.
    """
    if len(summaries) == 1:
        # If there's only one chunk, no need to consolidate.
        print("Only one chunk summary found; skipping final consolidation.")
        return summaries[0]

    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    url = "https://api.openai.com/v1/chat/completions"

    # Combine the summaries into a single text block:
    combined_summaries_text = ""
    for i, summary in enumerate(summaries, start=1):
        combined_summaries_text += f"\nSummary {i}:\n{summary}\n"

    prompt = f"""We have several partial summaries of a larger article. 
Please produce a final, cohesive summary that incorporates all key details 
and removes redundancies (note: the original chunks had ~10% overlap). 
Keep it concise yet thorough and consistent.
Stick to original structure of summaries as follows
Asset name: (e.g., USD, EUR, SEK, CEE FX)
Asset class: (e.g., currencies, stocks, metals, energy)
Author's view asset future price direction: (e.g., Up, Down, or Stable)
Rationale: Key reasons for the expected price direction, including:
 - Relevant economic data and market trends
 - Central bank policies and messaging
 - Geopolitical influences or external factors
 - Any specific forecasts, resistance/support levels, or anticipated events

Here are the intermediate summaries:
{combined_summaries_text}
"""

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    print("Consolidating intermediate summaries into one final summary...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        raise Exception(f"Failed to consolidate summaries: {response.status_code}, {response.text}")


def summarize_text(
    text,
    api_key,
    max_chunk_size=3000,
    overlap_ratio=0.1,
    temperature=0.3,
    max_tokens_chunk=512,
    max_tokens_final=700
):
    """
    Summarize the transcribed text or any plain text by:
      1) Splitting it into overlapping chunks
      2) Summarizing each chunk individually
      3) Consolidating all chunk summaries into one final summary (unless only 1 chunk)

    Args:
        text (str): The entire text to summarize
        api_key (str): OpenAI API key
        max_chunk_size (int): Token size limit for chunking
        overlap_ratio (float): Overlap between consecutive chunks (e.g. 0.1 for 10%)
        temperature (float): GPT temperature (0.0 - 2.0)
        max_tokens_chunk (int): max_tokens for the chunk-level summary
        max_tokens_final (int): max_tokens for the final consolidation
    """
    # 1) Split text into chunks
    chunks = split_text_into_token_chunks(
        text,
        max_chunk_size=max_chunk_size,
        overlap_ratio=overlap_ratio
    )
    summaries = []

    # 2) Summarize each chunk
    for i, chunk in enumerate(chunks, start=1):
        print(f"Processing chunk {i}/{len(chunks)}...")
        summary = summarize_text_chunk(
            chunk,
            api_key=api_key,
            max_tokens=max_tokens_chunk,
            temperature=temperature
        )
        summaries.append(summary)

    # 3) Consolidate chunk summaries (skip if only one)
    final_summary = consolidate_summaries(
        summaries,
        api_key=api_key,
        max_tokens=max_tokens_final,
        temperature=temperature
    )
    return final_summary


def process_audio_source(
    url,
    openai_api_key,
    use_local_whisper=False,
    local_whisper_model="base",
    local_whisper_device="cpu",
    compression_bitrate="64k"
):
    """
    Handle the entire flow for an audio source:
      1) Download
      2) Compress or skip
      3) Transcribe (local or cloud)
      4) Return the transcription
    """
    # Set up paths
    original_audio_path = "../audio_temp_original.mp3"
    compressed_audio_path = "../audio_temp_compressed.mp3"

    # 1: Download audio
    download_audio(url, original_audio_path)

    # 2: Compress audio (or skip if bitrate is None or "original")
    compress_audio(original_audio_path, compressed_audio_path, bitrate=compression_bitrate)

    # 3: Transcribe audio (local or cloud)
    if use_local_whisper:
        transcription = transcribe_audio_locally(
            compressed_audio_path,
            model=local_whisper_model,
            device=local_whisper_device
        )
    else:
        transcription = transcribe_audio_via_http(compressed_audio_path, openai_api_key)

    # Cleanup if desired:
    # os.remove(original_audio_path)
    # os.remove(compressed_audio_path)

    return transcription


def process_text_source(url):
    """
    Handle the entire flow for a text source:
      1) Fetch article or page content
      2) Return the text
    """
    return fetch_text_from_url(url)


def main():
    # --------------- USER SETTINGS ----------------#
    openai_api_key = "YOUR_OPENAI_API_KEY"
    use_local_whisper = True   # Set True to use local transcription
    local_whisper_model = "base"
    local_whisper_device = "cpu"
    compression_bitrate = "64k"

    # List of sources: audio or text
    sources = [
        {
            "type": "text",
            "url": "https://think.ing.com/articles/the-commodities-feed-gas-rallies-on-supply-risks120424/"
        },
        {
            "type": "audio",
            "url": (
                "https://dcs-spotify.megaphone.fm/"
                "ALFINVESTMENTSTRATEGYBV4832558841.mp3?"
                "key=f0aae9f5e6eae7e655274c61eb2744b5&request_event_id=a3e82909-0a08-436a-b6a9-6205cf788fcd&timetoken=1737833476_018377A49DDF4D6C5B6354295ED11F3C"
            )
        }
    ]

    # Iterate over sources and process each one
    for idx, source in enumerate(sources, start=1):
        print(f"\n--- Processing Source {idx}/{len(sources)} ---")
        source_type = source["type"]
        source_url = source["url"]

        try:
            if source_type.lower() == "audio":
                # Process the audio source
                text_data = process_audio_source(
                    url=source_url,
                    openai_api_key=openai_api_key,
                    use_local_whisper=use_local_whisper,
                    local_whisper_model=local_whisper_model,
                    local_whisper_device=local_whisper_device,
                    compression_bitrate=compression_bitrate
                )
            else:
                # Process the text source
                text_data = process_text_source(source_url)

            # Summarize
            summary = summarize_text(
                text_data,
                api_key=openai_api_key,
                max_chunk_size=3000,
                overlap_ratio=0.1,
                temperature=0.3,
                max_tokens_chunk=512,
                max_tokens_final=700
            )

            print("\nFinal Summary:\n", summary)

        except Exception as e:
            print(f"Error processing source '{source_url}': {e}")


if __name__ == "__main__":
    main()
