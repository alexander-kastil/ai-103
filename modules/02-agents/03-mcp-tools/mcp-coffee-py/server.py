import sys

# Add references
from fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP(name="Roastery")


# Add a bean inventory mcp tool
@mcp.tool()
def get_bean_inventory() -> dict:
    """Returns current stock levels (in 1 kg bags) for every coffee SKU in the roastery."""
    return {
        "Ethiopia Yirgacheffe": 6,
        "Colombia Supremo": 24,
        "Sumatra Mandheling": 8,
        "Espresso Blend": 4,
        "Guatemala Antigua": 19,
        "Kenya AA": 9,
        "Brazil Santos": 31,
        "Decaf House": 12,
        "Costa Rica Tarrazu": 7,
        "House Blend": 40,
    }


# Add a weekly sales mcp tool
@mcp.tool()
def get_weekly_sales() -> dict:
    """Returns the number of 1 kg bags sold for each coffee SKU during the past week."""
    return {
        "Ethiopia Yirgacheffe": 22,
        "Colombia Supremo": 5,
        "Sumatra Mandheling": 18,
        "Espresso Blend": 27,
        "Guatemala Antigua": 4,
        "Kenya AA": 16,
        "Brazil Santos": 3,
        "Decaf House": 6,
        "Costa Rica Tarrazu": 14,
        "House Blend": 21,
    }


# Run over HTTP (--http) to expose by URL, or stdio for the hand-written client
if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp", show_banner=False)
    else:
        mcp.run(show_banner=False)
