import os
import boto3
import time
import sys

os.environ['AWS_DEFAULT_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')

def delete_domain(domain_id):
    csp.login()  # Assuming csp.login() is defined elsewhere
    client = boto3.client('sagemaker')
    
    try:
        domain = client.describe_domain(DomainId=domain_id)
        print(f"Deleting SageMaker domain: {domain['DomainName']} ({domain['DomainId']})")

        # Deleting apps associated with the domain
        apps = client.list_apps(DomainIdEquals=domain_id)
        for app in apps['Apps']:
            if app['Status'] == 'InService' or app['Status'] == 'Delete_Failed':
                client.delete_app(DomainId=domain_id, UserProfileName=app['UserProfileName'], AppType=app['AppType'], AppName=app['AppName'])
            elif app['Status'] == 'Deleting':
                # Wait until deletion is complete
                while True:
                    time.sleep(5)
                    app_status = client.describe_app(DomainId=domain_id, UserProfileName=app['UserProfileName'], AppType=app['AppType'], AppName=app['AppName'])['Status']
                    if app_status != 'Deleting':
                        break

        # Deleting user profiles associated with the domain
        user_profiles = client.list_user_profiles(DomainIdEquals=domain_id)
        for user_profile in user_profiles['UserProfiles']:
            if user_profile['Status'] == 'InService':
                client.delete_user_profile(DomainId=domain_id, UserProfileName=user_profile['UserProfileName'])
            elif user_profile['Status'] == 'Deleting':
                # Wait until deletion is complete
                while True:
                    time.sleep(5)
                    user_profile_status = client.describe_user_profile(DomainId=domain_id, UserProfileName=user_profile['UserProfileName'])['Status']
                    if user_profile_status != 'Deleting':
                        break

        # Deleting the domain itself
        client.delete_domain(DomainId=domain_id, RetentionPolicy={'HomeEfsFileSystem': 'Delete'})
        
        print(f"SageMaker domain {domain['DomainName']} ({domain['DomainId']}) deleted successfully.")
    except Exception as e:
        print(f"Error deleting SageMaker domain {domain_id}: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python sagemaker_delete.py <domain_id>")
        sys.exit(1)
    
    domain_id = sys.argv[1]
    delete_domain(domain_id)


AWS_REGION: us-east-1
    DOMAIN_ID: "your_domain_id_here"
  image: docker.repo.ab.com/usaa/grp-ops-terraform/aws-triage:4t5t5
  script:
    - python sagemaker_delete.py $DOMAIN_ID



import os
import boto3
import time

os.environ['AWS_DEFAULT_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')

if __name__ == '__main__':
    csp.login()  # Assuming csp.login() is defined elsewhere
    
    client = boto3.client('sagemaker')
    
    domains = client.list_domains()
    
    print("List of SageMaker Domains:")
    for domain in domains['Domains']:
        print(f"Domain Name: {domain['DomainName']}, Domain ID: {domain['DomainId']}")
    
    for domain in domains['Domains']:
        SM_DOMAIN_ID = domain['DomainId']
        work_to_do = True
        retry_time = 5

        while work_to_do:
            work_to_do = False
            apps = client.list_apps(DomainIdEquals=SM_DOMAIN_ID)
            
            for app in apps['Apps']:
                if app['Status'] == 'InService' or app['Status'] == 'Delete_Failed':
                    print(client.delete_app(DomainId=SM_DOMAIN_ID, UserProfileName=app['UserProfileName'], AppType=app['AppType'], AppName=app['AppName']))
                elif app['Status'] == 'Deleting':
                    work_to_do = True
                    time.sleep(retry_time)
                    retry_time *= 3

        work_to_do = True
        retry_time = 5

        while work_to_do:
            work_to_do = False
            user_profiles = client.list_user_profiles(DomainIdEquals=SM_DOMAIN_ID)
            
            for user_profile in user_profiles['UserProfiles']:
                if user_profile['Status'] == 'InService':
                    print(client.delete_user_profile(DomainId=SM_DOMAIN_ID, UserProfileName=user_profile['UserProfileName']))
                elif user_profile['Status'] == 'Deleting':
                    work_to_do = True
                    time.sleep(retry_time)
                    retry_time *= 3

        print(client.delete_domain(DomainId=SM_DOMAIN_ID, RetentionPolicy={'HomeEfsFileSystem': 'Delete'}))
