import os
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph, MessagesState
from langgraph.graph.state import CompiledStateGraph

from langchain_mistralai import ChatMistralAI

from models import ChatMessage, LangGraphAgentResponse, UserContext
from util.secret_store import SecretStore

secrets = SecretStore("secrets.json")

llm = ChatMistralAI(
    model="mistral-small-latest",
    mistral_api_key=os.environ.get("MISTRAL_API_KEY"),
    temperature=0,
)

lite_llm =  ChatMistralAI(
    model="mistral-small-latest",
    mistral_api_key=os.environ.get("MISTRAL_API_KEY"),
    temperature=0.3,
)

checkpointer = InMemorySaver()

class AgentState(MessagesState):
    user: UserContext

@lru_cache()
def get_user_agent(username: str):
    return LangGraphAgent(username=username)


class LangGraphAgent():
    """
    The agent that gets called when a user sends a message in OpenWebUI
    """

    def __init__(self, username: str):
        self._username = username
        self._graph: Optional[CompiledStateGraph] = None
        self._create_graph()

    def get_graph(self):
        """
        Gets the Agents graph. If no graph exists, it will create one first.
        :return:
        """
        if self._graph is None:
            self._create_graph()
        return self._graph

    def _create_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("LLM", self._llm_node)
        graph.add_edge(START, "LLM")
        graph.add_edge("LLM", END)
        self._graph = graph.compile(checkpointer=checkpointer)

    def _llm_node(self, state: AgentState):
        """
        Langgraph Node calling the LLM

        :param state:
        :return:
        """

        vikunja_token = secrets.get(state.get("user").username, "vikunja")

        return {
            "messages": [
                llm.invoke(
                    [
                        SystemMessage(content="""
Please respond like a duck
"""
                                    )
                    ]
                    + state["messages"]
                )
            ]
        }


    def get_response(
            self,
            message: ChatMessage,
            chat_id: str,
            username: str,
            task_name: str = "",
    ) -> LangGraphAgentResponse:
        if task_name:
            # This comes from a task like topic-creation...so do not include the message in the LangGraph context
            return LangGraphAgentResponse(
                messages=[lite_llm.invoke([HumanMessage(content=message.content)])]
            )
        else:
            graph = self.get_graph()
            response = graph.invoke(
                input={
                    "messages": [message.model_dump()],
                    "user": UserContext(username=username),
                },
                config={"configurable": {"thread_id": chat_id}},
            )
            return LangGraphAgentResponse.model_validate(response)
