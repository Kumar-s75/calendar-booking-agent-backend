# Alternative implementation using Grok (xAI)
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from typing import Dict, List
import os
from datetime import datetime, timedelta

from calendar_service import CalendarService

class BookingAgentGrok:
    def __init__(self, calendar_service: CalendarService):
        self.calendar_service = calendar_service
        
        # Use Grok via OpenAI-compatible API
        self.llm = ChatOpenAI(
            model="grok-beta",
            temperature=0.7,
            openai_api_key=os.getenv('XAI_API_KEY'),
            openai_api_base="https://api.x.ai/v1"
        )
        
        self.sessions = {}
        self.tools = self._create_tools()
        self.agent_executor = self._create_agent()
    
    # ... rest of the implementation similar to main agent
