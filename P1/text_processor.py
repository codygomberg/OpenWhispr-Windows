import gc

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_ID = "Qwen/Qwen3-0.6B"

REFUSAL_PHRASES = (
    "i cannot", "i'm sorry", "as an ai", "i am an ai",
    "i'm unable", "i apologize",
)

TONE_INSTRUCTIONS = {
    "professional": (
        "Use a professional tone: remove contractions, use formal language."
    ),
    "casual": (
        "Use a casual, conversational tone with natural language."
    ),
    "neutral": "",
}


def _build_system_prompt(mode: str, tone: str, style_description: str = "") -> str:
    base_rules = (
        "Remove filler words (um, uh, like, you know). "
        "Fix punctuation and capitalization. "
        "Convert spoken numbers to digits (e.g. 'forty two' → '42'). "
        "Convert spoken list cues (first, second, third) into a numbered list. "
        "Keep the meaning exactly the same. "
        "Return only the result — no commentary, no explanation."
    )

    if mode == "summarize":
        return (
            "Summarize the following dictated text into concise bullet points. "
            "Capture key points, decisions, and action items. "
            "Return only the bullet points — no commentary."
        )

    if mode == "qa":
        return (
            "Answer the following question briefly and helpfully in 1 to 3 sentences. "
            "Return only the answer — no commentary."
        )

    tone_note = TONE_INSTRUCTIONS.get(tone, "")
    style_note = f" Additional style: {style_description.strip()}" if style_description.strip() else ""
    if tone_note:
        return f"You are a text editor. {base_rules} {tone_note}{style_note}"
    return f"You are a text editor. {base_rules}{style_note}"


def _is_safe(original: str, result: str) -> bool:
    """Return False if the model output looks like a refusal or hallucination."""
    lower = result.lower()
    if any(p in lower for p in REFUSAL_PHRASES):
        return False
    # Reject if output is more than 3× longer than input (likely hallucination)
    if len(result.split()) > len(original.split()) * 3:
        return False
    return True


class TextProcessor:
    def __init__(self, status_callback=None):
        """
        Loads Qwen3-0.6B onto the GPU in float16.
        First load downloads the model (~1.2 GB) — subsequent launches are instant.
        """
        if status_callback:
            status_callback("Loading language model…")

        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self._model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=torch.float16,
            low_cpu_mem_usage=True,
        )
        self._model = self._model.to("cuda")
        self._model.eval()
        gc.collect()

        if status_callback:
            status_callback("Language model ready.")

    def process(self, text: str, mode: str = "normal", tone: str = "neutral", style_description: str = "") -> str:
        """
        Polish, summarize, or answer the given text.
        Falls back to the original text if the model output looks wrong.
        """
        if not text.strip():
            return text

        system_prompt = _build_system_prompt(mode, tone, style_description)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": text},
        ]

        # enable_thinking=False keeps Qwen3 in fast, non-reasoning mode
        formatted = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        inputs = self._tokenizer(formatted, return_tensors="pt").to(self._model.device)

        max_new = 512 if mode in ("summarize", "qa") else 1024

        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=max_new,
                temperature=0.1 if mode == "normal" else 0.3,
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        new_tokens = output_ids[0][inputs["input_ids"].shape[-1]:]
        result = self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        return result if _is_safe(text, result) else text
