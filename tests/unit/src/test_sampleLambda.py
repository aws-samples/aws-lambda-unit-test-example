# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Start of unit test code: tests/unit/src/test_sampleLambda.py

import os
import json
from typing import Any, Dict
from unittest import TestCase
from unittest.mock import MagicMock, patch
import boto3
import moto
from src.sampleLambda.app import LambdaResources
from src.sampleLambda.app import create_letter_in_s3
from src.sampleLambda.app import lambda_handler
from src.sampleLambda import schemas
from aws_lambda_powertools.utilities.validation import validate


# [1] Mock all AWS Services in use
@moto.mock_dynamodb
@moto.mock_s3

class TestSampleLambda(TestCase):

    # Test Set up 
    def setUp(self) -> None:
    
        # [2] Mock environment
        self.test_ddb_table_name = "unit_test_ddb"
        self.test_s3_bucket_name = "unit_test_s3_bucket"
        os.environ["DYNAMODB_TABLE_NAME"] = self.test_ddb_table_name
        os.environ["S3_BUCKET_NAME"] = self.test_s3_bucket_name 
        
        # [3] Set up the services: construct a (mocked!) DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName = self.test_ddb_table_name,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}],
            BillingMode='PAY_PER_REQUEST'
            )
            
        # [3] Set up the services: construct a (mocked!) S3 Bucket table    
        s3_client = boto3.client('s3', region_name="us-east-1")
        s3_client.create_bucket(Bucket = self.test_s3_bucket_name )
        
        # [4] Establish the "GLOBAL" environment for use in tests.
        self.test_LAMBDA_GLOBAL = LambdaResources( initialize_resources = True)


    def test_create_letter_in_s3(self) -> None:

        # [5] Post test items to a mocked database
        self.test_LAMBDA_GLOBAL.ddb_table.put_item(Item={"PK":"D#UnitTestDoc", 
                                                         "data":"Unit Test Doc Corpi"})
        self.test_LAMBDA_GLOBAL.ddb_table.put_item(Item={"PK":"C#UnitTestCust", 
                                                         "data":"Unit Test Customer"})
 
        # [6] Run DynamoDB to S3 file function
        create_letter_in_s3(env = self.test_LAMBDA_GLOBAL, 
                            doc_type = "UnitTestDoc",
                            cust_id = "UnitTestCust"
                            )

        # [7] Ensure the data was written to S3 correctly, with correct contents
        body = self.test_LAMBDA_GLOBAL.s3_bucket.Object("UnitTestCust/UnitTestDoc.txt").get()['Body'].read()
        
        # Test
        self.assertEqual(body.decode('ascii'),"Dear Unit Test Customer;\nUnit Test Doc Corpi")


    # [8] Load and validate test events from the file system
    def load_test_event(self, test_event_file_name: str) ->  Dict[str, Any]:
        with open(f"tests/events/{test_event_file_name}.json") as f:
            event = json.load(f)
            validate(event=event, schema=schemas.INPUT)
            return event

    # [9] Patch the Global Class and any function calls
    @patch("src.sampleLambda.app._LAMBDA_GLOBAL_RESOURCES")
    @patch("src.sampleLambda.app.create_letter_in_s3")
    def test_lambda_handler(self, 
                            mock_create_letter_in_s3 : MagicMock,
                            mock_lambda_global_resources : MagicMock):
                            
        # [10] Test setup - Return a mock for the Global Var LAMBDA_GLOBAL
        mock_lambda_global_resources.return_value = self.test_LAMBDA_GLOBAL
        mock_create_letter_in_s3.return_value = {"statusCode" : 200, "body":"OK"}
        
        # [11] Run Test using a test event from /tests/events/*.json
        test_event = self.load_test_event("sampleEvent1")
        ret_val = lambda_handler(event=test_event, context=None)
        
        # [12] Validate the function was called with the mocked globals
        # and event values
        mock_create_letter_in_s3.assert_called_once_with( env=mock_lambda_global_resources, 
                                        doc_type=test_event["pathParameters"]["docType"],
                                        cust_id=test_event["pathParameters"]["customerId"])

        self.assertEqual(ret_val,mock_create_letter_in_s3.return_value)


    def tearDown(self) -> None:

        # [13] Remove (mocked!) S3 Objects and Bucket
        s3 = boto3.resource("s3",region_name="us-east-1")
        bucket = s3.Bucket( self.test_s3_bucket_name )
        for key in bucket.objects.all():
            key.delete()
        bucket.delete()

        # [14] Remove (mocked!) DynamoDB Table
        dynamodb = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb.delete_table(TableName = self.test_ddb_table_name )

        # [15] Remove the GLOBAL settings
        self.test_LAMBDA_GLOBAL = None
        
# End of unit test code