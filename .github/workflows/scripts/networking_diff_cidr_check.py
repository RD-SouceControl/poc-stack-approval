import yaml
import boto3

AZ_INDEX_MAPPING = {
    0: "us-east-1a",
    1: "us-east-1b",
    2: "us-east-1c",
    3: "us-east-1d",
    4: "us-east-1e",
    5: "us-east-1f"
}

dynamodb_table_name = "VpcCidrRegistry"

def format_value(val):
    if isinstance(val, dict):
        if "Fn::Select" in val:
            index = val["Fn::Select"][0]
            if isinstance(index, str): index = int(index)
            return f"AvailabilityZone: {AZ_INDEX_MAPPING.get(index, f'AZ-{index}')}"
        if "Ref" in val:
            return f"Ref: {val['Ref']}"
        return ", ".join(f"{k}: {format_value(v)}" for k, v in val.items())
    elif isinstance(val, list):
        if all(isinstance(i, dict) and "Key" in i and "Value" in i for i in val):
            return f"Tags: {{{', '.join(f'{t['Key']}: {t['Value']}' for t in val)}}}"
        return f"{len(val)} items"
    return str(val)

def extract_key_props(resource):
    props = resource.get("Properties", {})
    formatted = {}
    for k, v in props.items():
        formatted[k] = format_value(v)
    return formatted

def extract_template(path):
    with open(path) as f:
        return yaml.safe_load(f)

def fetch_registered_cidrs():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(dynamodb_table_name)
    response = table.scan()
    return [item["CidrBlock"] for item in response.get("Items", [])]

def cidrs_overlap(cidr1, cidr2):
    import ipaddress
    return ipaddress.IPv4Network(cidr1).overlaps(ipaddress.IPv4Network(cidr2))

# Load templates
synth_template = extract_template("template.yaml")
deployed_template = extract_template("deployed-template.yaml")

resources_synth = synth_template.get("Resources", {})
resources_deployed = deployed_template.get("Resources", {})

cidr_warnings = []
cidrs_from_dynamo = fetch_registered_cidrs()

with open("networking_table.md", "w") as out:
    out.write("## :warning: CIDR Overlap Check\n")

    for logical_id, resource in resources_synth.items():
        if resource["Type"] == "AWS::EC2::VPC":
            cidr = resource.get("Properties", {}).get("CidrBlock")
            if cidr and any(cidrs_overlap(cidr, existing) for existing in cidrs_from_dynamo):
                cidr_warnings.append(f"CIDR {cidr} for `{logical_id}` overlaps with existing VPCs")

    if cidr_warnings:
        for warning in cidr_warnings:
            out.write(f"- **{warning}**\n")
    else:
        out.write("- No overlaps detected\n")

    out.write("\n## Networking Resource Comparison\n")
    out.write("| Logical ID | Resource Type | Synth Properties | Deployed Properties |\n")
    out.write("|------------|----------------|------------------|---------------------|\n")

    networking_types = {
        "AWS::EC2::VPC", "AWS::EC2::Subnet", "AWS::EC2::InternetGateway",
        "AWS::EC2::VPCGatewayAttachment", "AWS::EC2::RouteTable",
        "AWS::EC2::Route", "AWS::EC2::SecurityGroup"
    }

    for logical_id, resource in resources_synth.items():
        r_type = resource.get("Type")
        if r_type in networking_types:
            synth_props = extract_key_props(resource)
            deployed_props = extract_key_props(resources_deployed.get(logical_id, {}))
            prop_rows = []

            for key in set(synth_props) | set(deployed_props):
                val1 = synth_props.get(key, "—")
                val2 = deployed_props.get(key, "—")
                changed = val1 != val2
                if changed:
                    val1 = f"**{val1}** :warning:"
                prop_rows.append(f"• `{key}: {val1}`")

            out.write(f"| {logical_id} | {r_type} | {'<br>'.join(prop_rows)} | {'<br>'.join(f'• `{k}: {v}`' for k, v in deployed_props.items())} |\n")
