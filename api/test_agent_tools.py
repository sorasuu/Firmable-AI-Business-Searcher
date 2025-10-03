"""
Test the agent tools locally
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent_tools import AgentTools

def test_agent_tools():
    # Mock cached data
    cached_data = {
        'scraped_data': {
            'url': 'https://example.com',
            'title': 'Example Company',
            'markdown_content': 'We are located in New York City. Our office is at 123 Main Street. Contact us at info@example.com',
            'structured_chunks': ['We are located in New York City.', 'Our office is at 123 Main Street.', 'Contact us at info@example.com']
        },
        'insights': {
            'location': 'New York, NY',
            'contact_info': {
                'emails': ['info@example.com'],
                'phones': ['555-123-4567']
            }
        }
    }

    agent_tools = AgentTools()
    agent_tools.cached_data = cached_data

    # Test business info
    print("Testing get_business_info with 'location':")
    result = agent_tools._get_business_info('location')
    print(result)
    print()

    # Test contact info
    print("Testing get_contact_info with 'email':")
    result = agent_tools._get_contact_info('email')
    print(result)
    print()

    # Test search content
    print("Testing _search_content with 'office':")
    result = agent_tools._search_content('office')
    print(result)
    print()

if __name__ == "__main__":
    test_agent_tools()