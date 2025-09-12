import json
import logging
import asyncio

import azure.functions as func
import azure.durable_functions as df

from src.run_ingestion import main

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="adxingestor/start_orchestrator")
@app.durable_client_input(client_name="client")
async def adxingestor(req: func.HttpRequest, client) -> func.HttpResponse:
    logging.info("[INFO] --> Python HTTP trigger function processed a request.")

    instance_id = await client.start_new("start_orchestrator", client_input=None)

    logging.info(f"[INFO] --> Started orchestration with ID = '{instance_id}'.")
    
    return client.create_check_status_response(req, instance_id)

@app.orchestration_trigger(context_name="context")
def start_orchestrator(context: df.DurableOrchestrationContext):
    logging.info("[INFO] --> Started orchestration")

    result = yield context.call_activity("start_ingestion", None)

    return result

@app.activity_trigger(input_name="payload")
def start_ingestion(payload: str) -> str:
    logging.info("[INFO] --> Started ingestion activity")

    asyncio.run(main())

@app.route(route="status/{instanceId}")
@app.durable_client_input(client_name="client")
async def get_status(req: func.HttpRequest, client) -> func.HttpResponse:
    instance_id = req.route_params.get('instanceId')
    
    status = await client.get_status(instance_id)
    
    if status is None:
        return func.HttpResponse(
            json.dumps({"error": "Instance not found"}),
            status_code=404,
            mimetype="application/json"
        )
    
    return func.HttpResponse(
        json.dumps({
            "instanceId": status.instance_id,
            "runtimeStatus": status.runtime_status.name,
            "input": status.input_,
            "output": status.output,
            "createdTime": status.created_time.isoformat() if status.created_time else None,
            "lastUpdatedTime": status.last_updated_time.isoformat() if status.last_updated_time else None
        }, default=str),
        mimetype="application/json"
    )

@app.route(route="terminate/{instanceId}")
@app.durable_client_input(client_name="client")
async def terminate_orchestration(req: func.HttpRequest, client) -> func.HttpResponse:
    instance_id = req.route_params.get('instanceId')
    reason = req.params.get('reason', 'Terminated via HTTP request')
    
    await client.terminate(instance_id, reason)
    
    return func.HttpResponse(
        json.dumps({"message": f"Orchestration {instance_id} terminated", "reason": reason}),
        mimetype="application/json"
    )
