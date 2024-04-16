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

def delete_lambda_functions(client, project_id, dry_run=False):
    print(f"Filtering Lambda functions for project ID: {project_id} (Dry Run: {dry_run})")
    if not dry_run:
        lambdas = client.list_functions()
        for func in lambdas['Functions']:
            if project_id in func['FunctionName']:
                print(f"Deleting Lambda Function: {func['FunctionName']}")
                client.delete_function(FunctionName=func['FunctionName'])
    else:
        print("Performing dry run for Lambda functions...")
        print("Dry run completed. No Lambda functions were deleted.")

def delete_network_interfaces(client, domain_id, dry_run=False):
    print(f"Filtering Network Interfaces for domain ID: {domain_id} (Dry Run: {dry_run})")
    if not dry_run:
        interfaces = client.describe_network_interfaces()
        for interface in interfaces['NetworkInterfaces']:
            for group in interface['Groups']:
                if domain_id in group['Groupname']:
                    print(f"Deleting Network Interface: {interface['NetworkInterfaceId']}")
                    client.delete_network_interface(NetworkInterfaceId=interface['NetworkInterfaceId'])
    else:
        print("Performing dry run for Network Interfaces...")
        print("Dry run completed. No Network Interfaces were deleted.")

def delete_efs_volumes(client, domain_id, dry_run=False):
    print(f"Filtering EFS Volumes for domain ID: {domain_id} (Dry Run: {dry_run})")
    if not dry_run:
        volumes = client.describe_file_systems()
        for volume in volumes['FileSystems']:
            for tag in volume['Tags']:
                if domain_id in tag['Value']:
                    print(f"Deleting EFS Volume: {volume['FileSystemId']}")
                    client.delete_file_system(FileSystemId=volume['FileSystemId'])
    else:
        print("Performing dry run for EFS Volumes...")
        print("Dry run completed. No EFS Volumes were deleted.")

def delete_domain(client, domain_id, domain_name, dry_run=False):
    print(f"Performing deletion for Domain: {domain_id} (Dry Run: {dry_run})")

    if not dry_run:
        # Delete Apps, User Profiles, Domain Resources, and Domain
        pass
    else:
        print("Performing dry run for domain deletion...")
        # Check for dependencies and print them without deleting
        print("Dry run completed. No resources were deleted.")

def delete_domain_resources(client, domain_id, domain_name, dry_run=False):
    print(f"Deleting Resources Associated with Domain: {domain_id} (Dry Run: {dry_run})")

    if not dry_run:
        delete_lambda_functions(client['lambda'], domain_id, dry_run)
        delete_network_interfaces(client['ec2'], domain_id, dry_run)
        delete_efs_volumes(client['efs'], domain_id, dry_run)
    else:
        print("Performing dry run for domain resources...")
        # Check for dependencies and print them without deleting
        print("Dry run completed. No resources were deleted.")

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

    if args.project_id:
        filtered_domains = filter_domain_id_with_project_id(client, args.project_id)
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
        domain_id = domain.get('DomainId')
        domain_name = get_domain_name(client, domain_id)
        if not domain_name:
            print(f"Error: Unable to retrieve domain name for domain ID '{domain_id}'. Skipping deletion.")
            continue

        print(f"Processing deletion for Domain ID: {domain_id}, Domain Name: {domain_name}")

        # Delete Domain Resources
        delete_domain_resources(client, domain_id, domain_name, args.dry_run)

        # Delete Domain
        delete_domain(client, domain_id, domain_name, args.dry_run)

    if args.dry_run:
        print("Dry run completed. No resources were deleted.")
    else:
        print("Deletion completed successfully.")



-----------------------------

pass-variable:
  stage: deploy
  script:
    - |
      curl --request POST \
           --form "token=$CI_JOB_TOKEN" \
           --form "ref=master" \
           --form "variables[PROJECT_ID]=$PROJECT_ID" \
           https://gitlab.com/api/v4/projects/$TRIAGE_PROJECT_ID/pipeline?ci_pipeline_source=pipeline
  only:
    changes:
      - .gitlab-ci.yml



variables:
  PROJECT_ID: $PROJECT_ID

my-job:
  script:
    - echo "Project ID is $PROJECT_ID"



curl --header "PRIVATE-TOKEN: <your_access_token>" "https://gitlab.com/api/v4/projects/grp-pi-cicd-configs%2Faws-triage"

script:
  - echo "Job token is $CI_JOB_TOKEN"
  - |
    curl --request POST \
         --form "token=$CI_JOB_TOKEN" \
         --form "ref=master" \
         --form "variables[PROJECT_ID]=$PROJECT_ID" \
         https://gitlab.com/api/v4/projects/$TRIAGE_PROJECT_ID/pipeline?ci_pipeline_source=pipeline
