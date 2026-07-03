from fastapi import FastAPI

from api.routers import answers, questions, seminars

app = FastAPI()
app.include_router(seminars.router)
app.include_router(questions.router)
app.include_router(answers.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
