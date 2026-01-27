from typing import TypedDict, Annotated, Sequence, List, Dict, Optional, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver
from src.chain_factory import get_llm, get_fast_llm
from src.tools import ALL_TOOLS
import operator
import json
import os

# Define the shared state for the agents
# Define the shared state for the agents
class AgentState(TypedDict):
    # Chat history
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # CV Data and context
    cv_id: int
    cv_data: Dict
    # Link verification status
    github_verified: bool
    linkedin_verified: bool
    # Tracker for research Phase
    unverified_skills: List[str]
    discovered_projects: List[Dict]
    # Tracker for Interview Phase
    unverified_asked: int
    projects_asked: int
    covered_topics: List[str]
    current_topic: Optional[str]
    # Misc
    job_description: str

# --- Node Implementations ---

# --- Node Implementations ---

async def research_node(state: AgentState):
    """
    Agent responsible for finding and verifying professional links.
    """
    cv_data = state.get('cv_data', {})
    if 'contact_information' not in cv_data:
        cv_data['contact_information'] = {}
    contact = cv_data['contact_information']
    
    # Support flat DB schema
    if not contact.get('github') and cv_data.get('github'):
        contact['github'] = cv_data.get('github')
    if not contact.get('linkedin') and cv_data.get('linkedin'):
        contact['linkedin'] = cv_data.get('linkedin')
    if not contact.get('name') and cv_data.get('name'):
        contact['name'] = cv_data.get('name')

    name = contact.get('name', 'candidate')
    github = contact.get('github')
    linkedin = contact.get('linkedin')
    
    # Bind only research-focused tools to avoid confusion with database management tools
    from src.tools import verify_candidate_link, discover_professional_links, fetch_github_repositories
    research_tools = [verify_candidate_link, discover_professional_links, fetch_github_repositories]
    llm = get_fast_llm().bind_tools(research_tools)
    
    # Check if we are ready for analysis (internal transition)
    if state.get('github_verified') and state.get('linkedin_verified') and not state.get('unverified_skills'):
        print(f"[Graph] Performing Deep Analysis for {name}")
        proj_text = json.dumps(state.get('discovered_projects', []))
        skills = ", ".join(cv_data.get('skills', []))
        
        analysis_prompt = f"""
        Compare CV Skills: {skills}
        Against Evidence: {proj_text}
        Identify 1-3 skills that LACK evidence.
        Return JSON ONLY: {{"unverified_skills": [], "discovered_projects": [], "analysis": ""}}
        """
        response = await get_fast_llm().ainvoke(analysis_prompt)
        try:
            text = response.content
            if "```json" in text: text = text.split("```json")[-1].split("```")[0].strip()
            data = json.loads(text)
            return {
                "unverified_skills": data.get("unverified_skills", []),
                "discovered_projects": data.get("discovered_projects", state.get('discovered_projects', [])),
                "messages": [AIMessage(content="INTERNAL_RESEARCH_COMPLETE")] 
            }
        except:
            return {"messages": [AIMessage(content="INTERNAL_RESEARCH_COMPLETE")], "unverified_skills": ["Technical Depth"]}

    # --- PROACTIVE GREETING ON FIRST TURN ---
    # We detect if this is the start of the session to acknowledge the user
    is_first_turn = len(state["messages"]) <= 1 
    user_greeting = ""
    if is_first_turn:
        user_greeting = f"Hi {name}, I'm checking your profiles now. "

    system_msg = SystemMessage(content=f"""
    You are the Research Agent for {name}. 
    
    CRITICAL INSTRUCTIONS:
    1. **NO REDUNDANCY**: You ALREADY HAVE the CV data for {name}. Do NOT ask for a CV ID, a resume, or an introduction.
    2. **STAY IN LOOP**: Your only job is to fill the gaps using your tools.
    3. **MISSION**:
       - Verify existing links ({github}, {linkedin}) using 'verify_candidate_link'.
       - If a link is missing or unverified, use 'discover_professional_links'.
       - Once links are verified, use 'fetch_github_repositories'.
    4. **INTERNAL ONLY**: Once you have the info, respond ONLY with "INTERNAL_READY_TO_ANALYZE".
    """)
    
    response = await llm.ainvoke([system_msg] + list(state["messages"]))
    
    # If starting research, let the user know
    if user_greeting and response.content == "" and response.tool_calls:
        # If it's a tool call with no content, we provide the greeting as content
        response.content = user_greeting
    elif user_greeting:
        response.content = user_greeting + response.content

    return {"messages": [response], "cv_data": cv_data}

async def interviewer_node(state: AgentState):
    """
    Agent responsible for technical interview questions.
    """
    llm = get_llm()
    
    cv_data = state.get('cv_data', {})
    unverified_skills = state.get('unverified_skills', [])
    discovered_projects = state.get('discovered_projects', [])
    unverified_asked = state.get('unverified_asked', 0)
    projects_asked = state.get('projects_asked', 0)
    covered_topics = state.get('covered_topics', [])
    current_topic = state.get('current_topic')
    
    if not current_topic:
        can_verify = unverified_asked < len(unverified_skills)
        must_do_project = projects_asked < (unverified_asked * 2) or not can_verify
        
        if can_verify and not must_do_project:
            skill = unverified_skills[unverified_asked]
            current_topic = f"Unverified: {skill}"
        else:
            available_projects = [p for p in discovered_projects if p.get('name') not in covered_topics]
            if available_projects:
                proj = available_projects[0]
                current_topic = f"Project: {proj['name']}"
            else:
                current_topic = "CV_Project"

    project_list = ", ".join([p.get('name', 'Project') for p in discovered_projects])
    
    system_msg = SystemMessage(content=f"""
    You are a Senior Technical Interviewer.
    
    CRITICAL PERSONA RULES:
    1. **NO SUMMARIES / NO SOLUTIONS**: Never explain how a technology works or provide a "lesson".
    2. **STRICTLY QUESTIONS**: Your response must consist of a brief critique of the last answer followed by exactly one or two deep technical questions.
    3. **DO NOT HELP**: If the user is vague, challenge them. Do not provide the answer for them.
    4. **CONCISENESS**: Keep your response under 100 words.
    
    Current Focus: {current_topic}
    Projects available: {project_list if project_list else "CV contents"}
    
    TASK: Ask a rigorous architectural or implementation question about the 'Current Focus'.
    """)
    
    response = await llm.ainvoke([system_msg] + list(state["messages"]))
    
    # Update trackers for "moving on" (internal logic)
    new_unverified = unverified_asked
    new_projects = projects_asked
    new_covered = covered_topics
    new_topic = current_topic
    
    if "moving on" in response.content.lower():
        if current_topic:
            topic_name = current_topic.split(': ')[-1]
            new_covered.append(topic_name)
            if "unverified" in current_topic.lower():
                new_unverified += 1
            else:
                new_projects += 1
        new_topic = None
    
    return {
        "messages": [response],
        "unverified_asked": new_unverified,
        "projects_asked": new_projects,
        "covered_topics": new_covered,
        "current_topic": new_topic
    }

def feedback_node(state: AgentState):
    """Agent for ending the session."""
    return {"messages": [AIMessage(content="The interview session is now complete. Thank you.")]}

# --- Router Logic ---

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    
    # Priority 1: Tools
    if last_message.tool_calls:
        return "tools"
    
    content = getattr(last_message, "content", "") or ""
    
    # Priority 2: Internal Transitions
    if "INTERNAL_READY_TO_ANALYZE" in content or "INTERNAL_RESEARCH_COMPLETE" in content:
        return "research"
    
    # Priority 3: Transition to Interview
    if "RESEARCH_COMPLETE" in content or "SKIP_RESEARCH" in content:
        return "interviewer"
    
    # Priority 4: Final Closure
    if "interview session is complete" in content.lower():
        return END
        
    # Priority 5: Stop for User Input
    if isinstance(last_message, AIMessage):
        # Only stop if there is actual non-internal content
        if content.strip() == "" or "INTERNAL_" in content:
            # Continue to interviewer to ensure we don't present a blank screen
            return "interviewer"
        return END
        
    return "interviewer" 

# --- Graph Compilation ---

def create_interview_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("research", research_node)
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("feedback", feedback_node)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))

    workflow.set_entry_point("research")

    workflow.add_conditional_edges(
        "research",
        should_continue,
        {
            "tools": "tools", 
            "interviewer": "interviewer", 
            "research": "research", # Recursive call for sub-steps
            END: END
        }
    )
    workflow.add_conditional_edges(
        "interviewer",
        should_continue,
        {
            "tools": "tools", 
            "feedback": "feedback", 
            "interviewer": "interviewer", 
            "research": "research", 
            END: END
        }
    )
    
    workflow.add_edge("tools", "research")
    workflow.add_edge("feedback", END)

    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

interview_graph = create_interview_graph()
