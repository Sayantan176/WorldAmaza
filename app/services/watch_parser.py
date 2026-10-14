import logging
import re
from app.schemas.watch import StructuredWatchRules
from app.services.groq_service import groq_service

logger = logging.getLogger("worldamaze.parser")

SYSTEM_WATCH_PARSER_PROMPT = """You are the Senior Intelligence Architect for WorldAmaze, a personal global intelligence monitoring platform.
Your mission is to transform a user's natural language monitoring request into a precise, structured monitoring specification.

Core principles:
1. Distinguish between confirmed developments and speculation/commentary.
2. Identify primary subjects (countries, organizations, programs, technologies, people).
3. Generate high-precision search keywords (include_terms) that query news engines without broad ambiguity.
4. Identify explicit exclusion terms (exclude_terms) to filter noise, rumors, opinion pieces, or irrelevant topics.
5. Identify specific trigger conditions (what exact development must occur to generate an alert).
6. Assign appropriate event categories (contract, announcement, policy, confirmation, cancellation, launch, first_flight, vulnerability, other).
7. Set evidence requirement based on user intent:
   - "official_confirmation" if user requested official confirmation or unverified reports excluded.
   - "multiple_sources" if user wants high certainty.
   - "any_report" for general or early discovery.
8. Set uncertainty_policy: "suppress" (ignore unverified rumors), "flag_unverified" (surface with warning), or "allow".
9. Set delivery_mode: "immediate" (for breaking alerts), "daily_digest" (for summaries), or "both".
10. Generate a crisp, professional title for the watch (e.g., "India Defence Aviation Programs", "Semiconductor Export Controls", "Critical Zero-Day Exploits").
"""


def parse_watch_prompt(prompt: str) -> StructuredWatchRules:
    """
    Parses a user's natural language request into a validated StructuredWatchRules object.
    Falls back to intelligent heuristic rule construction if Groq API is unavailable.
    """
    user_prompt = f"User monitoring request:\n\"{prompt.strip()}\"\n\nCreate the structured monitoring rules."

    try:
        rules = groq_service.generate_structured(
            system_prompt=SYSTEM_WATCH_PARSER_PROMPT,
            user_prompt=user_prompt,
            response_model=StructuredWatchRules,
            temperature=0.1,
            max_retries=2,
        )
        # Ensure description is original prompt
        rules.description = prompt.strip()
        return rules
    except Exception as e:
        logger.error(f"Groq parsing failed, invoking rule extraction fallback: {e}")
        return build_fallback_rules(prompt)


def build_fallback_rules(prompt: str) -> StructuredWatchRules:
    """
    Constructs a sensible default rule structure directly from prompt keywords
    if LLM API is unavailable.
    """
    clean_p = prompt.strip()
    words = re.findall(r"\b[A-Za-z0-9_-]+\b", clean_p)
    stopwords = {"and", "the", "for", "with", "from", "about", "notify", "track", "monitor", "alert", "put", "send", "only", "when", "into", "that", "this"}
    keywords = [w for w in words if len(w) > 3 and w.lower() not in stopwords]
    
    # Simple title generation
    title = " ".join(keywords[:4]).title() if keywords else "Custom Intelligence Watch"
    
    # Evidence check
    evidence_req = "any_report"
    if any(k in clean_p.lower() for k in ["official", "confirmed", "verified", "no rumors"]):
        evidence_req = "official_confirmation"

    uncertainty = "flag_unverified"
    if any(k in clean_p.lower() for k in ["do not alert me about rumors", "no speculation", "ignore rumors"]):
        uncertainty = "suppress"

    delivery = "immediate"
    if "daily digest" in clean_p.lower() or "daily summary" in clean_p.lower():
        delivery = "both" if "immediate" in clean_p.lower() else "daily_digest"

    return StructuredWatchRules(
        title=title,
        description=clean_p,
        subjects=keywords[:3] if keywords else ["Global Affairs"],
        include_terms=keywords[:5] if keywords else [clean_p[:30]],
        exclude_terms=["rumor", "speculation", "opinion", "unverified"] if uncertainty == "suppress" else [],
        trigger_conditions=["Official announcement or confirmed report matching subject matter"],
        event_categories=["announcement", "confirmation", "policy"],
        importance_threshold="medium",
        evidence_requirement=evidence_req,
        uncertainty_policy=uncertainty,
        immediate_alert_conditions=["High impact confirmed milestone"],
        digest_only_conditions=["Minor updates or routine developments"],
        delivery_mode=delivery,
        digest_time="08:00",
        timezone="UTC",
        polling_interval=30,
        status="active"
    )
