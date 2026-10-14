import json
import logging
import time
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from groq import Groq
from app.config import settings

logger = logging.getLogger("worldamaze.groq")
T = TypeVar("T", bound=BaseModel)


class GroqService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Groq:
        if self._client is None:
            self._client = Groq(api_key=self.api_key)
        return self._client

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.1,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ) -> T:
        """
        Executes a completion using Groq GPT-OSS 120B with JSON schema validation.
        Retries on rate limits or network issues with exponential backoff.
        """
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        system_with_schema = (
            f"{system_prompt}\n\n"
            f"You MUST output valid JSON conforming strictly to this JSON Schema:\n"
            f"{schema_json}\n\n"
            f"Respond with raw JSON only. Do not wrap in markdown quotes or code blocks."
        )

        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_with_schema},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    max_tokens=2048,
                )
                raw_content = response.choices[0].message.content or "{}"
                # Clean any accidental markdown fence
                cleaned = raw_content.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                parsed_data = json.loads(cleaned)
                return response_model.model_validate(parsed_data)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Groq API call attempt {attempt + 1}/{max_retries} failed: {type(e).__name__} {e}"
                )
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor ** (attempt + 1)
                    time.sleep(sleep_time)

        raise RuntimeError(f"Failed to generate structured output after {max_retries} attempts: {last_error}")


groq_service = GroqService()
