from agents import Agent, FileSearchTool
from openai import OpenAI
from prompts import standards_prompt, zoning_prompt, orchestration_prompt, calculations_prompt
from constants import STANDARDS_VECTOR_STORE_ID, ZONING_VECTOR_STORE_ID, DEFAULT_MODEL, MAX_SEARCH_RESULTS
from tools import (
    calculate_area_load,
    calculate_line_load,
    combine_line_loads,
    calculate_max_moment,
    calculate_max_shear,
    list_calculation_tools,
    list_accessible_standards
)



standards_agent = Agent(
    name="Standards_Lookup_Agent",
    instructions=standards_prompt,
    model=DEFAULT_MODEL,
    tools=[
        FileSearchTool(
            max_num_results=MAX_SEARCH_RESULTS,
            vector_store_ids=[STANDARDS_VECTOR_STORE_ID]
        )
    ]
)

zoning_agent = Agent(
    name="Zoning_Lookup_Agent",
    instructions=zoning_prompt,
    model=DEFAULT_MODEL,
    tools=[
        FileSearchTool(
            max_num_results=MAX_SEARCH_RESULTS,
            vector_store_ids=[ZONING_VECTOR_STORE_ID]
        )
    ]
)

calculation_agent = Agent(
    name="Calculation_Agent",
    instructions=calculations_prompt,
    model=DEFAULT_MODEL,
    tools=[
        calculate_area_load,
        calculate_line_load,
        combine_line_loads,
        calculate_max_moment,
        calculate_max_shear,
    ]
)

orchestrator_agent = Agent(
    name="Orchestrator",
    model=DEFAULT_MODEL,
    instructions=orchestration_prompt,
    tools=[
        standards_agent.as_tool(
            tool_name="standards_agent",
            tool_description="Look up and gather detailed information for engineering standards, clauses, the NZ building code and design requirements. "
        ),
        zoning_agent.as_tool(
            tool_name="zoning_agent",
            tool_description="Look up, quote, and compare high-density and medium-density residential zoning rules and requirements."
        ),
        calculation_agent.as_tool(
            tool_name="calculation_agent",
            tool_description="Perform structural engineering calculations using design inputs and applicable standards."
        ),
        list_calculation_tools, list_accessible_standards  # <-- Now available to orchestrator!
    ]
)