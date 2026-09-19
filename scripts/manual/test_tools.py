import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # repo root, imports use the src. prefix

from src.agents.tools.vnstock_tool import vnstock_get_quote, vnstock_get_company_info
from src.agents.tools.tavily_search import tavily_web_search

async def test():
    with open('test_result.txt', 'w', encoding='utf-8') as f:
        f.write("Testing vnstock_get_quote...\n")
        r1 = await vnstock_get_quote('VCB')
        f.write(f"Result: {r1}\n\n")
        
        f.write("Testing vnstock_get_company_info...\n")
        r2 = await vnstock_get_company_info('VCB')
        f.write(f"Result: {r2}\n\n")
        
        f.write("Testing tavily_web_search...\n")
        r3 = await tavily_web_search('VCB stock', max_results=2)
        f.write(f"Result: {r3}\n")
    
    return r1, r2, r3

if __name__ == "__main__":
    asyncio.run(test())
    print("Done! Check test_result.txt")
