import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/stacks/network-stack';
import { ServiceStack } from '../lib/stacks/service-stack';
import { VpcRegistryStack } from '../lib/stacks/dynamo-db-stack';

const app = new cdk.App();

const dbStack = new VpcRegistryStack(app, 'VpcRegistryStack');
const networkStack = new NetworkStack(app, 'NetworkStack');

new ServiceStack(app, 'ServiceStack', {
  vpc: networkStack.vpc,
});
