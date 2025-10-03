""" import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# Test AWS connection
try:
    s3_client = boto3.client(
        's3',
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    
    bucket_name = os.getenv("S3_BUCKET_NAME")
    
    # Test bucket access
    response = s3_client.head_bucket(Bucket=bucket_name)
    print(f"✅ Bucket {bucket_name} is accessible")
    
    # Test creating a presigned URL for a test object
    test_url = s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': bucket_name, 'Key': 'test.txt'},
        ExpiresIn=3600
    )
    print(f"✅ Presigned URL generation works")
    
except Exception as e:
    print(f"❌ AWS Error: {str(e)}") """

from services.aws_service import upload_invoice_to_s3

if __name__ == "__main__":
    test_file = "test_invoice.pdf"
    with open(test_file, "rb") as f:
        content = f.read()

    url = upload_invoice_to_s3(content, test_file)
    print("✅ Presigned URL:", url)

