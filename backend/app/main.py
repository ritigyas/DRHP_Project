import os
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import shutil
import tempfile
from app.classifier import DocumentClassifier
from app.parser import DocumentParser
from app.verifier import DocumentVerifier

app = FastAPI(title="DRHP Capital Structure Drafting Agent API")

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the Vite development port (e.g., http://localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for processed events and files (resets on server restart)
# In a full app, this would use a database or session cache
PROCESSED_DATA = {}

def process_file_content(content_str: str, filename: str) -> dict:
    """Classifies and parses file content."""
    classification = DocumentClassifier.classify(content_str, filename)
    doc_type = classification["document_type"]
    parsed_data = DocumentParser.parse_document(doc_type, content_str)
    
    return {
        "content": content_str,
        "filename": filename,
        "classification": classification,
        "parsed_data": parsed_data
    }

def compile_and_verify_all() -> list:
    """Group all processed files by Event ID and run verifications."""
    # Group by event_id
    grouped_events = {}
    for filename, file_info in PROCESSED_DATA.items():
        event_id = file_info["classification"]["event_id"]
        doc_type = file_info["classification"]["document_type"]
        if event_id == "UNKNOWN" or doc_type == "UNKNOWN":
            continue
        
        if event_id not in grouped_events:
            grouped_events[event_id] = {}
        
        grouped_events[event_id][doc_type] = file_info

    # Verify each group
    verified_results = []
    # Sort events chronologically (Event1, Event2, Event3)
    for event_id in sorted(grouped_events.keys()):
        event_docs = grouped_events[event_id]
        result = DocumentVerifier.verify_event(event_id, event_docs)
        
        # Attach raw contents for the frontend raw viewer
        result["raw_documents"] = {
            doc_type: {
                "filename": doc_data["filename"],
                "content": doc_data["content"],
                "classification": doc_data["classification"],
                "parsed_data": doc_data["parsed_data"]
            }
            for doc_type, doc_data in event_docs.items()
        }
        verified_results.append(result)

    return verified_results

@app.post("/api/ingest")
async def ingest_files(files: List[UploadFile] = File(...)):
    """Ingests uploaded files, processes them, and returns the verified results."""
    global PROCESSED_DATA
    
    for file in files:
        # Read file contents
        content = await file.read()
        try:
            content_str = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content_str = content.decode("latin-1")
            except Exception:
                continue  # Skip unreadable files
        
        # Process and store
        processed = process_file_content(content_str, file.filename)
        PROCESSED_DATA[file.filename] = processed

    results = compile_and_verify_all()
    return {"status": "success", "results": results}

@app.post("/api/preload-local")
def preload_local_dataset(dataset_path: Optional[str] = Query(None)):
    """Preloads the local dataset files from the workspace directory."""
    global PROCESSED_DATA
    
    # Locate dataset directory
    target_dir = dataset_path or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dataset"))
    if not os.path.exists(target_dir):
        # Try direct workspace path
        target_dir = "c:\\Users\\ritig\\Desktop\\s45_assignment\\dataset"
        
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail=f"Dataset path {target_dir} not found.")

    # Reset processed data
    PROCESSED_DATA = {}

    # Scan dataset directory for txt files
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content_str = f.read()
                    processed = process_file_content(content_str, file)
                    PROCESSED_DATA[file] = processed
                except Exception as e:
                    print(f"Error reading local file {file_path}: {e}")

    results = compile_and_verify_all()
    return {"status": "success", "results": results}

@app.get("/api/table")
def get_capital_table():
    """Compiles and returns the consolidated DRHP Capital Change Table."""
    results = compile_and_verify_all()
    return {"results": results}

@app.post("/api/reset")
def reset_data():
    """Resets the in-memory cache."""
    global PROCESSED_DATA
    PROCESSED_DATA = {}
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
