# -*- coding: utf-8 -*-
"""
Shared HTTP client for vLLM communication.

Provides connection pooling, automatic retries on transient errors,
and robust JSON parsing with structured error handling.

All Finanzberatung LLM services should use this client instead of
making direct requests.post() calls.
"""

import json
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config.base import FinanzConfig as finanz_config

logger = logging.getLogger(__name__)


class LLMClient:
    """HTTP client for vLLM with connection pooling and retry logic."""

    def __init__(self):
        self._session = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            retry = Retry(
                total=2,
                backoff_factor=1,
                status_forcelist=[502, 503, 504],
            )
            adapter = HTTPAdapter(
                pool_connections=5,
                pool_maxsize=5,
                max_retries=retry,
            )
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
        return self._session

    def chat_completion(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.1,
        timeout: int = 30,
    ) -> dict | None:
        """
        Send a chat completion request to vLLM.

        Returns:
            Parsed JSON dict from the LLM response, or None on any error.
        """
        try:
            response = self.session.post(
                f"{finanz_config.FINANZ_LLM_BASE_URL}/chat/completions",
                json={
                    "model": finanz_config.FINANZ_LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=timeout,
            )
            response.raise_for_status()

            data = response.json()
            choices = data.get("choices", [])
            if not choices or "message" not in choices[0]:
                logger.error(
                    "Unexpected vLLM response structure: %s", str(data)[:300]
                )
                return None

            content = choices[0]["message"].get("content", "").strip()
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.warning("vLLM returned invalid JSON: %s", e)
            return None
        except requests.RequestException as e:
            logger.error("vLLM request failed: %s", e)
            return None


llm_client = LLMClient()
