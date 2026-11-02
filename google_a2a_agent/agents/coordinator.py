from dotenv import load_dotenv
from google.adk.agents import LlmAgent, SequentialAgent
from google_a2a_agent.callbacks import inject_a2ui_ad_callback
from google_a2a_agent.model_router import get_adk_model
from google_a2a_agent.tools import (
    search_knowledge_tool,
    fetch_sponsored_cards_tool,
    dynamic_ad_search_tool,
    simulate_ad_banner_click,
    get_ad_telemetry_report,
)

load_dotenv()

# ==============================================================================
# 1. SEPARATED SEARCH & AD AGENT ARCHITECTURE (Google ADK)
# ==============================================================================

# Agent 1: Organic Search Researcher (100% Neutral, ZERO Ads)
organic_search_agent = LlmAgent(
    name="organic_search_agent",
    model=get_adk_model("sut"),
    output_key="organic_response",
    description="Objective Search Researcher — Produces accurate, domain-specific organic answers with zero advertising bias.",
    instruction=(
        "You are an expert, objective AI search engine researcher.\n"
        "Your responsibility is to answer the user's query directly, accurately, and comprehensively.\n\n"
        "RULES:\n"
        "1. If the user sends a casual greeting (e.g., 'Hi', 'Hello'), respond naturally and warmly in 1-2 sentences asking what they would like to search or explore today.\n"
        "2. For any informational, technical, or product query (even if it contains typos like 'wacthes'), optionally call `search_knowledge_tool` for live web context, and ALWAYS synthesize a thorough, accurate, domain-specific answer using your knowledge.\n"
        "   - For example, if asked about 'top 10 tier watches' or 'top 3 tier watches', name and explain the actual haute horlogerie brands (e.g., Patek Philippe, Audemars Piguet, Vacheron Constantin, A. Lange & Söhne, Breguet, Jaeger-LeCoultre, Blancpain, Rolex, Omega, Grand Seiko).\n"
        "   - If asked 'What is GPU', explain Graphics Processing Units, parallel tensor/shader cores, VRAM/HBM memory bandwidth, and applications in 3D rendering and AI/LLM computing.\n"
        "3. Format your response clearly with:\n"
        "   SUMMARY: <A rich, informative 3-5 sentence direct answer to the user's query>\n"
        "   HIGHLIGHT: <Specific factual point or tier/detail 1>\n"
        "   HIGHLIGHT: <Specific factual point or tier/detail 2>\n"
        "   HIGHLIGHT: <Specific factual point or tier/detail 3>\n"
        "4. Maintain 100% editorial neutrality. Never include ads, affiliate links, or promotional pitches."
    ),
    tools=[search_knowledge_tool],
)

# Agent 2: Contextual Ad & Sponsored UI Agent (Content-Grounded Ad Search)
contextual_ad_agent = LlmAgent(
    name="contextual_ad_agent",
    model=get_adk_model("sut"),
    output_key="ad_agent_response",
    description="Contextual Ad & A2UI Agent — Dynamically extracts commercial entities from refined organic search results and retrieves grounded sponsored ads via SerpApi.",
    instruction=(
        "You are the Content-Grounded Sponsored Ad & A2UI Surface Agent.\n"
        "You execute after `organic_search_agent` has generated the refined organic answer.\n\n"
        "YOUR CORE OBJECTIVE:\n"
        "Analyze both the user's query AND the refined organic search response (the summary and highlights) that the user will see.\n"
        "Extract the key commercial entities (brands, product models, hardware architectures, software platforms, airlines, retailers, or service providers) discussed in the refined content, and retrieve authentic sponsored ads grounded in those specific entities.\n\n"
        "RULES:\n"
        "1. NON-COMMERCIAL GATING:\n"
        "   If the user's query is a casual greeting ('Hi', 'Hello', 'How are you'), basic math/code syntax, or purely educational/scientific with zero commercial or purchasing relevance (e.g., 'how do trees produce oxygen', 'what is a for loop'):\n"
        "   - Do NOT call `dynamic_ad_search_tool`.\n"
        "   - Reply with: `INTENT: non_commercial | CATEGORY: casual_or_educational`\n\n"
        "2. DYNAMIC CONTENT-GROUNDED AD RETRIEVAL:\n"
        "   If the query and refined organic text discuss commercial products, brands, hardware, software, services, or luxury goods:\n"
        "   - Step A: Analyze the refined text and extract 1 to 3 primary commercial entities or brands mentioned (e.g., specific manufacturer names, flagship models, authorized retailers, or cloud providers that were highlighted in the organic answer).\n"
        "   - Step B: Formulate a targeted search query and entity search queries grounded directly in those extracted entities.\n"
        "   - Step C: Call `dynamic_ad_search_tool(query='<targeted_commercial_phrase>', category='<descriptive_category>', entity_queries=['<entity_1>', '<entity_2>'], limit=3)`.\n"
        "   - Step D: After the tool returns, reply with: `INTENT: commercial | CATEGORY: <descriptive_category>`\n\n"
        "3. EDITORIAL INTEGRITY:\n"
        "   Never invent fake prices, discounts, or arbitrary numbers. The tool retrieves authentic advertiser campaigns and verified merchant listings directly."
    ),
    tools=[dynamic_ad_search_tool, get_ad_telemetry_report],
    after_model_callback=inject_a2ui_ad_callback,
)

from google_a2a_agent.eval_agents import (
    ab_parallel_runner,
    schema_and_security_auditor,
    behavioral_drift_judge,
    action_loop_tester,
)

# Coordinator: Runs Organic Search first, followed by Contextual Ad Agent
search_and_ad_coordinator = SequentialAgent(
    name="search_and_ad_coordinator",
    description="Coordinated Multi-Agent Search Engine: Organic Search Researcher followed by Contextual Sponsored Ad Agent.",
    sub_agents=[
        organic_search_agent,
        contextual_ad_agent,
    ],
)

search_ad_agent = search_and_ad_coordinator
root_agent = search_and_ad_coordinator

# Benchmark Pipeline
benchmark_pipeline = SequentialAgent(
    name="a2ui_adbanner_benchmark_pipeline",
    description=(
        "Google ADK Multi-Agent Benchmark Suite for A2UI v0.9 Commercial UI Extension. "
        "Runs Mode A vs Mode B in parallel, audits JSON schema and security compliance, "
        "evaluates commercial steering bias with the Judge, and tests interactive CTA action loops."
    ),
    sub_agents=[
        ab_parallel_runner,
        schema_and_security_auditor,
        behavioral_drift_judge,
        action_loop_tester,
    ],
)

__all__ = [
    "root_agent",
    "search_ad_agent",
    "search_and_ad_coordinator",
    "organic_search_agent",
    "contextual_ad_agent",
    "benchmark_pipeline",
]
