import os
from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# AGENT CONFIGURATION — Edit this to customise your agent
# All secrets go in .env — never hardcode API keys here
# =============================================================================

# ── 1. GEMINI LIVE MODEL ──────────────────────────────────────────────────────
# gemini-3.1-flash-live-preview = STT + LLM + TTS in one model, free tier
# Do NOT use any -lite variant — lite models don't support Gemini Live

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-live-preview")

# Voice options (female): Aoede, Achernar, Autonoe, Callirrhoe, Despina,
#   Erinome, Gacrux, Kore, Laomedeia, Leda, Pulcherrima, Sulafat, Zephyr
# Voice options (male): Achird, Algenib, Charon, Enceladus, Fenrir,
#   Iapetus, Orus, Perseus, Puck, Sadachbia, Schedar, Umbriel
GEMINI_VOICE = os.getenv("GEMINI_VOICE", "Aoede")

# ── 2. AGENT PERSONA ──────────────────────────────────────────────────────────
# Customise these in .env or directly here

BUSINESS_NAME  = os.getenv("BUSINESS_NAME",   "our company")
SERVICES       = os.getenv("BUSINESS_SERVICES","our services")
BUSINESS_HOURS = os.getenv("BUSINESS_HOURS",  "Monday to Saturday, 9am to 6pm")
LOCATION       = os.getenv("BUSINESS_LOCATION","please call us for our address")

SYSTEM_PROMPT = f"""
You are Priya, a warm and professional AI receptionist answering WhatsApp voice calls
on behalf of {BUSINESS_NAME}.

CRITICAL — SPEAK FIRST:
The moment the call connects, speak immediately. Do NOT wait for the caller.
Open with: "Hello! Thank you for calling {BUSINESS_NAME}. This is Priya. How can I help you today?"

CALL BEHAVIOUR:
- Keep every response to 1-2 short sentences maximum.
- Speak fluent English and Hindi. Switch to Hindi immediately if the caller speaks Hindi.
- Never say you are an AI unless directly and persistently asked.
- Match the caller's energy — warm, natural, not robotic.
- If the caller says bye or thank you — wish them well and end naturally.

BUSINESS DETAILS:
- Services: {SERVICES}
- Hours: {BUSINESS_HOURS}
- Location: {LOCATION}

TOOLS:
- Use transfer_call only if the caller explicitly asks to speak to a human.
- Never transfer without the caller asking for it.

STYLE:
- Never start with "Certainly!", "Of course!", or "Absolutely!"
- Never say "As an AI" unless pushed repeatedly.
- Sound like a real person: casual, warm, confident.
- Respond in under 10 words where possible.
"""

# ── 3. TELEPHONY ──────────────────────────────────────────────────────────────
SIP_TRUNK_ID        = os.getenv("VOBIZ_SIP_TRUNK_ID", "")
SIP_DOMAIN          = os.getenv("VOBIZ_SIP_DOMAIN", "")
DEFAULT_TRANSFER_NUMBER = os.getenv("DEFAULT_TRANSFER_NUMBER", "")

# ── Legacy fields (kept for compatibility with setup_inbound.py) ──────────────
STT_MODEL    = "nova-2"   # Not used with Gemini Live — Gemini handles STT internally
STT_LANGUAGE = "en"
DEFAULT_TTS_PROVIDER = "gemini"
DEFAULT_TTS_VOICE    = GEMINI_VOICE
SARVAM_MODEL   = "bulbul:v2"
SARVAM_LANGUAGE = "en-IN"
CARTESIA_MODEL = "sonic-2"
CARTESIA_VOICE = ""
DEFAULT_LLM_PROVIDER = "gemini"
DEFAULT_LLM_MODEL    = GEMINI_MODEL
GROQ_MODEL       = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.7
