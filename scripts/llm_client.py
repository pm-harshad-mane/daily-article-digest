import os

from openai import OpenAI


class OpenAIClient:
    def __init__(self, model: str, api_key: str | None = None) -> None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError("OPENAI_API_KEY is required for non-dry-run execution.")
        resolved_model = os.getenv("OPENAI_MODEL", model).strip()
        if not resolved_model:
            raise ValueError("OpenAI model is empty. Set OPENAI_MODEL or llm_model in config.")
        self.client = OpenAI(api_key=resolved_key)
        self.model = resolved_model

    def summarize(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        output_text = getattr(response, "output_text", "")
        if not output_text:
            raise ValueError("OpenAI response did not include text output.")
        return output_text.strip()
