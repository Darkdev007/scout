# server.py
import secrets
import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agent import scout

app = FastAPI(title="Scout Research Agent", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

USERNAME = os.environ.get("SCOUT_USERNAME", "scout")
PASSWORD = os.environ.get("SCOUT_PASSWORD")

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if not PASSWORD:
        raise HTTPException(status_code=500, detail="Server not configured.")
    
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Wrong credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

templates = Jinja2Templates(directory="templates")

class QueryRequest(BaseModel):
    query: str

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/research")
async def research(request: QueryRequest, credentials: HTTPBasicCredentials = Depends(verify_credentials) ):
    result = scout.invoke({
        "messages": [HumanMessage(content=request.query)]
    })
    
    trace = []
    for message in result["messages"]:
        if isinstance(message, AIMessage) and message.tool_calls:
            for tc in message.tool_calls:
                trace.append({
                    "tool": tc["name"],
                    "input": tc["args"],
                })
        elif isinstance(message, ToolMessage):
            trace.append({
                "tool_result": message.name,
                "preview": message.content[:300],
            })
    
    return {
        "answer": result["messages"][-1].content,
        "trace": trace,
    }

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Scout v1.0"}