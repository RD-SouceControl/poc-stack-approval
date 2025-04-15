import yaml
import boto3
import ipaddress

dynamodb_table_name = "VpcCidrRegistry"

def extract_template(path):
    with open(path) as f:
        return yaml.safe_load(f)

def fetch_registered_cidrs():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(dynamodb_table_name)
    try:
        response = table.scan()
        return [item["CidrBlock"] for item in response.get("Items", [])]
    except Exception as e:
        print(f"Failed to read DynamoDB table: {e}")
        return []

def cidrs_overlap(cidr1, cidr2):
    try:
        return ipaddress.IPv4Network(cidr1).overlaps(ipaddress.IPv4Network(cidr2))
    except ValueError as e:
        print(f"Invalid CIDR format: {cidr1} or {cidr2}")
        return False

# Load synthesized template (post `cdk synth`)
synth_template = extract_template("template.yaml")
resources_synth = synth_template.get("Resources", {})

# Get existing CIDRs from DynamoDB
cidrs_from_dynamo = fetch_registered_cidrs()

# Output warning summary
with open("networking_table.md", "w") as out:
    out.write("## :warning: CIDR Overlap Check\n")

    if not cidrs_from_dynamo:
        out.write("- No entries found in DynamoDB. CIDR overlap check skipped.\n")
    else:
        cidr_warnings = []
        for logical_id, resource in resources_synth.items():
            if resource["Type"] == "AWS::EC2::VPC":
                cidr = resource.get("Properties", {}).get("CidrBlock")
                if cidr:
                    overlaps = [existing for existing in cidrs_from_dynamo if cidrs_overlap(cidr, existing)]
                    if overlaps:
                        cidr_warnings.append(f"CIDR `{cidr}` for `{logical_id}` overlaps with `{', '.join(overlaps)}`")

        if cidr_warnings:
            for warning in cidr_warnings:
                out.write(f"- **{warning}**\n")
        else:
            out.write("- No overlaps detected\n")
