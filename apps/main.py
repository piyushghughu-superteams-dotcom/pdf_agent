from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag import EnhancedRAG

app = FastAPI()
rag = EnhancedRAG()

# Enable CORS so frontend can call /query
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      
    allow_methods=["*"],      
    allow_headers=["*"],      
)

class Q(BaseModel): question: str
class A(BaseModel): answer: str

@app.get("/")
def root():
    return {"status": "API is running"}

@app.post("/query", response_model=A)
def query(q: Q):
    if not q.question.strip(): raise HTTPException(400, "Empty question")
    try:
        return {"answer": rag.ask(q.question)}
    except Exception as e:
        raise HTTPException(500, str(e))
