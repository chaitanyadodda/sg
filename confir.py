import os
import boto3
import csp
import time

os.environ['AWS_DEFAULT_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')

if __name__ == '__main__':
    # Assuming csp.login() is defined elsewhere
    csp.login()
    
    client = boto3.client('sagemaker')
    
    # Print all domain IDs
    domains = client.list_domains()
    print("Available Domain IDs:")
    for domain in domains['Domains']:
        print(domain['DomainId'])
    
    # Wait for domain ID input
    domain_id = input("Enter Domain ID to delete: ")
    
    # Confirm deletion
    confirm = input(f"Are you sure you want to delete domain ID {domain_id}? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Deletion cancelled.")
        exit()

    # Continue with deletion
    SM_DOMAIN_ID = domain_id
    
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

    # Uncomment if needed
    # sm_spaces = client.list_spaces(DomainIdEquals=SM_DOMAIN_ID)
    # for sm_space in sm_spaces['Spaces']:
    #     print(client.delete_space(DomainId=SM_DOMAIN_ID, SpaceName=sm_space['SpaceName']))

    print(client.delete_domain(DomainId=SM_DOMAIN_ID, RetentionPolicy={'HomeEfsFileSystem': 'Delete'}))
