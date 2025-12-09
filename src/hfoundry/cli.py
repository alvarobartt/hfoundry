import argparse
import logging
import os
from uuid import uuid4

from azure.ai.ml import MLClient
from azure.ai.ml.entities import ManagedOnlineDeployment, ManagedOnlineEndpoint
from azure.identity import DefaultAzureCredential
from huggingface_hub import model_info
from huggingface_hub.errors import RepositoryNotFoundError

parser = argparse.ArgumentParser(
    description="Deploy Hugging Face models to Microsoft Foundry"
)
parser.add_argument(
    "--model-id",
    required=True,
    help="The Hugging Face model ID (e.g., microsoft/deberta-xlarge-mnli)",
)
parser.add_argument(
    "--instance-type",
    required=True,
    choices=["Standard_NC40ads_H100_v5"],
    help="The Azure Machine Learning SKU to deploy the model",
)
parser.add_argument(
    "--instance-count",
    type=int,
    default=1,
    help="The number of instances to deploy. Defaults to 1.",
)


def main() -> None:
    args = parser.parse_args()
    if args.instance_count < 1:
        parser.error("--instance-count must be >= 1")

    for env in {"SUBSCRIPTION_ID", "RESOURCE_GROUP", "FOUNDRY_PROJECT"}:
        if not os.getenv(env):
            raise ValueError(
                f"The environment variable `{env}` not set. To run `hfoundry deploy` you need to set the "
                "following environment variables: `SUBSCRIPTION_ID`, `RESOURCE_GROUP`, and `FOUNDRY_PROJECT` "
                "(Microsoft Foundry Hub-based project)"
            )

    subscription_id = os.getenv("SUBSCRIPTION_ID")
    resource_group_name = os.getenv("RESOURCE_GROUP")
    workspace_name = os.getenv("FOUNDRY_PROJECT")

    logging.info("MLClient INIT")
    logging.info(f"    SUBSCRIPTION_ID={subscription_id}")
    logging.info(f"    RESOURCE_GROUP_NAME={resource_group_name}")
    logging.info(f"    WORKSPACE_NAME={workspace_name}")
    client = MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=os.getenv("SUBSCRIPTION_ID"),
        resource_group_name=os.getenv("RESOURCE_GROUP"),
        workspace_name=os.getenv("AI_FOUNDRY_HUB_PROJECT"),
    )
    logging.info("MLClient SUCCESS")

    model_id = args.model_id

    try:
        # NOTE: Validate that the provided `--model-id` exists on Hugging Face
        info = model_info(model_id)
    except RepositoryNotFoundError as e:
        logging.error(f"MODEL={model_id} NOT FOUND ON HUGGING FACE")
        raise e

    model_name = model_id.replace("/", "-").replace("_", "-").lower()
    model_uri = f"azureml://registries/HuggingFace/models/{model_name}/labels/latest"

    try:
        # NOTE: Validate that the provided `--model-id` exists on Microsoft Foundry
        _ = client.models.get(model_name, label="latest")
    except Exception as e:
        raise e

    # TODO: Check that instance is both valid and supported for the given model
    instance_type = args.instance_type
    instance_count = args.instance_count

    endpoint_name = f"endpoint-{str(uuid4())[:8]}"

    # TODO: If the model is gated i.e., `info.gated=True`, validate that the Hugging Face Hub connection is
    # set, and that the token has access to that model via the `huggingface_hub`
    logging.info(f"ENDPOINT={endpoint_name} BEGIN")
    endpoint = ManagedOnlineEndpoint(
        name=endpoint_name,
        properties={"enforce_access_to_default_secret_stores": "enabled"}
        if info.gated
        else {},
    )
    logging.info(f"ENDPOINT={endpoint_name} CREATE / UPDATE")
    client.begin_create_or_update(endpoint).wait()
    logging.info(f"ENDPOINT={endpoint_name} SUCCESS")

    deployment_name = f"deployment-{str(uuid4())[:8]}"

    logging.info(f"DEPLOYMENT={deployment_name} BEGIN")
    logging.info(f"    ENDPOINT={endpoint_name}")
    logging.info(f"    MODEL={model_uri}")
    logging.info(f"    INSTANCE={instance_type} x {instance_count}")
    deployment = ManagedOnlineDeployment(
        name=deployment_name,
        endpoint_name=endpoint_name,
        model=model_uri,
        instance_type=instance_type,
        instance_count=instance_count,
    )
    logging.info(f"DEPLOYMENT={deployment_name} CREATE / UPDATE")
    client.online_deployments.begin_create_or_update(deployment).wait()
    logging.info(f"DEPLOYMENT={deployment_name} SUCCESS")

    logging.info(f"ENDPOINT={endpoint_name} INFORMATION")
    online_endpoint = client.online_endpoints.get(endpoint_name)
    logging.info(f"    SCORING URI={online_endpoint.scoring_uri}")
    # NOTE: Setting the `azureml-model-deployment` header is mandatory, given that the same endpoint
    # can have multiple deployments, hence the need to point to a specific deployment
    logging.info(f'    HEADER={{"azureml-model-deployment": {deployment_name}}}')
    online_endpoint_keys = client.online_endpoints.get_keys(endpoint_name)
    if online_endpoint.auth_mode == "KEY":
        logging.info(f"    PRIMARY KEY={online_endpoint_keys.primary_key}")  # type: ignore
        logging.info(f"    SECONDARY KEY={online_endpoint_keys.secondary_key}")  # type: ignore
