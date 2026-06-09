from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
from PIL import Image
import fitz  # PyMuPDF
import tempfile
from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

app = FastAPI(title="OpenDataLoader PDF OCR Sidecar (Surya)")

# Load Surya models once at startup
det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()

class ExtractResponse(BaseModel):
    success: bool
    format: str
    content: str
    pages: int | None = None
    error: str | None = None

@app.get("/health")
def health():
    return {"status": "ok", "ocr": "surya", "langs": "multi"}

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

        doc = fitz.open(tmp_path)
        texts = []
        langs = ocr_lang.replace("+", ",").split(",")
        langs = [l.strip() for l in langs if l.strip()]

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            predictions = run_ocr(
                [img],
                [langs],
                det_model, det_processor,
                rec_model, rec_processor
            )
            page_text = "\n".join([line.text for line in predictions[0].text_lines])
            texts.append(page_text)

        content = "\n\n".join(texts)
        return ExtractResponse(success=True, format="markdown", content=content, pages=len(doc))
    except Exception as e:
        return ExtractResponse(success=False, format=format, content="", error=str(e)[:500])
