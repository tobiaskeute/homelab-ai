import logging
import os
from functools import lru_cache, partial
from typing import Optional, List, Callable, Coroutine

from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph, MessagesState
from langgraph.graph.state import CompiledStateGraph

from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.agents import create_agent

from langgraph.prebuilt.tool_node import ToolCallRequest

from core.clients import VikunjaAdapter, MonicaAdapter
from models import ChatMessage, LangGraphAgentResponse, UserContext
from util.secret_store import SecretStore

logger = logging.getLogger(__name__)

secrets = SecretStore("secrets.json")

llm_provider = os.environ.get("LLM_PROVIDER")

if llm_provider == "mistral":
    llm = ChatMistralAI(
        model=os.environ.get("MISTRAL_MODEL", "ministral-8b-2512"),
        mistral_api_key=os.environ.get("MISTRAL_API_KEY"),
        temperature=0,
    )
elif llm_provider == "google":
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("GOOGLE_MODEL", "models/gemini-4-hydrogen"),
        api_key=os.environ.get("GOOGLE_API_KEY")
    )
elif llm_provider == "openrouter":
    llm = ChatOpenRouter(
        model=os.environ.get("OPENROUTER_MODEL", "auto"),
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )
elif llm_provider == "nvidia":
    llm = ChatNVIDIA(
        model=os.environ.get("NVIDIA_MODEL"),
        api_key=os.environ.get("NVIDIA_API_KEY"),
    )
else:
    raise Exception("LLM_PROVIDER not in ['mistral', 'google', 'openrouter', 'nvidia']")

checkpointer = InMemorySaver()

class AgentState(MessagesState):
    user: UserContext

@lru_cache()
def get_user_agent(username: str):
    return LangGraphAgent(username=username)

class ToolProvider():
    """
    provides tools based on the availability of microservice credentials.
    """
    def __init__(self, username):
        self.username = username
        self.adapters = []
        self._tools = []

        self._collect_adapters()

    async def list_tools(self):
        if not self._tools:
            for adapter in self.adapters:
                adapter_tools = await adapter.list_tools()
                self._tools.extend(adapter_tools)

        return self._tools

    def _collect_adapters(self):
        if os.environ.get("VIKUNJA_URL"):
            try:
                vikunja_adapter = VikunjaAdapter(
                    base_url=os.environ.get("VIKUNJA_URL"),
                    mcp_token=secrets.get(username=self.username, service="vikunja"),
                )
                self.adapters.append(vikunja_adapter)
            except ValueError as e:
                logger.warning(f"Could not initialize VikunjaAdapter: {e}")

        if os.environ.get("MONICA_URL"):
            try:
                monica_adapter = MonicaAdapter(
                    base_url=os.environ.get("MONICA_URL"),
                    api_token=secrets.get(username=self.username, service="monica"),
                )
                self.adapters.append(monica_adapter)
            except (ValueError, KeyError) as e:
                logger.warning(f"Could not initialize MonicaAdapter: {e}")


class LangGraphAgent():
    """
    The agent that gets called when a user sends a message in OpenWebUI
    """

    def __init__(self, username: str):
        self._username = username
        self._graph: Optional[CompiledStateGraph] = None

        self._tool_provider = ToolProvider(self._username)
        self._tool_agent = None

    @wrap_tool_call
    async def handle_tool_errors(
            request: ToolCallRequest,
            handler: Callable[[ToolCallRequest], Coroutine],
    ) -> ToolMessage:
        """Convert tool exceptions into ToolMessages the model can handle."""
        try:
            return await handler(request)
        except Exception as e:
            return ToolMessage(
                content=f"Tool error: Please check your input and try again. ({e})",
                tool_call_id=request.tool_call["id"],
            )

    async def get_graph(self):
        """
        Gets the Agents graph. If no graph exists, it will create one first.
        :return:
        """
        if self._graph is None:
            await self._create_graph()
        return self._graph

    async def _create_graph(self):
        logger.info("Creating graph")

        tools = await self._tool_provider.list_tools()

        self._tool_agent = create_agent(
            model = llm,
            tools = tools,
            middleware=[self.handle_tool_errors]
        )

        graph = StateGraph(AgentState)

        graph.add_node("LLM", self._llm_node)
        graph.add_edge(START, "LLM")
        graph.add_edge("LLM", END)
        self._graph = graph.compile(checkpointer=checkpointer)

    async def _llm_node(self, state: AgentState):
        """
        Langgraph Node calling the LLM

        :param state:
        :return:
        """

        return await self._tool_agent.ainvoke(
                    {
                        "messages" : [
                            SystemMessage(content="""
    You are an AI assistant with access to various microservices in a homelab.
    
    Available applications through tools:
    
    Vikunja: Task and project management (tasks, projects, labels, etc.)
    
    Monica CRM: Contact management for friends and family.
    - Contacts: create_contact, list_contacts, search_contacts, get_contact, update_contact, delete_contact
    - Notes: create_note, list_notes, delete_note
    - Activities: create_activity, list_activities
    - Reminders: create_reminder, list_reminders
    - Tasks: create_task, list_tasks, complete_task
    - Relationships: add_relationship, list_relationships
    - Tags, Addresses, Gifts, Debts, Journals, etc.
    
    IMPORTANT for Monica contacts: Always provide first_name and last_name as separate parameters.
    Example: "Create a contact for Julia Grube" -> use create_contact(first_name="Julia", last_name="Grube")
    
    Du bist ein Assistent, der Zugriff auf diverse Microservices in einem Homelab hat.
    
    Auf folgende Anwendungen hast du durch Tools zugriff:
    
    Vikunja: Task und Projekte abrufen und bearbeiten (Tasks, Projects, Labels, etc.)
    
    Monica CRM: Kontaktmanagement für Freunde und Bekannte.
    - Kontakte: create_contact, list_contacts, search_contacts, get_contact, update_contact, delete_contact
    - Notizen: create_note, list_notes, delete_note
    - Aktivitäten: create_activity, list_activities
    - Erinnerungen: create_reminder, list_reminders
    - Aufgaben: create_task, list_tasks, complete_task
    - Beziehungen: add_relationship, list_relationships
    - Tags, Adressen, Geschenke, Schulden, Journale, etc.
    
    Wichtig: Für Monica-Kontakte immer first_name und last_name separat angeben.
    Beispiel: "Erstelle einen Kontakt für Julia Grube" -> create_contact(first_name="Julia", last_name="Grube")
    """
                                        )
                        ]
                        + state["messages"]
                    }
                )

    async def get_response(
            self,
            message: ChatMessage,
            chat_id: str,
    ) -> LangGraphAgentResponse:
        graph = await self.get_graph()
        response = await graph.ainvoke(
            input={
                "messages": [message.model_dump()],
            },
            config={"configurable": {"thread_id": chat_id}},
        )
        logger.info("Latest response: {}".format(response.get("messages")[-1]))
        return LangGraphAgentResponse.model_validate(response)
