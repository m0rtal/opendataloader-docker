import os, tempfile
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel
from PIL import Image
import fitz
import pytesseract

app = FastAPI(title="OpenDataLoader PDF Sidecar (Tesseract)")

class ExtractResponse(BaseModel):
    success: bool
    format: str
    content: str
    pages: int | None = None
    error: str | None = None

def is_likely_scanned(page, min_chars=30):
    """Heuristic: if embedded text is very short, assume scanned image."""
    text = page.get_text().strip()
    return len(text) < min_chars

@app.get("/health")
def health():
    return {"status": "ok", "ocr": "tesseract", "langs": "rus+eng"}

@app.post("/extract_file", response_model=ExtractResponse)
async def extract_file(
    file: UploadFile = File(...),
    format: str = Form("markdown"),
    ocr_lang: str = Form("rus+eng"),
    hybrid_mode: str = Form("auto"),
):
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        doc = fitz.open(tmp_path)
        texts = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            embedded = page.get_text().strip()
            if is_likely_scanned(page):
                # Raster → OCR via Tesseract
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img, lang=ocr_lang).strip()
                if not text and embedded:
                    text = embedded
            else:
                # Native text → no OCR
                text = embedded

            texts.append(text)

        content = "\n\n".join(texts)
        return ExtractResponse(success=True, format="markdown", content=content, pages=len(doc))
    except Exception as e:
        return ExtractResponse(success=False, format=format, content="", error=str(e)[:500])
