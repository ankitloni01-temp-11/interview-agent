import asyncio
from src.graph import get_compiled_graph

async def test_graph():
    print("Compiling LangGraph...")
    try:
        app = get_compiled_graph()
        print("✅ Graph compiled successfully!")
        print(f"✅ Nodes available: {list(app.nodes.keys())}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_graph())
