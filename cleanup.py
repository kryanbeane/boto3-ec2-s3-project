#!/usr/bin/env python3
import sys
import boto3

def clean_ec2s():
    ec2 = boto3.resource('ec2')
    try:
        for inst in ec2.instances.all():
            if inst.state['Name'] != 'terminated':
                inst.terminate()
                print('Instance', inst.instance_id, 'deleted.')

    except Exception as e:
        print('Error deleting instances')
        print(e)
    print('No instances to delete')

def clean_s3s():
    try:
        client = boto3.client('s3')
        s3 = boto3.resource('s3')

        buckets = client.list_buckets()

        for bucket in buckets['Buckets']:
            s3_bucket = s3.Bucket(bucket['Name'])
            s3_bucket.objects.all().delete()
            s3_bucket.delete()
            print('Bucket deleted')

    except Exception as e:
        print('No buckets to delete!')
        print(e)
    print('No buckets to delete')

clean_s3s()
clean_ec2s()