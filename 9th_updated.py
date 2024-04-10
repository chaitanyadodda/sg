import os
import boto3
import csp
import argparse

os.environ['AWS_DEFAULT_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')

def list_all_domains(client):
    
    print("All Domain IDs and Names:")
    domains = client.list_domains()
    for domain in domains['Domains']:
        print(f"Domain ID: {domain['DomainId']}, Domain Name: {domain['DomainName']}")

def filter_domain_id_with_project_id(client, project_id):
   
    filtered_domain_ids = []
    domains = client.list_domains()
    for domain in domains['Domains']:
        if domain['DomainName'].endswith(project_id):
            filtered_domain_ids.append({'DomainId': domain['DomainId'], 'DomainName': domain['DomainName']})
    return filtered_domain_ids

def delete_lambda_functions(client, domain_name):
    
    lambdas = client.list_functions()
    for func in lambdas['Functions']:
        if domain_name in func['FunctionName']:
            print(f"Deleting Lambda Function: {func['FunctionName']}")
            client.delete_function(FunctionName=func['FunctionName'])

def delete_network_interfaces(client, domain_name):
    
    interfaces = client.describe_network_interfaces()
    for interface in interfaces['NetworkInterfaces']:
        for group in interface['Groups']:
            if domain_name in group['GroupName']:
                print(f"Deleting Network Interface: {interface['NetworkInterfaceId']}")
                client.delete_network_interface(NetworkInterfaceId=interface['NetworkInterfaceId'])

def delete_efs_volumes(client, domain_id):
    
    volumes = client.describe_file_systems()
    for volume in volumes['FileSystems']:
        for tag in volume['Tags']:
            if domain_id in tag['Value']:
                print(f"Deleting EFS Volume: {volume['FileSystemId']}")
                client.delete_file_system(FileSystemId=volume['FileSystemId'])

def delete_domain_resources(client, domain_id, domain_name):
    
    delete_lambda_functions(client['lambda'], domain_name)
    delete_network_interfaces(client['ec2'], domain_name)
    delete_efs_volumes(client['efs'], domain_id)

def delete_domain(client, domain_id, domain_name, dry_run=False):
    
    # Delete Apps
    apps = client.list_apps(DomainIdEquals=domain_id)
    for app in apps['Apps']:
        print(f"Deleting App: {app['AppName']}")
        if not dry_run:
            client.delete_app(DomainId=domain_id, UserProfileName=app['UserProfileName'], AppType=app['AppType'], AppName=app['AppName'])

    # Delete User Profiles
    user_profiles = client.list_user_profiles(DomainIdEquals=domain_id)
    for user_profile in user_profiles['UserProfiles']:
        print(f"Deleting User Profile: {user_profile['UserProfileName']}")
        if not dry_run:
            client.delete_user_profile(DomainId=domain_id, UserProfileName=user_profile['UserProfileName'])

    # Delete Domain Resources
    print(f"Deleting Resources Associated with Domain: {domain_id}")
    delete_domain_resources(client, domain_id, domain_name)

    # Delete Domain
    print(f"Deleting Domain: {domain_id}")
    if not dry_run:
        client.delete_domain(DomainId=domain_id, RetentionPolicy={'HomeEfsFileSystem': 'Delete'})

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        Namespace: Object containing parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Delete SageMaker domain resources")
    parser.add_argument('--project-id', help="Project ID suffix to filter domains")
    parser.add_argument('--domain-ids', help="Comma-separated list of domain IDs to delete")
    parser.add_argument('--dry-run', action='store_true', help="Perform a dry run without deleting resources")
    return parser.parse_args()

if __name__ == '__main__':
    # Assuming csp.login() is defined elsewhere
    csp.login()

    args = parse_arguments()
    client = {
        'sagemaker': boto3.client('sagemaker'),
        'lambda': boto3.client('lambda'),
        'ec2': boto3.client('ec2'),
        'efs': boto3.client('efs')
    }

    # List all domain IDs and names
    list_all_domains(client['sagemaker'])

    if args.project_id:
        # Filter domain IDs with project_id as suffix
        filtered_domains = filter_domain_id_with_project_id(client['sagemaker'], args.project_id)
        if not filtered_domains:
            print(f"No domains found with project ID '{args.project_id}' as suffix.")
            exit(0)
    elif args.domain_ids:
        # Get domain IDs from command-line arguments
        domain_ids = args.domain_ids.split(',')
        filtered_domains = [{'DomainId': domain_id.strip()} for domain_id in domain_ids]
    else:
        print("Please provide either --project-id or --domain-ids argument.")
        exit(1)

    # Proceed with deletion for each filtered domain
    for domain in filtered_domains:
        print(f"Preparing to delete Domain ID: {domain['DomainId']}")
        delete_domain(client['sagemaker'], domain['DomainId'], domain['DomainName'], dry_run=args.dry_run)

    if args.dry_run:
        print("Dry run completed. No resources were deleted.")
    else:
        print("Deletion completed successfully.")
