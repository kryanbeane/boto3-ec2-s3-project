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

        ec2_client = boto3.client('ec2')
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

    except Exception as error:
        print('An error occurred during EC2 Instance creation.')
        print(error)
    
    try:
        # Reloads the instance and assigns the intance's ip to ec2_ip
        newInstance[0].reload()
        ec2_ip = newInstance[0].public_ip_address

        # Waits until web server is running to copy monitor.sh over and ssh in
        print('Please wait while the web server launches...')
        waiter = ec2_client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[newInstance[0].instance_id])
        subprocess.run("scp -o StrictHostKeyChecking=no -i bryankeanekeypair.pem monitor.sh ec2-user@" + ec2_ip + ":.", shell = True)
        subprocess.run("ssh -o StrictHostKeyChecking=no -i bryankeanekeypair.pem ec2-user@" + ec2_ip + " 'chmod 700 monitor.sh'", shell = True)
        subprocess.run("ssh -o StrictHostKeyChecking=no -i bryankeanekeypair.pem ec2-user@" + ec2_ip + " ' ./monitor.sh'", shell = True)

        # Launches web browser with public ip opened
        print('Opening webpage...')
        webbrowser.open_new_tab(ec2_ip)

    except Exception as error:
        print('An error occurred while  ')
        


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
        print('Creating S3 Bucket...')

        new_bucket = s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
            ACL='public-read',
        )

        print('Bucket successfully created.')

    except Exception as error:
        print('An error occurred during S3 Bucket creation.')
        print(error)


    ##### Upload image to S3 Bucket #####
    try:
        # Save image from URL
        subprocess.run("curl http://devops.witdemo.net/assign1.jpg > assign1.jpg", shell=True)
        subprocess.run("touch index.html", shell=True)

        # Places objects onto S3 bucket
        indexobject = 'index.html'
        s3.Object(bucket_name, indexobject).put(
            Body=open(indexobject, 'rb'), 
            ContentType='text/html',
            ACL='public-read'
        )

        jpegobject = 'assign1.jpg'
        s3.Object(bucket_name, jpegobject).put(
            Body=open(jpegobject, 'rb'), 
            ContentType='image/jpeg',
            ACL='public-read'
        )
        
        subprocess.run("echo '<img src='''https://bryan-keane-assignment-bucket.s3.eu-west-1.amazonaws.com/assign1.jpg'>''' > index.html", shell=True) 

        print('Bucket now populated with an objects.')
        
    except Exception as error:
        print('An error occurred during bucket object insertion. ')
        print(error)

    try:
        # Configures bucket to now host a static website
        website_configuration = {
            'ErrorDocument': {'Key': 'error.html'},
            'IndexDocument': {'Suffix': 'index.html'},
        }
        s3_client.put_bucket_website(
            Bucket=bucket_name, 
            WebsiteConfiguration=website_configuration,
        )

        print('Bucket website configuration successful.')
        webbrowser.open_new_tab('https://bryan-keane-assignment-bucket.s3.eu-west-1.amazonaws.com/index.html')

    except Exception as error:
        print('Bucket website configuration failed.')
        print(error)

createInstance()
createBucket()