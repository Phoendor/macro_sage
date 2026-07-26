import get_data
import feedparser
from io import BytesIO

# feed_url = "https://www.home.saxo/insights/content-hub/rss/articles"
feed_url = "https://think.ing.com/rss/"

# 1) Make an HTTP GET request, ignoring SSL cert errors
response = requests.get(feed_url, verify=False)

# 2) Parse the raw content using feedparser
feed_data = feedparser.parse(BytesIO(response.content))

# 3) Now loop through entries
for entry in feed_data.entries:
    title = entry.title
    link = entry.link
    published = getattr(entry, 'published', 'No date')
    print(f"Title: {title}\nLink: {link}\nDate: {published}\n")
