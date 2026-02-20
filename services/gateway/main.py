from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "MuleNet-X Omega API running"}
