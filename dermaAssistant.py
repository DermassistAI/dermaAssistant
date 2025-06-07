from agno.agent import Agent
import os
from agno.models.groq import Groq
from agno.models.google import Gemini
from agno.storage.sqlite import SqliteStorage
from agno.team import Team
from agno.tools.function import UserInputField
from agno.tools.user_control_flow import UserControlFlowTools
from agno.utils import pprint
from fastapi.responses import PlainTextResponse
from fastapi import FastAPI, Request, Form
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.pubmed import PubmedTools
from agno.tools.twilio import TwilioTools
from agno.exceptions import ModelProviderError
from skin.skin_kb import DermaKnowledgeBase
#Twilio imports
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from clinical_tools import get_clinical_input, ClinicalInfo

from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

#api_key = os.getenv("GOOGLE_API_KEY")
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(account_sid, auth_token)

agent_storage: str = "tmp/agents.db"

kb = None

derma_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load KB and create team
    global kb, derma_agent
    kb = await load_derma_kb()
    derma_agent = await create_teams()
    print("[INFO] Dermatology team initialized and ready.")
    yield
    # Shutdown: Clean up if needed
    print("[INFO] Shutting down dermatology service")

app = FastAPI(lifespan=lifespan)

# Load derma knowledge base (async only for this step)
async def load_derma_kb():
    kb = DermaKnowledgeBase(
        table_name="derma_knowledge",
        db_path="./my_local_lancedb",
        pdf_paths=["resources"],
        urls = []
    )
    await kb.aload(upsert=True, recreate=False)
    return kb

async def create_teams():
    # First ensure KB is loaded
    global kb
    if kb is None:
        kb = await load_derma_kb()
    
    # Conversation agent to handle initial interaction and data collection
    conversation_agent = Agent(
        name="Conversation Handler",
        model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
        tools=[
            get_clinical_input,
            TwilioTools(
                account_sid=account_sid,
                auth_token=auth_token,
                debug=True
            )
        ],
        instructions=[
            """
            You are the initial contact for a dermatology consultation service.
            Your role is to:
            1. Collect complete information from patients using the get_clinical_input tool
            2. Ensure all necessary details are provided before analysis
            3. Guide users to provide complete information
            
            If information is incomplete, ask specific questions.
            Once you have complete information, format it clearly for the medical analysis agent.
            
            Always respond to greetings politely and guide the conversation to collect clinical details.
            """
        ],
        storage=SqliteStorage(table_name="conversation_agent", db_file="./derma_agent.sqlite")
    )

    # Medical analysis agent
    analysis_agent = Agent(
        name="Medical Analyzer",
        model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
        tools=[
            DuckDuckGoTools(),
            PubmedTools(),
            UserControlFlowTools()
        ],
        knowledge=kb.get_knowledge_base() if kb else None,
        instructions=[
            """
            You are a Dermatology Analysis Assistant that processes validated clinical information.
            Your role is to:
            1. Analyze the complete clinical description
            2. Provide evidence-based assessment
            3. Suggest appropriate next steps
            
            Format your response as:
            - Clinical Features Analysis
            - Potential Diagnoses
            - Recommended Actions
            
            Always include appropriate medical disclaimers.
            """
        ],
        storage=SqliteStorage(table_name="analysis_agent", db_file="./derma_agent.sqlite")
    )

    # Create the team
    derma_team = Team(
        name="Dermatology Consultation Team",
        members=[conversation_agent, analysis_agent],
        model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
        instructions="""
        This is a two-stage dermatology consultation process:
        1. The conversation agent collects and validates patient information
        2. The medical analysis agent provides clinical assessment
        
        Team workflow:
        - First agent (Conversation Handler) extracts clinical information using get_clinical_input
        - If information is incomplete, ask specific questions
        - Once complete, second agent (Medical Analyzer) provides assessment based on ClinicalInfo
        
        The team must ensure complete information before proceeding with analysis.
        """
    )

    return derma_team

user_sessions = {}

@app.post("/twilio/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(request: Request):
    print("[DEBUG] /twilio/whatsapp endpoint hit")
    try:
        # Get form data from the request
        form = await request.form()
        print(f"[DEBUG] Form data received: {form}")
        
        # Extract message details with proper validation and type conversion
        sender = str(form.get("From") or form.get("from", ""))
        message = str(form.get("Body") or form.get("body", ""))
        media_url = form.get("MediaUrl0")  # Handle images if present
        print(f"[DEBUG] Sender: {sender}, Message: {message}, Media URL: {media_url}")
        
        if not sender or not message:
            print("[ERROR] Missing sender or message in request.")
            return PlainTextResponse(
                content="<Response><Message>Invalid request: Missing sender or message.</Message></Response>",
                media_type="application/xml"
            )

        print(f"Incoming WhatsApp from {sender}: {message}")
        
        # Initialize agent if needed
        global derma_agent
        if derma_agent is None:
            print("[ERROR] derma_agent is not initialized.")
            return PlainTextResponse(
                content="<Response><Message>Service is initializing. Please try again in a moment.</Message></Response>",
                media_type="application/xml"
            )

        # Process the message
        print("[DEBUG] Calling process_whatsapp_message...")
        response = await process_whatsapp_message(message, sender)
        print(f"[DEBUG] Response from agent: {response}")
        return PlainTextResponse(
            content=f"<Response><Message>{response}</Message></Response>",
            media_type="application/xml"
        )
    except Exception as e:
        print(f"[ERROR] Exception in whatsapp_webhook: {str(e)}")
        return PlainTextResponse(
            content="<Response><Message>Sorry, I had trouble processing that. Please describe your skin issue—e.g.,\"I have a red rash on my arm that has been there for 3 days.\"</Message></Response>",
            media_type="application/xml"
        )

async def process_whatsapp_message(message: str, sender: str) -> str:
    """Process incoming WhatsApp messages using the dermatology team."""
    try:
        print("[DEBUG] process_whatsapp_message called")
        # Run the team with the message
        if derma_agent is None:
            print("[ERROR] Dermatology team is not initialized")
            raise RuntimeError("Dermatology team is not initialized")
        print("[DEBUG] Running derma_agent.arun...")
        run_response = await derma_agent.arun(message)
        print(f"[DEBUG] derma_agent.arun response: {run_response}")
        return str(run_response)

    except ModelProviderError as e:
        print(f"[ERROR] ModelProviderError: {str(e)}")
        if "tool_use_failed" in str(e):
            return ("To provide an accurate assessment, please share:\n"
                   "1. Where is the skin condition located?\n"
                   "2. When did you first notice it?\n"
                   "3. What does it look like (color, size, texture)?\n"
                   "4. Are there any symptoms (itching, pain, etc)?")
        print(f"Error details: {str(e)}")
        raise
    except Exception as e:
        print(f"[ERROR] Exception in process_whatsapp_message: {str(e)}")
        raise
