"""
Local replacement for webhook_handler.py + processor_handler.py combined.
No Lambda, no API Gateway, no SQS needed for local testing -- a single
FastAPI endpoint handles a chat message synchronously (fine for local dev;
the AWS-cloud version's SQS split exists to handle WhatsApp's webhook
timeout, which doesn't apply here since there's no WhatsApp involved).

Run with: uvicorn src.main:app --reload --port 8000
Then open http://localhost:8000 in a browser for the chat UI.
"""
import base64

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src import conversation, s3_storage
from src.bill_parser import extract_bill

app = FastAPI(title="BillWise - Local")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html") as f:
        return f.read()


@app.post("/chat/text")
async def chat_text(user_id: str = Form(...), text: str = Form(...)):
    """Handles a plain text message from the local chat UI."""
    reply = conversation.route_message(
        user_id=user_id, message_type="text", text=text,
        bill_bytes=None, content_type="text/plain", extract_bill_fn=extract_bill,
    )
    return {"reply": reply}


@app.post("/chat/upload")
async def chat_upload(user_id: str = Form(...), file: UploadFile = File(...)):
    """Handles a bill photo/PDF upload from the local chat UI."""
    file_bytes = await file.read()
    content_type = file.content_type or "image/jpeg"

    s3_storage.store_bill(user_id, file_bytes, content_type)

    reply = conversation.route_message(
        user_id=user_id, message_type="image", text=None,
        bill_bytes=file_bytes, content_type=content_type, extract_bill_fn=extract_bill,
    )
    return {"reply": reply}


@app.get("/health")
async def health():
    return {"status": "ok"}