import logging
import os
import re
import requests

# Get a logger for this module
logger = logging.getLogger(__name__)


def download_video_vimeo(vimeo_url: str, download_directory: str, access_token: str) -> str:
    """
    Downloads a video from a Vimeo URL.

    Args:
        vimeo_url: The full URL of the Vimeo video.
        download_directory: The directory where the video will be saved.
        access_token: The Vimeo API access token.

    Returns:
        The full path to the downloaded video file on success.

    Raises:
        ValueError: If the Vimeo URL is invalid.
        IOError: If no downloadable files are found or a file system error occurs.
        requests.exceptions.RequestException: If an API or network error occurs.
    """
    logger.info("Starting video download process for URL: %s", vimeo_url)
    
    try:
        # Ensure the target directory exists
        os.makedirs(download_directory, exist_ok=True)

        # 1. Extract video ID from URL
        video_id_match = re.search(r"vimeo\.com/(\d+)", vimeo_url)
        if not video_id_match:
            logger.error("Invalid Vimeo URL format. Could not extract video ID from: %s", vimeo_url)
            raise ValueError("Invalid Vimeo URL format.")
        video_id = video_id_match.group(1)
        logger.info("Extracted Video ID: %s", video_id)

        # 2. Fetch video metadata from Vimeo API
        api_url = f"https://api.vimeo.com/videos/{video_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        logger.info("Fetching video metadata from Vimeo API for Video ID: %s", video_id)
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # This will raise an HTTPError for 4xx/5xx responses
        video_data = response.json()
        logger.info("Successfully fetched metadata for video: '%s'", video_data.get("name", "N/A"))

        # 3. Find the best download link (we'll choose the smallest resolution for speed)
        files = video_data.get('files', [])
        if not files:
            logger.error("No downloadable files found in API response for Video ID: %s", video_id)
            raise IOError("No downloadable files found for this video.")
        
        # Choose the link with the smallest height (often SD quality)
        download_info = min(files, key=lambda x: x.get('height', float('inf')))
        download_link = download_info.get('link')
        logger.info("Selected download link for quality: %sp", download_info.get('height'))

        # 4. Prepare file path
        video_title = video_data.get("name", video_id)
        # Sanitize the title to create a valid filename
        safe_title = re.sub(r'[^\w\s-]', '', video_title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        file_name = f"{safe_title}.mp4"
        file_path = os.path.join(download_directory, file_name)
        logger.info("Video will be saved to: %s", file_path)

        # 5. Download the video stream
        stream_response = requests.get(download_link, stream=True)
        stream_response.raise_for_status()
        
        total_size_mb = int(stream_response.headers.get('content-length', 0)) / (1024 * 1024)
        logger.info("Starting file download... Total size: %.2f MB", total_size_mb)

        with open(file_path, "wb") as f:
            for chunk in stream_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info("Successfully downloaded video to: %s", file_path)
        return file_path

    except requests.exceptions.RequestException as e:
        logger.error("A network or API error occurred for URL %s: %s", vimeo_url, e, exc_info=True)
        raise  # Re-raise the original exception
    except (IOError, ValueError, Exception) as e:
        logger.error("An error occurred during the download process for URL %s: %s", vimeo_url, e, exc_info=True)
        raise  # Re-raise the original exception