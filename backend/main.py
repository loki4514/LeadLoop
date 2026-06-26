from fastapi import FastAPI

app = FastAPI(title="Lead Agent API")


@app.get("/health")
def health():
    return {"status": "ok"}
