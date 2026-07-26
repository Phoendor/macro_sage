import requests

from text_tools import split_text_into_token_chunks


def summarize_corpus(
    text,
    api_key,
    model="gpt-4.1-mini",
    max_tokens=4000,
    temperature=0.1,
):
    """
    Feed the full day's corpus (≤ 1 M tokens) to GPT-4.1 mini in *one* call.
    Returns the model's concise market wrap.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}

    system_msg = (
        "You are a senior macro strategist at a global investment bank. "
        "You receive the day's entire feed – articles, sell-side notes and "
        "podcast transcripts. Produce a bullet-point market wrap **per asset**, "
        "with the following structure:\n\n"
        "Asset name:\nAsset class:\nConsensus price bias (Up / Down / Stable):\n"
        "Key drivers:\n"
        "- ...\n"
        "- ...\n\n"
        "Close with a 5-line Top-Risk checklist."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": text},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "seed": 42,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=900)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    raise RuntimeError(f"GPT call failed {resp.status_code}: {resp.text}")

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
    Summarize text by:
      1) Splitting it into overlapping chunks
      2) Summarizing each chunk
      3) Consolidating all chunk summaries into one final summary (unless only 1 chunk)
    """
    chunks = split_text_into_token_chunks(
        text,
        max_chunk_size=max_chunk_size,
        overlap_ratio=overlap_ratio
    )
    summaries = []

    for i, chunk in enumerate(chunks, start=1):
        print(f"Processing chunk {i}/{len(chunks)}...")
        summary = summarize_text_chunk(
            chunk,
            api_key=api_key,
            max_tokens=max_tokens_chunk,
            temperature=temperature
        )
        summaries.append(summary)

    final_summary = consolidate_summaries(
        summaries,
        api_key=api_key,
        max_tokens=max_tokens_final,
        temperature=temperature
    )
    return final_summary


def summarize_text_chunk(chunk, api_key, max_tokens=512, temperature=0.3):
    """
    Summarize a single chunk of text using GPT via HTTP.
    """
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    url = "https://api.openai.com/v1/chat/completions"

    prompt = f"""Read and summarize the given text in the following structured format for each relevant asset discussed:

1. Asset name: Clearly identify the specific asset being discussed (e.g., EURUSD, European equities, Apple, Gold).
2. Asset class: Specify the asset's class, such as currencies, stocks, metals, energy, or bonds.
3. Author's view asset future price direction: State the author’s perspective on the asset’s future price direction (e.g., Up, Down, or Stable).
4. Rationale: Provide a concise explanation of the key reasons behind the expected price direction, focusing on:
 - Relevant economic, geopolitical, or technical factors.
 - Central bank policies or macroeconomic divergences.
 - Market trends, sentiment, or specific forecasts (e.g., key support/resistance levels).
 - Any notable risks or influencing events.

Ensure the summary captures the main insights and implications for each asset as discussed in the text, while maintaining clarity and brevity.

{chunk}
"""

    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a financial analyst specializing in market reports. Always summarize the text in a structured format, providing clear and concise answers."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    print("Summarizing text chunk...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        print(response.json()["choices"][0]["message"]["content"].strip())
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

        prompt = f"""
        We have several partial summaries of a larger article. Each partial summary may mention one or more assets.
        Please produce a FINAL, COHESIVE summary, ensuring the structure below is used for EACH DISTINCT asset mentioned.

        ---
        Required Structure for EACH asset:

        Asset name: 
        Asset class: 
        Author's view asset future price direction: (Up, Down, or Stable)
        Rationale: Provide combined reasons from all partial summaries, including:
         - Relevant economic data and market trends
         - Central bank policies and messaging
         - Geopolitical influences or external factors
         - Any specific forecasts, resistance/support levels, or anticipated events

        ---

        Key Instructions:
        1. If multiple partial summaries mention the SAME asset, unify them into a SINGLE entry (do NOT duplicate).
        2. Keep each asset in its OWN section. Do NOT combine multiple assets under a single 'Asset name' heading.
        3. Remove redundancies caused by chunk overlaps (there was ~10% overlap).
        4. Keep it concise yet thorough and consistent.

        Here are the intermediate summaries:
        {combined_summaries_text}
        """

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a financial analyst specializing in market reports. Always summarize the text in a structured format, providing clear and concise answers."},
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
