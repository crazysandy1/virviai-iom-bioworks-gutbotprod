from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from storage import save_file

app = FastAPI(title="Report Upload Service")

# ✅ Enable CORS so frontend can talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Upload endpoint (matches frontend)
@app.post("/upload-report")
async def upload_report(file: UploadFile = File(...)):
    allowed_extensions = (".pdf", ".json")

    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Only PDF or JSON files allowed"
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )

    if len(file_bytes) > 20 * 1024 * 1024:  # 20 MB limit
        raise HTTPException(
            status_code=400,
            detail="File too large (max 20MB)"
        )

    metadata = save_file(file_bytes, file.filename)

    return {
        "status": "success",
        "message": "File uploaded successfully",
        "data": metadata
    }

# ✅ Health check
@app.get("/health")
def health_check():
    return {"status": "ok"}

# ✅ Ask endpoint (temporary dummy response)
@app.post("/ask")
async def ask_question(payload: dict):
    question = payload.get("question")

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    return {
        "status": "success",
        "answer": f"You asked: {question}"
    }
