from fastapi import FastAPI, HTTPException

from engine import (
    GraphCreateRequest,
    GraphCreateResponse,
    GraphRunRequest,
    GraphRunResponse,
    RunStateResponse,
    create_graph,
    run_graph,
    get_run,
)
import tools  # Ensures tools are registered


app = FastAPI(title="Mini Agent Workflow Engine")

# Endpoints
@app.post("/graph/create", response_model=GraphCreateResponse)
def create_graph_endpoint(req: GraphCreateRequest):
    try:
        graph_id = create_graph(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return GraphCreateResponse(graph_id=graph_id)


@app.post("/graph/run", response_model=GraphRunResponse)
def run_graph_endpoint(req: GraphRunRequest):
    try:
        run = run_graph(req.graph_id, req.initial_state)
    except KeyError as e:
        # graph not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # execution error
        raise HTTPException(status_code=500, detail=str(e))

    return GraphRunResponse(
        run_id=run.run_id,
        final_state=run.state,
        log=run.log,
    )

@app.get("/graph/state/{run_id}", response_model=RunStateResponse)
def get_run_state_endpoint(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunStateResponse(
        run_id=run.run_id,
        graph_id=run.graph_id,
        status=run.status,
        current_node=run.current_node,
        state=run.state,
        log=run.log,
    )
