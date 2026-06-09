import os, tempfile, json
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel
import requests

app = FastAPI(title="OpenDataLoader PDF Sidecar")
HYBRID_PORT = int(os.environ.get("HYBRID_PORT", "5002"))
HYBRID_URL = f"http://localhost:{HYBRID_PORT}"

class ExtractResponse(BaseModel):
    success: bool
    format: str
    content: str
    pages: int | None = None
    error: str | None = None

@app.get("/health")
def health():
    return {"status": "ok", "hybrid_port": HYBRID_PORT}

def _is_junk(text: str) -> bool:
    """Filter noise/spurious short fragments from docling JSON."""
    if len(text) < 3:
        return True
    # Discard strings that contain only punctuation/numbers/whitespace
    if all(c in "0123456789.,;:!?\"'\u2013\u2014 \t\n\r" for c in text):
        return True
    return False

def _extract_all_texts(node, texts):
    """Recursively collect all text/content strings from docling JSON."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("text", "content") and isinstance(v, str) and v.strip() and not _is_junk(v):
                texts.append(v)
            else:
                _extract_all_texts(v, texts)
    elif isinstance(node, list):
        for item in node:
            _extract_all_texts(item, texts)

def extract_text_from_docling(data: dict) -> str:
    texts = []
    doc = data.get("document") or data
    if isinstance(doc, dict):
        jc = doc.get("json_content")
        if isinstance(jc, dict):
            _extract_all_texts(jc, texts)
        else:
            _extract_all_texts(doc, texts)
    if not texts:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return "\n\n".join(texts)

@app.post("/extract_file", response_model=ExtractResponse)
async def extract_file(
    file: UploadFile = File(...),
    format: str = Form("markdown"),
    ocr_lang: str = Form("ru,en"),
    hybrid_mode: str = Form("auto"),
):
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            resp = requests.post(
                f"{HYBRID_URL}/v1/convert/file",
                files={"files": f},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("status") == "failure":
            return ExtractResponse(success=False, format=format, content="",
                error=json.dumps(data.get("errors", ["Unknown error"])))
        content = extract_text_from_docling(data)
        return ExtractResponse(success=True, format="markdown", content=content, pages=1)
    except Exception as e:
        return ExtractResponse(success=False, format=format, content="", error=str(e)[:500])
