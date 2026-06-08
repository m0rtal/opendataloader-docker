import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel

app = FastAPI(title="OpenDataLoader PDF Sidecar")

# Hybrid backend порт (внутри контейнера)
HYBRID_PORT = int(os.environ.get("HYBRID_PORT", "5002"))
HYBRID_URL = f"http://localhost:{HYBRID_PORT}"


class ExtractRequest(BaseModel):
    path: str                      # Абсолютный путь к PDF (bind mount)
    format: str = "markdown"       # markdown | json | html
    ocr_lang: str = "rus,eng"
    hybrid: bool = True            # использовать hybrid backend


class ExtractResponse(BaseModel):
    success: bool
    format: str
    content: str
    pages: Optional[int] = None
    error: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "hybrid_port": HYBRID_PORT}


@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    import opendataloader_pdf

    path = Path(req.path)
    if not path.exists():
        return ExtractResponse(success=False, format=req.format, content="", error=f"File not found: {req.path}")

    try:
        # Временный выходной каталог
        with tempfile.TemporaryDirectory() as tmpdir:
            kwargs = {
                "input_path": [str(path)],
                "output_dir": tmpdir,
                "format": req.format,
            }
            if req.hybrid:
                kwargs["hybrid"] = HYBRID_URL
                kwargs["hybrid_mode"] = "full"

            opendataloader_pdf.convert(**kwargs)

            # Ищем выходной файл
            out_dir = Path(tmpdir)
            out_files = list(out_dir.glob("*.*"))
            if not out_files:
                return ExtractResponse(success=False, format=req.format, content="", error="No output generated")

            out_file = out_files[0]
            content = out_file.read_text(encoding="utf-8", errors="replace")

            # Подсчёт страниц по количеству заголовков или разделителей
            pages = content.count("\n---\n") + 1 if req.format == "markdown" else None

            return ExtractResponse(success=True, format=req.format, content=content, pages=pages)

    except Exception as e:
        return ExtractResponse(success=False, format=req.format, content="", error=str(e)[:500])


@app.post("/extract_file", response_model=ExtractResponse)
async def extract_file(
    file: UploadFile = File(...),
    format: str = Form("markdown"),
    ocr_lang: str = Form("rus,eng"),
    hybrid: bool = Form(True),
):
    import opendataloader_pdf

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = Path(tmpdir) / (file.filename or "upload.pdf")
            in_path.write_bytes(await file.read())

            kwargs = {
                "input_path": [str(in_path)],
                "output_dir": tmpdir,
                "format": format,
            }
            if hybrid:
                kwargs["hybrid"] = HYBRID_URL
                kwargs["hybrid_mode"] = "full"

            opendataloader_pdf.convert(**kwargs)

            out_dir = Path(tmpdir)
            out_files = list(out_dir.glob("*.*"))
            if not out_files:
                return ExtractResponse(success=False, format=format, content="", error="No output generated")

            out_file = out_files[0]
            content = out_file.read_text(encoding="utf-8", errors="replace")
            pages = content.count("\n---\n") + 1 if format == "markdown" else None

            return ExtractResponse(success=True, format=format, content=content, pages=pages)

    except Exception as e:
        return ExtractResponse(success=False, format=format, content="", error=str(e)[:500])
