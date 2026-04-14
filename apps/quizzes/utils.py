from urllib.parse import urlparse


def is_youtube_url(youtube_url):
    """Checks if the given URL belongs to YouTube."""
    hostname = urlparse(youtube_url).hostname or ""
    allowed_hosts = ["youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be"]
    return hostname in allowed_hosts
