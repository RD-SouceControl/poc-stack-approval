import yaml

# Static AZ index mapping (customize per region if needed)
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
        # Handle Fn::Select -> Fn::GetAZs
        if "Fn::Select" in val:
            select_val = val["Fn::Select"]
            index = select_val[0]
            if isinstance(index, str):
                index = int(index)
            az_name = AZ_INDEX_MAPPING.get(index, f"AZ-{index}")
            return f" {az_name}"
        
        # Handle Ref
        if "Ref" in val:
            return f"Ref: {val['Ref']}"
        
        # Fallback for other nested structures
        return ", ".join(f"{k}: {format_value(v)}" for k, v in val.items())
    
    elif isinstance(val, list):
        # Special handling for Tags
        if all(isinstance(item, dict) and "Key" in item and "Value" in item for item in val):
            tags = {tag["Key"]: tag["Value"] for tag in val}
            return f"Tags: {tags}"
        
        # Security Group Rule formatting
        if all(isinstance(item, dict) and "IpProtocol" in item for item in val):
            return "[" + "; ".join(format_security_rule(rule) for rule in val) + "]"
        
        return f"{len(val)} items"

    return str(val)

with open("template.yaml", "r") as f:
    content = f.read()
    print(":mag: Raw template.yaml content:\n")
    print(content)
    print("\n--- End of template.yaml preview ---\n")
    if not content.strip():
        raise ValueError("template.yaml is empty.")
    template = yaml.safe_load(content)

if not isinstance(template, dict):
    raise ValueError("Parsed template is not a valid dictionary.")

resources = template.get("Resources", {})

with open("networking_table.md", "w") as out:
    out.write("| Logical ID | Resource Type | Key Properties |\n")
    out.write("|------------|----------------|----------------|\n")

    networking_types = {
        "AWS::EC2::VPC",
        "AWS::EC2::Subnet",
        "AWS::EC2::InternetGateway",
        "AWS::EC2::VPCGatewayAttachment",
        "AWS::EC2::RouteTable",
        "AWS::EC2::Route",
        "AWS::EC2::SecurityGroup"
    }

    for logical_id, resource in resources.items():
        r_type = resource.get("Type")
        if r_type in networking_types:
            props = resource.get("Properties", {})
            key_props = []
            for k, v in props.items():
                val_str = format_value(v)
                key_props.append(f"{k}: {val_str}")
            # Use bullet points and line breaks for better Markdown formatting
            prop_str = "<br>".join(f"• `{p}`" for p in key_props)
            out.write(f"| {logical_id} | {r_type} | {prop_str} |\n")
