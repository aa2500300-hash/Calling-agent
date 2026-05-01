"""
setup_inbound.py — Run this ONCE to configure LiveKit to receive
inbound SIP calls from Vobiz (which receives WhatsApp calls).

What this does:
1. Creates a LiveKit SIP Inbound Trunk (tells LiveKit to accept calls from Vobiz)
2. Creates a LiveKit SIP Dispatch Rule (tells LiveKit which agent to run per call)

Run: python setup_inbound.py

After running, copy the printed IDs into your .env file.
"""

import asyncio
import os
from dotenv import load_dotenv
from livekit import api

load_dotenv(".env")


async def setup():
    url = os.getenv("LIVEKIT_URL")
    key = os.getenv("LIVEKIT_API_KEY")
    secret = os.getenv("LIVEKIT_API_SECRET")
    vobiz_domain = os.getenv("VOBIZ_SIP_DOMAIN", "")
    phone_number = os.getenv("VOBIZ_OUTBOUND_NUMBER", "")

    if not all([url, key, secret]):
        print("❌ Missing LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET in .env")
        return

    lk = api.LiveKitAPI(url=url, api_key=key, api_secret=secret)

    print("=" * 60)
    print("Setting up LiveKit Inbound SIP for WhatsApp via Vobiz")
    print("=" * 60)

    # ── Step 1: Create Inbound SIP Trunk ────────────────────────────────────
    # This tells LiveKit: "Accept SIP calls coming from Vobiz"
    print("\n[1/2] Creating LiveKit Inbound SIP Trunk...")
    try:
        trunk = await lk.sip.create_sip_inbound_trunk(
            api.CreateSIPInboundTrunkRequest(
                trunk=api.SIPInboundTrunkInfo(
                    name="Vobiz WhatsApp Inbound",
                    # Numbers that are allowed to call in.
                    # Leave empty to accept from all numbers (easier for testing).
                    allowed_numbers=[phone_number] if phone_number else [],
                    # No auth needed for inbound from Vobiz
                    # (Vobiz authenticates on their end)
                )
            )
        )
        trunk_id = trunk.sip_trunk_id
        print(f"   ✅ Inbound trunk created: {trunk_id}")
        print(f"   Add to .env: LIVEKIT_INBOUND_TRUNK_ID={trunk_id}")
    except Exception as e:
        print(f"   ❌ Failed to create inbound trunk: {e}")
        trunk_id = None

    # ── Step 2: Create Dispatch Rule ─────────────────────────────────────────
    # This tells LiveKit: "When an inbound SIP call arrives, dispatch the
    # 'inbound-caller' agent to handle it"
    print("\n[2/2] Creating SIP Dispatch Rule...")
    try:
        rule = await lk.sip.create_sip_dispatch_rule(
            api.CreateSIPDispatchRuleRequest(
                rule=api.SIPDispatchRule(
                    dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                        agent_name="inbound-caller",  # Must match agent.py WorkerOptions agent_name
                        room_prefix="whatsapp-inbound-",
                    )
                ),
                trunk_ids=[trunk_id] if trunk_id else [],
                name="WhatsApp Inbound Dispatch",
            )
        )
        rule_id = rule.sip_dispatch_rule_id
        print(f"   ✅ Dispatch rule created: {rule_id}")
        print(f"   Add to .env: LIVEKIT_DISPATCH_RULE_ID={rule_id}")
    except Exception as e:
        print(f"   ❌ Failed to create dispatch rule: {e}")

    await lk.aclose()

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print()
    print("1. In Vobiz dashboard → SIP → Trunks → your trunk")
    print("   Set the outbound SIP URI to route to LiveKit:")
    print("   sip:<your-livekit-project>.sip.livekit.cloud")
    print()
    print("2. In your WhatsApp Business account (Meta for Developers):")
    print("   → Phone Numbers → Call Settings → SIP Configuration")
    print("   Point it at your Vobiz DID number")
    print()
    print("3. Start the agent worker:")
    print("   python agent.py start")
    print()
    print("4. Call your WhatsApp Business number from any phone")
    print("   The AI agent should answer within 3-5 seconds")
    print()


if __name__ == "__main__":
    asyncio.run(setup())
