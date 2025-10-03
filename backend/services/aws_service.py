from config.aws_config import s3_client, S3_BUCKET_NAME
import uuid

def upload_invoice_to_s3(file_content, file_name):
    """
    Upload invoice file to S3 bucket and return presigned URL for secure access
    
    Args:
        file_content: Binary content of the file
        file_name: Original filename
    
    Returns:
        str: Presigned URL for secure file access (valid for 7 days)
    """
    try:
        # Generate unique filename
        unique_name = f"invoices/{uuid.uuid4()}_{file_name}"
        
        # Upload file to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=unique_name,
            Body=file_content,
            ContentType="application/pdf"
        )
        
        # Generate presigned URL for secure access (valid for 7 days)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': unique_name},
            ExpiresIn=604800  # 7 days in seconds
        )
        
        print(f"File uploaded successfully: {unique_name}")
        return presigned_url
        
    except Exception as e:
        print(f"S3 Upload Error: {str(e)}")
        raise Exception(f"Failed to upload to S3: {str(e)}")

def delete_invoice_from_s3(file_url):
    """
    Delete invoice file from S3 bucket
    
    Args:
        file_url: The presigned URL or S3 key to delete
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract key from URL if it's a full URL
        if file_url.startswith('https://'):
            # Extract key from presigned URL
            key = file_url.split('.com/')[1].split('?')[0]
        else:
            # Assume it's already a key
            key = file_url
        
        # Delete from S3
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
        print(f"File deleted successfully: {key}")
        return True
        
    except Exception as e:
        print(f"S3 Delete Error: {str(e)}")
        return False

def generate_new_presigned_url(s3_key, expires_in=604800):
    """
    Generate a new presigned URL for an existing S3 object
    
    Args:
        s3_key: The S3 key of the object
        expires_in: URL expiration time in seconds (default 7 days)
    
    Returns:
        str: New presigned URL
    """
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=expires_in
        )
        return presigned_url
    except Exception as e:
        print(f"Presigned URL generation error: {str(e)}")
        raise Exception(f"Failed to generate presigned URL: {str(e)}")