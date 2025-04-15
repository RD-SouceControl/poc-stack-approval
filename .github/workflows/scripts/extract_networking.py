import yaml

AZ_INDEX_MAPPING = {
    0: "us-east-1a",
    1: "us-east-1b",
    2: "us-east-1c",
    3: "us-east-1d",
    4: "us-east-1e",
    5: "us-east-1f"
}

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

synth_template = extract_template("template.yaml")
deployed_template = extract_template("deployed-template.yaml")

synth_resources = synth_template.get("Resources", {})
deployed_resources = deployed_template.get("Resources", {})

with open("networking_table.md", "w") as out:
    out.write("| Logical ID | Resource Type | Key Properties (Synth) | Deployed Properties |\n")
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

        out.write(f"| {logical_id} | {r_type} | {synth_str} | {deployed_str} |\n")
