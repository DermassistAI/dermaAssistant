from agno.agent import Agent
import os
from agno.models.groq import Groq
from agno.storage.sqlite import SqliteStorage
from fastapi import FastAPI, Request, Form
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.pubmed import PubmedTools
from agno.tools.twilio import TwilioTools
from skin.skin_kb import DermaKnowledgeBase
from fastapi.responses import PlainTextResponse

from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory

#Twilio imports
import base64
import requests
from typing import Optional
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from clinical_tools import get_clinical_input, ClinicalInfo

from dotenv import load_dotenv
load_dotenv()

#api_key = os.getenv("GOOGLE_API_KEY")
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(account_sid, auth_token)

agent_memory = Memory(
    db=SqliteMemoryDb(table_name="derma_user_memory", db_file="./derma_agent.sqlite")
)
agent_storage: str = "tmp/agents.db"

app = FastAPI()

derma_agent = Agent(
        name="Derma Agent",
        model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"), 
        tools=[DuckDuckGoTools(), PubmedTools()],
        memory=agent_memory,
        enable_user_memories=True,
        session_id="derma_whatsapp_session",
        #knowledge=kb.get_knowledge_base(),
        show_tool_calls=True,
        instructions=[
            """
        You are a Dermatology Diagnosis Assistant designed to help clinicians accurately diagnose dermatological conditions. 
        Given a clinical description or image or set of features, analyze and summarize the key lesion characteristics, and then proceed with the following structure:

        Lesion Characteristics:
        1) Morphology (e.g., macule, papule, plaque, vesicle)
        2) Color
        3) Distribution (localized, generalized, symmetrical, dermatomal)
        4) Configuration (linear, annular, grouped)
        5) Surface features (scaling, crusting, ulceration, lichenification)

        #ABCDE Description of lesions
        #the 5s - size, shape,
        Definitive Diagnosis:
        Provide a clear and concise diagnosis.
        Justify your choice based on the clinical presentation and typical findings.

        Differential Diagnoses:
        List up to three plausible alternatives.
        Briefly explain how each differs from the primary diagnosis.

        Recommended Next Steps:
        Suggest appropriate diagnostic tests (e.g., skin biopsy, KOH prep, bacterial/fungal cultures, patch testing, dermoscopy).
        Mention any urgent red flags or indications for specialist referral if applicable.

        Constraints:
        Be concise — maximum 100 words.
        Use clinical language appropriate for healthcare professionals.
        Do not speculate beyond the provided clinical findings.
        Always prioritize evidence-based reasoning.
        """
        ],
        storage=SqliteStorage(table_name="derma_agent", db_file="./derma_agent.sqlite"),
        add_datetime_to_instructions=True,
        add_history_to_messages=True,
        num_history_responses=5,
        markdown=True,
    )

def download_image(media_url, account_sid, auth_token):
    
    response = requests.get(media_url, auth=(account_sid, auth_token))
    if response.status_code == 200:
        return response.content
    else:
        print(f"Failed to download image: {response.status_code}, {response.content}")
        return None



@app.post("/twilio/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: Optional[str] = Form(None),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None),
):
    body_text = Body or ""
    print(f"Incoming from {From}: {body_text}")
    print(f"Media URL: {MediaUrl0}, Content Type: {MediaContentType0}")

    messages = []

    if Body and Body.strip():
        messages.append({"role": "user", "content": Body.strip()})

    if MediaUrl0:
        print(f"MediaUrl0 received from Twilio webhook: '{MediaUrl0}'")
        image_bytes = download_image(MediaUrl0, account_sid, auth_token)
        if image_bytes:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            # Adjust the message format below to match Groq's multimodal API
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": Body.strip() if Body else ""},
                    {"type": "image", "image": {"base64": image_b64}}

                ]
            })
        else:
            messages.append({"role": "user", "content": "User sent an image, but it could not be downloaded."})

    if not messages:
        messages.append({"role": "user", "content": "No message content received."})

    try:
        agent_response = await derma_agent.arun(
            messages=messages,
            user_id=From,
            tools=[TwilioTools()]
        )

        assistant_reply = next(
            (msg.content for msg in agent_response.messages if msg.role == "assistant"),
            "Sorry, I couldn’t process your message."
        )

        response = MessagingResponse()
        response.message(assistant_reply)
        print(f"Response to {From}: {assistant_reply}")

    except Exception as e:
        print("Agent error:", e)
        response = MessagingResponse()
        response.message("Sorry, there was an error processing your request.")

    return PlainTextResponse(content=str(response), media_type="application/xml")
