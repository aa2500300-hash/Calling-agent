import os
import certifi

# Fix SSL certificate errors (macOS + some Linux) — MUST be before other imports
os.environ['SSL_CERT_FILE'] = certifi.where()

import asyncio
import logging
import json
from dotenv import load_dotenv
from livekit import agents, api, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.agents import llm
from typing import Optional

load_dotenv(".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inbound-agent")

import config


# ── TTS builder ──────────────────────────────────────────────────────────────

def _build_tts(voice_id: str = None):
    """
    Build TTS from config. Supports: openai, deepgram, sarvam, cartesia.
    Sarvam is the best free option for Indian-accented voices.
    """
    provider = os.getenv("TTS_PROVIDER", config.DEFAULT_TTS_PROVIDER).lower()

    # Auto-detect Sarvam voices
    if voice_id in ["anushka", "aravind", "amartya", "dhruv"]:
        provider = "sarvam"

    if provider == "sarvam":
        try:
            from livekit.plugins import sarvam
            voice = voice_id or os.getenv("SARVAM_VOICE", "anushka")
            logger.info(f"TTS: Sarvam ({voice})")
            return sarvam.TTS(
                model=config.SARVAM_MODEL,
                speaker=voice,
                target_language_code=os.getenv("SARVAM_LANGUAGE", config.SARVAM_LANGUAGE),
            )
        except ImportError:
            logger.warning("livekit-plugins-sarvam not installed, falling back to deepgram")
            provider = "deepgram"

    if provider == "deepgram":
        model = os.getenv("DEEPGRAM_TTS_MODEL", "aura-asteria-en")
        logger.info(f"TTS: Deepgram ({model})")
        return deepgram.TTS(model=model)

    if provider == "cartesia":
        try:
            from livekit.plugins import cartesia
            logger.info("TTS: Cartesia")
            return cartesia.TTS(model=config.CARTESIA_MODEL, voice=config.CARTESIA_VOICE)
        except ImportError:
            logger.warning("livekit-plugins-cartesia not installed, falling back to openai")

    # Default: OpenAI TTS
    voice = voice_id or os.getenv("OPENAI_TTS_VOICE", config.DEFAULT_TTS_VOICE)
    logger.info(f"TTS: OpenAI ({voice})")
    return openai.TTS(model=os.getenv("OPENAI_TTS_MODEL", "tts-1"), voice=voice)


# ── LLM builder ──────────────────────────────────────────────────────────────

def _build_llm(provider_override: str = None):
    """
    Build LLM from config. Supports: openai, groq.
    Groq is free and very fast — recommended for testing.
    """
    provider = (provider_override or os.getenv("LLM_PROVIDER", config.DEFAULT_LLM_PROVIDER)).lower()

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not set — falling back to OpenAI")
        else:
            logger.info(f"LLM: Groq ({config.GROQ_MODEL})")
            return openai.LLM(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key,
                model=os.getenv("GROQ_MODEL", config.GROQ_MODEL),
                temperature=float(os.getenv("GROQ_TEMPERATURE", str(config.GROQ_TEMPERATURE))),
            )

    logger.info(f"LLM: OpenAI ({config.DEFAULT_LLM_MODEL})")
    return openai.LLM(model=os.getenv("OPENAI_MODEL", config.DEFAULT_LLM_MODEL))


# ── Tool context ──────────────────────────────────────────────────────────────

class InboundCallTools(llm.ToolContext):
    """
    Tools available to the inbound agent.
    For WhatsApp inbound testing, transfer_call is the main useful tool.
    """

    def __init__(self, ctx: agents.JobContext):
        super().__init__(tools=[])
        self.ctx = ctx

    @llm.function_tool(description="Transfer the call to a human agent or specific number.")
    async def transfer_call(self, destination: Optional[str] = None) -> str:
        """
        Transfer the active call via SIP REFER.
        destination: a phone number or SIP URI. If empty, uses DEFAULT_TRANSFER_NUMBER.
        """
        destination = destination or config.DEFAULT_TRANSFER_NUMBER
        if not destination:
            return "Transfer unavailable — no transfer number configured."

        # Build a proper SIP URI if needed
        if "@" not in destination:
            clean = destination.replace("tel:", "").replace("sip:", "")
            if config.SIP_DOMAIN:
                destination = f"sip:{clean}@{config.SIP_DOMAIN}"
            else:
                destination = f"tel:{clean}"

        # Find the remote SIP participant
        participant_identity = None
        for p in self.ctx.room.remote_participants.values():
            participant_identity = p.identity
            break

        if not participant_identity:
            return "Transfer failed — could not identify caller in room."

        try:
            await self.ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=self.ctx.room.name,
                    participant_identity=participant_identity,
                    transfer_to=destination,
                    play_dialtone=False,
                )
            )
            logger.info(f"Transferred to {destination}")
            return "Transferring you now. Please hold."
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            return f"Transfer failed: {e}"


# ── Agent class ───────────────────────────────────────────────────────────────

class InboundAssistant(Agent):
    def __init__(self, tools: list) -> None:
        super().__init__(
            instructions=config.SYSTEM_PROMPT,
            tools=tools,
        )


# ── Entrypoint ────────────────────────────────────────────────────────────────

async def entrypoint(ctx: agents.JobContext):
    """
    Inbound-only entrypoint.

    Flow:
    1. Connect to the LiveKit room (agent joins)
    2. Build and start the AgentSession
    3. Wait for the inbound SIP participant to appear (WhatsApp caller)
    4. Greet them immediately once they're in the room
    5. Keep session alive until the caller disconnects

    KEY DECISIONS:
    - close_on_disconnect=False: WhatsApp SIP has brief audio dropouts that look
      like disconnects. We watch participant_disconnected manually instead.
    - No create_sip_participant: we never dial out. The caller comes to us.
    - generate_reply() used for the greeting since we control when to speak.
    """
    logger.info(f"Inbound agent started — room: {ctx.room.name}")

    # Connect the agent to the room first
    await ctx.connect()
    logger.info("Agent connected to LiveKit room")

    # Build tool context
    tool_ctx = InboundCallTools(ctx)

    # Build agent session with STT + LLM + TTS pipeline
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            model=config.STT_MODEL,
            language=config.STT_LANGUAGE,
        ),
        llm=_build_llm(),
        tts=_build_tts(),
    )

    # Start the session
    # IMPORTANT: close_on_disconnect=False prevents the agent from dying
    # when WhatsApp's SIP has brief audio gaps (very common with WA calling)
    await session.start(
        room=ctx.room,
        agent=InboundAssistant(tools=list(tool_ctx.function_tools.values())),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(),
            # DO NOT set close_on_disconnect=True — kills on any WA audio dropout
        ),
    )

    logger.info("Agent session started — waiting for caller to join...")

    # ── Wait for the SIP participant (the WhatsApp caller) ──────────────────
    # When a WhatsApp user calls your number, Vobiz routes it as a SIP INVITE
    # into this LiveKit room. We wait up to 30 seconds for them to appear.

    caller_joined = asyncio.Event()
    caller_identity: Optional[str] = None

    def on_participant_connected(participant: rtc.RemoteParticipant):
        nonlocal caller_identity
        logger.info(f"Participant joined: {participant.identity} | kind: {participant.kind}")
        # Accept any remote participant — on inbound they are the caller
        if caller_identity is None:
            caller_identity = participant.identity
            caller_joined.set()

    ctx.room.on("participant_connected", on_participant_connected)

    # Check if someone is already in the room (race condition guard)
    for p in ctx.room.remote_participants.values():
        if caller_identity is None:
            caller_identity = p.identity
            caller_joined.set()
            logger.info(f"Caller already in room: {p.identity}")
            break

    try:
        await asyncio.wait_for(caller_joined.wait(), timeout=30.0)
        logger.info(f"Caller confirmed in room: {caller_identity}")
    except asyncio.TimeoutError:
        logger.warning("No caller joined within 30s — shutting down")
        await session.aclose()
        return

    # Small buffer for audio to stabilise after SIP connect
    await asyncio.sleep(0.8)

    # ── Greet the caller ────────────────────────────────────────────────────
    logger.info("Greeting the caller...")
    try:
        await session.generate_reply(instructions=config.INBOUND_GREETING)
    except Exception as e:
        logger.warning(f"generate_reply failed: {e}")

    # ── Keep alive until caller disconnects ─────────────────────────────────
    # We watch specifically for the caller's disconnect, not any disconnect.
    # This means brief SIP audio dropouts won't kill the session.

    disconnect_event = asyncio.Event()

    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        if participant.identity == caller_identity:
            logger.info(f"Caller disconnected: {participant.identity}")
            disconnect_event.set()

    def on_room_disconnected():
        logger.info("Room disconnected")
        disconnect_event.set()

    ctx.room.on("participant_disconnected", on_participant_disconnected)
    ctx.room.on("disconnected", on_room_disconnected)

    try:
        # 1-hour safety timeout — no call should last longer than this
        await asyncio.wait_for(disconnect_event.wait(), timeout=3600)
    except asyncio.TimeoutError:
        logger.warning("1-hour safety timeout reached")

    logger.info("Call ended — closing session")
    await session.aclose()


# ── Worker entry ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="inbound-caller",  # Must match LiveKit dispatch agent_name
        )
    )
