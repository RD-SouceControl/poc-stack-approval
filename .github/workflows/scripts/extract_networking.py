import yaml

def format_value(val):
    if isinstance(val, dict):
        # Handle Fn::Select with Fn::GetAZs
        if "Fn::Select" in val:
            select_val = val["Fn::Select"]
            index = select_val[0]
            get_azs = select_val[1]
            if isinstance(get_azs, dict) and "Fn::GetAZs" in get_azs:
                return f"Auto-resolved (AZ Index {index})"
        
        # Handle Ref
        if "Ref" in val:
            return f"Ref: {val['Ref']}"
        
        # Handle other intrinsics or nested objects
        return ", ".join(f"{k}: {format_value(v)}" for k, v in val.items())
    
    elif isinstance(val, list):
        return f"{len(val)} items"
    
    return str(val)

# Read and parse the CDK synthesized CloudFormation template
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

# Write the markdown table summarizing networking-related resources
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
                key_props.append(f"{k}: `{val_str}`")
            prop_str = ", ".join(key_props)
            out.write(f"| {logical_id} | {r_type} | {prop_str} |\n")
