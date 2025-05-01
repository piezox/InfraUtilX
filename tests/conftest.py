import pulumi
import pytest

class MyMocks(pulumi.runtime.Mocks):
    def new_resource(self, type_, name, inputs, provider, id_):
        # Return a fake resource ID and the same inputs as outputs
        return name + '_id', inputs

    def call(self, call_args):
        if call_args.token == 'aws:ec2/getAmi:getAmi':
            # Mock the AMI lookup
            return {
                'id': 'ami-123456',
                'architecture': 'x86_64',
                'name': 'mock-ami',
                'rootDeviceName': '/dev/xvda',
                'rootDeviceType': 'ebs',
                'virtualizationType': 'hvm',
            }
        return {}

@pytest.fixture(autouse=True, scope="session")
def pulumi_mocks():
    pulumi.runtime.set_mocks(MyMocks()) 