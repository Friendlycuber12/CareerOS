import json
import os
import urllib.request

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
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

# ── Gemini client (lazy) ──────────────────────────────────────────────────────
_gemini_client = None

def get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client

def call_gemini(prompt: str, system: str = "", max_tokens: int = 1500,
                temperature: float = 0.7, json_mode: bool = False):
    """Call Gemini and return (text, error_msg)."""
    try:
        from google import genai
        from google.genai import types

        client = get_gemini()

        config_kwargs = dict(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system:
            config_kwargs["system_instruction"] = system
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**config_kwargs)

        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            config=config,
            contents=prompt,
        )
        return resp.text, None
    except Exception as e:
        err = str(e)
        if "quota" in err.lower() or "429" in err or "RESOURCE_EXHAUSTED" in err:
            return None, "quota"
        if "API_KEY_INVALID" in err or "invalid" in err.lower():
            return None, "invalid_key"
        return None, err

def call_gemini_chat(messages: list[dict], system: str = "",
                     max_tokens: int = 1500, temperature: float = 0.7):
    """Call Gemini with chat history and return (text, error_msg)."""
    try:
        from google import genai
        from google.genai import types

        client = get_gemini()

        # Build contents from history
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=m["content"])])
            )

        config = types.GenerateContentConfig(
            system_instruction=system if system else None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            config=config,
            contents=contents,
        )
        return resp.text, None
    except Exception as e:
        err = str(e)
        if "quota" in err.lower() or "429" in err or "RESOURCE_EXHAUSTED" in err:
            return None, "quota"
        if "API_KEY_INVALID" in err or "invalid" in err.lower():
            return None, "invalid_key"
        return None, err


# ── Pydantic schemas ───────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

class RoadmapRequest(BaseModel):
    goal: str
    level: str = "Intermediate (50–150 problems)"
    timeline: str = "8 weeks"

class InterviewRequest(BaseModel):
    category: str
    action: str
    answer: str = ""
    question_count: int = 0


# ── Helpers ────────────────────────────────────────────────────────────────
def get_context(request: Request, title: str):
    return {"request": request, "title": title}

def get_ready_db():
    try:
        ensure_database_initialized()
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable.") from exc
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


# ── Page routes ────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context=get_context(request, "CareerOS"))

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
    return templates.TemplateResponse(request=request, name="applications.html", context=get_context(request, "Applications - CareerOS"))

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


# ── Application CRUD ──────────────────────────────────────────────────────
@app.get("/api/health/db")
def read_database_health():
    return database_health()

@app.get("/api/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_ready_db)):
    seed_applications(db)
    return db.query(Application).order_by(Application.created_at.desc()).all()

@app.post("/api/applications", response_model=ApplicationOut, status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_ready_db)):
    application = Application(**payload.model_dump())
    db.add(application)
    try:
        db.commit(); db.refresh(application)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save application.") from exc
    return application

@app.patch("/api/applications/{application_id}", response_model=ApplicationOut)
def update_application(application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_ready_db)):
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Not found.")
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(application, field, value)
    try:
        db.commit(); db.refresh(application)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update.") from exc
    return application

@app.delete("/api/applications/{application_id}", status_code=204)
def delete_application(application_id: int, db: Session = Depends(get_ready_db)):
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Not found.")
    try:
        db.delete(application); db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not delete.") from exc


# ── Coding Stats Proxy ────────────────────────────────────────────────────
def fetch_url(url: str, timeout: int = 8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CareerOS/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

@app.get("/api/coding/stats")
async def coding_stats(lc: str = "", cf: str = ""):
    result = {}

    if lc:
        data = fetch_url(f"https://leetcode-stats-api.herokuapp.com/{lc}")
        if data and data.get("status") == "success":
            result["leetcode"] = {
                "username": lc,
                "totalSolved": data.get("totalSolved", 0),
                "easySolved": data.get("easySolved", 0),
                "mediumSolved": data.get("mediumSolved", 0),
                "hardSolved": data.get("hardSolved", 0),
                "totalQuestions": data.get("totalQuestions", 3000),
                "acceptanceRate": round(data.get("acceptanceRate", 0), 1),
                "ranking": data.get("ranking", 0),
                "profileUrl": f"https://leetcode.com/u/{lc}/",
            }
        else:
            data2 = fetch_url(f"https://alfa-leetcode-api.onrender.com/userProfile/{lc}")
            if data2 and not data2.get("errors"):
                result["leetcode"] = {
                    "username": lc,
                    "totalSolved": data2.get("totalSolved", 0),
                    "easySolved": data2.get("easySolved", 0),
                    "mediumSolved": data2.get("mediumSolved", 0),
                    "hardSolved": data2.get("hardSolved", 0),
                    "totalQuestions": 3000,
                    "acceptanceRate": round(data2.get("acceptanceRate", 0), 1),
                    "ranking": data2.get("ranking", 0),
                    "profileUrl": f"https://leetcode.com/u/{lc}/",
                }
            else:
                result["leetcode_error"] = f"Could not fetch stats for '{lc}'. Check the username."

    if cf:
        data = fetch_url(f"https://codeforces.com/api/user.info?handles={cf}")
        if data and data.get("status") == "OK" and data.get("result"):
            u = data["result"][0]
            result["codeforces"] = {
                "username": cf,
                "handle": u.get("handle", cf),
                "rating": u.get("rating", 0),
                "maxRating": u.get("maxRating", 0),
                "rank": u.get("rank", "unrated"),
                "maxRank": u.get("maxRank", "unrated"),
                "contribution": u.get("contribution", 0),
                "friendOfCount": u.get("friendOfCount", 0),
                "avatar": u.get("titlePhoto", ""),
                "profileUrl": f"https://codeforces.com/profile/{cf}",
            }
        else:
            result["codeforces_error"] = f"Could not fetch stats for '{cf}'. Check the username."

    return result


# ── AI Error helpers ──────────────────────────────────────────────────────
def ai_error_response(err: str, feature: str = "AI"):
    if err == "quota":
        return JSONResponse(status_code=429, content={
            "error": "quota",
            "message": f"{feature} quota exceeded. Check your Gemini API quota at console.cloud.google.com"
        })
    if err == "invalid_key":
        return JSONResponse(status_code=401, content={
            "error": "invalid_key",
            "message": "Invalid Gemini API key. Please check your GEMINI_API_KEY secret."
        })
    raise HTTPException(status_code=500, detail=f"{feature} error: {err}")


# ── AI Chat ───────────────────────────────────────────────────────────────
CHAT_SYSTEM = """You are CareerOS AI — an expert internship preparation coach for software engineering students.

Your expertise:
- Data Structures & Algorithms (with Python/Java/C++ code examples)
- System Design (scalability, databases, caching, REST APIs, microservices)
- Core CS: Operating Systems, DBMS, Computer Networks, OOP
- Behavioral interviews (STAR method)
- Resume writing and ATS optimization
- Career strategy and company-specific tips (FAANG, startups)

Style: concise but thorough, use markdown code blocks for code, explain WHY behind concepts, give time/space complexity, be encouraging."""

@app.post("/api/ai/chat")
async def ai_chat(payload: ChatRequest):
    messages = []
    for h in payload.history[-12:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            role = "user" if h["role"] == "user" else "model"
            messages.append({"role": role, "content": h["content"]})
    messages.append({"role": "user", "content": payload.message})

    text, err = call_gemini_chat(messages, system=CHAT_SYSTEM, max_tokens=1500)
    if text:
        return {"reply": text}
    return ai_error_response(err, "Chat AI")


# ── AI Roadmap ────────────────────────────────────────────────────────────
@app.post("/api/ai/roadmap")
async def ai_roadmap(payload: RoadmapRequest):
    num_phases = 3 if "4 week" in payload.timeline else 5 if "6 month" in payload.timeline else 4

    prompt = f"""Generate a detailed internship preparation roadmap.

Profile:
- Goal: {payload.goal}
- Current Level: {payload.level}
- Timeline: {payload.timeline}

Return ONLY valid JSON with this EXACT structure (no markdown, no extra text):
{{
  "phases": [
    {{
      "title": "Phase 1: Foundation (Weeks 1-2)",
      "description": "Brief description of this phase",
      "tags": ["15 Easy", "5 Medium"],
      "tasks": [
        {{"text": "Specific actionable task with problem count", "done": false}}
      ]
    }}
  ]
}}

Requirements:
- Generate exactly {num_phases} phases matching the {payload.timeline} timeline
- Each phase must have 3-5 specific, actionable tasks with problem counts
- Tailor ALL content specifically to: {payload.goal}
- For SWE roles: DSA progression (Easy → Medium → Hard) + System Design in later phases
- For Data Science: Python, ML algorithms, Statistics, SQL, Pandas
- For DevOps: Linux, Docker, Kubernetes, CI/CD, Cloud (AWS/GCP)
- For PM: Product thinking, metrics, case studies, SQL, user research
- Include relevant CS subjects (OS, DBMS, Networks) in the final phase
- Make task descriptions specific and actionable (not generic)"""

    text, err = call_gemini(prompt, max_tokens=2000, temperature=0.7, json_mode=True)
    if text:
        try:
            return json.loads(text)
        except Exception:
            # Try to extract JSON if wrapped in markdown
            import re
            m = re.search(r'\{[\s\S]+\}', text)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass

    if err in ("quota", "invalid_key"):
        return JSONResponse(status_code=429 if err == "quota" else 401,
                            content={"error": err, "message": f"Gemini API error: {err}"})

    return _fallback_roadmap(payload.goal, payload.timeline)


def _fallback_roadmap(goal: str, timeline: str):
    return {
        "phases": [
            {
                "title": "Phase 1: Foundation",
                "description": f"Core fundamentals for {goal} — Arrays, Strings, Hash Maps",
                "tags": ["15 Easy", "5 Medium"],
                "tasks": [
                    {"text": "Master Array & String patterns — solve 15 Easy problems", "done": False},
                    {"text": "Hash Map fundamentals — Two Sum, Group Anagrams, LRU Cache", "done": False},
                    {"text": "Two Pointer technique — Valid Palindrome, Container With Water", "done": False},
                ]
            },
            {
                "title": "Phase 2: Core Algorithms",
                "description": "Sliding Window, Binary Search, Linked Lists, Trees",
                "tags": ["20 Medium", "5 Hard"],
                "tasks": [
                    {"text": "Binary Search — 8 problems including rotated arrays", "done": False},
                    {"text": "Sliding Window — Max Subarray, Min Window Substring", "done": False},
                    {"text": "Linked List — reverse, merge, detect cycle", "done": False},
                    {"text": "Binary Trees — BFS, DFS, Level Order — 10 problems", "done": False},
                ]
            },
            {
                "title": "Phase 3: Advanced Topics",
                "description": "Dynamic Programming, Graphs, Backtracking",
                "tags": ["15 Medium", "10 Hard"],
                "tasks": [
                    {"text": "DP patterns — 0/1 Knapsack, LCS, LIS — 10 problems", "done": False},
                    {"text": "Graph BFS, DFS, Dijkstra, Topological Sort", "done": False},
                    {"text": "Backtracking — Subsets, Permutations, N-Queens", "done": False},
                    {"text": "System Design — Design Twitter / URL Shortener", "done": False},
                ]
            },
            {
                "title": "Phase 4: Interview Prep",
                "description": "Mock interviews, CS fundamentals, behavioral prep",
                "tags": ["Mock Interviews", "CS Theory"],
                "tasks": [
                    {"text": "OS concepts — Processes, Threads, Memory Management, Deadlocks", "done": False},
                    {"text": "DBMS — SQL, Indexing, Transactions, ACID properties", "done": False},
                    {"text": "Computer Networks — HTTP, TCP/IP, DNS, TLS", "done": False},
                    {"text": "Behavioral prep — 10 STAR stories (leadership, teamwork, failures)", "done": False},
                    {"text": "Mock interview — complete 3 full DSA mock sessions", "done": False},
                ]
            },
        ]
    }


# ── AI Resume ─────────────────────────────────────────────────────────────
@app.post("/api/ai/resume")
async def ai_resume(file: UploadFile = File(...)):
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
        raise HTTPException(status_code=400, detail="Could not extract text from file.")

    resume_text = resume_text[:5000]

    prompt = f"""You are an expert ATS resume analyzer for software engineering internship roles.

Analyze this resume and return ONLY valid JSON (no markdown) with this EXACT structure:
{{
  "ats_score": <integer 0-100>,
  "metrics": [
    {{"name": "Action Verbs", "status": "strong", "description": "Strong verbs used in most bullets"}},
    {{"name": "Quantified Impact", "status": "improve", "description": "Only 3/10 bullets have numbers"}},
    {{"name": "Keyword Match", "status": "weak", "description": "Missing: Docker, CI/CD, REST APIs"}},
    {{"name": "Formatting", "status": "strong", "description": "Clean single-column ATS-friendly layout"}},
    {{"name": "Contact Info", "status": "strong", "description": "Name, email, phone, LinkedIn/GitHub present"}},
    {{"name": "Skills Section", "status": "good", "description": "Good coverage, consider categorizing"}}
  ],
  "skills": ["Python", "JavaScript", "React", "SQL"],
  "missing_keywords": ["Docker", "Kubernetes", "CI/CD", "REST API", "Agile"],
  "suggestions": [
    {{
      "title": "Add quantified impact to every bullet",
      "detail": "Hiring managers scan for numbers. Aim for 80%+ bullets with metrics.",
      "example": "Before: 'Built API endpoints' → After: 'Built 8 REST API endpoints serving 50K+ daily requests'"
    }}
  ]
}}

Status values must be one of: "strong", "good", "great", "perfect", "improve", "weak"
Provide 3-5 improvement suggestions specific to THIS resume.
Be specific and realistic based on the actual content below.

Resume:
---
{resume_text}
---"""

    text, err = call_gemini(prompt, max_tokens=1800, temperature=0.2, json_mode=True)
    if text:
        try:
            return json.loads(text)
        except Exception:
            import re
            m = re.search(r'\{[\s\S]+\}', text)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass

    return ai_error_response(err, "Resume AI")


# ── AI Interview ──────────────────────────────────────────────────────────
INTERVIEW_CONTEXTS = {
    "dsa": "LeetCode-style Data Structures & Algorithms. Ask a real problem with constraints and example I/O. Expect working code with time/space complexity analysis.",
    "system_design": "System Design. Ask to design a real-world system (Twitter feed, URL shortener, Uber, Netflix). Expect architecture, components, data models, and trade-offs.",
    "os": "Operating Systems. Cover processes, threads, scheduling algorithms, memory management, virtual memory, deadlocks, synchronization (mutex, semaphore, monitor).",
    "dbms": "Database Management Systems. Cover SQL queries, normalization, indexing (B-trees), transactions, ACID properties, joins, query optimization, NoSQL vs SQL.",
    "networks": "Computer Networks. Cover OSI model, TCP vs UDP, HTTP/HTTPS, TLS handshake, DNS resolution, REST APIs, WebSockets, CDN, load balancing, subnetting.",
    "behavioral": "Behavioral interview using the STAR method. Ask about specific real situations involving leadership, conflict resolution, failures, teamwork, and measurable impact.",
}

@app.post("/api/ai/interview")
async def ai_interview(payload: InterviewRequest):
    ctx = INTERVIEW_CONTEXTS.get(payload.category, "general software engineering interview")

    if payload.action == "start":
        prompt = f"""You are a senior engineer at Google/Meta/Amazon conducting a live {payload.category.upper()} mock interview.

Context: {ctx}

Start with a warm professional greeting (1-2 sentences), then immediately ask Question #{payload.question_count + 1}.

For DSA: State the problem clearly with example inputs/outputs and constraints. End with "Take your time. Think out loud as you approach it."
For System Design: Describe the system scenario and scale requirements clearly. End with "Start with clarifying questions, then walk me through your architecture."
For OS/DBMS/Networks: Ask a specific conceptual question that tests deep understanding.
For Behavioral: Ask about a specific past situation (not hypothetical).

Keep it natural and encouraging. Do NOT give hints or solutions."""

    elif payload.action == "answer":
        prompt = f"""You are conducting a {payload.category.upper()} mock interview. Evaluate this candidate answer:

"{payload.answer}"

Provide structured feedback:

**✅ What you got right:**
[List specific strengths from their answer]

**⚠️ What to improve:**
[Specific gaps, missed edge cases, or better approaches]

**💡 Model answer:**
[Complete ideal answer — include working code with complexity analysis for DSA, full architecture for system design, or thorough explanation for theory questions]

**Score: X/10** — [1-sentence justification]

After the score, add: "Ready for the next question? Click 'Next Question' or keep discussing."

Be honest, constructive, and educational. Keep under 300 words."""

    elif payload.action == "next":
        prompt = f"""You are conducting a {payload.category.upper()} mock interview.

Context: {ctx}

Ask Question #{payload.question_count + 1}. Make it:
- A DIFFERENT topic/pattern from previous questions
- Appropriately harder (questions get progressively more challenging)
- Realistic and commonly asked at top tech companies

For DSA: Different algorithm/data structure with clear constraints and examples.
For System Design: A different system type.
For theory: A different sub-topic.
For Behavioral: A different life situation (teamwork vs leadership vs failure).

Ask the question directly. No preamble. No hints."""

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use: start, answer, next")

    text, err = call_gemini(prompt, max_tokens=700, temperature=0.75)
    if text:
        return {"message": text, "next_question": payload.action == "answer"}

    if err in ("quota", "invalid_key"):
        sample = _sample_question(payload.category)
        fallback = {
            "start": f"👋 Welcome to your {payload.category.upper()} mock interview!\n\n⚠️ **Gemini API issue** ({err}). Showing a sample question:\n\n{sample}",
            "answer": f"⚠️ **Gemini API issue** ({err}). Unable to evaluate your answer right now.",
            "next": f"⚠️ **Gemini API issue** ({err}). Here's a sample next question:\n\n{sample}",
        }
        return {"message": fallback.get(payload.action, "AI unavailable."), "next_question": False}

    raise HTTPException(status_code=500, detail=f"Interview AI error: {err}")


def _sample_question(category: str) -> str:
    samples = {
        "dsa": "**Two Sum** — Given `nums = [2,7,11,15]` and `target = 9`, return `[0,1]`.\n\nConstraints: 2 ≤ n ≤ 10⁴, -10⁹ ≤ nums[i] ≤ 10⁹, exactly one solution exists.\n\nWhat's your approach and time/space complexity?",
        "system_design": "**Design a URL Shortener** (bit.ly)\n\nRequirements: Shorten URLs to 7-character codes, redirect on visit, handle 100M URLs and 1B redirects/day.\n\nWalk me through your full system architecture.",
        "os": "**Explain the difference between a process and a thread.** When would you use multiple processes vs threads? Discuss memory, communication overhead, and fault isolation trade-offs.",
        "dbms": "**What is database indexing?** Explain how a B-tree index works internally, when to add vs avoid indexes, and what a composite index is with an example.",
        "networks": "**What happens when you type google.com in a browser?** Walk through every step: DNS resolution, TCP handshake, TLS negotiation, HTTP request, and page rendering.",
        "behavioral": "**Tell me about a time you faced a significant technical challenge on a project.** Use the STAR format: Situation, Task, Action, Result.",
    }
    return samples.get(category, "Tell me about your most challenging technical project and how you overcame the obstacles.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
