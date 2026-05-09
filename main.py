from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import DatabaseUnavailableError, database_health, ensure_database_initialized, get_db
from models import Application
from schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate

app = FastAPI(title="CareerOS API")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates setup
templates = Jinja2Templates(directory="templates")

# Context helper
def get_context(request: Request, title: str):
    return {"request": request, "title": title}


def get_ready_db():
    try:
        ensure_database_initialized()
    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL is not available. Confirm the 'careeros' database is running and DATABASE_URL is correct.",
        ) from exc

    yield from get_db()


def seed_applications(db: Session):
    if db.query(Application).count() > 0:
        return

    db.add_all([
        Application(company="Amazon", role="SDE Intern - Summer 2027", status="applied", tag="Backend"),
        Application(company="Netflix", role="Core Engineering Intern", status="applied", tag="Referral"),
        Application(company="Meta", role="Frontend Engineer Intern", status="oa", tag="HackerRank", notes="70 min OA due soon."),
        Application(company="Google", role="SWE Intern, Core", status="interview", tag="Passed OA", notes="Technical Round 1"),
        Application(company="Stripe", role="Software Engineer Intern", status="rejected", tag="Resume Screen"),
    ])
    db.commit()


# Routes
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context=get_context(request, "CareerOS - AI Internship Platform"))

@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context=get_context(request, "Login - CareerOS"))

@app.get("/signup", response_class=HTMLResponse)
async def read_signup(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html", context=get_context(request, "Sign Up - CareerOS"))

@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context=get_context(request, "Dashboard - CareerOS"))

@app.get("/roadmap", response_class=HTMLResponse)
async def read_roadmap(request: Request):
    return templates.TemplateResponse(request=request, name="roadmap.html", context=get_context(request, "Roadmap - CareerOS"))

@app.get("/applications", response_class=HTMLResponse)
async def read_applications(request: Request):
    return templates.TemplateResponse(request=request, name="applications.html", context=get_context(request, "Application Tracker - CareerOS"))

@app.get("/coding", response_class=HTMLResponse)
async def read_coding(request: Request):
    return templates.TemplateResponse(request=request, name="coding.html", context=get_context(request, "Coding Analytics - CareerOS"))

@app.get("/resume", response_class=HTMLResponse)
async def read_resume(request: Request):
    return templates.TemplateResponse(request=request, name="resume.html", context=get_context(request, "Resume Analyzer - CareerOS"))

@app.get("/interviews", response_class=HTMLResponse)
async def read_interviews(request: Request):
    return templates.TemplateResponse(request=request, name="interviews.html", context=get_context(request, "Mock Interviews - CareerOS"))

@app.get("/assistant", response_class=HTMLResponse)
async def read_assistant(request: Request):
    return templates.TemplateResponse(request=request, name="assistant.html", context=get_context(request, "AI Assistant - CareerOS"))

@app.get("/settings", response_class=HTMLResponse)
async def read_settings(request: Request):
    return templates.TemplateResponse(request=request, name="settings.html", context=get_context(request, "Settings - CareerOS"))

@app.get("/profile", response_class=HTMLResponse)
async def read_profile(request: Request):
    return templates.TemplateResponse(request=request, name="profile.html", context=get_context(request, "Profile - CareerOS"))


@app.get("/api/health/db")
def read_database_health():
    return database_health()


@app.get("/api/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_ready_db)):
    seed_applications(db)
    return db.query(Application).order_by(Application.created_at.desc()).all()


@app.post("/api/applications", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_ready_db)):
    application = Application(**payload.model_dump())
    db.add(application)

    try:
        db.commit()
        db.refresh(application)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save application.") from exc

    return application


@app.patch("/api/applications/{application_id}", response_model=ApplicationOut)
def update_application(application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_ready_db)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        setattr(application, field, value)

    try:
        db.commit()
        db.refresh(application)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update application.") from exc

    return application


@app.delete("/api/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: int, db: Session = Depends(get_ready_db)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")

    try:
        db.delete(application)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not delete application.") from exc

    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
