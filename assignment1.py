#!/usr/bin/env python3
# Setup
import os
import sys
import boto3
import subprocess
import webbrowser
import urllib.request

# Try later to automatically fetch newest AMI Id

# Launch an EC2 Instance
def createInstance():
    try:
        print('Starting Instance...')

        ec2 = boto3.resource('ec2')
        # Creates a list: newInstance, containing the newly created instance
        newInstance = ec2.create_instances(
            # Amazon Linux 2 AMI
            ImageId = 'ami-05cd35b907b4ffe77', 
            MinCount = 1,
            MaxCount = 1,
            InstanceType = 't2.nano',
            KeyName = 'bryankeanekeypair',
            # Group allows SSH access and HTTP traffic
            SecurityGroupIds = [
                'sg-0feb83198fdf59512'       
            ],
            UserData = 
                ''' 
                #!/bin/bash
                sudo apt-get update
                sudo yum install httpd -y
                sudo systemctl enable httpd 
                sudo systemctl start httpd 
                echo '<html>' > index.html
                echo 'Private IP address: ' >> index.html
                curl -s http://169.254.169.254/latest/meta-data/local-ipv4>> index.html
                echo 'Public IP address: ' >> index.html 
                curl -s http://169.254.169.254/latest/meta-data/public-ipv4 >> index.html
                echo 'Instance type: ' >> index.html
                curl -s http://169.254.169.254/latest/meta-data/instance-type >> index.html
                echo 'Instance ID: ' >> index.html
                curl -s http://169.254.169.254/latest/meta-data/instance-id >> index.html
                cp index.html /var/www/html/index.html
                ''',
            TagSpecifications = [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'Assignment Instance'
                        }
                    ]
                }
            ]
        )
        
        newInstance[0].wait_until_running()
        print('Instance running ~(˘▾˘~)')
        newInstance[0].reload()
        ec2_ip = newInstance[0].public_ip_address
        subprocess.run("scp -o StrictHostKeyChecking=no -i bryankeanekeypair.pem monitor.sh ec2-user@" + ec2_ip + ":.", shell = True)
        subprocess.run("ssh -o StrictHostKeyChecking=no -i bryankeanekeypair.pem ec2-user@" + ec2_ip + " 'chmod 700 monitor.sh'", shell = True)
        subprocess.run("ssh -o StrictHostKeyChecking=no -i bryankeanekeypair.pem ec2-user@" + ec2_ip + " ' ./monitor.sh'", shell = True)
        print('Opening webpage...')
        webbrowser.open_new_tab(ec2_ip)
        
    except Exception as error:
        print(error)

#def getNewestAMI():
#    client = boto3.client('ssm', region_name='eu-west-1a')
#    result = client.get_parameter(Name='/aws/service/ecs/optimized-ami/amazon-linux-2/recommended')
#    values = result['Parameter']['Value']
#    i = values.find('"image_id":"') + 12
#    return result['Parameter']['Value'][i:i+21]

def createBucket():
    s3 = boto3.resource("s3")
    s3_client = boto3.client('s3')
    bucket_name = 'bryan-keane-assignment-bucket'

    ##### Create the S3 Bucket #####

    try:
        new_bucket = s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
            ACL='public-read'
        )
        print('Bucket successfully created.')
        print(new_bucket)

    except Exception as error:
        print('An error occurred during S3 Bucket creation. Error: ')
        print(error)

    ##### Upload image to S3 Bucket #####
    
    try:
        # Save image from URL
        subprocess.run("curl http://devops.witdemo.net/assign1.jpg > assign1.jpg",shell=True)

        # Sets directory to directory of python file
        object_name = ( os.path.dirname(os.path.realpath(__file__)) )+'/assign1.jpg'
        s3.Object(bucket_name, object_name).put(Body=open(object_name, 'rb'))
        print('Bucket now populated with an object.')
        
    except Exception as error:
        print('An error occurred during bucket object insertion. Error: ')
        print(error)

createBucket()