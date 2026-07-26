import tiktoken

from get_data import fetch_text_from_url


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


def process_text_source(url):
    """
    Generic handler for text-based URLs (non-ING).
    """
    return fetch_text_from_url(url)
