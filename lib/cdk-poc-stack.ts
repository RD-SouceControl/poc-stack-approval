import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
// import * as sqs from 'aws-cdk-lib/aws-sqs';

export class CdkPocStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // The code that defines your stack goes here   21654
    
    // const queue = new sqs.Queue(this, 'CdkPocQueue', {
    //   visibilityTimeout: cdk.Duration.seconds(300)
    // });
  }
}
