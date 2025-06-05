# test_agent.py

# from dermaAssistant import derma_agent  # Replace with actual import

# def test_agent():
#     response = derma_agent.run("What causes acne?")
#     print("Agent response:", response)

# if __name__ == "__main__":
#     test_agent()
#from fastapi import FastAPI, Request, Form
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dermaAssistant import derma_agent  # Import the agent from your module

app= FastAPI()

@app.get("/test-agent")
def test_agent():
    test_input = "What causes acne?"
    response = derma_agent.run(test_input)
    return {"input": test_input, "response": response}

