import json
import os
import urllib.request
import urllib.error

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
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

# ── OpenAI client (lazy) ──────────────────────────────────────────────────────
_openai_client = None

def get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="OPENAI_API_KEY not set.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client

def call_openai(messages, max_tokens=1200, temperature=0.7, json_mode=False):
    """Call OpenAI with error handling. Returns (text, error_msg)."""
    try:
        client = get_openai()
        kwargs = dict(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content, None
    except Exception as e:
        err = str(e)
        if "insufficient_quota" in err or "quota" in err.lower():
            return None, "quota"
        return None, err


# ── Pydantic schemas ────────────────────────────────────────────────────────
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


# ── Application CRUD ─────────────────────────────────────────────────────
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


# ── Coding Stats Proxy ───────────────────────────────────────────────────
def fetch_url(url: str, timeout: int = 8):
    """Fetch a URL and return parsed JSON or None."""
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
                "contributionPoints": data.get("contributionPoints", 0),
                "profileUrl": f"https://leetcode.com/u/{lc}/",
            }
        else:
            # Try alternate API
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


# ── AI Endpoints ─────────────────────────────────────────────────────────

QUOTA_MSG = (
    "⚠️ **OpenAI API Quota Exceeded**\n\n"
    "Your OpenAI API key has run out of credits. To fix this:\n"
    "1. Go to [platform.openai.com/account/billing](https://platform.openai.com/account/billing)\n"
    "2. Add a payment method and purchase credits\n"
    "3. Come back and try again — no code changes needed!\n\n"
    "**In the meantime**, here's a quick answer: "
)

@app.post("/api/ai/chat")
async def ai_chat(payload: ChatRequest):
    system_prompt = """You are CareerOS AI — an expert internship preparation coach for software engineering students.

Your expertise:
- Data Structures & Algorithms (with Python/Java/C++ code examples)
- System Design (scalability, databases, caching, REST APIs, microservices)
- Core CS: Operating Systems, DBMS, Computer Networks, OOP
- Behavioral interviews (STAR method)
- Resume writing and ATS optimization
- Career strategy and company-specific tips (FAANG, startups)

Style: concise but thorough, use code blocks for code, explain WHY behind concepts, give time/space complexity, be encouraging."""

    messages = [{"role": "system", "content": system_prompt}]
    for h in payload.history[-10:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": payload.message})

    text, err = call_openai(messages, max_tokens=1500)
    if text:
        return {"reply": text}
    if err == "quota":
        return {"reply": QUOTA_MSG + "I'm unable to answer right now — please add OpenAI credits to enable the AI Assistant.", "quota_error": True}
    raise HTTPException(status_code=500, detail=f"AI error: {err}")


@app.post("/api/ai/roadmap")
async def ai_roadmap(payload: RoadmapRequest):
    prompt = f"""Generate a detailed internship preparation roadmap.

Profile:
- Goal: {payload.goal}
- Current Level: {payload.level}
- Timeline: {payload.timeline}

Return ONLY valid JSON (no markdown, no extra text) in this EXACT structure:
{{
  "phases": [
    {{
      "title": "Phase 1: Foundation (Weeks 1-2)",
      "description": "Arrays, Strings, Hash Maps, Two Pointers — core building blocks",
      "tags": ["15 Easy", "5 Medium"],
      "tasks": [
        {{"text": "Master Array & String patterns — solve 10 problems", "done": false}},
        {{"text": "Hash Map fundamentals + practice 8 problems", "done": false}},
        {{"text": "Two Pointer technique — 6 problems", "done": false}}
      ]
    }},
    {{
      "title": "Phase 2: Core Algorithms (Weeks 3-5)",
      "description": "Sliding Window, Binary Search, Linked Lists, Trees",
      "tags": ["20 Medium", "5 Hard"],
      "tasks": [
        {{"text": "Binary Search — 8 problems including rotated arrays", "done": false}},
        {{"text": "Sliding Window — 6 problems", "done": false}},
        {{"text": "Linked List — reverse, merge, cycle detection", "done": false}},
        {{"text": "Binary Trees — BFS, DFS, 10 problems", "done": false}}
      ]
    }}
  ]
}}

Requirements:
- Generate exactly {3 if '4 weeks' in payload.timeline else 4 if '8 weeks' in payload.timeline else 5} phases matching the {payload.timeline} timeline
- Each phase: 3-5 specific, actionable tasks with problem counts
- Tailor content specifically to: {payload.goal}
- For SWE roles: include DSA progression + System Design in later phases
- For Data Science: include ML, Python, Statistics
- For PM: include product thinking, case studies, metrics
- Progress: Easy → Medium → Hard
- Include CS subjects (OS, DBMS, Networks) appropriate for the role"""

    text, err = call_openai([{"role": "user", "content": prompt}], max_tokens=2000, json_mode=True)
    if text:
        try:
            return json.loads(text)
        except Exception:
            pass

    if err == "quota":
        return JSONResponse(status_code=402, content={"error": "quota", "message": "OpenAI quota exceeded. Please add credits at platform.openai.com/account/billing"})

    # Fallback: return a goal-appropriate default roadmap
    return _fallback_roadmap(payload.goal, payload.timeline)

def _fallback_roadmap(goal: str, timeline: str):
    """Return a static fallback roadmap when AI is unavailable."""
    return {
        "phases": [
            {
                "title": "Phase 1: Foundation",
                "description": f"Core fundamentals for {goal} — Arrays, Strings, Hash Maps",
                "tags": ["15 Easy", "5 Medium"],
                "tasks": [
                    {"text": "Master Array & String patterns — solve 15 Easy problems", "done": False},
                    {"text": "Hash Map fundamentals — 8 problems (Two Sum, Group Anagrams)", "done": False},
                    {"text": "Two Pointer technique — 6 problems (Valid Palindrome, Container With Water)", "done": False},
                ]
            },
            {
                "title": "Phase 2: Core Algorithms",
                "description": "Sliding Window, Binary Search, Linked Lists, Trees",
                "tags": ["20 Medium", "5 Hard"],
                "tasks": [
                    {"text": "Binary Search — 8 problems including rotated arrays", "done": False},
                    {"text": "Sliding Window — 6 problems (Max Subarray, Min Window)", "done": False},
                    {"text": "Linked List — reverse, merge, detect cycle", "done": False},
                    {"text": "Binary Trees — BFS, DFS, Level Order, 10 problems", "done": False},
                ]
            },
            {
                "title": "Phase 3: Advanced Topics",
                "description": "Dynamic Programming, Graphs, Backtracking",
                "tags": ["15 Medium", "10 Hard"],
                "tasks": [
                    {"text": "DP patterns — 0/1 Knapsack, LCS, LIS (10 problems)", "done": False},
                    {"text": "Graph traversal — BFS, DFS, Dijkstra's algorithm", "done": False},
                    {"text": "Backtracking — Subsets, Permutations, N-Queens", "done": False},
                    {"text": "System Design basics — URL Shortener, Design Twitter Feed", "done": False},
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
                    {"text": "Behavioral prep — 10 STAR stories for leadership, teamwork, failures", "done": False},
                    {"text": "Mock interview — complete 3 full DSA mock sessions", "done": False},
                ]
            },
        ]
    }


@app.post("/api/ai/resume")
async def ai_resume(file: UploadFile = File(...)):
    content = await file.read()
    resume_text = ""
    filename = file.filename or ""

    if filename.lower().endswith(".pdf"):
        try:
            import io, PyPDF2
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

    prompt = f"""You are an expert ATS resume analyzer. Analyze this resume for software engineering internship roles.

Return ONLY valid JSON (no markdown) with this EXACT structure:
{{
  "ats_score": <integer 0-100>,
  "metrics": [
    {{"name": "Action Verbs", "status": "strong", "description": "Strong action verbs used in most bullet points"}},
    {{"name": "Quantified Impact", "status": "improve", "description": "Add metrics — only 3 bullets have numbers"}},
    {{"name": "Keyword Match", "status": "weak", "description": "Missing: Docker, CI/CD, REST APIs, Microservices"}},
    {{"name": "Formatting", "status": "strong", "description": "Clean single-column layout, ATS-friendly"}},
    {{"name": "Contact Info", "status": "strong", "description": "Name, email, phone, LinkedIn/GitHub present"}},
    {{"name": "Skills Section", "status": "good", "description": "Technical skills listed, consider categorizing"}}
  ],
  "skills": ["Python", "JavaScript", "React", "SQL"],
  "missing_keywords": ["Docker", "Kubernetes", "CI/CD", "REST API", "Agile", "Git"],
  "suggestions": [
    {{"title": "Add quantified impact to every bullet", "detail": "Hiring managers scan for numbers. Aim for 80%+ of bullets to have a metric.", "example": "Before: 'Built API endpoints' → After: 'Built 8 REST API endpoints serving 50K+ daily requests'"}},
    {{"title": "Include missing DevOps keywords", "detail": "Top ATS systems screen for Docker, CI/CD, Git in SWE roles.", "example": "Add to skills: Docker, GitHub Actions, CI/CD, REST APIs"}},
    {{"title": "Strengthen project descriptions", "detail": "Each project should state the problem, your solution, and measurable impact.", "example": "Add: 'Reduced page load time by 40% by implementing lazy loading and code splitting'"}}
  ]
}}

Status values: "strong", "good", "great", "perfect", "improve", "weak"

Analyze this resume:
---
{resume_text}
---

Be specific and realistic based on the actual content."""

    text, err = call_openai([{"role": "user", "content": prompt}], max_tokens=1800, temperature=0.2, json_mode=True)
    if text:
        try:
            return json.loads(text)
        except Exception:
            pass

    if err == "quota":
        return JSONResponse(status_code=402, content={"error": "quota", "message": "OpenAI quota exceeded. Add credits at platform.openai.com/account/billing"})

    raise HTTPException(status_code=500, detail=f"Analysis failed: {err}")


INTERVIEW_PROMPTS = {
    "dsa": "LeetCode-style Data Structures & Algorithms coding interview. Ask a real problem with constraints and example I/O. Expect working code with time/space complexity.",
    "system_design": "System Design interview. Ask to design a real system (Twitter feed, URL shortener, Uber, Netflix). Expect architecture, components, trade-offs.",
    "os": "Operating Systems interview covering processes, threads, scheduling algorithms, memory management, virtual memory, deadlocks, synchronization primitives (mutex, semaphore).",
    "dbms": "Database Management Systems interview covering SQL queries, normalization, indexing strategies, transactions, ACID, joins, query optimization, NoSQL vs SQL trade-offs.",
    "networks": "Computer Networks interview covering OSI model, TCP vs UDP, HTTP/HTTPS, TLS handshake, DNS resolution, REST APIs, WebSockets, CDN, load balancing.",
    "behavioral": "Behavioral interview using STAR method. Ask about specific situations involving leadership, conflict resolution, failures, teamwork, impact.",
}

@app.post("/api/ai/interview")
async def ai_interview(payload: InterviewRequest):
    cat_desc = INTERVIEW_PROMPTS.get(payload.category, "general software engineering interview")

    if payload.action == "start":
        prompt = f"""You are a senior engineer at a top tech company (Google/Meta/Amazon) conducting a mock {payload.category.upper()} interview.

Category context: {cat_desc}

Start with a professional greeting, then ask ONE specific question (question #{payload.question_count + 1}).
- DSA: Give a real problem with example inputs, expected output, constraints
- System Design: Set the scenario, scale requirements, constraints clearly
- OS/DBMS/Networks: Ask a concept question that tests deep understanding
- Behavioral: Ask about a specific real situation

Be encouraging but realistic. After the question, say: "Take your time. Think out loud as you work through it."

Do NOT give hints or solutions yet."""

    elif payload.action == "answer":
        prompt = f"""You are conducting a {payload.category.upper()} mock interview. The candidate answered:

"{payload.answer}"

Give structured feedback in this format:
**✅ What you got right:**
[specific strengths]

**⚠️ Areas to improve:**
[specific gaps, missed edge cases, better approaches]

**💡 Ideal answer:**
[complete model answer with code if applicable, time/space complexity]

**Score: X/10** — [brief justification]

After feedback, say: "Ready for the next question? Press 'Next Question' or type your answer."

Keep feedback under 250 words. Be constructive and educational."""

    elif payload.action == "next":
        prompt = f"""You are conducting a {payload.category.upper()} mock interview.

Context: {cat_desc}

Ask the NEXT question (#{payload.question_count + 1}). Make it:
- Different topic/pattern from previous questions
- Appropriate difficulty (progressively harder: easy → medium → hard)
- Realistic and interview-relevant

For DSA: Give a different algorithm/pattern with constraints and examples.
For others: Vary the sub-topic.

Just ask the question directly. Do NOT give hints."""

    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    text, err = call_openai([{"role": "user", "content": prompt}], max_tokens=700, temperature=0.8)
    if text:
        return {"message": text, "next_question": payload.action == "answer"}

    if err == "quota":
        quota_resp = {
            "start": f"⚠️ **OpenAI quota exceeded.** I can't start the interview right now.\n\nTo fix: Add credits at [platform.openai.com/account/billing](https://platform.openai.com/account/billing)\n\n**Sample {payload.category.upper()} question while you fix this:**\n\n" + _sample_question(payload.category),
            "answer": "⚠️ **OpenAI quota exceeded.** Cannot provide feedback right now. Please add OpenAI credits to continue.",
            "next": "⚠️ **OpenAI quota exceeded.** Cannot load next question. Please add OpenAI credits.\n\n**Sample question:**\n\n" + _sample_question(payload.category),
        }
        return {"message": quota_resp.get(payload.action, "OpenAI quota exceeded."), "next_question": False}

    raise HTTPException(status_code=500, detail=f"Interview AI error: {err}")

def _sample_question(category: str) -> str:
    samples = {
        "dsa": "**Two Sum** — Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to target.\n\nExample: `nums = [2,7,11,15], target = 9` → `[0,1]`\n\nConstraints: 2 ≤ nums.length ≤ 10⁴, -10⁹ ≤ nums[i] ≤ 10⁹\n\nWhat's your approach? What's the time and space complexity?",
        "system_design": "**Design a URL Shortener** (like bit.ly)\n\nRequirements:\n- Shorten long URLs to 7-character codes\n- Redirect users when they visit the short URL\n- Handle 100M URLs, 1B redirects/day\n\nWalk me through your system architecture.",
        "os": "**Explain the difference between a process and a thread.** When would you use multiple processes vs multiple threads? What are the trade-offs in terms of memory, communication, and fault isolation?",
        "dbms": "**What is database indexing?** Explain how a B-tree index works internally, when you would and wouldn't add an index, and what a composite index is.",
        "networks": "**What happens when you type google.com in a browser?** Walk me through every step: DNS resolution, TCP handshake, TLS, HTTP request, and rendering.",
        "behavioral": "**Tell me about a time you faced a significant technical challenge.** What was the situation, what was your role, what actions did you take, and what was the result?",
    }
    return samples.get(category, "Tell me about your most challenging technical project and how you overcame obstacles.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
