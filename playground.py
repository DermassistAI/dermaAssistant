import asyncio
from agno.agent import Agent
from agno.models.groq import Groq
from agno.playground import Playground, serve_playground_app
from agno.storage.sqlite import SqliteStorage
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.pubmed import PubmedTools
from skin.skin_kb import DermaKnowledgeBase
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
        instructions=["Always include sources"],
        storage=SqliteStorage(table_name="web_agent", db_file=agent_storage),
        add_datetime_to_instructions=True,
        add_history_to_messages=True,
        num_history_responses=5,
        markdown=True,
    )

    med_agent = Agent(
        name="Medical Agent",
        model=Groq(id="llama-3.3-70b-versatile"),
        tools=[PubmedTools()],
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
        model=Groq(id="llama-3.3-70b-versatile"),
        tools=[PubmedTools()],
        knowledge=kb.get_knowledge_base(),
        show_tool_calls=True,
        instructions=["Always include sources"],
        storage=SqliteStorage(table_name="derma_agent", db_file="./derma_agent.sqlite"),
        add_datetime_to_instructions=True,
        add_history_to_messages=True,
        num_history_responses=5,
        markdown=True,
    )

    app = Playground(agents=[web_agent, med_agent, derma_agent]).get_app()
    serve_playground_app(app)

# Only run if the script is executed directly
if __name__ == "__main__":
    main()
