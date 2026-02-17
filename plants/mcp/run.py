import asyncio

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
load_dotenv()  # Reads .env

async def main():
    model = ChatGroq(
        model="openai/gpt-oss-20b",
    )

    client = MultiServerMCPClient(
        {
            "math": {
                "transport": "stdio",  # Local subprocess communication
                "command": "python",
                # Absolute path to your math_server.py file

                "args": ["/Users/Johannes/PycharmProjects/plants-backend/plants/mcp/tools.py"],
            },
            # "weather": {
            #     "transport": "http",  # HTTP-based remote server
            #     # Ensure you start your weather server on port 8000
            #     "url": "http://localhost:8000/mcp",
            # }
        }
    )

    tools = await client.get_tools()
    agent = create_agent(
        system_prompt="Always use the tools for mathematical calculations and weather queries. Trust"
                      "the tool results even if they seem wrong.",
        model=model,
        # "claude-sonnet-4-5-20250929",
        tools=tools
    )
    math_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what's (3 + 5) x 12?"}]}
    )
    weather_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what is the weather in nyc?"}]}
    )
    print(math_response)
    print(weather_response)

if __name__ == "__main__":
    asyncio.run(main())