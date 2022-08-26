# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Start of lambda handler code:  src/sampleLambda/app.py
import os
from typing import Any, Dict
import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.validation import validator

# [1] Accomodate local imports during production or test
try:
  import schemas
except:
  from src.sampleLambda import schemas

# [2] Define a LambdaResources class for Environment Vaiables and AWS Resource
# connections.  Make initializing the resources optional for testing.
class LambdaResources:
   def __init__(self, initialize_resources: bool  ):
      
      if initialize_resources:
        # Initialize a DynamoDB Resource
        self.ddb_table_name = os.environ["DYNAMODB_TABLE_NAME"]
        self.ddb_resource = boto3.resource('dynamodb')
        self.ddb_table = self.ddb_resource.Table(self.ddb_table_name)

        # Initialize an S3 Resource
        self.s3_bucket_name = os.environ["S3_BUCKET_NAME"]
        self.s3_resource = boto3.resource('s3')
        self.s3_bucket = self.s3_resource.Bucket(self.s3_bucket_name)


# [3] Globally scoped resources: created only if running in a Lambda runtime
_LAMBDA_GLOBAL_RESOURCES = LambdaResources(initialize_resources = 
                              os.getenv("AWS_LAMBDA_FUNCTION_NAME", None) != None
                            )

# [4] Validate the event schema and return schema using Lambda Power Tools
@validator(inbound_schema=schemas.INPUT, outbound_schema=schemas.OUTPUT)
def lambda_handler(event:  Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:

    # [5] Use the Global variable
    global _LAMBDA_GLOBAL_RESOURCES
      
    # [6] Explicitly pass the global to subsequent functions
    return create_letter_in_s3(env = _LAMBDA_GLOBAL_RESOURCES, 
                            doc_type = event["pathParameters"]["docType"], 
                            cust_id = event["pathParameters"]["customerId"])    

def create_letter_in_s3( env: LambdaResources, 
                         doc_type: str,
                         cust_id: str) -> dict:
                           
  # [7] Use the passed environment class for AWS resource access - DynamoDB
  cust_name = env.ddb_table.get_item(Key={"PK": f"C#{cust_id}"})["Item"]["data"]
  doc_text = env.ddb_table.get_item(Key={"PK": f"D#{doc_type}"})["Item"]["data"]

  # [8] Use the passed environment class for AWS resource access - S3
  s3_file_key = f"{cust_id}/{doc_type}.txt"                                                               
  s3_return = env.s3_bucket.put_object(Key=s3_file_key, 
                             Body=f"Dear {cust_name};\n{doc_text}".encode('utf-8'),
                             ServerSideEncryption='AES256')

  return {"statusCode": 200, "body" : f"OK {s3_file_key}" }

# End of lambda handler code