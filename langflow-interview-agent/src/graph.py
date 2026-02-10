from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from src.chain_factory import get_llm, get_fast_llm
import json

# Define the state object for the entire graph
class InterviewTeamState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next_node: str
    cv_data: Dict[str, Any]
    kpis: str
    unverified_skills: List[str]
    context: Dict[str, Any] # For agent-specific memory

# Define the Supervisor Node
def create_supervisor_node(llm):
    options = ["GREETING", "RESEARCH", "KPI", "INTERVIEW", "FEEDBACK", "FINISH"]
    
    system_prompt = f"""You are the Interview Supervisor. Your job is to manage the technical interview process.
    Based on the conversation history and current state, decide which worker should act next.

    WORKERS:
    - GREETING: Use this if the user is just saying hi, asking how you are, or starting the conversation.
    - RESEARCH: Use this when the conversation moves towards profile verification (LinkedIn/GitHub) or when profiles need verification.
    - KPI: Use this after research is done to define technical benchmarks.
    - INTERVIEW: Use this for the technical questioning phase.
    - FEEDBACK: Use this when the interview is finished to provide the final score.
    - FINISH: Use this only when the final feedback has been given and the session is over.

    RULES:
    1. If the user is just greeting you and hasn't provided links, go to GREETING.
    2. Once the user is ready to proceed or provides links, go to RESEARCH.
    3. Once research confirms profiles, move to KPI.
    4. Once KPIs are set, move to INTERVIEW.
    5. After the interview, call FEEDBACK.

    Response must be a JSON object with a single key 'next' containing one of: {options}"""

    async def supervisor_node(state: InterviewTeamState) -> Dict[str, Any]:
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = await llm.ainvoke(messages)
        
        # Parse the decision
        try:
            content = response.content.strip().replace("```json", "").replace("```", "")
            decision = json.loads(content).get("next", "RESEARCH")
        except:
            decision = "RESEARCH" # Default fallback
            
        return {"next_node": decision}
    
    return supervisor_node

# Generic Node Wrapper for existing Agents
def create_worker_node(agent_instance, name):
    async def worker_node(state: InterviewTeamState) -> Dict[str, Any]:
        # Extract last user message
        user_input = state["messages"][-1].content if state["messages"] else ""
        
        # Prepare context for the agent
        context = state.get("context", {})
        context.update({
            "cv_data": state.get("cv_data", {}),
            "kpis": state.get("kpis", ""),
            "unverified_skills": state.get("unverified_skills", []),
            "state": state.get("next_node") 
        })
        
        # Process via existing agent logic
        result = await agent_instance.process(user_input, context)
        
        # Update graph state
        return {
            "messages": [AIMessage(content=result["response"], name=name)],
            "cv_data": result["context"].get("cv_data", state["cv_data"]),
            "kpis": result["context"].get("kpis", state["kpis"]),
            "unverified_skills": result["context"].get("unverified_skills", state["unverified_skills"]),
            "context": result["context"]
        }
    
    return worker_node

def get_compiled_graph():
    from src.agents.greeting_agent import GreetingAgent
    from src.agents.research_agent import ResearchAgent
    from src.agents.kpi_agent import KPIAgent
    from src.agents.interviewer_agent import InterviewerAgent
    from src.agents.feedback_agent import FeedbackAgent
    
    # Initialize agents
    greeting_agent = GreetingAgent()
    research_agent = ResearchAgent()
    kpi_agent = KPIAgent()
    interviewer_agent = InterviewerAgent()
    feedback_agent = FeedbackAgent()
    
    # Initialize LLMs
    supervisor_llm = get_fast_llm()
    
    # Create the Graph
    builder = StateGraph(InterviewTeamState)
    
    # Add Nodes
    builder.add_node("SUPERVISOR", create_supervisor_node(supervisor_llm))
    builder.add_node("GREETING", create_worker_node(greeting_agent, "GreetingWorker"))
    builder.add_node("RESEARCH", create_worker_node(research_agent, "ResearchWorker"))
    builder.add_node("KPI", create_worker_node(kpi_agent, "KPIWorker"))
    builder.add_node("INTERVIEW", create_worker_node(interviewer_agent, "InterviewWorker"))
    builder.add_node("FEEDBACK", create_worker_node(feedback_agent, "FeedbackWorker"))
    
    # Define Edges
    builder.add_edge(START, "SUPERVISOR")
    
    builder.add_conditional_edges(
        "SUPERVISOR",
        lambda x: x["next_node"],
        {
            "GREETING": "GREETING",
            "RESEARCH": "RESEARCH",
            "KPI": "KPI",
            "INTERVIEW": "INTERVIEW",
            "FEEDBACK": "FEEDBACK",
            "FINISH": END
        }
    )
    
    builder.add_edge("GREETING", "SUPERVISOR")
    builder.add_edge("RESEARCH", "SUPERVISOR")
    builder.add_edge("KPI", "SUPERVISOR")
    builder.add_edge("INTERVIEW", "SUPERVISOR")
    builder.add_edge("FEEDBACK", "SUPERVISOR")
    
    return builder.compile()
