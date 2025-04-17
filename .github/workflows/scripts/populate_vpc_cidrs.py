import boto3

dynamodb_table_name = "VpcCidrRegistry"

def get_all_vpcs():
    ec2 = boto3.client("ec2")
    paginator = ec2.get_paginator("describe_vpcs")
    for page in paginator.paginate():
        for vpc in page["Vpcs"]:
            cidr_block = vpc.get("CidrBlock")
            vpc_id = vpc.get("VpcId")
            tags = vpc.get("Tags", [])
            vpc_name = next((tag["Value"] for tag in tags if tag["Key"] == "Name"), "Unnamed-VPC")

            yield {
                "VpcId": vpc_id,
                "CidrBlock": cidr_block,
                "VpcName": vpc_name
            }

def populate_dynamodb(vpcs):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(dynamodb_table_name)

    for vpc in vpcs:
        try:
            table.put_item(Item=vpc)
            print(f" Added {vpc['VpcId']} ({vpc['VpcName']}) with CIDR {vpc['CidrBlock']}")
        except Exception as e:
            print(f" Failed to add {vpc['VpcId']}: {e}")

if __name__ == "__main__":
    existing_vpcs = list(get_all_vpcs())
    if not existing_vpcs:
        print("No VPCs found in the account.")
    else:
        populate_dynamodb(existing_vpcs)
