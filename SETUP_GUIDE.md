# WhatsApp Inbound AI Agent — Setup Guide

This guide gets your AI agent answering WhatsApp calls for free.
**Total cost: ₹0** for testing (inbound WhatsApp calls are free).

---

## What you need (all free tier)

| Service | Purpose | Free tier |
|---|---|---|
| LiveKit Cloud | Voice room + SIP routing | 100k minutes/month |
| Groq | AI brain (LLM) | Unlimited free |
| Deepgram | Speech-to-text + voice | $200 credit |
| Vobiz | SIP trunk (connects WA to LiveKit) | Free account |
| Meta for Developers | WhatsApp Business API | Free |
| ngrok | Expose local PC to internet | Free |

---

## Step 1 — Create accounts

### 1a. LiveKit Cloud
1. Go to `cloud.livekit.io` → create account
2. Create a new project
3. Settings → API Keys → create a key pair
4. Copy: URL (`wss://...`), API Key, API Secret

### 1b. Groq (free LLM)
1. Go to `console.groq.com` → create account
2. API Keys → Create API Key
3. Copy the key (starts with `gsk_`)

### 1c. Deepgram (free STT + TTS)
1. Go to `console.deepgram.com` → create account
2. API Keys → Create API Key
3. Copy the key (you get $200 free credit — more than enough)

### 1d. Vobiz
1. Go to `vobiz.ai` → create account
2. SIP → Trunks → Create Trunk
3. Note: SIP Domain, Username, Password, Trunk ID

### 1e. Meta for Developers (WhatsApp Business)
1. Go to `developers.facebook.com`
2. My Apps → Create App → Business type
3. Add WhatsApp product
4. Complete Business Verification (takes 1-2 days — start this first)
5. Phone Numbers → Add a number (can use your existing WhatsApp Business number)
6. In Phone Number settings → Call Settings → enable SIP Calling
7. Set SIP URI to: `sip:your-vobiz-domain.sip.vobiz.ai`

---

## Step 2 — Install on your PC

```bash
# Clone your repo
git clone https://github.com/aa2500300-hash/Calling-agent.git
cd Calling-agent

# Create virtual environment
python3 -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 3 — Configure environment

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in all your API keys from Step 1.

Minimum required for free inbound testing:
```
LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=API...
LIVEKIT_API_SECRET=...
GROQ_API_KEY=gsk_...
DEEPGRAM_API_KEY=...
VOBIZ_SIP_DOMAIN=...
VOBIZ_SIP_TRUNK_ID=...
BUSINESS_NAME=Your Business Name
```

---

## Step 4 — Run the one-time setup script

This creates the LiveKit inbound trunk and dispatch rule (run once only):

```bash
python setup_inbound.py
```

You will see output like:
```
✅ Inbound trunk created: ST_xxxxxxxxxxxxxxxx
✅ Dispatch rule created: RU_xxxxxxxxxxxxxxxx
```

---

## Step 5 — Start the agent

```bash
python agent.py start
```

You should see:
```
INFO  registered worker agent_name=inbound-caller
```

Keep this terminal open — the agent is now listening for calls.

---

## Step 6 — Test with a call

1. Open WhatsApp on your phone
2. Find your WhatsApp Business number
3. Tap the call button (voice call)
4. The AI agent should answer within 3-5 seconds and say hello

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named 'livekit'` | Run `pip install -r requirements.txt` with venv active |
| Agent starts but no answer | Check Vobiz SIP URI points to LiveKit correctly |
| Audio works but AI is silent | Check GROQ_API_KEY is set correctly in .env |
| Call drops immediately | Normal — WhatsApp has 30s timeout. Check agent logs. |
| `registered worker` but no calls | Check dispatch rule was created with setup_inbound.py |

---

## How the call flow works

```
You (WhatsApp) → Meta SIP gateway → Vobiz SIP trunk → LiveKit room
                                                           ↓
                                                    agent.py starts
                                                           ↓
                                                    Groq LLM thinks
                                                           ↓
                                                    Deepgram speaks
                                                           ↓
                                                   You hear the AI
```

---

## Customising the agent

Edit `config.py`:
- `SYSTEM_PROMPT` — change the AI's personality and role
- `INBOUND_GREETING` — change what the AI says first
- `BUSINESS_NAME`, `SERVICES`, etc. — or set these in `.env`

---

## Going live (when ready)

For production (always-on, no PC needed):
1. Create an Oracle Cloud free account — free VPS forever (2 vCPUs, 1GB RAM)
2. SSH into the VPS
3. Clone your repo, install dependencies, run `python agent.py start`
4. Use `screen` or `pm2` to keep it running after you close the terminal
