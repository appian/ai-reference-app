import boto3
import json

s3_client = boto3.client('s3')
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

def lambda_handler(event, context):
    try:
        # Extract bucket name and object keys from the event
        bucket = event['s3']['bucket']['name']
        keys = event['s3']['object']['keys']  # Now matches the API Gateway mapping
        
        # Ensure keys is always a list and remove any empty strings
        if not isinstance(keys, list):
            keys = [keys]
        keys = [key for key in keys if key.strip()]  # Remove empty or whitespace-only keys
        
        if not keys:
            return {
                'statusCode': 400,
                'body': json.dumps('No valid image keys provided')
            }
        
        # Download all image files from S3
        images = []
        for key in keys:
            try:
                image_object = s3_client.get_object(Bucket=bucket, Key=key)
                image = image_object['Body'].read()
                images.append({
                    "image": {
                        "format": key.split('.')[-1],
                        "source": {"bytes": image}
                    }
                })
            except s3_client.exceptions.NoSuchKey:
                return {
                    'statusCode': 404,
                    'body': json.dumps(f'Image not found: {key}')
                }
        
        user_message = event.get('user_message', '')
        
        if images and user_message:
            messages = [
                {
                    "role": "user",
                    "content": images + [{"text": user_message}],
                }
            ]

            response = bedrock_runtime.converse(
                modelId=MODEL_ID,
                messages=messages,
            )

            response_text = response["output"]["message"]["content"][0]["text"]
            return {
                'statusCode': 200,
                'body': json.dumps(response_text)
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps('Please upload image file(s) and enter a message to proceed.')
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'An error occurred: {str(e)}')
        }