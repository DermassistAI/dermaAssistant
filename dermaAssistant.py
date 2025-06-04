from agno.agent import Agent
import os
from agno.models.groq import Groq
from agno.models.google import Gemini
from agno.storage.sqlite import SqliteStorage
#from agno.media import Image
#from agno.playground import Playground, serve_playground_app
#from imagehandler import router as image_router
#whatsapp
from agno.app.whatsapp.app import WhatsappAPI
from agno.app.whatsapp.serve import serve_whatsapp_app
#tools
from fastapi.responses import PlainTextResponse
from fastapi import Request
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.pubmed import PubmedTools
#knowledge
from skin.skin_kb import DermaKnowledgeBase

from dotenv import load_dotenv

load_dotenv()

#api_key = os.getenv("GOOGLE_API_KEY")

agent_storage: str = "tmp/agents.db"

# Load derma knowledge base (async only for this step)
def load_derma_kb():
    kb = DermaKnowledgeBase(
        table_name="derma_knowledge",
        db_path="./my_local_lancedb",
        pdf_paths=["resources"],
        urls = [""]
    )
    import asyncio
    asyncio.run(kb.aload(upsert=True, recreate=False))
    return kb

kb = load_derma_kb()


#Our Agent
derma_agent = Agent(
        name="Derma Assistant",
        model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
        tools=[DuckDuckGoTools(), PubmedTools()],
        knowledge=kb.get_knowledge_base(),
        show_tool_calls=True,
        instructions=[
            """
        You are a Dermatology Diagnosis Assistant designed to help clinicians accurately diagnose dermatological conditions. 
        Given a clinical description, image, or set of features, analyze and summarize the key lesion characteristics, and then proceed with the following structure:

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
        Be concise — maximum 300 words.
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

# whatsapp_app = WhatsappAPI( 
#     agent=derma_agent, 
#     #name="Derma Assistant",
#     #app_id="derma_agent",
#     #description="A Dermatology Diagnosis Assistant designed to help clinicians accurately diagnose dermatological conditions.",
# )

VERIFY_TOKEN = "BruceNicoleKoome"
app = WhatsappAPI( agent=derma_agent,).get_app()
  

@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print(f"Webhook verification: mode={mode}, token={token}, challenge={challenge}, VERIFY_TOKEN={VERIFY_TOKEN}")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse("Invalid token", status_code=403)

serve_whatsapp_app(app, port=8000, reload=False)

#app = Playground(agents=[derma_agent]).get_app()

#serve_playground_app(app)
