import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import { Construct } from 'constructs';

export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Original VPC (unchanged)
    this.vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 2,
      natGateways: 1,
    });

    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
    });

    // Additional VPC with NAT, Public and Private Subnets
    // const extraVpc = new ec2.Vpc(this, 'ExtraVpc', {
    //   maxAzs: 2,
    //   natGateways: 1,
    //   subnetConfiguration: [
    //     {
    //       cidrMask: 24,
    //       name: 'ExtraPublic',
    //       subnetType: ec2.SubnetType.PUBLIC,
    //     },
    //     {
    //       cidrMask: 24,
    //       name: 'ExtraPrivate',
    //       subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
    //     },
    //   ],
    // });

    // // ALB in the public subnet
    // const alb = new elbv2.ApplicationLoadBalancer(this, 'ExtraALB', {
    //   vpc: extraVpc,
    //   internetFacing: true,
    //   vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
    // });

    // new cdk.CfnOutput(this, 'ExtraVpcId', {
    //   value: extraVpc.vpcId,
    // });

    // new cdk.CfnOutput(this, 'ExtraALBDNS', {
    //   value: alb.loadBalancerDnsName,
    // });
  }
}
