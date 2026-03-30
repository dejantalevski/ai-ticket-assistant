"""
End-to-End IT Ticket Assistant
==============================
A complete AI feature combining all three production patterns:

  Pattern 1 — SCHEMA      : Structured output via tool_use
                            Raw IT ticket  →  guaranteed JSON fields
                            (perfect for webhooks to Okta/Jira)

  Pattern 2 — DELEGATION  : Three specialised steps in sequence
                            Extract  →  Evaluate & Route  →  Write Response
                            (separates data parsing from decision-making)

  Pattern 3 — ROLE        : Identity + Constraints + Context in every call
                            Enforces strict behavior so the AI never 
                            hallucinates unapproved software.

RUN:
    export OPENAI_API_KEY=your_key_here
    python app.py
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables (ensure you have your .env file setup)
load_dotenv()
client = OpenAI()

# ============================================================
# PATTERN 3 — ROLE
# Single source of truth for the AI's behavior across all steps.
# ============================================================

TICKET_AGENT_ROLE = """
## IDENTITY
You are IT-Bot, an enterprise Level 1 Support orchestrator. You are fast,
analytical, and strictly follow security protocols. You route tickets,
extract entities, and determine if an action can be automated.

## CONSTRAINTS
You MUST:
- Only classify intents as: software_provisioning, password_reset, human_routing, unknown
- Set user_sentiment accurately (escalate angry users to humans)
- Output a confidence score between 0.0 and 1.0

You MUST NOT:
- Guess or assume missing information (leave software_requested as null if missing)
- Offer troubleshooting advice not requested
- Approve software that isn't standard enterprise tooling
"""

# ============================================================
# PATTERN 1 — SCHEMA
# The extraction tool guarantees we get exact fields for our APIs.
# ============================================================

EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_extracted_ticket",
        "description": "Submit structured data extracted from the IT ticket. You MUST call this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "intent":             {"type": "string", "enum": ["software_provisioning", "password_reset", "human_routing", "unknown"]},
                "software_requested": {"type": ["string", "null"], "description": "The specific software name, or null if missing."},
                "urgency":            {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "user_sentiment":     {"type": "string", "enum": ["neutral", "frustrated", "urgent", "appreciative"]},
                "confidence_score":   {"type": "number", "description": "Float between 0.0 and 1.0 representing certainty."},
                "missing_info":       {"type": "array", "items": {"type": "string"}, "description": "Questions to ask the user if required data is missing."},
                "summary":            {"type": "string", "description": "A 1-sentence summary of the request."}
            },
            "required": ["intent", "urgency", "user_sentiment", "confidence_score", "missing_info", "summary"],
        },
    },
}

# ============================================================
# PATTERN 2 — DELEGATION
# Three focused steps handling extraction, logic, and response.
# ============================================================

def step1_extract(raw_ticket: str) -> dict:
    """
    STEP 1 — Extract
    Job: Read natural language and output guaranteed JSON fields.
    """
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), # Using mini for fast extraction
        max_tokens=500,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "function", "function": {"name": "submit_extracted_ticket"}},
        messages=[
            {"role": "system", "content": TICKET_AGENT_ROLE},
            {"role": "user", "content": f"Extract structured data from this IT ticket:\n\n{raw_ticket}"},
        ],
    )
    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "submit_extracted_ticket":
                return json.loads(tool_call.function.arguments)
    raise RuntimeError("Extraction tool was not called")

def step2_evaluate_and_route(extracted: dict) -> dict:
    """
    STEP 2 — Evaluate & Route (The Orchestrator Logic)
    Job: Look at the clean data and decide the system action.
    This replaces LLM guessing with hardcoded business logic.
    """
    routing_decision = {
        "action": "unknown",
        "system_logs": []
    }

    # Rule A: Safety & Escalation
    if extracted.get("user_sentiment") == "frustrated" or extracted.get("confidence_score", 0) < 0.85:
        routing_decision["action"] = "escalate_to_human"
        routing_decision["system_logs"].append("AI halted: User frustrated or low confidence.")
    
    # Rule B: Missing Information
    elif len(extracted.get("missing_info", [])) > 0:
        routing_decision["action"] = "ask_user_for_clarification"
        routing_decision["system_logs"].append("AI halted: Missing required entities.")
        
    # Rule C: Automate Provisioning
    elif extracted.get("intent") == "software_provisioning" and extracted.get("software_requested"):
        routing_decision["action"] = "automate_provisioning"
        routing_decision["system_logs"].append(f"MOCK OKTA API: Provisioned {extracted['software_requested']}")
        routing_decision["system_logs"].append("MOCK SLACK API: Notified manager.")
        
    else:
        routing_decision["action"] = "route_to_tier_1"

    return routing_decision

def step3_draft_resolution(extracted: dict, routing: dict) -> str:
    """
    STEP 3 — Write
    Job: Format the final output for the ticketing system or the user.
    """
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_tokens=400,
        messages=[
            {"role": "system", "content": TICKET_AGENT_ROLE},
            {
                "role": "user",
                "content": (
                    f"Draft the final ticket update based on these details.\n\n"
                    f"Extracted Data: {extracted}\n"
                    f"System Action Taken: {routing['action']}\n\n"
                    f"Format the output strictly like this:\n"
                    f"**STATUS:** [Resolved / Escalated / Waiting on User]\n"
                    f"**SUMMARY:** ...\n"
                    f"**INTERNAL LOGS:** (List the system actions taken)\n"
                    f"**MESSAGE TO USER:** (Draft a polite 1-2 sentence message to the user based on the action taken. If asking for clarification, include the missing_info question.)"
                ),
            },
        ],
    )
    return response.choices[0].message.content


# ============================================================
# ORCHESTRATOR — Chains the three steps
# ============================================================

def process_ticket(raw_ticket: str) -> str:
    print("  [1/3] Extracting structured fields ...")
    extracted = step1_extract(raw_ticket)

    print("  [2/3] Evaluating business logic & routing ...")
    routing = step2_evaluate_and_route(extracted)

    print("  [3/3] Drafting final system update ...")
    final_output = step3_draft_resolution(extracted, routing)

    return final_output


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":
    # Mocking a ticket from a specific user profile
    mock_ticket = """
    Ticket ID: IT-9942
    From: dejan@pirka.mk
    Title: Power BI Desktop Access
    
    Hey team, I'm doing some data analysis for the new label compilation this week. 
    Can you please provision a Power BI Desktop license for my workstation? 
    Thanks!
    """

    print("=" * 60)
    print("AI TICKET ASSISTANT — Agentic Pipeline Demo")
    print("=" * 60)
    print("\nIncoming Ticket:")
    print(mock_ticket)
    print("-" * 60)
    print("\nRunning pipeline:\n")

    result = process_ticket(mock_ticket)

    print("\n" + "=" * 60)
    print("SYSTEM OUTPUT:")
    print("=" * 60)
    print(result)
    print()