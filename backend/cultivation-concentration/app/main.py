from fastapi import FastAPI

app = FastAPI(title="Cultivation Concentration Risk Prediction")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Cultivation concentration backend"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
