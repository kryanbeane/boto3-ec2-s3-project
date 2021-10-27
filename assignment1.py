#!/usr/bin/env python3
# Setup
import os, sys, boto3, subprocess, webbrowser, random, string, time, stat
from operator import itemgetter

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
            # Sorts by newest to the end of the list so reverse so newest is at index 0
            reverse=True
        )
        
        newest_ami = image_details[0]['ImageId']
        print('Most recent AMI found:', newest_ami)
        return newest_ami

    except Exception as e:
        print('An error occurred while fetching the most recent Amazon Linux 2 AMI.')
        print(e)
        
def instance_setup(key_name):
    ec2_client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')
    new_instance = launch_instance(key_name)

    try:
        new_instance[0].wait_until_running()
        print('Instance running ~(˘▾˘~)')
        
        # Reloads the instance and assigns the intance's ip to ec2_ip
        new_instance[0].reload()
        ec2_ip = new_instance[0].public_ip_address

        # Waits until web server is running to copy monitor.sh over and ssh in
        print('Please wait while the web server launches...')

        waiter = ec2_client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[new_instance[0].instance_id])
        subprocess.run("scp -o StrictHostKeyChecking=no -i {}.pem monitor.sh ec2-user@".format(key_name) + ec2_ip + ":.", shell=True)
        subprocess.run("ssh -o StrictHostKeyChecking=no -i {}.pem ec2-user@".format(key_name) + ec2_ip + " 'chmod 700 monitor.sh'", shell=True)
        subprocess.run("ssh -o StrictHostKeyChecking=no -i {}.pem ec2-user@".format(key_name) + ec2_ip + " ' ./monitor.sh'", shell=True)

        # Launches web browser with public ip opened
        print('Opening webpage...')
        webbrowser.open_new_tab(ec2_ip)

    except Exception as e:
        print('An error occurred while setting up monitoring.')
        print(e)

def launch_instance(key_name):
    ec2_client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')
    try:
        print('Starting Instance...')
        # Creates a list: new_instance, containing the newly created instance
        return ec2.create_instances(
            # Amazon Linux 2 AMI
            ImageId = fetch_latest_ami(), 
            MinCount = 1,
            MaxCount = 1,
            InstanceType = 't2.nano',
            KeyName = key_name,
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

    except Exception as e:
        if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
            print('The used key pair can not be found, creating a new one.')
            print()
            instance_setup(create_key_pair(key_name))

        else:
            print('An unexpected error occurred during EC2 Instance creation.')
            print(e)

def create_key_pair(name):
    client = boto3.client("ec2")

    print('New key pair:', name + ', successfully created.')
    key_pair = client.create_key_pair(KeyName=name)
    # create_key_pair() uploads public key to AWS, so now create private key to download locally
    private_key = key_pair["KeyMaterial"]

    # Write private key to file with 400 permissions
    with os.fdopen(os.open("./{}.pem".format(name), os.O_WRONLY | os.O_CREAT, 0o400), "w+") as handle:
        handle.write(private_key)
    return name

def create_bucket(bucket_name):
    s3 = boto3.resource("s3")
    s3_client = boto3.client('s3')

    try:
        print('Creating S3 Bucket...')

        new_bucket = s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
            ACL='public-read',
        )

        print('Bucket successfully created.')

        s3_website_conversion(bucket_name)
        populate_bucket(bucket_name)
        print('Loading website...')
    
        # Reloads bucket website to make sure all changes are up to date, then opens browser automatically for user
        s3.BucketWebsite(bucket_name).reload()
        webbrowser.open_new_tab('https://{}.s3.eu-west-1.amazonaws.com/index.html'.format(bucket_name))
    
    except Exception as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print('The bucket name already exists')
            txt = input('Randomise the bucket name? (y/n)')

            if txt=='y' or txt == 'Y':
                # Joins the bucket name string with a random selection of lowercase characters and creates a new bucket with that name
                bucket_name2 = bucket_name.join(random.choices(string.ascii_lowercase + string.digits, k=2))
                print('New bucket name:', bucket_name2)
                create_bucket(bucket_name2)

            else: 
                print('A bucket cannot be created with this name. Please try again.')
                os._exit(0)
        else:
            print('An error has occurred while creating your S3 bucket.')
            os._exit(0)

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
    try:
        topic = sns.create_topic(Name=name)
        return topic

    except Exception as e:
        print('An error has occurred while setting up your topic.')
        print(e)

def sns_sub_to_topic(topic, protocol, endpoint):
    try:
        subscription = topic.subscribe(
            Protocol = protocol,
            Endpoint = endpoint,
            ReturnSubscriptionArn = True
        )
        return subscription

    except Exception as e:
        print('An error has occurred while subscribing to your chosen topic.')
        print(e)

def publish_text_message(number, msg):
    sns = boto3.resource('sns')
    try:
        response = sns.meta.client.publish(
            PhoneNumber = number,
            Message = msg
        )
        message_id=response['MessageId']

    except Exception as e:
        print('An error has occured while publishing your text message.')
        print(e)

def send_sns_text_msg(msg):
    try:
        topic=sns_topic_setup('Assignment_Topic')
        number = '+353861727312'
        number_sub = sns_sub_to_topic(topic, 'sms', number)
        publish_text_message(number, msg)
    
    except Exception as e:
        print('An error has occured while sending your text message.')
        print(e)

print('INSTANCE SETUP')
instance_setup('bkkeypair')
send_sns_text_msg('You just launched an instance, dont forget to terminate it when youre finished.')

print()

print('BUCKET SETUP')
create_bucket('keane-bryan-s3')
send_sns_text_msg('You just launched an S3 bucket, dont forget to terminate it when youre finished.')