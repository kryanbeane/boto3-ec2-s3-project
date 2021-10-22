#!/usr/bin/env python3
# Setup
import os
import sys
import boto3
import subprocess
import webbrowser
from operator import itemgetter
from datetime import datetime
import random
import string

def fetch_latest_ami():
    ec2_client = boto3.client('ec2')
    try:
        response = ec2_client.describe_images(
            Filters=[{'Name':'name','Values':['amzn2-ami-hvm-2.0.????????-x86_64-gp2']}],
            Owners=['amazon']   
        )
        # Sort by creation date and description
        image_details = sorted(
            response['Images'],
            key=itemgetter('CreationDate'),
            reverse=True
        )
        ami = image_details[0]['ImageId']
        print('Most recent AMI found:', ami)
        return ami

    except Exception as e:
        print('An error occurred while fetching the most recent Amazon Linux 2 AMI.')
        print(e)
        
def instance_setup():
    ec2_client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')
    newInstance = launch_instance()

    try:
        # Reloads the instance and assigns the intance's ip to ec2_ip
        newInstance[0].reload()
        ec2_ip = newInstance[0].public_ip_address

        # Waits until web server is running to copy monitor.sh over and ssh in
        print('Please wait while the web server launches...')
        waiter = ec2_client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[newInstance[0].instance_id])
        subprocess.run("scp -o StrictHostKeyChecking=no -i bryankeanekeypair.pem monitor.sh ec2-user@" + ec2_ip + ":.", shell=True)
        subprocess.run("ssh -o StrictHostKeyChecking=no -i bryankeanekeypair.pem ec2-user@" + ec2_ip + " 'chmod 700 monitor.sh'", shell=True)
        subprocess.run("ssh -o StrictHostKeyChecking=no -i bryankeanekeypair.pem ec2-user@" + ec2_ip + " ' ./monitor.sh'", shell=True)

        # Launches web browser with public ip opened
        print('Opening webpage...')
        webbrowser.open_new_tab(ec2_ip)

    except Exception as e:
        print('An error occurred while setting up monitoring.')#
        print(e)

def launch_instance():
    ec2_client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')

    try:
        print('Starting Instance...')
        # Creates a list: newInstance, containing the newly created instance
        newInstance = ec2.create_instances(
            # Amazon Linux 2 AMI
            ImageId = fetch_latest_ami(), 
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
        send_sns_text_msg()
        return newInstance

    except Exception as e:
        print('An error occurred during EC2 Instance creation.')
        print(e)

def create_bucket():
    s3 = boto3.resource("s3")
    s3_client = boto3.client('s3')
    bucket_name = 'keane-bryan-s3'

    try:
        print('Creating S3 Bucket...')

        new_bucket = s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
            ACL='public-read',
        )

        print('Bucket successfully created.')
    
    except Exception as e:
        print('The bucket name "keane-bryan-s3" already exists')
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':

            txt = input('Randomise the bucket name? (y/n)')
            if txt=='y' or txt == 'Y':
                bucket_name = bucket_name.join(random.choices(string.ascii_uppercase + string.digits, k=N))
                print(bucket_name)
            else: 
                print('A bucket cannot be created with this name. Please try again.')
                os._exit(0)
        else:
            print('An error has occurred while creating your S3 bucket.')
            os._exit(0)

    finally:
        s3_website_conversion(bucket_name)
        populate_bucket(bucket_name)

        print('Loading website...')
        webbrowser.open_new_tab('https://{}.s3.eu-west-1.amazonaws.com/index.html'.format(bucket_name))

def populate_bucket(bucket_name):
    s3 = boto3.resource("s3")
    s3_client = boto3.client('s3')

    try:
        # Save image from URL
        subprocess.run("curl http://devops.witdemo.net/assign1.jpg > assign1.jpg", shell=True)
        subprocess.run("touch index.html", shell=True)

        # Places index.html onto S3 bucket
        indexobject = 'index.html'
        s3.Object(bucket_name, indexobject).put(
            Body=open(indexobject, 'rb'), 
            ContentType='text/html',
            ACL='public-read'
        )

        # Places assign1.jpg onto S3 bucket
        jpegobject = 'assign1.jpg'
        s3.Object(bucket_name, jpegobject).put(
            Body=open(jpegobject, 'rb'), 
            ContentType='image/jpeg',
            ACL='public-read'
        )
        subprocess.run("echo '<img src='''https://{}.s3.eu-west-1.amazonaws.com/assign1.jpg'>''' > index.html".format(bucket_name), shell=True) 
        print('Bucket now populated with objects.')
        
    except Exception as e:
        print('An error occurred during bucket object insertion. ')
        print(e)

def s3_website_conversion(bucket_name):
    s3 = boto3.resource("s3")
    s3_client = boto3.client('s3')
    try:
        website_configuration = {
            'ErrorDocument': {'Key': 'error.html'},
            'IndexDocument': {'Suffix': 'index.html'},
        }

        s3_client.put_bucket_website(
            Bucket=bucket_name, 
            WebsiteConfiguration=website_configuration,
        )

        print('Bucket website configuration successful.')

    except Exception as e:
        print('Bucket website configuration failed.')
        print(e)    

def sns_topic_setup(name):
    sns = boto3.resource('sns')
    topic = sns.create_topic(Name=name)
    return topic

def sns_sub_to_topic(topic, protocol, endpoint):
    subscription=topic.subscribe(
        Protocol=protocol,
        Endpoint=endpoint,
        ReturnSubscriptionArn=True
    )
    return subscription

def publish_text_message(number, msg):
    sns = boto3.resource('sns')
    response = sns.meta.client.publish(
        PhoneNumber=number,
        Message=msg
    )
    message_id=response['MessageId']

def send_sns_text_msg():
    try:
        topic=sns_topic_setup('test_topic')
        number = '+353851791723'
        number_sub=sns_sub_to_topic(topic, 'sms', number)
        publish_text_message(number, 'You have an instance running, dont forget to terminate it!')
    
    except Exception as e:
        print('An error has occured while launching your instance.')
        print(e)

instance_setup()