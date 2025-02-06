import pandas as pd
import youtube_transcript_api
from langchain_community.document_loaders import YoutubeLoader
from langchain_community.document_loaders.youtube import TranscriptFormat

from langflow.custom import Component
from langflow.inputs import DropdownInput, IntInput, MultilineInput
from langflow.schema import Data, DataFrame, Message
from langflow.template import Output


class YouTubeTranscriptsComponent(Component):
    """A component that extracts spoken content from YouTube videos as transcripts."""

    display_name: str = "YouTube Transcripts"
    description: str = "Extracts spoken content from YouTube videos with multiple output options."
    icon: str = "YouTube"
    name = "YouTubeTranscripts"

    inputs = [
        MultilineInput(
            name="url",
            display_name="Video URL",
            info="Enter the YouTube video URL to get transcripts from.",
            tool_mode=True,
            required=True,
        ),
        IntInput(
            name="chunk_size_seconds",
            display_name="Chunk Size (seconds)",
            value=60,
            info="The size of each transcript chunk in seconds.",
        ),
        DropdownInput(
            name="translation",
            display_name="Translation Language",
            advanced=True,
            options=["", "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "hi", "ar", "id"],
            info="Translate the transcripts to the specified language. Leave empty for no translation.",
        ),
    ]

    outputs = [
        Output(name="dataframe", display_name="Chunks", method="get_dataframe_output"),
        Output(name="message", display_name="Transcript", method="get_message_output"),
        Output(name="data_output", display_name="Transcript + Source", method="get_data_output"),
    ]

    def _load_transcripts(self, *, as_chunks: bool = True):
        """Internal method to load transcripts from YouTube."""
        loader = YoutubeLoader.from_youtube_url(
            self.url,
            transcript_format=TranscriptFormat.CHUNKS if as_chunks else TranscriptFormat.TEXT,
            chunk_size_seconds=self.chunk_size_seconds,
            translation=self.translation or None,
        )
        return loader.load()

    def get_dataframe_output(self) -> DataFrame:
        """Provides transcript output as a DataFrame with timestamp and text columns."""
        try:
            transcripts = self._load_transcripts(as_chunks=True)

            # Create DataFrame with timestamp and text columns
            data = []
            for doc in transcripts:
                start_seconds = int(doc.metadata["start_seconds"])
                start_minutes = start_seconds // 60
                start_seconds %= 60
                timestamp = f"{start_minutes:02d}:{start_seconds:02d}"
                data.append({"timestamp": timestamp, "text": doc.page_content})

            return DataFrame(pd.DataFrame(data))

        except (youtube_transcript_api.TranscriptsDisabled, youtube_transcript_api.NoTranscriptFound) as exc:
            return DataFrame(pd.DataFrame({"error": [f"Failed to get YouTube transcripts: {exc!s}"]}))

    def get_message_output(self) -> Message:
        """Provides transcript output as continuous text."""
        try:
            transcripts = self._load_transcripts(as_chunks=False)
            result = transcripts[0].page_content if transcripts and transcripts[0].page_content else None
            return Message(text=result)

        except (youtube_transcript_api.TranscriptsDisabled, youtube_transcript_api.NoTranscriptFound) as exc:
            error_msg = f"Failed to get YouTube transcripts: {exc!s}"
            return Message(text=error_msg)

    def get_data_output(self) -> Data:
        """
        Returns a Data object containing:
          - 'transcript': continuous text from the entire video
          - 'video_url': the input YouTube URL
        """
        try:
            transcripts = self._load_transcripts(as_chunks=False)
            result = transcripts[0].page_content if transcripts and transcripts[0].page_content else None

            # Build the Data object with two fields
            data_dict = {
                "transcript": result,
                "video_url": self.url
            }
            return Data(data=data_dict)

        except (youtube_transcript_api.TranscriptsDisabled, youtube_transcript_api.NoTranscriptFound) as exc:
            error_msg = f"Failed to get YouTube transcripts: {exc!s}"
            return Data(data={"error": error_msg, "video_url": self.url})

