import os
import sys
import boto3
import csp
import time
import argparse

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

def delete_lambda_functions(client, domain_id, domain_name, dry_run=False):
    """
    Delete Lambda functions associated with the given domain ID and domain name.

    Args:
        client: Boto3 Lambda client.
        domain_id (str): Domain ID.
        domain_name (str): Domain name.
        dry_run (bool): If True, perform a dry-run and don't delete the resources.

    Returns:
        list: List of Lambda function names that can be deleted.
    """
    lambda_client = boto3.client('lambda')
    functions = lambda_client.list_functions()
    deletable_functions = []
    for function in functions['Functions']:
        if function['FunctionName'].endswith(domain_name):
            print(f"Deleting Lambda Function: {function['FunctionName']}")
            if not dry_run:
                lambda_client.delete_function(FunctionName=function['FunctionName'])
            else:
                print(f"Dry-run: Would delete Lambda Function: {function['FunctionName']}")
            deletable_functions.append(function['FunctionName'])
    return deletable_functions

def delete_network_interfaces(client, domain_id, domain_name, dry_run=False):
    """
    Delete network interfaces associated with the given domain ID and domain name.

    Args:
        client: Boto3 EC2 client.
        domain_id (str): Domain ID.
        domain_name (str): Domain name.
        dry_run (bool): If True, perform a dry-run and don't delete the resources.

    Returns:
        list: List of network interface IDs that can be deleted.
    """
    ec2_client = boto3.client('ec2')
    network_interfaces = ec2_client.describe_network_interfaces()
    deletable_interfaces = []
    for interface in network_interfaces['NetworkInterfaces']:
        for group in interface['Groups']:
            if domain_name in group['GroupName']:
                print(f"Deleting Network Interface: {interface['NetworkInterfaceId']}")
                if not dry_run:
                    ec2_client.delete_network_interface(NetworkInterfaceId=interface['NetworkInterfaceId'])
                else:
                    print(f"Dry-run: Would delete Network Interface: {interface['NetworkInterfaceId']}")
                deletable_interfaces.append(interface['NetworkInterfaceId'])
    return deletable_interfaces

def delete_efs_volumes(client, domain_id, domain_name, dry_run=False):
    """
    Delete EFS volumes associated with the given domain ID and domain name.

    Args:
        client: Boto3 EFS client.
        domain_id (str): Domain ID.
        domain_name (str): Domain name.
        dry_run (bool): If True, perform a dry-run and don't delete the resources.

    Returns:
        list: List of EFS file system IDs that can be deleted.
    """
    efs_client = boto3.client('efs')
    file_systems = efs_client.describe_file_systems()
    deletable_file_systems = []
    for file_system in file_systems['FileSystems']:
        if f"arn:aws:sagemaker:{os.environ['AWS_REGION']}:{client.get_caller_identity()['Account']}:domain/{domain_id}" in file_system['Tags']:
            print(f"Deleting EFS Volume: {file_system['FileSystemId']}")
            if not dry_run:
                efs_client.delete_file_system(FileSystemId=file_system['FileSystemId'])
            else:
                print(f"Dry-run: Would delete EFS Volume: {file_system['FileSystemId']}")
            deletable_file_systems.append(file_system['FileSystemId'])
    return deletable_file_systems

def delete_domain(client, domain_id, domain_name, dry_run=False):
    """
    Delete resources associated with the given domain ID and domain name.

    Args:
        client: Boto3 SageMaker client.
        domain_id (str): Domain ID to delete.
        domain_name (str): Domain name.
        dry_run (bool): If True, perform a dry-run and don't delete the resources.

    Returns:
        dict: Dictionary containing the lists of deletable resources.
    """
    deletable_resources = {
        'lambda_functions': [],
        'network_interfaces': [],
        'efs_volumes': [],
        'apps': [],
        'user_profiles': []
    }

    # Delete Apps
    apps = client.list_apps(DomainIdEquals=domain_id)
    for app in apps['Apps']:
        print(f"Deleting App: {app['AppName']}")
        if not dry_run:
            client.delete_app(DomainId=domain_id, UserProfileName=app['UserProfileName'], AppType=app['AppType'], AppName=app['AppName'])
        else:
            print(f"Dry-run: Would delete App: {app['AppName']}")
        deletable_resources['apps'].append(app['AppName'])

    # Delete User Profiles
    user_profiles = client.list_user_profiles(DomainIdEquals=domain_id)
    for user_profile in user_profiles['UserProfiles']:
        print(f"Deleting User Profile: {user_profile['UserProfileName']}")
        if not dry_run:
            client.delete_user_profile(DomainId=domain_id, UserProfileName=user_profile['UserProfileName'])
        else:
            print(f"Dry-run: Would delete User Profile: {user_profile['UserProfileName']}")
        deletable_resources['user_profiles'].append(user_profile['UserProfileName'])

    # Delete Lambda Functions
    deletable_resources['lambda_functions'] = delete_lambda_functions(client, domain_id, domain_name, dry_run)

    # Delete Network Interfaces
    deletable_resources['network_interfaces'] = delete_network_interfaces(client, domain_id, domain_name, dry_run)

    # Delete EFS Volumes
    deletable_resources['efs_volumes'] = delete_efs_volumes(client, domain_id, domain_name, dry_run)

    # Delete Domain
    if not dry_run:
        print(f"Deleting Domain: {domain_id}")
        client.delete_domain(DomainId=domain_id, RetentionPolicy={'HomeEfsFileSystem': 'Delete'})
    else:
        print(f"Dry-run: Would delete Domain: {domain_id}")

    return deletable_resources

if __name__ == '__main__':
    # Assuming csp.login() is defined elsewhere
    csp.login()

    client = boto3.client('sagemaker')

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Delete SageMaker domains and associated resources.')
    parser.add_argument('--project-id', type=str, help='Project ID suffix for domain names')
    parser.add_argument('--domain-ids', type=str, help='Comma-separated list of domain IDs to delete')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry-run and don't delete any resources')
    args = parser.parse_args()

    if args.project_id:
        # Filter domain IDs with project_id as suffix
        filtered_domains = filter_domain_id_with_project_id(client, args.project_id)

        if not filtered_domains:
            print(f"No domains found with project ID '{args.project_id}' as suffix.")
            exit(0)

        # Proceed with deletion for each filtered domain
        for domain in filtered_domains:
            print(f"Preparing to delete Domain ID: {domain['DomainId']}, Domain Name: {domain['DomainName']}")
            deletable_resources = delete_domain(client, domain['DomainId'], domain['DomainName'], args.dry_run)

            if args.dry_run:
                print(f"Dry-run: Domain ID {domain['DomainId']} can be deleted with the following resources:")
            else:
                print(f"Domain ID {domain['DomainId']} has been deleted with the following resources:")

            for resource_type, resources in deletable_resources.items():
                if resources:
                    print(f"  {resource_type.replace('_', ' ').capitalize()}: {', '.join(resources)}")
    elif args.domain_ids:
        # Delete specific domain IDs
        domain_ids = args.domain_ids.split(',')
        for domain_id in domain_ids:
            # Get domain name from domain ID
            domains = client.list_domains()
            for domain in domains['Domains']:
                if domain['DomainId'] == domain_id:
                    domain_name = domain['DomainName']
                    break
            print(f"Preparing to delete Domain ID: {domain_id}, Domain Name: {domain_name}")
            deletable_resources = delete_domain(client, domain_id, domain_name, args.dry_run)

            if args.dry_run:
                print(f"Dry-run: Domain ID {domain_id} can be deleted with the following resources:")
            else:
                print(f"Domain ID {domain_id} has been deleted with the following resources:")

            for resource_type, resources in deletable_resources.items():
                if resources:
                    print(f"  {resource_type.replace('_', ' ').capitalize()}: {', '.join(resources)}")
    else:
        print("Error: Either --project-id or --domain-ids must be provided.")
        exit(1)



import pdb


def delete_domain(client, domain_id, domain_name, dry_run=False):
    pdb.set_trace()
    # Rest of the function code


def delete_domain(client, domain_id, domain_name, dry_run=False):
    pdb.set_trace()
    deletable_resources = {
        'lambda_functions': [],
        'network_interfaces': [],
        'efs_volumes': [],
        'apps': [],
        'user_profiles': []
    }

    # ... (rest of the function code)

(Pdb) n  # Execute the next line
(Pdb) p domain_id  # Print the value of domain_id
(Pdb) s  # Step into the next function call
# ... (continue debugging)


Role Mapping Through AWS STS at USAA
1. Custom App-Created Roles
Within USAA, custom application-created roles are roles specifically designed and managed by applications to control access to AWS resources.
These roles are tailored to the specific needs and permissions required by the applications they serve.
2. Service Accounts
Service accounts are special accounts used by processes or applications to interact with AWS services and resources.
These accounts typically have restricted permissions based on the principle of least privilege, ensuring that they only have access to the resources necessary for their functions.
3. Role Mapping Process
The role mapping process involves associating a custom app-created role or service account with an AWS IAM role using AWS STS to obtain temporary security credentials.
4. Source Process Execution
The source process, running as a service account within USAA's environment, initiates the role mapping process by executing the AWS STS binary.
This binary is responsible for facilitating the communication with AWS STS to request temporary security credentials for the mapped role.
5. STS Binary Execution
When the STS binary is executed, it communicates with AWS STS to authenticate the source process and request temporary security credentials for the mapped role.
The authentication process typically involves validating the identity and permissions of the source process based on its service account credentials.
6. Retrieval of STS Credentials
Upon successful authentication and authorization, AWS STS issues temporary security credentials for the mapped role.
These credentials include an access key ID, secret access key, and session token, which are used by the source process to access AWS resources.
7. Usage of STS Credentials
The source process, now equipped with the temporary security credentials obtained from AWS STS, can access AWS resources and services based on the permissions granted to the mapped role.
These credentials have a limited lifespan and are automatically rotated by AWS STS, enhancing security.
8. Custom Build for Non-Existent Roles
For roles that do not exist or require custom configurations beyond standard IAM roles, custom-built solutions may be necessary.
This could involve developing custom IAM policies, role assumptions logic, and integration with AWS STS to meet the specific requirements of the application or service.
