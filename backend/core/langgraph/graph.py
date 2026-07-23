from typing import Optional

from langgraph.constants import END, START
from langgraph.graph import StateGraph, MessagesState
from langgraph.graph.state import CompiledStateGraph

from models import ChatMessage


class AgentState(MessagesState):
    pass

class LangGraphAgent():
    """
    The agent that gets called when a user sends a message in OpenWebUI
    """

    def __init__(self):
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
        graph.add_node("LLM", self._llm)
        graph.add_edge(START, "LLM")
        graph.add_edge("LLM", END)
        self._graph = graph.compile()

    def _llm(self, state: AgentState):
        """
        Langgraph Node calling the LLM

        :param state:
        :return:
        """
        return {"messages": [{"role": "ai", "content": "This is from langgraph"}]}

    def get_response(
            self,
            messages: list[ChatMessage],
            chat_id: str,
    ):
        graph = self.get_graph()
        response = graph.invoke(
            input={"messages": [m.model_dump() for m in messages]}
        )
        return response
