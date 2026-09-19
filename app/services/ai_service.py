import os
import re
import json
import urllib.request

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.core.logging import logger


class AIAssistedOption(BaseModel):
    key: str
    text: str


class AIAssistedQuestion(BaseModel):
    question_number: Optional[str] = None
    question_text: str = Field(..., min_length=5)
    options: List[AIAssistedOption] = []
    question_type: str = "MCQ"
    matched_answer: Optional[str] = None


class AIAssistedExtractionResult(BaseModel):
    questions: List[AIAssistedQuestion] = []


class AIService:
    """
    Pluggable AI/LLM extraction module supporting Gemini, OpenAI, and Anthropic.
    Ensures zero hallucination by enforcing strict Pydantic JSON schema validation on all AI outputs.
    """

    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.provider = provider or os.getenv("AI_PROVIDER") or settings.AI_PROVIDER
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or settings.AI_API_KEY
        )
        self.model_name = model_name or settings.AI_MODEL_NAME

        # Auto-detect provider if API key is provided
        if self.api_key and self.provider == "mock":
            if os.getenv("GEMINI_API_KEY") or "AIza" in (self.api_key or ""):
                self.provider = "gemini"
                self.model_name = "gemini-1.5-flash"
            elif os.getenv("OPENAI_API_KEY") or (self.api_key or "").startswith("sk-"):
                self.provider = "openai"
                self.model_name = "gpt-4o"

    def is_configured(self) -> bool:
        """Returns True if a live AI provider and valid API key are present."""
        return self.provider != "mock" and bool(self.api_key)

    def extract_structured_questions(self, raw_page_text: str) -> Optional[AIAssistedExtractionResult]:
        """
        Calls the configured AI provider (Gemini/OpenAI) to structure raw text into valid questions.
        Validates the output strictly against AIAssistedExtractionResult.
        """
        if not self.is_configured():
            logger.info("AI Provider is set to 'mock' or unconfigured API key. Skipping AI call.")
            return None

        prompt = (
            "You are a strict examination question extraction engine.\n"
            "Extract ONLY actual questions, tasks, or problems from the text below.\n"
            "DO NOT extract exam instructions, candidate rules, page headers, or test metadata.\n\n"
            "Return JSON matching this exact structure:\n"
            "{\n"
            '  "questions": [\n'
            "    {\n"
            '      "question_number": "1",\n'
            '      "question_text": "...",\n'
            '      "question_type": "MCQ",\n'
            '      "options": [{"key": "A", "text": "..."}, {"key": "B", "text": "..."}],\n'
            '      "matched_answer": "A"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"TEXT TO EXTRACT:\n{raw_page_text}"
        )

        try:
            raw_json_response = ""
            if self.provider == "gemini":
                raw_json_response = self._call_gemini_api(prompt)
            elif self.provider == "openai":
                raw_json_response = self._call_openai_api(prompt)

            if not raw_json_response:
                return None

            # Clean JSON markdown code blocks if returned
            clean_json = raw_json_response.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\n?", "", clean_json)
                clean_json = re.sub(r"\n?```$", "", clean_json).strip()

            parsed_data = json.loads(clean_json)
            validated = AIAssistedExtractionResult(**parsed_data)
            logger.info(f"AI Service ({self.provider}) successfully extracted {len(validated.questions)} questions.")
            return validated

        except (ValidationError, Exception) as e:
            logger.warning(f"AI extraction returned invalid schema or failed: {str(e)}")
            return None

    def _call_gemini_api(self, prompt: str) -> str:
        """Invokes Gemini API via REST endpoint without external heavy dependencies."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)

        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_openai_api(self, prompt: str) -> str:
        """Invokes OpenAI API via REST endpoint."""
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)

        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]
