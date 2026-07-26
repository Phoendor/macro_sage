import requests


def download_audio(url, output_path):
    """Download audio file from the given URL."""
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"Audio file downloaded to {output_path}")
    else:
        raise Exception(f"Failed to download audio: {response.status_code}")


def fetch_text_from_url(url):
    """
    Fetch textual content from a given URL (for generic articles).
    """
    response = requests.get(url)
    if response.status_code == 200:
        print(f"Fetched text content from {url}")
        return response.text
    else:
        raise Exception(f"Failed to fetch text from URL: {response.status_code}")
