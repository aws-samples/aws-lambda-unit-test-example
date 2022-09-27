# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Start of lambda handler code:  src/sampleLambda/app.py
from os import environ, getenv
from typing import Any, Dict
from boto3 import resource
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.validation import validator


# [1] Import the schema for the Lambda Powertools Validator
from schemas import INPUT_SCHEMA, OUTPUT_SCHEMA

# [2] Define a LambdaResources class for Environment Vaiables and AWS Resource
# connections.  Make initializing the resources optional for testing.
class LambdaDynamoDBClass:
    def __init__(self, initialize_resources: bool ):
        if initialize_resources:
            # Initialize a DynamoDB Resource
            self.table_name = environ["DYNAMODB_TABLE_NAME"]
            self.resource = resource('dynamodb')
            self.table = self.resource.Table(self.table_name)

class LambdaS3Class:
    def __init__(self, initialize_resources: bool ):
        if initialize_resources:
            # Initialize an S3 Resource
            self.bucket_name = environ["S3_BUCKET_NAME"]
            self.resource = resource('s3')
            self.bucket = self.resource.Bucket(self.bucket_name)


# [3] Globally scoped resources: created only if running in a Lambda runtime
_LAMBDA_DYNAMODB = LambdaDynamoDBClass(initialize_resources = 
                          getenv("LAMBDA_TASK_ROOT", None) != None
                          )
_LAMBDA_S3 = LambdaS3Class(initialize_resources = 
                          getenv("LAMBDA_TASK_ROOT", None) != None
                          )

# [4] Validate the event schema and return schema using Lambda Power Tools
@validator(inbound_schema=INPUT_SCHEMA, outbound_schema=OUTPUT_SCHEMA)
def lambda_handler(event: APIGatewayProxyEvent, context: LambdaContext) -> Dict[str, Any]:

    # [5] Use the Global variable
    global _LAMBDA_DYNAMODB
    global _LAMBDA_S3
 
    # [6] Explicitly pass the global to subsequent functions
    return create_letter_in_s3(dynamo_db = _LAMBDA_DYNAMODB,
                            s3 = _LAMBDA_S3,
                            doc_type = event["pathParameters"]["docType"],
                            cust_id = event["pathParameters"]["customerId"])

def create_letter_in_s3( dynamo_db: LambdaDynamoDBClass,
                         s3: LambdaS3Class,
                         doc_type: str,
                         cust_id: str) -> dict:
                  
    # [7] Use the passed environment class for AWS resource access - DynamoDB
    cust_name = dynamo_db.table.get_item(Key={"PK": f"C#{cust_id}"})["Item"]["data"]
    doc_text = dynamo_db.table.get_item(Key={"PK": f"D#{doc_type}"})["Item"]["data"]

    # [8] Use the passed environment class for AWS resource access - S3
    s3_file_key = f"{cust_id}/{doc_type}.txt"
    s3.bucket.put_object(Key=s3_file_key, 
                       Body=f"Dear {cust_name};\n{doc_text}".encode('utf-8'),
                       ServerSideEncryption='AES256')

    return {"statusCode": 200, "body" : f"OK {s3_file_key}" }

# End of lambda handler code