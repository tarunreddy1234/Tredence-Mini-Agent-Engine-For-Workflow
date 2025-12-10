from typing import Dict, Any, Callable, Optional, List
from pydantic import BaseModel
import uuid

# Core Types & Registries
State = Dict[str, Any]
ToolFn = Callable[[State], State]

# Global registries (in-memory)
tool_registry: Dict[str, ToolFn] = {}
graphs: Dict[str, "Graph"] = {}
runs: Dict[str, "Run"] = {}

# Pydantic Models (API Schemas)

class BranchConfig(BaseModel):
    condition_key: str        # key in state to check, e.g. "summary_too_long"
    operator: str             # "eq", "ne", "gt", "ge", "lt", "le"
    value: Any                # value to compare with
    true_next: Optional[str]  # next node if condition is True
    false_next: Optional[str] # next node if condition is False


class NodeConfig(BaseModel):
    name: str                 # node id
    tool: str                 # tool name in registry


class EdgeConfig(BaseModel):
    source: str               # name of source node
    next: Optional[str] = None
    branch: Optional[BranchConfig] = None


class GraphCreateRequest(BaseModel):
    nodes: List[NodeConfig]
    edges: List[EdgeConfig]
    start_node: str


class GraphCreateResponse(BaseModel):
    graph_id: str


class GraphRunRequest(BaseModel):
    graph_id: str
    initial_state: State


class LogEntry(BaseModel):
    step: int
    node: str
    tool: str
    state_before: State
    state_after: State


class GraphRunResponse(BaseModel):
    run_id: str
    final_state: State
    log: List[LogEntry]


class RunStateResponse(BaseModel):
    run_id: str
    graph_id: str
    status: str               # "running" or "completed"
    current_node: Optional[str]
    state: State
    log: List[LogEntry]

# Internal Graph / Run Structures

class Graph:
    def __init__(
        self,
        graph_id: str,
        start_node: str,
        nodes: Dict[str, NodeConfig],
        edges: Dict[str, EdgeConfig],
    ):
        self.graph_id = graph_id
        self.start_node = start_node
        self.nodes = nodes
        self.edges = edges


class Run:
    def __init__(self, run_id: str, graph: Graph, initial_state: State):
        self.run_id = run_id
        self.graph_id = graph.graph_id
        self.current_node: Optional[str] = graph.start_node
        self.state: State = dict(initial_state)
        self.log: List[LogEntry] = []
        self.status: str = "running"

# Engine Helpers
MAX_STEPS_PER_RUN = 100


def eval_condition(left: Any, operator: str, right: Any) -> bool:
    if operator == "eq":
        return left == right
    if operator == "ne":
        return left != right
    if operator == "gt":
        return left > right
    if operator == "ge":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "le":
        return left <= right
    raise ValueError(f"Unsupported operator: {operator}")

# Public Engine Functions

def create_graph(req: GraphCreateRequest) -> str:
    """Creating and storing a graph, and returning its id."""
    nodes_dict: Dict[str, NodeConfig] = {}
    for n in req.nodes:
        if n.name in nodes_dict:
            raise ValueError(f"Duplicate node name: {n.name}")
        nodes_dict[n.name] = n

    edges_dict: Dict[str, EdgeConfig] = {}
    for e in req.edges:
        if e.source in edges_dict:
            raise ValueError(f"Duplicate edge from node: {e.source}")
        edges_dict[e.source] = e

    if req.start_node not in nodes_dict:
        raise ValueError("start_node not present in nodes list")

    graph_id = str(uuid.uuid4())
    graph = Graph(graph_id, req.start_node, nodes_dict, edges_dict)
    graphs[graph_id] = graph
    return graph_id


def run_graph(graph_id: str, initial_state: State) -> Run:
    """Running a stored graph end-to-end and returning the Run object."""
    graph = graphs.get(graph_id)
    if graph is None:
        raise KeyError(f"Graph '{graph_id}' not found")

    run_id = str(uuid.uuid4())
    run = Run(run_id, graph, initial_state)

    step = 0
    node_name = run.current_node

    while node_name is not None and step < MAX_STEPS_PER_RUN:
        step += 1

        if node_name not in graph.nodes:
            raise RuntimeError(f"Node '{node_name}' not found in graph")

        node_cfg = graph.nodes[node_name]
        tool_name = node_cfg.tool

        if tool_name not in tool_registry:
            raise RuntimeError(f"Tool '{tool_name}' not registered")

        tool_fn = tool_registry[tool_name]

        state_before = dict(run.state)
        new_state = tool_fn(dict(run.state))

        if not isinstance(new_state, dict):
            raise RuntimeError(f"Tool '{tool_name}' must return a dict-like state")

        run.state = new_state

        run.log.append(
            LogEntry(
                step=step,
                node=node_name,
                tool=tool_name,
                state_before=state_before,
                state_after=new_state,
            )
        )

        # Deciding next node (with optional branching)
        edge = graph.edges.get(node_name)
        if edge is None:
            node_name = None
        else:
            if edge.branch is not None:
                cond_val = run.state.get(edge.branch.condition_key)
                result = eval_condition(cond_val, edge.branch.operator, edge.branch.value)
                node_name = edge.branch.true_next if result else edge.branch.false_next
            else:
                node_name = edge.next

        run.current_node = node_name

    run.status = "completed"
    runs[run.run_id] = run
    return run


def get_run(run_id: str) -> Optional[Run]:
    return runs.get(run_id)
