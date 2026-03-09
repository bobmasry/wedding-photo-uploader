import os
import json
from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Get credentials from environment variable
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
FOLDER_ID = os.getenv("FOLDER_ID")

# Parse service account JSON if it's provided as string
if SERVICE_ACCOUNT_JSON and isinstance(SERVICE_ACCOUNT_JSON, str):
    try:
        service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive_service = build("drive", "v3", credentials=credentials)
    except Exception as e:
        print(f"Error setting up credentials: {e}")
        drive_service = None
else:
    print("No valid service account JSON found")
    drive_service = None

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def handle_upload(
    guest_name: str = Form(None),
    files: list[UploadFile] = File(...)
):
    if not drive_service:
        return {"error": "Drive service not configured"}
    
    results = []
    for file in files:
        try:
            # Read file content
            content = await file.read()
            
            # Prepare file metadata
            file_metadata = {
                "name": f"{guest_name + '_' if guest_name else ''}{file.filename}",
                "parents": [FOLDER_ID]
            }
            
            # Create media object
            media = MediaIoBaseUpload(
                io.BytesIO(content),
                mimetype=file.content_type or "application/octet-stream"
            )
            
            # Upload to Google Drive
            uploaded_file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name"
            ).execute()
            
            results.append({
                "filename": file.filename,
                "success": True,
                "file_id": uploaded_file.get("id")
            })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return {"results": results}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
