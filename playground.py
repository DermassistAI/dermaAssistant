import asyncio
from agno.agent import Agent
from agno.models.groq import Groq
#add image analysis
#from agno.media import Image
#from agno.playground import Playground, serve_playground_app
from agno.storage.sqlite import SqliteStorage
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.pubmed import PubmedTools
from skin.skin_kb import DermaKnowledgeBase
#wozzap
from agno.app.whatsapp.app import WhatsappAPI
from agno.app.whatsapp.serve import serve_whatsapp_app
#fastAPI
from fastapi.responses import PlainTextResponse
from fastapi import Request
#from imagehandler import router as image_router


from dotenv import load_dotenv

load_dotenv()

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

# Main entry point (sync)
def main():
    kb = load_derma_kb()

    web_agent = Agent(
        name="Web Agent",
        model=Groq(id="meta-llama/llama-4-maverick-17b-128e-instruct"),
        tools=[DuckDuckGoTools()],
        instructions=["""
        You are a Dermatology Diagnosis Assistant designed to help clinicians accurately diagnose dermatological conditions. 
        Given a clinical description, image, or set of features, analyze and summarize the key lesion characteristics, and then proceed with the following structure:

        Lesion Characteristics:
        1) Morphology (e.g., macule, papule, plaque, vesicle)
        2) Color
        3) Distribution (localized, generalized, symmetrical, dermatomal)
        4) Configuration (linear, annular, grouped)
        5) Surface features (scaling, crusting, ulceration, lichenification)

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
        """],
        storage=SqliteStorage(table_name="web_agent", db_file=agent_storage),
        add_datetime_to_instructions=True,
        add_history_to_messages=True,
        num_history_responses=5,
        markdown=True,
    )

    med_agent = Agent(
        name="Medical Agent",
        model=Groq(id="llama-3.3-70b-versatile"),
        tools=[DuckDuckGoTools(),PubmedTools()],
        show_tool_calls=True,
        instructions=["Always include sources"],
        storage=SqliteStorage(table_name="med_agent", db_file=agent_storage),
        add_datetime_to_instructions=True,
        add_history_to_messages=True,
        num_history_responses=5,
        markdown=True,
    )

    derma_agent = Agent(
        name="Derma Agent",
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

    #app = Playground(agents=[web_agent, med_agent, derma_agent]).get_app()
    #serve_playground_app(app)

    # Async router by default (use_async=True)
    
    app = WhatsappAPI( agent=derma_agent, ).get_app()
  
    VERIFY_TOKEN = "BruceNicoleKoome"

    @app.get("/webhook", response_class=PlainTextResponse)
    async def verify_webhook(request: Request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return PlainTextResponse(content=challenge, status_code=200)
        return PlainTextResponse("Invalid token", status_code=403)

    serve_whatsapp_app(app, port=8000, reload=False)

# Only run if the script is executed directly
if __name__ == "__main__":
    main()
