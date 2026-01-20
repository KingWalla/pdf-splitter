from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pypdf import PdfReader, PdfWriter
import io

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/split")
async def split_lr(file: UploadFile = File(...)):
    # Basic content-type guard (not bulletproof, but helps)
    if file.content_type not in (None, "", "application/pdf"):
        # Some clients omit content_type; don't be too strict
        pass

    try:
        pdf_bytes = await file.read()
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {e}")

    writer = PdfWriter()

    for src_page in reader.pages:
        # Use mediabox for exact page dimensions
        mb = src_page.mediabox
        x0, y0 = float(mb.left), float(mb.bottom)
        x1, y1 = float(mb.right), float(mb.top)
        mid = (x0 + x1) / 2.0

        # LEFT half
        left_page = src_page  # will clone via writer.add_page(copy)
        # pypdf pages are mutable; safest is to copy by adding then editing that instance:
        writer.add_page(left_page)
        writer.pages[-1].cropbox.lower_left = (x0, y0)
        writer.pages[-1].cropbox.upper_right = (mid, y1)

        # RIGHT half
        writer.add_page(src_page)
        writer.pages[-1].cropbox.lower_left = (mid, y0)
        writer.pages[-1].cropbox.upper_right = (x1, y1)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)

    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=split.pdf"},
    )
