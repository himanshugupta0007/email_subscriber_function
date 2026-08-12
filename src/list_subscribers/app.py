import json
import os

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ["TABLE_NAME"]
CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "*")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
            "Access-Control-Allow-Headers": "content-type",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
        },
        "body": json.dumps(body),
    }


def _http_method(event):
    request_context = event.get("requestContext", {})
    return (
        (request_context.get("http", {}) or {}).get("method")
        or event.get("httpMethod")
        or ""
    ).upper()


def lambda_handler(event, context):
    method = _http_method(event)

    if method == "OPTIONS":
        return _response(200, {"message": "ok"})

    if method != "GET":
        return _response(405, {"message": "Method not allowed"})

    query_params = event.get("queryStringParameters") or {}
    application = (query_params.get("application") or "").strip()

    if not application:
        return _response(400, {"message": "An application query parameter is required"})

    result = table.query(KeyConditionExpression=Key("application").eq(application))
    items = result.get("Items", [])

    while "LastEvaluatedKey" in result:
        result = table.query(
            KeyConditionExpression=Key("application").eq(application),
            ExclusiveStartKey=result["LastEvaluatedKey"],
        )
        items.extend(result.get("Items", []))

    items.sort(key=lambda x: x.get("subscribedAt", ""), reverse=True)

    return _response(
        200,
        {
            "application": application,
            "count": len(items),
            "subscribers": items,
        },
    )
