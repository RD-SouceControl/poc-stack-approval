import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import { Construct } from 'constructs';

export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Main VPC
    this.vpc = new ec2.Vpc(this, 'Vpc', {
      cidr: '10.2.0.0/16',
      maxAzs: 2,
      natGateways: 0,
    });

    cdk.Tags.of(this.vpc).add('Environment', 'Test');

    new cdk.CfnOutput(this, 'VpcId', { value: this.vpc.vpcId });

    // Additional VPC
    const extraVpc = new ec2.Vpc(this, 'ExtraVpc', {
      cidr: '10.2.0.0/16',
      maxAzs: 2,
      natGateways: 0,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'ExtraPublic',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'ExtraPrivate',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
      ],
    });

    cdk.Tags.of(extraVpc).add('Name', 'ExtraVpc-2');
    cdk.Tags.of(extraVpc).add('Environment', 'Test');

    // ALB in public subnet
    const alb = new elbv2.ApplicationLoadBalancer(this, 'ExtraALB', {
      vpc: extraVpc,
      internetFacing: true,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
    });

    cdk.Tags.of(alb).add('Name', 'ExtraALB');

    // Security Group
    const albSg = new ec2.SecurityGroup(this, 'ExtraALBSecurityGroup', {
      vpc: extraVpc,
      description: 'Security group for ALB',
      allowAllOutbound: true,
    });

    // albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'Allow HTTP');
    // albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'Allow HTTPS');
    // albSg.addEgressRule(ec2.Peer.anyIpv4(), ec2.Port.allTraffic(), 'Allow all egress');

    cdk.Tags.of(albSg).add('Name', 'ExtraALBSG');

    new cdk.CfnOutput(this, 'ExtraVpcId', { value: extraVpc.vpcId });
    new cdk.CfnOutput(this, 'ExtraALBDNS', { value: alb.loadBalancerDnsName });
  }
}
