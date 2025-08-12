import boto3
import json
from botocore.exceptions import ClientError


ROLE_NAME = "lambda-resize-role"
FUNCTION_NAME = "resize-images-fn"
POLICY_NAME = "resize-policy"
BUCKET_NAME = "image-processing-demo-hassan"
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]

iam_client = boto3.client("iam")
lambda_client = boto3.client("lambda")

# 1. Check if IAM role exists
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
    else:
        raise

# 2. Check if inline policy exists for the role
try:
    policies = iam_client.list_role_policies(RoleName=ROLE_NAME)["PolicyNames"]
    if POLICY_NAME in policies:
        print(f"Policy '{POLICY_NAME}' already exists on role.")
    else:
        policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:PutObject"],
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

# S3 triggers

# 1. Give Lambda permission to be triggered by S3
lambda_client.add_permission(
    FunctionName=FUNCTION_NAME,
    StatementId="s3invoke",
    Action="lambda:InvokeFunction",
    Principal="s3.amazonaws.com",
    SourceArn=f"arn:aws:s3:::{BUCKET_NAME}"
)
print(f"Added S3 invoke permission to Lambda '{FUNCTION_NAME}'.")

# 2. Configure S3 event to trigger Lambda on object creation
s3_client = boto3.client("s3")

notification_config = {
    "LambdaFunctionConfigurations": [
        {
            "LambdaFunctionArn": f"arn:aws:lambda:us-east-1:{ACCOUNT_ID}:function:{FUNCTION_NAME}",
            "Events": ["s3:ObjectCreated:*"]
        }
    ]
}

s3_client.put_bucket_notification_configuration(
    Bucket=BUCKET_NAME,
    NotificationConfiguration=notification_config
)
print(f"S3 bucket '{BUCKET_NAME}' is now set to trigger Lambda '{FUNCTION_NAME}' on new uploads.")
