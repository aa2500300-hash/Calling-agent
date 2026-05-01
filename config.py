import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# AGENT CONFIGURATION
# Edit this file to change your agent's personality, voice, and behaviour.
# All secrets go in .env — never hardcode API keys here.
# =============================================================================


# ── 1. AGENT PERSONA ─────────────────────────────────────────────────────────
# This is the full personality and instruction set for your AI agent.
# Customise the business name, services, and behaviour here.

SYSTEM_PROMPT = """
You are Priya, a warm and professional virtual receptionist answering WhatsApp calls
on behalf of {business_name}.

**Your goal:** Help callers with their questions, book appointments if needed,
and transfer to a human only when the caller explicitly asks.

**Call behaviour:**
- You answer inbound calls — the caller is reaching out to YOU.
- Greet them warmly and ask how you can help.
- Keep responses short — 1 to 2 sentences maximum per turn.
- You speak fluent English and Hindi. Match the caller's language automatically.
- Never say you are an AI unless directly and persistently asked.
- If the caller says "bye" or "thank you, that's all" — wish them well and end naturally.

**If asked to transfer:** Use the transfer_call tool immediately.
**If you cannot help:** Apologise briefly and offer to transfer to a human.

Business details:
- Name: {business_name}
- Services: {services}
- Hours: {business_hours}
- Location: {location}
"""

# Fill in your actual business details here:
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "our company")
SERVICES = os.getenv("BUSINESS_SERVICES", "our services")
BUSINESS_HOURS = os.getenv("BUSINESS_HOURS", "Monday to Saturday, 9am to 6pm")
LOCATION = os.getenv("BUSINESS_LOCATION", "please call us for our address")

# Build the final prompt with business details injected
SYSTEM_PROMPT = SYSTEM_PROMPT.format(
    business_name=BUSINESS_NAME,
    services=SERVICES,
    business_hours=BUSINESS_HOURS,
    location=LOCATION,
)

# ── Greeting instructions ─────────────────────────────────────────────────────
# What the agent says the moment the caller joins.
# For inbound: caller is unknown, so greet generically and ask how to help.

INBOUND_GREETING = (
    "The caller has just connected via WhatsApp. "
    "Greet them warmly, introduce yourself as Priya, mention the business name, "
    "and ask how you can help them today. Be natural and friendly."
)

# Legacy — kept for compatibility if make_call.py is used for outbound testing
INITIAL_GREETING = "The user has picked up. Introduce yourself and ask how you can help."
fallback_greeting = "Greet the caller warmly and ask how you can help."


# ── 2. SPEECH-TO-TEXT (STT) ──────────────────────────────────────────────────
# Deepgram nova-2 is the best free-tier STT for Indian English + Hindi.
# nova-3 is newer but nova-2 handles code-switching better.

STT_PROVIDER = "deepgram"
STT_MODEL = os.getenv("STT_MODEL", "nova-2")
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en")   # "en" handles Hindi switching in nova-2


# ── 3. TEXT-TO-SPEECH (TTS) ──────────────────────────────────────────────────
# Best free options in order:
#   "deepgram"  — free tier, good quality, aura-asteria-en voice
#   "sarvam"    — Indian voices (anushka/aravind), free tier, needs SARVAM_API_KEY
#   "openai"    — best quality, costs money (tts-1 model)
#   "cartesia"  — ultra-low latency, costs money

DEFAULT_TTS_PROVIDER = os.getenv("TTS_PROVIDER", "deepgram")
DEFAULT_TTS_VOICE = os.getenv("TTS_VOICE", "aura-asteria-en")

# Sarvam (Indian accent voices — highly recommended for Indian market)
SARVAM_MODEL = "bulbul:v2"
SARVAM_LANGUAGE = os.getenv("SARVAM_LANGUAGE", "en-IN")

# Cartesia (ultra-fast, paid)
CARTESIA_MODEL = "sonic-2"
CARTESIA_VOICE = os.getenv("CARTESIA_VOICE", "f786b574-daa5-4673-aa0c-cbe3e8534c02")


# ── 4. LARGE LANGUAGE MODEL (LLM) ────────────────────────────────────────────
# Best free options:
#   "groq"    — completely free, llama-3.3-70b, very fast. RECOMMENDED for testing.
#   "openai"  — gpt-4o-mini is cheap but not free

DEFAULT_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
DEFAULT_LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Groq settings (free tier — use this for zero-cost testing)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.7"))


# ── 5. TELEPHONY ─────────────────────────────────────────────────────────────
# Vobiz SIP credentials — loaded from .env

SIP_TRUNK_ID = os.getenv("VOBIZ_SIP_TRUNK_ID", "")
SIP_DOMAIN = os.getenv("VOBIZ_SIP_DOMAIN", "")
DEFAULT_TRANSFER_NUMBER = os.getenv("DEFAULT_TRANSFER_NUMBER", "")
