#!/usr/bin/env python3
"""Test RDS database connection using boto3 and psycopg2."""

import json
import os

import boto3
import psycopg2

AWS_PROFILE = os.environ.get("AWS_PROFILE", "norwood")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
RDS_INSTANCE_ID = "norwood-db1"
SECRET_NAME = "rds!db-772d01d0-2a2c-4a0a-b7c3-e24f1c38f0c1"


def get_aws_session():
    """Create boto3 session with profile."""
    return boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)


def get_db_credentials():
    """Get DB credentials from Secrets Manager."""
    session = get_aws_session()
    secrets = session.client("secretsmanager")

    response = secrets.get_secret_value(SecretId=SECRET_NAME)
    secret = json.loads(response["SecretString"])

    print(f"Retrieved credentials for user: {secret['username']}")
    return secret


def get_rds_endpoint():
    """Get RDS instance endpoint using boto3."""
    session = get_aws_session()
    rds = session.client("rds")

    response = rds.describe_db_instances(DBInstanceIdentifier=RDS_INSTANCE_ID)
    instance = response["DBInstances"][0]

    endpoint = instance["Endpoint"]["Address"]
    port = instance["Endpoint"]["Port"]

    print(f"RDS Endpoint: {endpoint}")
    print(f"RDS Port: {port}")
    print(f"DB Engine: {instance['Engine']}")
    print(f"DB Status: {instance['DBInstanceStatus']}")

    return endpoint, port


def test_connection(endpoint: str, port: int, credentials: dict):
    """Test PostgreSQL connection."""
    db_name = os.environ.get("DB_NAME", "postgres")

    try:
        conn = psycopg2.connect(
            host=endpoint,
            port=port,
            user=credentials["username"],
            password=credentials["password"],
            database=db_name,
            connect_timeout=10,
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\nConnected successfully!")
        print(f"PostgreSQL version: {version}")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"\nConnection failed: {e}")
        return False


if __name__ == "__main__":
    print(f"Using AWS Profile: {AWS_PROFILE}")
    print(f"Using AWS Region: {AWS_REGION}")
    print(f"RDS Instance: {RDS_INSTANCE_ID}")
    print(f"Secret: {SECRET_NAME}\n")

    credentials = get_db_credentials()
    endpoint, port = get_rds_endpoint()
    test_connection(endpoint, port, credentials)
