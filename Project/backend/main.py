from fastapi import FastAPI
from pydantic import BaseModel
#from services.query_engine import QueryEngine
from dotenv import load_dotenv

load_dotenv()


app = FastAPI(
    title="MastersMatch API",
    description="Backend API for semantic search + LLM explanations",
    version="1.0.0"
)

#engine = QueryEngine()

# class QueryRequest(BaseModel):
#     query: str

# class QueryResponse(BaseModel):
#     result: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

# @app.post("/query", response_model=QueryResponse)
# def query_master(data: QueryRequest):
#     result = engine.handle_user_query(data.query)
#     return QueryResponse(result=result)