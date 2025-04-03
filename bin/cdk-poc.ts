import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/stacks/network-stack';
import { ServiceStack } from '../lib/stacks/service-stack';

const app = new cdk.App();

const networkStack = new NetworkStack(app, 'NetworkStack');

new ServiceStack(app, 'ServiceStack', {
  vpc: networkStack.vpc,
});
