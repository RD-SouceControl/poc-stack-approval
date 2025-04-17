import yaml
import boto3
import ipaddress

AZ_INDEX_MAPPING = {
    0: "us-east-1a",
    1: "us-east-1b",
    2: "us-east-1c",
    3: "us-east-1d",
    4: "us-east-1e",
    5: "us-east-1f"
}

dynamodb_table_name = "VpcCidrRegistry"

def fetch_registered_vpcs():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(dynamodb_table_name)
    try:
        response = table.scan()
        return response.get("Items", [])
    except Exception as e:
        print(f"Failed to read DynamoDB table: {e}")
        return []

def cidrs_overlap(cidr1, cidr2):
    try:
        return ipaddress.IPv4Network(cidr1).overlaps(ipaddress.IPv4Network(cidr2))
    except ValueError as e:
        print(f"Invalid CIDR format: {cidr1} or {cidr2}")
        return False

def format_security_rule(rule):
    ip_protocol = rule.get("IpProtocol", "ALL")
    from_port = rule.get("FromPort", "")
    to_port = rule.get("ToPort", "")
    cidr = rule.get("CidrIp", rule.get("CidrIpv6", ""))
    source_sg = rule.get("SourceSecurityGroupId", "")
    
    if ip_protocol == "-1":
        proto = "ALL"
    else:
        if from_port == to_port or to_port == "":
            proto = f"{ip_protocol.upper()} {from_port}"
        else:
            proto = f"{ip_protocol.upper()} {from_port}-{to_port}"
    
    if cidr:
        return f"{proto} from {cidr}"
    elif source_sg:
        return f"{proto} from {source_sg}"
    return proto

def format_value(val):
    if isinstance(val, dict):
        if "Fn::Select" in val:
            index = val["Fn::Select"][0]
            if isinstance(index, str):
                index = int(index)
            az = AZ_INDEX_MAPPING.get(index, f"AZ-{index}")
            return f"AvailabilityZone: {az}"
        if "Ref" in val:
            return f"Ref: {val['Ref']}"
        return ", ".join(f"{k}: {format_value(v)}" for k, v in val.items())
    
    elif isinstance(val, list):
        if all(isinstance(item, dict) and "Key" in item and "Value" in item for item in val):
            tags = {tag["Key"]: tag["Value"] for tag in val}
            return f"Tags: {tags}"
        if all(isinstance(item, dict) and "IpProtocol" in item for item in val):
            return "[" + "; ".join(format_security_rule(rule) for rule in val) + "]"
        return f"{len(val)} items"

    return str(val)

def extract_template(file_path):
    with open(file_path, "r") as f:
        content = f.read()
        if not content.strip():
            raise ValueError(f"{file_path} is empty.")
        return yaml.safe_load(content)

def extract_key_props(resource):
    props = resource.get("Properties", {})
    return {k: format_value(v) for k, v in props.items()}

def get_resource_name(resource, logical_id):
    tags = resource.get("Properties", {}).get("Tags", [])
    for tag in tags:
        if tag.get("Key") == "Name":
            return tag.get("Value", logical_id)
    return logical_id

synth_template = extract_template("template.yaml")
deployed_template = extract_template("deployed-template.yaml")

synth_resources = synth_template.get("Resources", {})
deployed_resources = deployed_template.get("Resources", {})

with open("networking_table.md", "w") as out:
    out.write("## :warning: CIDR Overlap Check\n")

    vpcs_from_dynamo = fetch_registered_vpcs()
    if not vpcs_from_dynamo:
        out.write("- No entries found in DynamoDB. CIDR overlap check skipped.\n")
    else:
        cidr_warnings = []

        for logical_id, resource in synth_resources.items():
            if resource.get("Type") != "AWS::EC2::VPC":
                continue

            cidr = resource.get("Properties", {}).get("CidrBlock")
            if not cidr:
                continue

            deployed_cidr = deployed_resources.get(logical_id, {}).get("Properties", {}).get("CidrBlock")

            is_new_or_modified = deployed_cidr != cidr
            if not is_new_or_modified:
                continue  # Skip if there's no change to this VPC

            synth_vpc_name = get_resource_name(resource, logical_id)
            for vpc_entry in vpcs_from_dynamo:
                existing_cidr = vpc_entry.get("CidrBlock")
                existing_vpc_name = vpc_entry.get("VpcName", "Unknown")
                existing_vpc_id = vpc_entry.get("VpcId", "Unknown")

                if cidrs_overlap(cidr, existing_cidr):
                    cidr_warnings.append(
                        f"CIDR `{cidr}` for `{synth_vpc_name}` (Logical ID: `{logical_id}`) "
                        f"overlaps with `{existing_cidr}` used by `{existing_vpc_name}` (VPC ID: `{existing_vpc_id}`)"
                    )

        if cidr_warnings:
            for warning in cidr_warnings:
                out.write(f"- **{warning}**\n")
        else:
            out.write("- No overlaps detected\n")

    out.write("\n## Networking Resource Comparison\n")
    out.write("| Resource Name | Resource Type | Future State | Current State |\n")
    out.write("|------------|----------------|-------------------------|----------------------|\n")

    networking_types = {
        "AWS::EC2::VPC",
        "AWS::EC2::Subnet",
        "AWS::EC2::InternetGateway",
        "AWS::EC2::VPCGatewayAttachment",
        "AWS::EC2::RouteTable",
        "AWS::EC2::Route",
        "AWS::EC2::SecurityGroup"
    }

    for logical_id, resource in synth_resources.items():
        r_type = resource.get("Type")
        if r_type not in networking_types:
            continue

        synth_props = extract_key_props(resource)
        deployed_props = extract_key_props(deployed_resources.get(logical_id, {})) if logical_id in deployed_resources else {}

        synth_lines = []
        deployed_lines = []

        all_keys = set(synth_props.keys()).union(set(deployed_props.keys()))

        for key in sorted(all_keys):
            synth_val = synth_props.get(key, "(Missing)")
            deployed_val = deployed_props.get(key, "(Missing)")

            is_changed = synth_val != deployed_val

            synth_line = f"{key}: `{synth_val}`"
            deployed_line = f"{key}: `{deployed_val}`"

            if is_changed:
                synth_line = f"**{synth_line}** :warning: Changed"
                deployed_line = f"**{deployed_line}**"

            synth_lines.append(f"• {synth_line}")
            deployed_lines.append(f"• {deployed_line}")

        synth_str = "<br>".join(synth_lines)
        deployed_str = "<br>".join(deployed_lines)
        display_name = get_resource_name(resource, logical_id)

        out.write(f"| {display_name} | {r_type} | {synth_str} | {deployed_str} |\n")
