import json
import boto3
from datetime import datetime, timedelta

ec2c = boto3.client('ec2')

def lambda_handler(event, context):
    global ec2c
    global ec2r

    # Get list of regions
    regionslist = ec2c.describe_regions().get('Regions',[] )

    # Iterate over regions
    for region in regionslist:
        print("=================================\n\n")
        print ("Looking at region %s " % region['RegionName'])
        reg=region['RegionName']

        # Connect to region
        ec2r = boto3.resource('ec2', region_name=reg)

        # get a list of all instances
        all_running_instances = [i for i in ec2r.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])]
        for instance in all_running_instances:
            envTagMissing = True
            nameTagMissing = True
            createdBy = None
            print("Running instance found : %s" % instance.id)

            for tag in instance.tags:
                if 'Name' == tag['Key']:
                    nameTagMissing = False
                if 'Environment' == tag['Key']:
                    envTagMissing = False
                if 'created by' == tag['Key']:
                    createdBy = tag['Value']
            
            if envTagMissing or nameTagMissing:
                process_ec2(instance, envTagMissing, nameTagMissing, createdBy)


def process_ec2(instance, envTagMissing, nameTagMissing, createdBy):
    if 'terminateAfter' in [tag['Key'] for tag in instance.tags]:
        for tag in instance.tags:
            if 'terminateAfter' == tag['Key']:
                time_to_delete = datetime.fromisoformat(tag['Value'])
                cur_time = datetime.now()
                
                # Terminate ec2 instance if 6 hours have passed.
                if time_to_delete <= cur_time:
                    send_email_to_owner(instance, envTagMissing, nameTagMissing, createdBy, 'deletion')
                    print('Terminating ec2 instance : %s' % (instance.id))
                    instance.terminate()
    else:
        # Send warning email to owner for missing tags
        send_email_to_owner(instance, envTagMissing, nameTagMissing, createdBy, 'warning')
        time_after_6_hours = datetime.now() + timedelta(hours=6)
        time_after_6_hours = time_after_6_hours.isoformat()
        
        # Create a new tag on the EC2 with terminateAfter time.
        ec2r.create_tags(Resources=[instance.id], Tags=[{'Key':'terminateAfter', 'Value':str(time_after_6_hours)}])
        

def send_email_to_owner(instance, envTagMissing, nameTagMissing, createdBy, messageType):
    print('sending email to owner: %s for ec2 instance: %s, messageType: %s' % (createdBy, instance.id, messageType))
    
    ses_client = boto3.client('ses')
    
    missingTags = ''
    if envTagMissing:
        missingTags += ' Environment '
    if nameTagMissing:
        missingTags += ' Name '
        
    message = ''
    if messageType == 'warning':
        message = 'The required tags ( %s ) are missing on your EC2 instance id %s. Please tag your instance else they get terminated after 6 hours' % (missingTags, instance.id)
    elif messageType == 'deletion':
        message = 'Your EC2 instance id : %s is being terminated now as it was missing required tags for more than 6 hours' % (instance.id)
    
    response = ses_client.send_email(
        Source='agarwalharsh0512@gmail.com',
        Destination={
            'ToAddresses': [createdBy],
        },
        Message={
            'Subject': {
                'Data': 'EC2 Instance missing required tags',
                'Charset': 'utf-8'
            },
            'Body': {
                'Text': {
                    'Data': message,
                    'Charset': 'utf-8'
                }
            }
        }
    )