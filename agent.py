from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage
from typing import Dict, List
import os
from datetime import datetime, timedelta
import json

from calendar_service import CalendarService

class BookingAgent:
    def __init__(self, calendar_service: CalendarService):
        self.calendar_service = calendar_service
        
        # Use Google Gemini as specified in requirements
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            google_api_key=os.getenv('GOOGLE_API_KEY')
        )
        
        self.sessions = {}  # Store conversation sessions
        self.tools = self._create_tools()
        self.agent_executor = self._create_agent()
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent"""
        
        def check_availability(date_str: str) -> str:
            """Check available time slots for a given date (YYYY-MM-DD format)"""
            try:
                slots = self.calendar_service.get_available_slots(date_str)
                if not slots:
                    return f"No available slots found for {date_str}. Please try another date."
                
                slot_list = []
                for slot in slots[:8]:  # Limit to 8 slots
                    slot_list.append(f"{slot['start_time']} - {slot['end_time']}")
                
                return f"Available slots for {date_str}:\n" + "\n".join(slot_list)
            except Exception as e:
                return f"Error checking availability: {str(e)}"
        
        def book_appointment(title: str, date: str, time: str, duration: str = "60") -> str:
            """Book an appointment with title, date (YYYY-MM-DD), time (HH:MM), and duration in minutes"""
            try:
                # Combine date and time
                datetime_str = f"{date} {time}"
                start_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                
                result = self.calendar_service.create_event(
                    title=title,
                    start_datetime=start_datetime.isoformat(),
                    duration_minutes=int(duration)
                )
                
                if result['success']:
                    return f"✅ Appointment '{title}' booked successfully for {date} at {time}!"
                else:
                    return f"❌ Failed to book appointment: {result['message']}"
                    
            except Exception as e:
                return f"Error booking appointment: {str(e)}"
        
        def get_current_date() -> str:
            """Get the current date"""
            return datetime.now().strftime('%Y-%m-%d')
        
        def get_events_for_date(date: str) -> str:
            """Get existing events for a specific date (YYYY-MM-DD format)"""
            try:
                events = self.calendar_service.get_events(date)
                if not events:
                    return f"No events found for {date}"
                
                event_list = []
                for event in events:
                    event_list.append(f"- {event['title']} at {event['start_time']}")
                
                return f"Events for {date}:\n" + "\n".join(event_list)
            except Exception as e:
                return f"Error getting events: {str(e)}"
        
        return [
            Tool(
                name="check_availability",
                description="Check available time slots for a specific date. Use YYYY-MM-DD format.",
                func=check_availability
            ),
            Tool(
                name="book_appointment",
                description="Book an appointment. Requires title, date (YYYY-MM-DD), time (HH:MM), and optional duration in minutes (default 60).",
                func=book_appointment
            ),
            Tool(
                name="get_current_date",
                description="Get the current date in YYYY-MM-DD format",
                func=get_current_date
            ),
            Tool(
                name="get_events_for_date",
                description="Get existing events for a specific date. Use YYYY-MM-DD format.",
                func=get_events_for_date
            )
        ]
    
    def _create_agent(self) -> AgentExecutor:
        """Create the agent executor"""
        
        system_prompt = """You are a helpful calendar booking assistant powered by Google Gemini. Your job is to help users book appointments on their Google Calendar through natural conversation.

You can:
1. Check availability for specific dates
2. Book appointments with title, date, and time
3. Get current date
4. View existing events for a date

Guidelines:
- Always be conversational and friendly
- Ask for missing information (title, date, time) before booking
- Suggest available time slots when asked
- Confirm booking details before creating the appointment
- Use proper date format (YYYY-MM-DD) and time format (HH:MM)
- Default appointment duration is 60 minutes unless specified otherwise

When a user wants to book an appointment:
1. Get the appointment title/purpose
2. Get the preferred date
3. Check availability for that date
4. Get the preferred time from available slots
5. Confirm and book the appointment

Be helpful and guide users through the booking process step by step. Engage in natural conversation and understand context from previous messages."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
    
    async def process_message(self, message: str, session_id: str = "default") -> str:
        """Process a user message and return the agent's response"""
        try:
            # Initialize session if it doesn't exist
            if session_id not in self.sessions:
                self.sessions[session_id] = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                )
            
            memory = self.sessions[session_id]
            
            # Get chat history
            chat_history = memory.chat_memory.messages
            
            # Process the message
            response = self.agent_executor.invoke({
                "input": message,
                "chat_history": chat_history
            })
            
            # Update memory
            memory.chat_memory.add_user_message(message)
            memory.chat_memory.add_ai_message(response["output"])
            
            return response["output"]
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
