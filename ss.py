import os
import sys
import boto3
import csp
import time

os.environ['AWS_DEFAULT_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')

def filter_domain_id_with_project_id(client, project_id):
    filtered_domain_ids = []
    domains = client.list_domains()
    for domain in domains['Domains']:
        if domain['DomainName'].endswith(project_id):
            filtered_domain_ids.append({'DomainId': domain['DomainId'], 'DomainName': domain['DomainName']})
    return filtered_domain_ids

def delete_domain(client, domain_id):
    work_to_do = True
    retry_time = 5

    while work_to_do:
        work_to_do = False
        apps = client.list_apps(DomainIdEquals=domain_id)
        
        for app in apps['Apps']:
            if app['Status'] == 'InService' or app['Status'] == 'Delete_Failed':
                print(client.delete_app(DomainId=domain_id, UserProfileName=app['UserProfileName'], AppType=app['AppType'], AppName=app['AppName']))
            elif app['Status'] == 'Deleting':
                work_to_do = True
                time.sleep(retry_time)
                retry_time *= 3

    work_to_do = True
    retry_time = 5

    while work_to_do:
        work_to_do = False
        user_profiles = client.list_user_profiles(DomainIdEquals=domain_id)
        
        for user_profile in user_profiles['UserProfiles']:
            if user_profile['Status'] == 'InService':
                print(client.delete_user_profile(DomainId=domain_id, UserProfileName=user_profile['UserProfileName']))
            elif user_profile['Status'] == 'Deleting':
                work_to_do = True
                time.sleep(retry_time)
                retry_time *= 3

    # Uncomment if needed
    # sm_spaces = client.list_spaces(DomainIdEquals=domain_id)
    # for sm_space in sm_spaces['Spaces']:
    #     print(client.delete_space(DomainId=domain_id, SpaceName=sm_space['SpaceName']))

    print(client.delete_domain(DomainId=domain_id, RetentionPolicy={'HomeEfsFileSystem': 'Delete'}))

if __name__ == '__main__':
    # Assuming csp.login() is defined elsewhere
    csp.login()
    
    client = boto3.client('sagemaker')
    
    # Get project ID from environment variable
    project_id = os.getenv('PROJECT_ID')
    if project_id is None:
        print("Error: PROJECT_ID not provided.")
        exit(1)
    
    # Filter domain IDs with project_id as suffix
    filtered_domains = filter_domain_id_with_project_id(client, project_id)
    
    if not filtered_domains:
        print(f"No domains found with project ID '{project_id}' as suffix.")
        exit(0)
    
    # Proceed with deletion for each filtered domain
    for domain in filtered_domains:
        print(f"Deleting Domain ID: {domain['DomainId']}, Domain Name: {domain['DomainName']}")
        delete_domain(client, domain['DomainId'])


sagemaker_create:
  when: manual 
  variables:
    RUNTIME_ENV: dev
    AWS_REGION: us-east-1
    PROJECT_ID: your_project_id_here
  stage: domain_update
  image: docker.repo.ab.com/usaa/grp-ops-terraform/terraform-base-aws:16.88.0
  script:
    - python /path_to_your_script/sagemaker_create.py $PROJECT_ID


updated:
import os
import sys
import boto3
import csp
import time

os.environ['AWS_DEFAULT_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')

def list_all_domains(client):
    """
    List all domain IDs and their respective names.

    Args:
        client: Boto3 SageMaker client.
    """
    print("All Domain IDs and Names:")
    domains = client.list_domains()
    for domain in domains['Domains']:
        print(f"Domain ID: {domain['DomainId']}, Domain Name: {domain['DomainName']}")

def filter_domain_id_with_project_id(client, project_id):
    """
    Filter domain IDs with the given project ID as suffix.

    Args:
        client: Boto3 SageMaker client.
        project_id (str): Project ID suffix.

    Returns:
        list: List of dictionaries containing DomainId and DomainName.
    """
    filtered_domain_ids = []
    domains = client.list_domains()
    for domain in domains['Domains']:
        if domain['DomainName'].endswith(project_id):
            filtered_domain_ids.append({'DomainId': domain['DomainId'], 'DomainName': domain['DomainName']})
    return filtered_domain_ids

def delete_domain(client, domain_id):
    """
    Delete resources associated with the given domain ID.

    Args:
        client: Boto3 SageMaker client.
        domain_id (str): Domain ID to delete.
    """
    # Delete Apps
    apps = client.list_apps(DomainIdEquals=domain_id)
    for app in apps['Apps']:
        print(f"Deleting App: {app['AppName']}")
        client.delete_app(DomainId=domain_id, UserProfileName=app['UserProfileName'], AppType=app['AppType'], AppName=app['AppName'])

    # Delete User Profiles
    user_profiles = client.list_user_profiles(DomainIdEquals=domain_id)
    for user_profile in user_profiles['UserProfiles']:
        print(f"Deleting User Profile: {user_profile['UserProfileName']}")
        client.delete_user_profile(DomainId=domain_id, UserProfileName=user_profile['UserProfileName'])

    # Delete Domain
    print(f"Deleting Domain: {domain_id}")
    client.delete_domain(DomainId=domain_id, RetentionPolicy={'HomeEfsFileSystem': 'Delete'})

if __name__ == '__main__':
    # Assuming csp.login() is defined elsewhere
    csp.login()
    
    client = boto3.client('sagemaker')
    
    # List all domain IDs and names
    list_all_domains(client)
    
    # Get project ID from environment variable
    project_id = os.getenv('PROJECT_ID')
    if project_id is None:
        print("Error: PROJECT_ID not provided.")
        exit(1)
    
    # Filter domain IDs with project_id as suffix
    filtered_domains = filter_domain_id_with_project_id(client, project_id)
    
    if not filtered_domains:
        print(f"No domains found with project ID '{project_id}' as suffix.")
        exit(0)
    
    # Proceed with deletion for each filtered domain
    for domain in filtered_domains:
        print(f"Preparing to delete Domain ID: {domain['DomainId']}, Domain Name: {domain['DomainName']}")
        delete_domain(client, domain['DomainId'])

