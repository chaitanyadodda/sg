import logging
from datetime import timedelta
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from kubernetes.client import models as k8s_models

class KittuK8sPodOperator(BaseOperator):
    template_fields = ("namespace", "image", "cmds", "arguments", "name", "task_id")

    @apply_defaults
    def __init__(
        self,
        namespace: str = "default",
        image: str = "busybox",
        cmds: list = None,
        arguments: list = None,
        name: str = "default_name",
        task_id: str = "default_task_id",
        in_cluster: bool = True,
        is_delete_operator_pod: bool = True,
        get_logs: bool = True,
        image_pull_policy: str = "IfNotPresent",
        full_pod_spec: k8s_models.V1Pod = None,
        execution_timeout: timedelta = timedelta(hours=12),
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.namespace = namespace
        self.image = image
        self.cmds = cmds or []
        self.arguments = arguments or []
        self.name = name
        self.task_id = task_id
        self.in_cluster = in_cluster
        self.is_delete_operator_pod = is_delete_operator_pod
        self.get_logs = get_logs
        self.image_pull_policy = image_pull_policy
        self.full_pod_spec = full_pod_spec
        self.execution_timeout = execution_timeout

        # Logger setup
        self.logger = self._get_logger()

    def execute(self, context):
        self.logger.info(
            "KittuK8sPodOperator Parameters: namespace=%s, image=%s, cmds=%s, arguments=%s, name=%s, task_id=%s, in_cluster=%s, is_delete_operator_pod=%s, get_logs=%s, image_pull_policy=%s, execution_timeout=%s",
            self.namespace,
            self.image,
            self.cmds,
            self.arguments,
            self.name,
            self.task_id,
            self.in_cluster,
            self.is_delete_operator_pod,
            self.get_logs,
            self.image_pull_policy,
            self.execution_timeout,
        )

        if self.full_pod_spec is None:
            self.full_pod_spec = k8s_models.V1Pod(
                spec=k8s_models.V1PodSpec(
                    containers=[
                        k8s_models.V1Container(
                            name=self.name,
                            image=self.image,
                            command=self.cmds,
                            args=self.arguments,
                        )
                    ]
                )
            )

        pod_operator = KubernetesPodOperator(
            namespace=self.namespace,
            image=self.image,
            cmds=self.cmds,
            arguments=self.arguments,
            name=self.name,
            task_id=self.task_id,
            in_cluster=self.in_cluster,
            is_delete_operator_pod=self.is_delete_operator_pod,
            get_logs=self.get_logs,
            image_pull_policy=self.image_pull_policy,
            full_pod_spec=self.full_pod_spec,
        )

        pod_operator.execute(context)

    def _get_logger(self, level=logging.INFO):
        logging.basicConfig(level=level)
        return logging.getLogger(__name__)


Updated DAG Using Custom Operator
from datetime import timedelta
from airflow import DAG, Dataset
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.dates import days_ago
from kubernetes.client import models as k8s_models
from custom_k8s_operator import KittuK8sPodOperator  # Import your custom operator

_le_data = Dataset("file:/Domino/volumes/airflow_pv/logs")

default_args = {
    'owner': 'Airflow',
    'depends_on_past': False,
    'start_date': days_ago(0),
    'catchup': False,
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

CONJUR_CONTAINER_SPEC = k8s_models.V1Container(
    name="authenticator",
    image="docker.repo.usaa.com/cyberark/conjur-kubernetes-authenticator:0.19.0",
    env=[
        k8s_models.V1EnvVar(name="CONJUR_MAJOR_VERSION", value="5"),
        k8s_models.V1EnvVar(
            name="MY_POD_NAME",
            value_from=k8s_models.V1EnvVarSource(
                field_ref=k8s_models.V1ObjectFieldSelector(
                    field_path="metadata.name"
                )
            ),
        ),
        k8s_models.V1EnvVar(
            name="MY_POD_NAMESPACE",
            value_from=k8s_models.V1EnvVarSource(
                field_ref=k8s_models.V1ObjectFieldSelector(
                    field_path="metadata.namespace"
                )
            ),
        ),
        k8s_models.V1EnvVar(
            name="MY_POD_IP",
            value_from=k8s_models.V1EnvVarSource(
                field_ref=k8s_models.V1ObjectFieldSelector(
                    field_path="status.podIP"
                )
            ),
        ),
        k8s_models.V1EnvVar(
            name="CONJUR_APPLIANCE_URL",
            value="https://conjur-follower.grp-inf-csi-conjur.svc.cluster.local",
        ),
        k8s_models.V1EnvVar(
            name="CONJUR_AUTHN_URL",
            value="https://conjur-follower.grp-inf-csi-conjur.svc.cluster.local/authn-k8s/ocp",
        ),
        k8s_models.V1EnvVar(
            name="CONJUR_AUTHN_LOGIN",
            value="host/conjur/authn-k8s/ocp/apps/grp-mlops-notebook-server/*/*",
        ),
        k8s_models.V1EnvVar(name="CONJUR_ACCOUNT", value="usaa"),
        k8s_models.V1EnvVar(
            name="CONJUR_SSL_CERTIFICATE",
            value_from=k8s_models.V1EnvVarSource(
                config_map_key_ref=k8s_models.V1ConfigMapKeySelector(
                    name="conjur-config-map",
                    key="ssl-certificate",
                )
            ),
        ),
    ],
    volume_mounts=[
        k8s_models.V1VolumeMount(
            mount_path="/run/conjur/",
            name="conjur-access-token",
        ),
        k8s_models.V1VolumeMount(
            mount_path="/mnt/airflow-" + Variable.get("AIRFLOW_ENV", "stage") + "-logs",
            name="airflow-" + Variable.get("AIRFLOW_ENV", "stage") + "-logs",
        ),
    ],
)

le_pod = k8s_models.V1Pod(
    spec=k8s_models.V1PodSpec(
        containers=[
            k8s_models.V1Container(
                name="task-basic-python-helloworld",
                image="docker.repo.usaa.com/usaa/grp-python-innersource/python-runtime-data-py39-ubi8:2023.1-3",
                args=['python', '-c', 'import time;start=time.time(); print("Python is getting sleepy..."); [time.sleep(s) for s in range(5, 0, -1)]; print(f"Execution time: {time.time() - start} seconds")'],
                command=["python", "-c"],
                volume_mounts=[
                    k8s_models.V1VolumeMount(
                        mount_path="/run/conjur/",
                        name="conjur-access-token",
                    ),
                    k8s_models.V1VolumeMount(
                        mount_path="/mnt/airflow-" + Variable.get("AIRFLOW_ENV", "stage") + "-logs",
                        name="airflow-" + Variable.get("AIRFLOW_ENV", "stage") + "-logs",
                    ),
                ],
            ),
            CONJUR_CONTAINER_SPEC,
        ],
        volumes=[
            k8s_models.V1Volume(
                name="conjur-access-token",
                empty_dir=k8s_models.V1EmptyDirVolumeSource(),
            ),
            k8s_models.V1Volume(
                name="airflow-" + Variable.get("AIRFLOW_ENV", "stage") + "-logs",
                persistent_volume_claim=k8s_models.V1PersistentVolumeClaimVolumeSource(
                    claim_name="airflow-" + Variable.get("AIRFLOW_ENV", "stage") + "-logs"
                ),
            ),
        ],
    )
)

example_dataset = Dataset("s3://dataset/example.txt")

with DAG(
    'dag_that_executes_via_KittuK8sPodOperator',
    default_args=default_args,
    schedule_interval=None,
    max_active_runs=2
) as dag:

    example_task = KittuK8sPodOperator(
        namespace="grp-mlops-notebook-server",
        image="docker.repo.usaa.com/usaa/grp-python-innersource/python-runtime-data-py39-ubi8:2023.1-3",
        cmds=["python", "-c"],
        arguments=[
            'import time;start=time.time(); print("Python is getting sleepy..."); [time.sleep(s) for s in range(5, 0, -1)]; print(f"Execution time: {time.time() - start} seconds")'
        ],
        name="python-innersource-runtime-hello-world",
        task_id="python-innersource-runtime-hello-world",
        full_pod_spec=le_pod,
        get_logs=True,
        image_pull_policy="Always",
        in_cluster=True,
        is_delete_operator_pod=True,
        outlets=[_le_data],
    )
