# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Start of unit test code: tests/unit/src/test_sampleLambda.py
import sys
import os
import json
from typing import Any, Dict
from unittest import TestCase
from unittest.mock import MagicMock, patch
import boto3
import moto
from aws_lambda_powertools.utilities.validation import validate
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent

sys.path.append('./src/sampleLambda')
from src.sampleLambda.app import LambdaDynamoDBClass
from src.sampleLambda.app import LambdaS3Class
from src.sampleLambda.app import create_letter_in_s3
from src.sampleLambda.app import lambda_handler
from src.sampleLambda.schemas import INPUT_SCHEMA


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
        
        # [3a] Set up the services: construct a (mocked!) DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName = self.test_ddb_table_name,
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}],
            BillingMode='PAY_PER_REQUEST'
            )
            
        # [3b] Set up the services: construct a (mocked!) S3 Bucket table    
        s3_client = boto3.client('s3', region_name="us-east-1")
        s3_client.create_bucket(Bucket = self.test_s3_bucket_name )
        
        # [4] Establish the "GLOBAL" environment for use in tests.
        self.test_LAMBDA_DYNAMODB = LambdaDynamoDBClass( initialize_resources = True)
        self.test_LAMBDA_S3 = LambdaS3Class( initialize_resources = True)


    def test_create_letter_in_s3(self) -> None:

        # [5] Post test items to a mocked database
        self.test_LAMBDA_DYNAMODB.table.put_item(Item={"PK":"D#UnitTestDoc", 
                                                        "data":"Unit Test Doc Corpi"})
        self.test_LAMBDA_DYNAMODB.table.put_item(Item={"PK":"C#UnitTestCust", 
                                                        "data":"Unit Test Customer"})
 
        # [6] Run DynamoDB to S3 file function
        return_val = create_letter_in_s3(dynamo_db = self.test_LAMBDA_DYNAMODB, 
                            s3=self.test_LAMBDA_S3,
                            doc_type = "UnitTestDoc",
                            cust_id = "UnitTestCust"
                            )

        # [7] Ensure the data was written to S3 correctly, with correct contents 
        body = self.test_LAMBDA_S3.bucket.Object("UnitTestCust/UnitTestDoc.txt").get()['Body'].read()
        
        # Test
        self.assertEqual(return_val["statusCode"], 200)
        self.assertIn("UnitTestCust/UnitTestDoc.txt", return_val["body"])
        self.assertEqual(body.decode('ascii'),"Dear Unit Test Customer;\nUnit Test Doc Corpi")


    def test_create_letter_in_s3_doc_notfound(self) -> None:

        # [8] Post test items to a mocked database
        self.test_LAMBDA_DYNAMODB.table.put_item(Item={"PK":"D#UnitTestDoc", 
                                                        "data":"Unit Test Doc Corpi"})
        self.test_LAMBDA_DYNAMODB.table.put_item(Item={"PK":"C#UnitTestCust", 
                                                        "data":"Unit Test Customer"})
        
        # [9] Run DynamoDB to S3 file function
        return_val = create_letter_in_s3(dynamo_db = self.test_LAMBDA_DYNAMODB, 
                            s3=self.test_LAMBDA_S3,
                            doc_type = "NOTVALID",
                            cust_id = "UnitTestCust"
                            )                  

        # Test
        self.assertEqual(return_val["statusCode"], 404)
        self.assertIn("NOTFOUND", return_val["body"])

    def test_create_letter_in_s3_user_notfound(self) -> None:

        # [10] Post test items to a mocked database
        self.test_LAMBDA_DYNAMODB.table.put_item(Item={"PK":"D#UnitTestDoc", 
                                                        "data":"Unit Test Doc Corpi"})
        self.test_LAMBDA_DYNAMODB.table.put_item(Item={"PK":"C#UnitTestCust", 
                                                        "data":"Unit Test Customer"})
        
        # [11] Run DynamoDB to S3 file function
        return_val = create_letter_in_s3(dynamo_db = self.test_LAMBDA_DYNAMODB, 
                            s3=self.test_LAMBDA_S3,
                            doc_type = "UnitTestDoc",
                            cust_id = "NOTVALID"
                            )                  

        # Test
        self.assertEqual(return_val["statusCode"], 404)
        self.assertIn("NOTFOUND", return_val["body"])

    # [12] Load and validate test events from the file system
    def load_test_event(self, test_event_file_name: str) ->  dict:
        with open(f"tests/events/{test_event_file_name}.json") as f:
            event = json.load(f)
            validate(event=event, schema=INPUT_SCHEMA)
            return event

    # [13] Patch the Global Class and any function calls
    @patch("src.sampleLambda.app._LAMBDA_DYNAMODB")
    @patch("src.sampleLambda.app._LAMBDA_S3")
    @patch("src.sampleLambda.app.create_letter_in_s3")
    def test_lambda_handler(self, 
                            mock_create_letter_in_s3 : MagicMock,
                            mock_lambda_s3 : MagicMock,
                            mock_lambda_dynamo_db : MagicMock):
                            
        # [14] Test setup - Return a mock for the Global Var LAMBDA_GLOBAL
        mock_lambda_dynamo_db.return_value = self.test_LAMBDA_DYNAMODB
        mock_lambda_s3.return_value = self.test_LAMBDA_S3
        mock_create_letter_in_s3.return_value = {"statusCode" : 200, "body":"OK"}
        
        # [15] Run Test using a test event from /tests/events/*.json
        test_event = self.load_test_event("sampleEvent1")
        ret_val = lambda_handler(event=test_event, context=None)
        
        # [16] Validate the function was called with the mocked globals
        # and event values
        mock_create_letter_in_s3.assert_called_once_with( dynamo_db=mock_lambda_dynamo_db, 
                                        s3=mock_lambda_s3,
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