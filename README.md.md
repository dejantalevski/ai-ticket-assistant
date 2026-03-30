# **End-to-End Example: Enterprise AI Ticket Assistant**

A complete production-ready Agentic AI feature that combines all three core architectural patterns into one coherent orchestration system.

### **The scenario**

An employee submits a raw, unstructured support ticket (e.g., *"I need an Adobe license for a new project"*). The system must:

* **Extract structured data** (intent, urgency, entities, and missing info) from the natural language request.  
* **Analyze confidence and sentiment** to safely decide between automation or human handoff.  
* **Execute the workflow** by triggering the correct mock API actions (Slack approval, Okta provisioning, or Jira escalation).

### **The three patterns — where each one appears**

| Pattern | Where it's used | Why it's needed |
| :---- | :---- | :---- |
| **Schema** | Step 1 — extraction | Tickets arrive in unpredictable natural language; downstream APIs (Okta, Slack) require guaranteed JSON fields and data types. |
| **Delegation** | Steps 1→2→3 pipeline | Classification, extraction, and execution/escalation are entirely different jobs requiring distinct logic gates. |
| **Role** | The AI System Prompt | Keeps the LLM acting strictly as an objective "Triage Specialist," preventing it from hallucinating troubleshooting steps. |

### **Files**

* `app.py` ← **START HERE** — the full FastAPI orchestration server, validation schema, and mock APIs in one file.  
* `requirements.txt` ← Python dependencies (`fastapi`, `uvicorn`, `pydantic`).  
* `.env.example` ← Template for environment variables (for future API key integration).

### **Run:**

**1\. Install dependencies:**

Bash  
pip install \-r requirements.txt

**2\. Start the local server:**

Bash  
uvicorn app:app \--reload

**3\. Trigger the pipeline (Run this in a separate PowerShell terminal):**

PowerShell  
Invoke-RestMethod \-Uri "http://127.0.0.1:8000/webhook/ticket-created" \-Method Post \-ContentType "application/json" \-Body '{"ticket\_id": "IT-1042", "user\_email": "alice@company.com", "description": "Can I get an Adobe license for my new project?"}'