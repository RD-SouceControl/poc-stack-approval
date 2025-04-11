import yaml
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
                val_str = str(v)
                if isinstance(v, dict):
                    val_str = ", ".join(f"{kk}: {vv}" for kk, vv in v.items())
                elif isinstance(v, list):
                    val_str = f"{len(v)} items"
                key_props.append(f"{k}: `{val_str}`")
            prop_str = ", ".join(key_props)
            out.write(f"| {logical_id} | {r_type} | {prop_str} |\n")

