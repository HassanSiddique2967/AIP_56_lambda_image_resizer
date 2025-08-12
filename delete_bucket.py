import boto3

s3 = boto3.client('s3')
BUCKET_NAME = "image-processing-demo-hassan"

def lambda_handler(event, context):
    # List all objects in the bucket
    objects = s3.list_objects_v2(Bucket=BUCKET_NAME)

    if "Contents" in objects:
        keys = [{"Key": obj["Key"]} for obj in objects["Contents"]]
        s3.delete_objects(Bucket=BUCKET_NAME, Delete={"Objects": keys})

    else:
        return {"status": "Bucket is already empty"}

    return {"status": "Bucket emptied successfully"}
