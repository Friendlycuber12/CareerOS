import json
import os

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import DatabaseUnavailableError, database_health, ensure_database_initialized, get_db
from models import Application
from schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate

app = FastAPI(title="CareerOS API")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── OpenAI client (lazy) ──────────────────────────────────────────────────────
_openai_client = None

def get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


# ── Pydantic schemas for AI endpoints ─────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

class RoadmapRequest(BaseModel):
    goal: str
    level: str = "Intermediate (50–150 problems)"
    timeline: str = "8 weeks"

class InterviewRequest(BaseModel):
    category: str
    action: str  # start | answer | next
    answer: str = ""
    question_count: int = 0


# ── Context helper ─────────────────────────────────────────────────────────────
def get_context(request: Request, title: str):
    return {"request": request, "title": title}


def get_ready_db():
    try:
        ensure_database_initialized()
    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL is not available.",
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


# ── Page routes ────────────────────────────────────────────────────────────────
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


# ── Application CRUD ───────────────────────────────────────────────────────────
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


# ── AI Endpoints ───────────────────────────────────────────────────────────────

@app.post("/api/ai/chat")
async def ai_chat(payload: ChatRequest):
    """General-purpose AI assistant for career prep."""
    client = get_openai()

    system_prompt = """You are CareerOS AI Assistant — an expert career preparation coach for software engineering internship candidates.

Your expertise covers:
- Data Structures & Algorithms (with code examples in Python/Java/C++)
- System Design (scalability, databases, caching, APIs)
- Core CS subjects: Operating Systems, DBMS, Computer Networks, OOP
- Behavioral interview prep (STAR method)
- Resume writing and ATS optimization
- Career strategy and company-specific tips

Response style:
- Be concise yet thorough. Use code blocks for code.
- Format responses clearly with headings, bullet points, and examples.
- Always explain the WHY behind concepts — don't just state facts.
- For coding questions, give time & space complexity.
- Be encouraging and practical."""

    messages = [{"role": "system", "content": system_prompt}]
    for h in payload.history[-10:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": payload.message})

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1500,
            temperature=0.7,
        )
        return {"reply": resp.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/roadmap")
async def ai_roadmap(payload: RoadmapRequest):
    """Generate a personalized study roadmap."""
    client = get_openai()

    prompt = f"""Generate a detailed internship preparation roadmap for someone with this profile:
- Goal: {payload.goal}
- Current Level: {payload.level}
- Available Time: {payload.timeline}

Return ONLY valid JSON (no markdown, no explanation) in this exact structure:
{{
  "phases": [
    {{
      "title": "Phase 1: Foundation (Weeks 1-2)",
      "description": "Brief description of what this phase covers",
      "tags": ["10 Easy", "5 Medium"],
      "tasks": [
        {{"text": "Specific actionable task description", "done": false}},
        {{"text": "Another specific task", "done": false}}
      ]
    }}
  ]
}}

Requirements:
- Generate 3-5 phases appropriate for the timeline
- Each phase should have 3-5 specific, actionable tasks
- Tasks should be concrete (e.g., "Solve 10 Binary Search problems on LeetCode", not "Practice coding")
- Tags should indicate difficulty/volume (e.g., "15 Easy", "10 Medium", "System Design")
- Tailor content specifically to the goal: {payload.goal}
- Progress logically from foundations to advanced topics
- Include system design topics for SWE roles
- Include relevant CS subjects (OS, DBMS, Networks) as appropriate"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/resume")
async def ai_resume(file: UploadFile = File(...)):
    """Analyze uploaded resume for ATS score and suggestions."""
    client = get_openai()

    content = await file.read()
    resume_text = ""

    filename = file.filename or ""
    if filename.lower().endswith(".pdf"):
        try:
            import io
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                resume_text += page.extract_text() or ""
        except Exception:
            resume_text = content.decode("utf-8", errors="ignore")
    else:
        resume_text = content.decode("utf-8", errors="ignore")

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from resume.")

    resume_text = resume_text[:6000]

    prompt = f"""You are an expert ATS (Applicant Tracking System) analyzer and career coach.

Analyze this resume text and return ONLY valid JSON (no markdown) with this exact structure:
{{
  "ats_score": <integer 0-100>,
  "metrics": [
    {{"name": "Action Verbs", "status": "strong", "description": "85% of bullets start with strong action verbs like 'Implemented', 'Designed', 'Optimized'"}},
    {{"name": "Quantified Impact", "status": "improve", "description": "Only 40% of bullets have metrics. Add numbers like 'reduced latency by 30%'"}},
    {{"name": "Keywords Match", "status": "weak", "description": "Missing key terms: 'CI/CD', 'Microservices', 'Docker'"}},
    {{"name": "Formatting", "status": "strong", "description": "Clean single-column format. No tables or complex layouts detected."}},
    {{"name": "Contact Info", "status": "strong", "description": "Name, email, phone, GitHub/LinkedIn all present."}},
    {{"name": "Skills Section", "status": "improve", "description": "Skills section present but could be organized by category."}}
  ],
  "skills": ["Python", "JavaScript", "React", "Node.js", "SQL"],
  "missing_keywords": ["Docker", "Kubernetes", "CI/CD", "GraphQL", "Redis"],
  "suggestions": [
    {{
      "title": "Quantify your impact",
      "detail": "Add specific metrics to at least 80% of your bullet points. Hiring managers and ATS systems look for measurable achievements.",
      "example": "Before: 'Worked on backend APIs' → After: 'Designed and deployed 12 REST APIs serving 50K+ daily requests with 99.9% uptime'"
    }},
    {{
      "title": "Add missing technical keywords",
      "detail": "Include industry-standard keywords that ATS systems screen for in software engineering roles.",
      "example": "Add a dedicated 'Technical Skills' section listing: Docker, Kubernetes, CI/CD pipelines, REST APIs, Agile/Scrum"
    }},
    {{
      "title": "Strengthen action verbs",
      "detail": "Start each bullet with a powerful action verb. Weak verbs like 'worked on' or 'helped with' reduce your ATS score.",
      "example": "Use: Architected, Engineered, Optimized, Spearheaded, Deployed, Automated, Reduced, Increased"
    }}
  ]
}}

Status values must be one of: "strong", "good", "great", "perfect", "improve", "weak"

Resume text to analyze:
---
{resume_text}
---

Be realistic and specific based on the actual resume content. The ATS score should reflect the real quality."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


INTERVIEW_PROMPTS = {
    "dsa": "Data Structures & Algorithms coding interview questions (LeetCode-style). Ask a real problem, specify constraints, and expect the candidate to write working code with time/space complexity analysis.",
    "system_design": "System Design interview questions. Ask about designing real-world systems like URL shortener, Twitter feed, ride-sharing app, etc. Expect architecture diagrams and trade-off discussions.",
    "os": "Operating Systems interview questions covering processes, threads, scheduling, memory management, virtual memory, deadlocks, synchronization, and IPC.",
    "dbms": "Database Management Systems questions covering SQL, normalization, indexing, transactions, ACID properties, joins, query optimization, and NoSQL vs SQL.",
    "networks": "Computer Networks questions covering OSI model, TCP/IP, HTTP/HTTPS, DNS, TLS/SSL, REST, WebSockets, CDNs, load balancing, and network security.",
    "behavioral": "Behavioral interview questions using the STAR (Situation, Task, Action, Result) method. Ask about leadership, teamwork, conflicts, failures, and achievements.",
}

@app.post("/api/ai/interview")
async def ai_interview(payload: InterviewRequest):
    """AI mock interviewer for various technical and behavioral categories."""
    client = get_openai()
    category_desc = INTERVIEW_PROMPTS.get(payload.category, "general software engineering interview questions")

    if payload.action == "start":
        prompt = f"""You are a senior software engineer at a top tech company (Google/Meta/Amazon) conducting a mock interview.

Category: {category_desc}

Start the interview professionally. Ask ONE specific question appropriate for this category. 
- For DSA: give a real problem with example inputs/outputs and constraints
- For System Design: set the scenario and requirements clearly  
- For OS/DBMS/Networks: ask a conceptual question that tests deep understanding
- For Behavioral: ask a specific situation-based question

Be encouraging but professional. Do NOT give hints or answers yet. End with "Take your time to think through this."

Question #{payload.question_count + 1}:"""

    elif payload.action == "answer":
        prompt = f"""You are conducting a mock interview. The candidate just answered a {payload.category} question.

Their answer: "{payload.answer}"

Provide structured feedback:
1. **What was good** — specific strengths in their answer
2. **What to improve** — specific gaps, missed edge cases, or better approaches  
3. **Model answer** — the ideal/complete answer with code if applicable
4. **Score** — rate their answer X/10 with brief justification

Be constructive and educational. After feedback, say "Ready for the next question? Reply 'yes' or I'll move on."

Keep feedback concise but thorough (under 300 words)."""

    elif payload.action == "next":
        prompt = f"""You are conducting a mock interview. 

Category: {category_desc}

Ask the next interview question (question #{payload.question_count + 1}). Make it different from previous questions but still in the same category.
- Vary difficulty (easy → medium → hard progression)
- For DSA: give a different topic/pattern than before
- Keep questions realistic and interview-relevant

Question #{payload.question_count + 1}:"""
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.8,
        )
        message = resp.choices[0].message.content
        next_q = payload.action == "answer" and "next question" in message.lower()
        return {"message": message, "next_question": next_q}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
