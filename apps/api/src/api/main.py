from fastapi import FastAPI

from api.routers import questions, seminars

app = FastAPI()
app.include_router(seminars.router)
app.include_router(questions.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
