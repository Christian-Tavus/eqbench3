"""PAL persona configuration loader.

Parses --pal-persona input: either a Tavus persona JSON or plain text.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PalPersonaConfig:
    """Parsed PAL persona configuration."""

    system_prompt: str
    greeting: Optional[str] = None
    model: Optional[str] = None
    context: Optional[str] = None

    def build_system_prompt(self) -> str:
        """Return the full system prompt, appending context if present."""
        if not self.context:
            return self.system_prompt
        return f"{self.system_prompt}\n\n# Conversational Context\n\n{self.context}"


def load_pal_persona(
    persona_path: str,
    context_path: Optional[str] = None,
) -> PalPersonaConfig:
    """Load a PAL persona from a file path.

    Args:
        persona_path: Path to persona file. Either a Tavus persona JSON
            (must contain "system_prompt" key) or a plain text file
            treated as a raw system prompt.
        context_path: Optional path to a text file with per-session
            conversational context to append to the system prompt.

    Returns:
        PalPersonaConfig with extracted fields.

    Raises:
        FileNotFoundError: If persona_path does not exist.
    """
    path = Path(persona_path)
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {persona_path}")

    raw_text = path.read_text(encoding="utf-8").strip()

    system_prompt = None
    greeting = None
    model = None
    context = None

    # Try parsing as JSON
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and "system_prompt" in data:
            system_prompt = data["system_prompt"]
            greeting = data.get("greeting") or None
            # Extract model from layers.llm.model
            layers = data.get("layers")
            if isinstance(layers, dict):
                llm = layers.get("llm")
                if isinstance(llm, dict):
                    model = llm.get("model") or None
            # Extract context field
            context = data.get("context") or data.get("conversational_context") or None
            # Treat empty strings as None
            if context and not context.strip():
                context = None
            logging.info(
                "Loaded PAL persona from JSON: greeting=%s, model=%s",
                "yes" if greeting else "no",
                model or "none",
            )
        else:
            # Valid JSON but no system_prompt key -- treat as plain text
            logging.info(
                "Persona file is valid JSON but has no 'system_prompt' key. "
                "Treating as raw system prompt."
            )
            system_prompt = raw_text
    except (json.JSONDecodeError, ValueError):
        # Not JSON -- treat as plain text system prompt
        system_prompt = raw_text
        logging.info("Loaded PAL persona as plain text system prompt.")

    # Load external context file if provided
    if context_path:
        ctx_path = Path(context_path)
        if not ctx_path.exists():
            raise FileNotFoundError(f"Context file not found: {context_path}")
        external_context = ctx_path.read_text(encoding="utf-8").strip()
        if external_context:
            # External context overrides JSON context if both are present
            context = external_context
            logging.info("Loaded external context from %s", context_path)

    return PalPersonaConfig(
        system_prompt=system_prompt,
        greeting=greeting,
        model=model,
        context=context,
    )
