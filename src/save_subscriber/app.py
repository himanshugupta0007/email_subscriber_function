import base64
import json
import logging
import os
import re
from datetime import datetime, timezone
from email.utils import parseaddr

import boto3
from botocore.exceptions import ClientError

APPLICATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")

TABLE_NAME = os.environ["TABLE_NAME"]
TOPIC_ARN = os.environ["TOPIC_ARN"]
CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "*")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")
table = dynamodb.Table(TABLE_NAME)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
            "Access-Control-Allow-Headers": "content-type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
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


def _is_valid_email(email):
    _, parsed = parseaddr(email or "")
    return bool(parsed and "@" in parsed and "." in parsed.split("@")[-1])


def _is_valid_application(application):
    return bool(APPLICATION_PATTERN.match(application or ""))


def _parse_json_body(event):
    raw_body = event.get("body") or "{}"

    if event.get("isBase64Encoded"):
        try:
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        except Exception:
            raise ValueError("Invalid base64 body")

    if len(raw_body) > 4096:
        raise ValueError("Request body too large")

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON body") from exc


def lambda_handler(event, context):
    method = _http_method(event)

    if method == "OPTIONS":
        return _response(200, {"message": "ok"})

    if method != "POST":
        return _response(405, {"message": "Method not allowed"})

    try:
        body = _parse_json_body(event)
    except ValueError as error:
        return _response(400, {"message": str(error)})

    application = (body.get("application") or "").strip()
    email = (body.get("email") or "").strip().lower()
    name = (body.get("name") or "").strip()
    source = (body.get("source") or "landing-page").strip()

    if not _is_valid_application(application):
        return _response(400, {"message": "A valid application is required"})

    if not _is_valid_email(email):
        return _response(400, {"message": "A valid email is required"})

    if name and len(name) > 120:
        return _response(400, {"message": "Name is too long"})

    if source and len(source) > 80:
        return _response(400, {"message": "Source is too long"})

    key = {"application": application, "email": email}

    existing = table.get_item(Key=key, ProjectionExpression="email")
    if "Item" in existing:
        logger.info("Email already subscribed: %s (%s)", email, application)
        return _response(200, {"message": "Email Subscribed Successfully"})

    item = {
        "application": application,
        "email": email,
        "name": name,
        "source": source,
        "subscribedAt": datetime.now(timezone.utc).isoformat(),
    }

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(email)",
        )
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            logger.info("Email already subscribed (race-safe check): %s (%s)", email, application)
            return _response(200, {"message": "Email already subscribed"})
        return _response(500, {"message": "Failed to save subscriber"})

    try:
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject="New {} subscriber".format(application),
            Message="New subscriber for {}: {} <{}> from {}".format(
                application, name or "N/A", email, source
            ),
        )
    except Exception:
        # Persisted successfully; notification failure should not rollback subscription.
        pass

    return _response(201, {"message": "Email Subscribed Successfully", "subscriber": item})
