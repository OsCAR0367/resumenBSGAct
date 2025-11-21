import logging
import subprocess
from pathlib import Path
import re

# Get a logger for this module
logger = logging.getLogger(__name__)


class AudioExtractionError(Exception):
    """Raised when audio extraction fails."""
    pass


def _validate_paths(video_path: Path, audio_output_path: Path) -> None:
    """Ensure paths exist and the destination folder is ready."""
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not video_path.is_file():
        raise IsADirectoryError(f"Video path is not a file: {video_path}")

    # This is a safe operation, so logging isn't strictly necessary unless debugging.
    audio_output_path.parent.mkdir(parents=True, exist_ok=True)


def extract_audio_to_memory(video_path: str) -> bytes:
    """
    Extracts audio from a video, converts it to a 32kbps mono MP3, and
    returns the result as a bytes object without writing to disk.
    """
    logger.info("Starting IN-MEMORY audio extraction for video: %s", video_path)
    
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    try:
        # Command to extract the audio and pipe it as uncompressed WAV to stdout.
        # WAV is a robust format for piping between processes.
        extract_command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',              # No video
            '-f', 'wav',        # Output raw WAV format to the pipe
            '-'                 # Pipe to stdout
        ]

        # Command to read from stdin, convert to MP3 with desired settings, and pipe to stdout.
        convert_command = [
            'ffmpeg',
            '-i', '-',          # Read from stdin
            '-ac', '1',         # Mono
            '-ar', '16000',     # 16kHz sample rate
            '-c:a', 'libmp3lame', # MP3 encoder
            '-b:a', '32k',      # 32kbps bitrate
            '-f', 'mp3',        # Output MP3 format
            '-'                 # Pipe to stdout
        ]

        # Start the extraction process
        extract_process = subprocess.Popen(extract_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Pipe the output of the extraction process into the conversion process
        convert_process = subprocess.Popen(convert_command, stdin=extract_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Allow extract_process to receive a SIGPIPE if convert_process exits.
        extract_process.stdout.close()

        # Capture the final MP3 data and any errors
        mp3_data, stderr_convert = convert_process.communicate()
        _, stderr_extract = extract_process.communicate() # get any errors from first process

        if extract_process.returncode != 0:
            raise AudioExtractionError(f"FFMPEG (extract) failed: {stderr_extract.decode()}")
        if convert_process.returncode != 0:
            raise AudioExtractionError(f"FFMPEG (convert) failed: {stderr_convert.decode()}")

        logger.info("Successfully extracted and converted audio in-memory. Size: %.2f KB", len(mp3_data) / 1024)
        return mp3_data

    except FileNotFoundError:
        logger.error("FFMPEG not found. Ensure it is installed and in your system's PATH.")
        raise AudioExtractionError("FFMPEG executable not found.")
    except Exception as e:
        logger.error("An unexpected error occurred during in-memory audio extraction: %s", e, exc_info=True)
        raise AudioExtractionError(f"Failed to extract audio from {video_path}") from e


def extract_audio(video_path: str, audio_output_path: str | None = None) -> str:
    """
    Extracts and re-encodes the audio track from a video into a 32 kbps mono MP3.
    
    Args:
        video_path: Full path to the source video file.
        audio_output_path: Target path for the MP3 file. Defaults to a sanitized name
                           in the same directory.
    
    Returns:
        Absolute path to the extracted MP3 file.
    
    Raises:
        AudioExtractionError: When ffmpeg fails or paths are invalid.
    """
    logger.info("Starting audio extraction process for video: %s", video_path)
    
    try:
        # 1) Derive default output path and validate
        if audio_output_path is None:
            vp = Path(video_path)
            # Sanitize the filename stem to prevent issues
            safe_stem = re.sub(r"[^\w.-]+", "_", vp.stem)
            audio_output_path = str(vp.parent / f"{safe_stem}.mp3")
            logger.info("No output path provided. Derived path: %s", audio_output_path)
        
        video_p, audio_p = Path(video_path), Path(audio_output_path)
        _validate_paths(video_p, audio_p)

        # 2) Construct the ffmpeg command
        cmd = [
            "ffmpeg",
            "-y",                   # Overwrite output file without asking
            "-i", str(video_p),     # Input video file
            "-vn",                  # No video output
            "-ac", "1",             # Set audio to 1 channel (mono)
            "-ar", "16000",         # Set audio sample rate to 16 kHz
            "-c:a", "libmp3lame",   # Use MP3 encoder
            "-b:a", "32k",          # Set audio bitrate to 32 kbps
            "-f", "mp3",            # Force MP3 container format
            str(audio_p)            # Output audio file
        ]
        
        # This is the most critical log for debugging!
        logger.info("Executing ffmpeg command: %s", ' '.join(cmd))

        # 3) Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        # 4) Check for errors
        if result.returncode != 0:
            # Log the detailed error from ffmpeg before raising our own exception
            error_details = (
                f"ffmpeg process failed for '{video_path}' with exit code {result.returncode}.\n"
                f"Stderr: {result.stderr.strip()}"
            )
            logger.error(error_details)
            raise AudioExtractionError(error_details)

        final_path = str(audio_p)
        logger.info("Successfully extracted audio to: %s", final_path)
        return final_path

    except (FileNotFoundError, IsADirectoryError, AudioExtractionError) as exc:
        # Re-raise known errors directly after logging
        logger.error("A predictable error occurred during audio extraction: %s", exc)
        raise
    except Exception as exc:
        # Catch any other unexpected exception
        logger.error(
            "An unexpected error occurred during audio extraction for '%s': %s",
            video_path, exc, exc_info=True
        )
        raise AudioExtractionError(f"Failed to extract audio from {video_path}") from exc


# Alias para mantener compatibilidad
extract_audio_from_video = extract_audio