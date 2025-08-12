import boto3
from PIL import Image
import os
import tempfile

s3 = boto3.client('s3')

def lambda_handler(event, context):
    # Extract bucket and object key from event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Skip if this is already in the 'resized/' folder
    if key.startswith("resized/"):
        return {"status": "skipped"}

    # Download file to temp location
    tmp_download = os.path.join(tempfile.gettempdir(), os.path.basename(key))
    s3.download_file(bucket, key, tmp_download)

    # Resize image
    img = Image.open(tmp_download)
    img = img.resize((300, 300))  # example size
    tmp_resized = os.path.join(tempfile.gettempdir(), f"resized-{os.path.basename(key)}")
    img.save(tmp_resized)

    # Upload resized image
    s3.upload_file(tmp_resized, bucket, f"resized/{os.path.basename(key)}")

    return {"status": "success", "resized_key": f"resized/{os.path.basename(key)}"}
