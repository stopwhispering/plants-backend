from fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return 100
    # return a + b
#
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return 100
    # return a * b

@mcp.tool()
async def get_weather(location: str) -> str:
    """Get weather for location."""
    return "It's rainy in New York"

if __name__ == "__main__":
    mcp.run(transport="stdio")
    # mcp.run(transport="streamable-http")