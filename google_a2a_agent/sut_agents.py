from google.adk.agents import LlmAgent
from google_a2a_agent.callbacks import inject_a2ui_ad_callback, validate_a2ui_security_callback
from google_a2a_agent.model_router import get_adk_model
from google_a2a_agent.schema_manager import A2uiSchemaManager

schema_manager = A2uiSchemaManager()

# 1. Mode A Agent (Prompt-Injected):
# The LLM is forced to generate both organic UI and the AdBanner by embedding
# the AdBanner schema, advertiser parameters, and disclosure rules in the system prompt.
mode_a_agent = LlmAgent(
    name="mode_a_prompt_ad_agent",
    model=get_adk_model("sut"),
    description="Generates A2UI JSON with AdBanner instructions embedded directly into the system prompt.",
    instruction=schema_manager.build_system_instruction(include_ad_catalog=True),
    after_model_callback=validate_a2ui_security_callback,
    output_key="mode_a_result",
)

# 2. Mode B Agent (Callback-Injected):
# The LLM focuses 100% on organic technical comparison with only BasicCatalog in its prompt.
# An ADK after_model_callback deterministically injects a compliant AdBanner node post-inference.
mode_b_agent = LlmAgent(
    name="mode_b_callback_ad_agent",
    model=get_adk_model("sut"),
    description="Generates pure organic A2UI JSON while ADK after_model_callback deterministically injects the AdBanner.",
    instruction=schema_manager.build_system_instruction(include_ad_catalog=False),
    after_model_callback=inject_a2ui_ad_callback,
    output_key="mode_b_result",
)

