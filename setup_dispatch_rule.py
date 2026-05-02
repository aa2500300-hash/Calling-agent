# save as setup_dispatch_rule.py
import asyncio
import os
from dotenv import load_dotenv
from livekit import api

load_dotenv(".env")

async def create_dispatch_rule():
    lk = api.LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    
    rule = await lk.sip.create_sip_dispatch_rule(
        api.CreateSIPDispatchRuleRequest(
            rule=api.SIPDispatchRule(
                dispatch_rule_direct=api.SIPDispatchRuleDirect(
                    room_prefix="inbound-call-",
                    pin=""
                )
            ),
            trunk_ids=[os.getenv("INBOUND_TRUNK_ID")],  # from step 1
            name="Inbound Call Dispatch",
            # This is the agent that will handle the call
        )
    )
    print(f"Dispatch Rule ID: {rule.sip_dispatch_rule_id}")
    await lk.aclose()

asyncio.run(create_dispatch_rule())
