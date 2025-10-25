""" from config.aws_config import s3_client, S3_BUCKET_NAME
import uuid

def upload_invoice_to_s3(file_content, file_name):
   
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

def upload_profile_photo_to_s3(file_content, file_name):
   
    try:
        unique_name = f"profile-photos/{uuid.uuid4()}_{file_name}"
        
        # Determine content type based on file extension
        content_type = 'image/jpeg'
        if file_name.lower().endswith('.png'):
            content_type = 'image/png'
        elif file_name.lower().endswith('.gif'):
            content_type = 'image/gif'
        elif file_name.lower().endswith('.webp'):
            content_type = 'image/webp'
        
    except Exception as e:
        print(f"profile photo error: {str(e)}")
        raise Exception(f"Failed to upload profile photo: {str(e)}") """



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
        
        print(f"✅ Invoice uploaded successfully: {unique_name}")
        return presigned_url
        
    except Exception as e:
        print(f"❌ S3 Invoice Upload Error: {str(e)}")
        raise Exception(f"Failed to upload invoice to S3: {str(e)}")

def upload_profile_photo_to_s3(file_content, file_name):
    """
    Upload profile photo to S3 and return presigned URL
    
    Args:
        file_content: Binary content of the image file
        file_name: Original filename with extension
    
    Returns:
        str: Presigned URL for the uploaded photo (valid for 1 year)
    """
    try:
        # Generate unique filename in profile-photos folder
        unique_name = f"profile-photos/{uuid.uuid4()}_{file_name}"
        
        # Determine content type based on file extension
        content_type = 'image/jpeg'  # default
        file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        content_type = content_type_map.get(file_ext, 'image/jpeg')
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=unique_name,
            Body=file_content,
            ContentType=content_type,
            # Make it accessible for longer period
            CacheControl='max-age=31536000'  # 1 year cache
        )
        
        # Generate long-lived presigned URL (1 year = 31536000 seconds)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': unique_name},
            ExpiresIn=31536000  # 1 year
        )
        
        print(f"✅ Profile photo uploaded successfully: {unique_name}")
        return presigned_url
        
    except Exception as e:
        print(f"❌ Profile Photo Upload Error: {str(e)}")
        raise Exception(f"Failed to upload profile photo: {str(e)}")

def delete_file_from_s3(file_url):
    """
    Delete file from S3 bucket (works for both invoices and photos)
    
    Args:
        file_url: The presigned URL or S3 key to delete
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract key from URL if it's a full URL
        if file_url.startswith('https://'):
            # Extract key from presigned URL (part between .com/ and ?)
            key = file_url.split('.com/')[1].split('?')[0]
        else:
            # Assume it's already a key
            key = file_url
        
        # Delete from S3
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
        print(f"✅ File deleted successfully: {key}")
        return True
        
    except Exception as e:
        print(f"❌ S3 Delete Error: {str(e)}")
        return False

def generate_new_presigned_url(s3_key, expires_in=604800):
    """
    Generate a new presigned URL for an existing S3 object
    
    Args:
        s3_key: The S3 key of the object (e.g., 'invoices/file.pdf')
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
        print(f"✅ New presigned URL generated for: {s3_key}")
        return presigned_url
        
    except Exception as e:
        print(f"❌ Presigned URL generation error: {str(e)}")
        raise Exception(f"Failed to generate presigned URL: {str(e)}")

def get_file_info(file_url):
    """
    Get information about a file in S3
    
    Args:
        file_url: The presigned URL or S3 key
    
    Returns:
        dict: File metadata or None if not found
    """
    try:
        # Extract key from URL
        if file_url.startswith('https://'):
            key = file_url.split('.com/')[1].split('?')[0]
        else:
            key = file_url
        
        # Get object metadata
        response = s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=key)
        
        return {
            'key': key,
            'size': response['ContentLength'],
            'content_type': response['ContentType'],
            'last_modified': response['LastModified'],
            'exists': True
        }
        
    except s3_client.exceptions.NoSuchKey:
        return {'exists': False, 'error': 'File not found'}
    except Exception as e:
        print(f"❌ Error getting file info: {str(e)}")
        return {'exists': False, 'error': str(e)}