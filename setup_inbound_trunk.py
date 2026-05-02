import asyncio
import os
from dotenv import load_dotenv
from livekit import api

load_dotenv(".env")

async def create_inbound_trunk():
    lk = api.LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    
    # Create inbound SIP trunk — this gives you a LiveKit SIP URI
    # Vobiz will forward calls to this URI
    trunk = await lk.sip.create_sip_inbound_trunk(
        api.CreateSIPInboundTrunkRequest(
            trunk=api.SIPInboundTrunkInfo(
                name="Vobiz Inbound",
                # Leave numbers empty for now — any call from Vobiz will match
                allowed_addresses=["0.0.0.0/0"],  # Accept from any IP initially
            )
        )
    )
    print(f"Inbound Trunk ID: {trunk.sip_trunk_id}")
    print(f"LiveKit SIP URI: {trunk.sip_trunk_id}.sip.livekit.cloud")
    
    await lk.aclose()

asyncio.run(create_inbound_trunk())
