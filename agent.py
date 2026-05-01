import os
import ssl
import certifi

# Fix SSL certificate errors — MUST be first
os.environ['SSL_CERT_FILE'] = certifi.where()
_orig_ssl = ssl.create_default_context
def _certifi_ssl(purpose=ssl.Purpose.SERVER_AUTH, **kwargs):
    if not kwargs.get("cafile") and not kwargs.get("capath") and not kwargs.get("cadata"):
        kwargs["cafile"] = certifi.where()
    return _orig_ssl(purpose, **kwargs)
ssl.create_default_context = _certifi_ssl

import asyncio
import logging
from dotenv import load_dotenv
from livekit import agents, api, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation, silero
from livekit.agents import llm
from typing import Optional

load_dotenv(".env")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inbound-agent")

import config

# ── Load Gemini Live plugin ───────────────────────────────────────────────────
_gemini_realtime = None
try:
    from livekit.plugins import google as _gp
    try:
        _gemini_realtime = _gp.realtime.RealtimeModel
        logger.info("Loaded google.realtime.RealtimeModel")
    except AttributeError:
        try:
            _gemini_realtime = _gp.beta.realtime.RealtimeModel
            logger.info("Loaded google.beta.realtime.RealtimeModel")
        except AttributeError:
            pass
except ImportError:
    logger.error("livekit-plugins-google not installed. Run: pip install livekit-plugins-google")


def _build_gemini_session(system_prompt: str) -> AgentSession:
    if _gemini_realtime is None:
        raise RuntimeError(
            "Gemini Live plugin not available. "
            "Run: pip install 'livekit-plugins-google>=1.0'"
        )

    model = os.getenv("GEMINI_MODEL", config.GEMINI_MODEL)
    voice = os.getenv("GEMINI_VOICE", config.GEMINI_VOICE)

    realtime_input_cfg = None
    session_resumption_cfg = None
    ctx_compression_cfg = None
    try:
        from google.genai import types as _gt
        realtime_input_cfg = _gt.RealtimeInputConfig(
            automatic_activity_detection=_gt.AutomaticActivityDetection(
                end_of_speech_sensitivity=_gt.EndSensitivity.END_SENSITIVITY_LOW,
                silence_duration_ms=2000,
                prefix_padding_ms=200,
            ),
        )
        session_resumption_cfg = _gt.SessionResumptionConfig(transparent=True)
        ctx_compression_cfg = _gt.ContextWindowCompressionConfig(
            trigger_tokens=25600,
            sliding_window=_gt.SlidingWindow(target_tokens=12800),
        )
        logger.info("Silence-prevention configs applied")
    except Exception as e:
        logger.warning(f"Could not build silence-prevention config: {e}")

    kwargs = dict(model=model, voice=voice, instructions=system_prompt)
    if realtime_input_cfg:
        kwargs["realtime_input_config"] = realtime_input_cfg
        kwargs["session_resumption"] = session_resumption_cfg
        kwargs["context_window_compression"] = ctx_compression_cfg

    logger.info(f"Building Gemini Live session — model={model}, voice={voice}")
    return AgentSession(llm=_gemini_realtime(**kwargs), vad=silero.VAD.load())


class InboundCallTools(llm.ToolContext):
    def __init__(self, ctx: agents.JobContext):
        super().__init__(tools=[])
        self.ctx = ctx

    @llm.function_tool(description="Transfer the call to a human agent.")
    async def transfer_call(self, destination: Optional[str] = None) -> str:
        destination = destination or config.DEFAULT_TRANSFER_NUMBER
        if not destination:
            return "Transfer unavailable — no transfer number configured."
        if "@" not in destination:
            clean = destination.replace("tel:", "").replace("sip:", "")
            if config.SIP_DOMAIN:
                destination = f"sip:{clean}@{config.SIP_DOMAIN}"
            else:
                destination = f"tel:{clean}"
        participant_identity = None
        for p in self.ctx.room.remote_participants.values():
            participant_identity = p.identity
            break
        if not participant_identity:
            return "Transfer failed — could not identify caller."
        try:
            await self.ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=self.ctx.room.name,
                    participant_identity=participant_identity,
                    transfer_to=destination,
                    play_dialtone=False,
                )
            )
            return "Transferring you now. Please hold."
        except Exception as e:
            return f"Transfer failed: {e}"


class InboundAssistant(Agent):
    def __init__(self, tools: list) -> None:
        super().__init__(instructions=config.SYSTEM_PROMPT, tools=tools)


async def entrypoint(ctx: agents.JobContext):
    logger.info(f"Inbound agent started — room: {ctx.room.name}")
    await ctx.connect()
    logger.info("Agent connected to LiveKit room")

    tool_ctx = InboundCallTools(ctx)
    try:
        session = _build_gemini_session(config.SYSTEM_PROMPT)
    except RuntimeError as e:
        logger.error(str(e))
        return

    await session.start(
        room=ctx.room,
        agent=InboundAssistant(tools=list(tool_ctx.function_tools.values())),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )
    logger.info("Gemini Live session started — waiting for caller...")

    caller_joined = asyncio.Event()
    caller_identity: Optional[str] = None

    def on_participant_connected(participant: rtc.RemoteParticipant):
        nonlocal caller_identity
        logger.info(f"Caller joined: {participant.identity}")
        if caller_identity is None:
            caller_identity = participant.identity
            caller_joined.set()

    ctx.room.on("participant_connected", on_participant_connected)

    for p in ctx.room.remote_participants.values():
        if caller_identity is None:
            caller_identity = p.identity
            caller_joined.set()
            logger.info(f"Caller already in room: {p.identity}")
            break

    try:
        await asyncio.wait_for(caller_joined.wait(), timeout=30.0)
        logger.info(f"Caller confirmed: {caller_identity}")
    except asyncio.TimeoutError:
        logger.warning("No caller joined within 30s — shutting down")
        await session.aclose()
        return

    # Gemini 3.1 speaks autonomously — do NOT call generate_reply()
    logger.info("Gemini will greet autonomously from system prompt")

    disconnect_event = asyncio.Event()

    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        if participant.identity == caller_identity:
            logger.info(f"Caller disconnected: {participant.identity}")
            disconnect_event.set()

    def on_room_disconnected():
        disconnect_event.set()

    ctx.room.on("participant_disconnected", on_participant_disconnected)
    ctx.room.on("disconnected", on_room_disconnected)

    try:
        await asyncio.wait_for(disconnect_event.wait(), timeout=3600)
    except asyncio.TimeoutError:
        logger.warning("1-hour safety timeout reached")

    logger.info("Call ended — closing session")
    await session.aclose()


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="inbound-caller",
        )
    )
