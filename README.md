# OpsLyftEc2Project

## Code Logic
1. First fetched all currently running EC2 instances.
2. For each instance, checking if 'Name' or 'Environment' Tag is missing. If so, sent out a mail to owner to add the missing tags. And then added another tag 'terminateAfter' in this EC2 to denote after which time shoud it be terminated, that is, current time plus 6 hours.
3. Next hour when this lambda runs, it will find EC2 with 'terminatedAfter' tag present - so it will just check if that time set has been already passed. If so, it again mails the owner and terminates the instance.     

Lambda has Cloudwatch Event trigger set to invoke every 1 hour.
