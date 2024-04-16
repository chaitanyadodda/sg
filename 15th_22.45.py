22:45 code

import boto3
import argparse
import botocore.exceptions

def list_all_domains(client):
    print("All Domain IDs and Domain Names:")
    domains = client.list_domains()
    for domain in domains['Domains']:
        print(f"Domain ID: {domain['DomainId']}, Domain Name: {domain['DomainName']}")

def filter_domain_id_with_project_id(client, project_id):
    filtered_domain_ids = []
    client = boto3.client('sagemaker')
    domains = client.list_domains()
    for domain in domains['Domains']:
        if domain['DomainName'].endswith(project_id):
            filtered_domain_ids.append({'DomainId': domain['DomainId'], 'DomainName': domain['DomainName']})
    return filtered_domain_ids

def delete_lambda_functions(client, project_id):
    print(f"Filtering Lambda functions for project ID: {project_id}")
    lambdas = client.list_functions()
    for func in lambdas['Functions']:
        if project_id in func['FunctionName']:
            print(f"Deleting Lambda Function: {func['FunctionName']}")
            client.delete_function(FunctionName=func['FunctionName'])

def delete_network_interfaces(client, domain_id):
    interfaces = client.describe_network_interfaces()
    for interface in interfaces['NetworkInterfaces']:
        for group in interface['Groups']:
            if domain_id in group['Groupname']:
                print(f"Deleting Network Interface: {interface['NetworkInterfaceId']}")
                client.delete_network_interface(NetworkInterfaceId=interface['NetworkInterfaceId'])

def delete_efs_volumes(client, domain_id):
    volumes = client.describe_file_systems()
    for volume in volumes['FileSystems']:
        for tag in volume['Tags']:
            if domain_id in tag['Value']:
                print(f"Deleting EFS Volume: {volume['FileSystemId']}")
                client.delete_file_system(FileSystemId=volume['FileSystemId'])

def delete_domain(client, domain_id, domain_name, dry_run=False):
    # Delete Apps
    apps = client['sagemaker'].list_apps(DomainIdEquals=domain_id)
    for app in apps['Apps']:
        print(f"Deleting App: {app['AppName']}")
        if not dry_run:
            print(f"Deleting App: {app['AppName']}")
            client.delete_app(DomainId=domain_id, UserProfileName=app['UserProfileName'], AppType=app['AppType'], AppName=app['AppName'])

    # Delete User Profiles
    user_profiles = client['sagemaker'].list_user_profiles(DomainIdEquals=domain_id)
    for user_profile in user_profiles['UserProfiles']:
        print(f"Deleting User Profile: {user_profile['UserProfileName']}")
        if not dry_run:
            print(f"Deleting User Profile: {user_profile['UserProfileName']}")
            client.delete_user_profile(DomainId=domain_id, UserProfileName=user_profile['UserProfileName'])

    # Delete Domain Resources
    print(f"Deleting Resources Associated with Domain: {domain_id}")
    delete_domain_resources(client, domain_id, domain_name)

    # Delete Domain
    print(f"Deleting Domain: {domain_id}")
    if not dry_run:
        print(f"Deleting Domain: {domain_id}")
        client.delete_domain(DomainId=domain_id, RetentionPolicy={'HomeEfsFileSystem': 'Delete'})


def delete_domain_resources(client, domain_id, domain_name):
    print("Domain ID:", domain_id)
    print("Domain Name:", domain_name)
    
    delete_lambda_functions(client['lambda'], project_id)
    delete_network_interfaces(client['ec2'], domain_id)
    delete_efs_volumes(client['efs'], domain_id)

def get_project_id_from_domain_name(domain_name):
    parts = domain_name.split('-')
    if len(parts) > 2:
        return '-'.join(parts[2:])
    else:
        return None

def get_domain_name(client, domain_id):
    try:
        response=client.describe_domain(DomainId=domain_id)
        print("describe domain response", response)
        return response['DomainName'] if 'DomaiName' in response else None
    except Exception as e:
        print(f"Error reterving domain name for domain ID '{domain_id}': {e}")
        return None

def parse_arguments():
    parser = argparse.ArgumentParser(description="Delete SageMaker domain resources")
    parser.add_argument('--project-id', default=None, help="Project ID suffix to filter domains")
    parser.add_argument('--domain-ids', default=None, help="Comma-separated list of domain IDs to delete")
    parser.add_argument('--dry-run', action='store_true', help="Perform a dry run without deleting resources")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    client = boto3.client('sagemaker')
    project_id = args.project_id
    domain_ids = args.domain_ids

    print("Domain IDs from command line:", domain_ids)  # Debug statement

    if project_id:
        print("Project ID provided:", project_id)  # Debug statement
        filtered_domains = filter_domain_id_with_project_id(client, project_id)
        if not filtered_domains:
            print(f"No domains found with project ID '{project_id}' as suffix.")
            exit(0)
    elif domain_ids:
        print("No project ID provided. Processing domain IDs:", domain_ids)  # Debug statement
        for domain_id in domain_ids.split(','):
            print(f"Processing domain ID: {domain_id}")  # Debug statement
            try:
                response = client.describe_domain(DomainId=domain_id)
                domain_name = response.get('DomainName')
                if domain_name:
                    print(f"Retrieved domain name: {domain_name}")
                    project_id = get_project_id_from_domain_name(domain_name)
                    if project_id:
                        print(f"Extracted project id: {project_id}")
                        filter_domain_id_with_project_id(client, project_id)
                    else:
                        print("Unable to extract project id from domain name")
                else:
                    print(f"Unable to retrieve domain name from domain ID {domain_id}")
            except botocore.exceptions.ClientError as e:
                print(f"Error retrieving domain information for domain ID {domain_id}")
    else:
        print("Neither Project ID nor domain IDs are provided")


    client = {
        'sagemaker': boto3.client('sagemaker'),
        'lambda': boto3.client('lambda'),
        'ec2': boto3.client('ec2'),
        'efs': boto3.client('efs')
    }

    list_all_domains(client['sagemaker'])

    if args.project_id:
        filtered_domains = filter_domain_id_with_project_id(client['sagemaker'], args.project_id)
        if not filtered_domains:
            print(f"No domains found with project ID '{args.project_id}' as suffix.")
            exit(0)
    elif args.domain_ids:
        domain_ids = args.domain_ids.split(',')
        filtered_domains = [{'DomainId': domain_id.strip()} for domain_id in domain_ids]
    else:
        print("Please provide either --project-id or --domain-ids argument.")
        exit(1)

    for domain in filtered_domains:
        print("Processing domain:", domain)  # Debug statement
        domain_id = domain.get('DomainId')
        domain_name = domain.get('DomainName')
        print("Domain ID:", domain_id)  # Debug statement
        print("Domain Name:", domain_name)  # Debug statement
        print(f"Preparing to delete Domain ID: {domain['DomainId']}")
        delete_domain_resources(client, domain_id, domain_name)
        delete_domain(client, domain_id, domain_name, dry_run=False)
        
        

    if args.dry_run:
        print("Dry run completed. No resources were deleted.")
    else:
        print("Deletion completed successfully.")
