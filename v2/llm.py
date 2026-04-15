"""
SOW Generator v2 — LLM Client (Anthropic Claude Sonnet + Opus)
"""

import time
import json
import re
import anthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, CLAUDE_FAST_MODEL, CLAUDE_STRONG_MODEL, MAX_RETRIES


class ClaudeClient:
    """Wrapper for Claude Sonnet (fast) and Opus (strong) models."""

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY or None,  # None = use env/default auth
            base_url=ANTHROPIC_BASE_URL,
        )

    def generate(self, prompt, model="fast", temperature=0.3, max_output_tokens=4096):
        """
        Generate text with retry logic.
        model: "fast" (Sonnet) or "strong" (Opus)
        Returns: (text, tokens_in, tokens_out, duration_ms)
        """
        model_id = CLAUDE_STRONG_MODEL if model == "strong" else CLAUDE_FAST_MODEL

        last_error = None
        for attempt in range(MAX_RETRIES):
            start = time.time()
            try:
                message = self.client.messages.create(
                    model=model_id,
                    max_tokens=max_output_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                duration_ms = int((time.time() - start) * 1000)

                text = message.content[0].text
                tokens_in = message.usage.input_tokens
                tokens_out = message.usage.output_tokens

                return text, tokens_in, tokens_out, duration_ms

            except anthropic.RateLimitError as e:
                last_error = e
                wait = 2 ** (attempt + 1)
                print(f"  [LLM] Rate limited, waiting {wait}s...")
                time.sleep(wait)

            except anthropic.APIError as e:
                last_error = e
                duration_ms = int((time.time() - start) * 1000)

                if attempt < MAX_RETRIES - 1:
                    # If Opus fails, fall back to Sonnet on last retry
                    if model == "strong" and attempt == MAX_RETRIES - 2:
                        print(f"  [LLM] Opus failed, falling back to Sonnet...")
                        model_id = CLAUDE_FAST_MODEL
                    else:
                        wait = 2 ** attempt
                        print(f"  [LLM] Retry {attempt + 1}/{MAX_RETRIES} in {wait}s: {e}")
                        time.sleep(wait)

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    print(f"  [LLM] Retry {attempt + 1}/{MAX_RETRIES} in {wait}s: {e}")
                    time.sleep(wait)

        raise RuntimeError(f"LLM generation failed after {MAX_RETRIES} retries: {last_error}")

    def generate_json(self, prompt, model="fast"):
        """Generate and parse JSON response."""
        text, tin, tout, dur = self.generate(prompt, model=model, temperature=0.2)

        # Extract JSON from markdown code blocks or raw response
        json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```', text)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'(\{[\s\S]*\})', text)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = text

        parsed = json.loads(json_str)
        return parsed, tin, tout, dur
