import asyncio
from fetchai import fetch
from uagents_core.identity import Identity
from fetchai.communication import send_message_to_agent
from uuid import uuid4
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Discover agents from Agentverse based on a keyword
def discover_agents(agent_keyword: str):
    """
    Discover and return a list of agents from Agentverse based on a keyword.
    """
    discovered_agents = fetch.ai(agent_keyword)

    agents_list = []
    for agent in discovered_agents.get('ais', []):
        agents_list.append({
            "name": agent.get("name"),
            "description": agent.get("description"),
            "address": agent.get("address"),
            "tags": agent.get("tags", [])
        })

    return agents_list

# Discover a specific type of agent and send a query
async def discover_and_query_agent(agent_type: str, user_query: str):
    discovered_agents = fetch.ai(agent_type)

    relevant_agents = []
    for agent in discovered_agents.get('ais', []):
        description = agent.get("description", "").lower()
        tags = agent.get("tags", [])

        if agent_type.lower() in description or agent_type.lower() in tags:
            relevant_agents.append(agent)

    if not relevant_agents:
        return {"error": "No relevant agents found"}

    target_agent = relevant_agents[0]  # select first discovered agent
    agent_address = target_agent.get("address")

    sender_identity = Identity.from_seed("your-secure-seed", 0)
    payload = {"query": user_query}
    session_id = uuid4()

    response = await send_message_to_agent(
        sender=sender_identity,
        target=agent_address,
        payload=payload,
        session=session_id
    )

    return response

# Example usage
async def main():
    logger.info("Discovering available weather agents")
    agents = discover_agents("weather")
    if agents:
        for agent in agents:
            logger.info(f"Agent discovered", name=agent['name'], description=agent['description'], address=agent['address'], tags=agent['tags'])
    else:
        logger.warning("No agents found")

    logger.info("Querying a weather agent")
    response = await discover_and_query_agent("weather", "What is the weather in Boston?")
    logger.info("Response from agent", response=response)

# Run the main async function
if __name__ == "__main__":
    asyncio.run(main())
