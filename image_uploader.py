import boto3
from botocore.exceptions import ClientError

# Initialize S3 client
print("Initializing S3 client...")
s3_client = boto3.client('s3')

bucket_name = 'image-processing-demo-hassan'

def upload_file(file_name, key_name):
    print(f"Starting upload: {file_name} → s3://{bucket_name}/{key_name}")
    try:
        s3_client.upload_file(
            Filename=file_name,
            Bucket=bucket_name,
            Key=key_name,
            ExtraArgs={'StorageClass': 'STANDARD'}  # Free tier eligible
        )
        print(f"✅ Successfully uploaded: {key_name}")
    except FileNotFoundError:
        print(f"❌ ERROR: File {file_name} not found.")
    except ClientError as e:
        print(f"❌ AWS Error uploading {file_name}: {e}")

print("Uploading files to S3...")
upload_file('images/images2.jpeg', 'photo3.jpg')
# upload_file('ferrari-188954_1920.jpg', 'photo2.jpg')

print("All uploads attempted.")
