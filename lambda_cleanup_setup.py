import boto3
import json
import os
import zipfile
from botocore.exceptions import ClientError
import time

ROLE_NAME = "lambda-cleanup-role"
FUNCTION_NAME = "cleanup-bucket-fn"
POLICY_NAME = "cleanup-policy"
BUCKET_NAME = "image-processing-demo-hassan"
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]

iam_client = boto3.client("iam")
lambda_client = boto3.client("lambda")
events_client = boto3.client("events")

# 1. Check/create IAM role
try:
    role = iam_client.get_role(RoleName=ROLE_NAME)
    print(f"Role already exists: {role['Role']['Arn']}")
except ClientError as e:
    if e.response["Error"]["Code"] == "NoSuchEntity":
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        role = iam_client.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        print(f"Created role: {role['Role']['Arn']}")
        print("Waiting for IAM role propagation...")
        time.sleep(15)  # wait 15 seconds
    else:
        raise

# 2. Check/create inline policy
try:
    policies = iam_client.list_role_policies(RoleName=ROLE_NAME)["PolicyNames"]
    if POLICY_NAME in policies:
        print(f"Policy '{POLICY_NAME}' already exists.")
    else:
        policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:ListBucket"],
                    "Resource": [f"arn:aws:s3:::{BUCKET_NAME}"]
                },
                {
                    "Effect": "Allow",
                    "Action": ["s3:DeleteObject"],
                    "Resource": [f"arn:aws:s3:::{BUCKET_NAME}/*"]
                },
                {
                    "Effect": "Allow",
                    "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                    "Resource": "arn:aws:logs:*:*:*"
                }
            ]
        }
        iam_client.put_role_policy(
            RoleName=ROLE_NAME,
            PolicyName=POLICY_NAME,
            PolicyDocument=json.dumps(policy_doc)
        )
        print(f"Attached policy '{POLICY_NAME}' to role.")
except ClientError as e:
    raise

# 3. Package Lambda function
zip_filename = "cleanup_function.zip"
with zipfile.ZipFile(zip_filename, "w") as z:
    z.write("delete_bucket.py")

# 4. Create Lambda function
try:
    lambda_client.get_function(FunctionName=FUNCTION_NAME)
    print(f"Lambda function '{FUNCTION_NAME}' already exists.")
except ClientError as e:
    if e.response["Error"]["Code"] == "ResourceNotFoundException":
        lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime="python3.12",
            Role=f"arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}",
            Handler="delete_bucket.lambda_handler",
            Code={"ZipFile": open(zip_filename, "rb").read()},
            Timeout=30,
            MemorySize=128
        )
        print(f"Created Lambda function '{FUNCTION_NAME}'.")
    else:
        raise

# 5. Create EventBridge cron job (runs every day at 21:30 UTC)
rule_name = "cleanup-bucket-daily"
schedule_expression = "cron(30 21 * * ? *)"  # 21:30 UTC daily = 2:30 AM
rule = events_client.put_rule(
    Name=rule_name,
    ScheduleExpression=schedule_expression,
    State="ENABLED"
)
print(f"Created EventBridge rule '{rule_name}' with schedule {schedule_expression}.")

# 6. Give EventBridge permission to invoke Lambda
lambda_client.add_permission(
    FunctionName=FUNCTION_NAME,
    StatementId="eventbridgeinvoke",
    Action="lambda:InvokeFunction",
    Principal="events.amazonaws.com",
    SourceArn=rule["RuleArn"]
)
print("Added EventBridge invoke permission to Lambda.")

# 7. Link rule to Lambda target
events_client.put_targets(
    Rule=rule_name,
    Targets=[{"Id": "1", "Arn": f"arn:aws:lambda:us-east-1:{ACCOUNT_ID}:function:{FUNCTION_NAME}"}]
)
print(f"Linked EventBridge rule '{rule_name}' to Lambda '{FUNCTION_NAME}'.")
