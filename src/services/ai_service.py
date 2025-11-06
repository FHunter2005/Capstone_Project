"""
AI Service - Handles all Gemini API interactions

This service is:
- Generic (doesn't know about contracts specifically)
- Reusable across different domains
- Fully traced with Langfuse
- Testable (can mock the client)
"""

from google import genai
from google.genai import types
from langfuse import observe
import os
import json


class AIService:
    """Service for all AI/LLM operations."""

    def __init__(self, model: str = "gemini-2.5-flash-lite"):
        """Initialize AI service.

        Args:
            model: Gemini model to use
        """
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = model

    @observe()
    def extract_structured(
        self,
        file_bytes: bytes,
        schema: dict,
        mime_type: str = 'application/pdf'
    ) -> dict:
        """Extract structured data from document.

        Args:
            file_bytes: Document bytes
            schema: JSON schema defining what to extract
            mime_type: Document MIME type

        Returns:
            Extracted data as dictionary

        Raises:
            Exception: If extraction fails
        """
        prompt = self._build_extraction_prompt(schema)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                prompt,
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            ],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.1
            )
        )

        return json.loads(response.text)

    @observe()
    def chat_with_context(
        self,
        question: str,
        context: dict,
        system_instruction: str = None
    ) -> str:
        """Chat with AI about specific context.

        Args:
            question: User's question
            context: Context data to reference
            system_instruction: Optional system instruction

        Returns:
            AI's answer as string
        """
        if system_instruction is None:
            system_instruction = "You are a helpful AI assistant analyzing data."

        chat = self.client.chats.create(
            model=self.model,
            config={
                'system_instruction': f"""{system_instruction}

Context data:
{json.dumps(context, indent=2)}"""
            }
        )

        response = chat.send_message(question)
        return response.text

    @observe()
    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """Summarize text.

        Args:
            text: Text to summarize
            max_sentences: Maximum sentences in summary

        Returns:
            Summary string
        """
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"Summarize this in {max_sentences} sentences or less:\n\n{text}"
        )

        return response.text

    def _build_extraction_prompt(self, schema: dict) -> str:
        """Build prompt for structured extraction.

        Args:
            schema: JSON schema

        Returns:
            Formatted prompt
        """
        return f"""Extract information from this document as JSON.

Schema (use these exact field names):
{json.dumps(schema, indent=2)}

Rules:
- Return ONLY valid JSON
- Use null for missing information
- Follow the exact field names
- Match the data types specified

JSON:"""
