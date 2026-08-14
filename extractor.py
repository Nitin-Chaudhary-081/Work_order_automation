import json
import re

from google import genai

import config

_client = None

EXTRACTION_PROMPT = """You are reading a scanned "Work Order Traveler" shop-floor document from Raychem RPG.

Extract exactly these four fields from the document:

1. Work Order — the numeric Work Order number near the top of the form (not the barcode number, not the Report Date).
2. Product — the alphanumeric Product/Item code (labelled "Product").
3. Product Description — the text labelled "Product Description" under Work Order Information.
4. Work Order Quantity — the numeric quantity labelled "Work Order Quantity" (not UOM, not MRP).

Respond with ONLY a raw JSON object, no markdown fences, no commentary, in this exact shape:

{
  "work_order": "string",
  "item_code": "string",
  "description": "string",
  "qty": number
}

If any field is unreadable or missing, set its value to null instead of guessing."""


class ExtractionError(Exception):
    """Raised when the image could not be processed or extraction is incomplete.

    The `tag` attribute categorizes the failure for the log:
    API KEY, NETWORK, MODEL, PARSE, or OTHER.
    """

    def __init__(self, message, tag="OTHER"):
        super().__init__(message)
        self.tag = tag


def _strip_fences(text):
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def _parse_json(text):
    cleaned = _strip_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _validate(data):
    if not isinstance(data, dict):
        raise ExtractionError("Gemini response was not a JSON object")

    work_order = data.get("work_order")
    item_code = data.get("item_code")
    description = data.get("description")
    qty = data.get("qty")

    if work_order in (None, "", "null"):
        raise ExtractionError("Field 'work_order' is null or missing")
    if item_code in (None, "", "null"):
        raise ExtractionError("Field 'item_code' is null or missing")
    if description in (None, "", "null"):
        raise ExtractionError("Field 'description' is null or missing")
    if qty in (None, "", "null"):
        raise ExtractionError("Field 'qty' is null or missing")

    try:
        qty = int(float(str(qty).replace(",", "")))
    except (ValueError, TypeError):
        raise ExtractionError(f"Field 'qty' is not numeric: {qty!r}")

    return {
        "work_order": str(work_order).strip(),
        "item_code": str(item_code).strip(),
        "description": str(description).strip(),
        "qty": qty,
    }


def extract_from_image(image_path):
    """Send the image to Gemini and return the extracted fields dict.

    Returns:
        dict with keys work_order, item_code, description, qty

    Raises:
        ExtractionError: on network/API failure or missing/null fields.
    """
    if not config.get_api_key():
        raise ExtractionError(
            "GEMINI_API_KEY is not set. "
            "Run:  setx GEMINI_API_KEY \"your-key-here\"   then close and reopen the terminal.",
            tag="API KEY",
        )

    global _client
    if _client is None:
        _client = genai.Client(api_key=config.get_api_key())

    try:
        image = _client.files.upload(file=str(image_path))
    except Exception as exc:
        raise ExtractionError(f"Could not upload image: {exc}", tag="NETWORK")

    try:
        response = _client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[EXTRACTION_PROMPT, image],
        )
    except Exception as exc:
        raise ExtractionError(f"Gemini request failed: {exc}", tag="MODEL")

    try:
        text = response.text
    except Exception as exc:
        raise ExtractionError(f"Gemini returned no usable text: {exc}", tag="MODEL")

    if not text or not text.strip():
        raise ExtractionError("Gemini returned an empty response", tag="MODEL")

    try:
        data = _parse_json(text)
    except json.JSONDecodeError as exc:
        preview = text.strip()[:300]
        raise ExtractionError(
            f"Response was not valid JSON: {exc}\n"
            f"Raw response (first 300 chars): {preview}",
            tag="PARSE",
        )

    return _validate(data)
