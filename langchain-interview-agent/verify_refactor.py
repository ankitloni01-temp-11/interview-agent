import asyncio
import sys
import os

# Set up paths
sys.path.append(os.getcwd())

async def verify_orchestrator():
    print("--- Starting Verification ---")
    
    # 1. Check LangGraph removal
    try:
        import langgraph
        print("[!] Note: langgraph package still installed (expected if requirements not re-installed), but checking usage...")
    except ImportError:
        print("[✓] langgraph package not found.")

    # 2. Initialize Orchestrator
    try:
        from src.agents.orchestrator import Orchestrator
        orch = Orchestrator()
        print("[✓] Orchestrator initialized successfully.")
    except Exception as e:
        print(f"[✗] Failed to initialize Orchestrator: {e}")
        return

    # 3. Simulate Conversation Flow
    context = {
        "cv_id": 1,
        "cv_data": {
            "contact_information": {"name": "Test Candidate"},
            "skills": ["Python", "Machine Learning"]
        },
        "history": [],
        "state": "START"
    }

    # Step: Greeting
    print("\nTesting Greeting...")
    result = await orch.route("Hello!", context)
    print(f"Agent: {result.get('agent')}")
    print(f"Response: {result.get('response')}")
    
    # Step: Research (Simulated input)
    print("\nTesting Research State...")
    context['state'] = 'RESEARCH'
    result = await orch.route("I'm ready", context)
    print(f"Next State: {result.get('next_state')}")
    print(f"Response: {result.get('response')}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_orchestrator())
