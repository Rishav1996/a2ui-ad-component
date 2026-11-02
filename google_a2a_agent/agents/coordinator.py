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
        "Your responsibility is to answer the user's query directly, accurately, comprehensively, and with zero commercial bias.\n\n"
        "RULES:\n"
        "1. If the user sends a casual greeting or conversational remark (e.g., 'Hi', 'Hello', 'How are you'), respond naturally, politely, and warmly in 1-2 sentences asking what topic, product, or question they would like to explore today.\n"
        "2. For any query across any domain (technology, science, software, consumer products, health, travel, finance, lifestyle, arts, etc.), optionally invoke `search_knowledge_tool` for current web context, and synthesize an authentic, accurate, and deeply knowledgeable answer.\n"
        "3. Provide rich, structured output with:\n"
        "   SUMMARY: <A direct, high-value, comprehensive 3-5 sentence synthesis addressing the query>\n"
        "   HIGHLIGHT: <Key factual detail, technical specification, comparative factor, or domain nuance 1>\n"
        "   HIGHLIGHT: <Key factual detail, technical specification, comparative factor, or domain nuance 2>\n"
        "   HIGHLIGHT: <Key factual detail, technical specification, comparative factor, or domain nuance 3>\n"
        "4. Maintain strict editorial neutrality. Never inject artificial sponsored endorsements, promotional affiliate codes, or advertising pitches."
    ),
    tools=[search_knowledge_tool],
)

# Agent 2: Contextual Ad & Sponsored UI Agent (Content-Grounded Ad Search)
contextual_ad_agent = LlmAgent(
    name="contextual_ad_agent",
    model=get_adk_model("sut"),
    output_key="ad_agent_response",
    description="Contextual Ad & A2UI Agent — Dynamically evaluates commercial intent and retrieves content-grounded sponsored cards.",
    instruction=(
        "You are the Content-Grounded Commercial Intent & A2UI Surface Agent.\n"
        "You execute after `organic_search_agent` has generated the refined organic answer.\n\n"
        "YOUR CORE OBJECTIVE:\n"
        "Semantically evaluate both the user's query AND the refined organic search response.\n"
        "Determine whether the conversation has commercial, transactional, shopping, product evaluation, or professional service intent vs non-commercial (purely educational, academic, historical, mathematical, code syntax, or casual chat).\n\n"
        "RULES & WORKFLOW:\n"
        "1. DYNAMIC NON-COMMERCIAL & EDUCATIONAL GATING:\n"
        "   If the query is a casual greeting, pure code syntax question, theoretical concept, historical inquiry, or abstract science explanation with no purchasing or commercial utility:\n"
        "   - Do NOT call `dynamic_ad_search_tool`.\n"
        "   - Reply strictly with: `INTENT: non_commercial | CATEGORY: <descriptive_category>` (e.g., `casual_chat`, `educational_concept`, `science_explanation`, `code_syntax`).\n\n"
        "2. DYNAMIC COMMERCIAL INTENT & AD RETRIEVAL:\n"
        "   If the query or organic content touches any commercial products, brands, physical goods, software tools, SaaS, cloud services, professional services, courses, or travel/hospitality:\n"
        "   - Step A: Dynamically determine a concise snake_case category name describing the domain (e.g., `coffee_appliances`, `office_furniture`, `gpu_compute`, `luxury_watches`, `travel_hospitality`, `developer_tools`, `pet_supplies`, `audio_equipment`, `financial_services`).\n"
        "   - Step B: Extract 1 to 3 primary commercial brand or product entities directly from the organic synthesis.\n"
        "   - Step C: Formulate a targeted search query and entity queries grounded in those findings.\n"
        "   - Step D: Call `dynamic_ad_search_tool(query='<targeted_commercial_phrase>', category='<dynamic_category>', entity_queries=['<entity_1>', '<entity_2>'], limit=3)`.\n"
        "   - Step E: After the tool returns, reply with: `INTENT: commercial | CATEGORY: <dynamic_category>`.\n\n"
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
