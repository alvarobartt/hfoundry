# (Experimental) From the Hugging Face Hub to Microsoft Foundry

`hfoundry` is an experimental and independent open-source project not affiliated
with or endorsed by Microsoft.

## Installation

```bash
uv venv --python 3.11
source .venv/bin/activate
uv sync --active
```

## Environment

You need a Microsoft Azure account and bla bla bla, and then set the following
environment variables.

```bash
export SUBSCRIPTION_ID=...
export RESOURCE_GROUP=...
export FOUNDRY_PROJECT=...
export LOCATION=eastus
```

## Run

```bash
uv run hfoundry --model-id Tongyi-MAI/Z-Image-Turbo --instance-type Standard_NC40ads_H100_v5 --instance-count 1
```

Which produces logging messages similarly to the ones below:

```console
MLClient INIT
    SUBSCRIPTION_ID=***
    RESOURCE_GROUP_NAME=***
    WORKSPACE_NAME=***
MLClient SUCCESS
ENDPOINT=endpoint-5938dcb6 BEGIN
ENDPOINT=endpoint-5938dcb6 CREATE / UPDATE
ENDPOINT=endpoint-5938dcb6 SUCCESS
DEPLOYMENT=deployment-9d047244 BEGIN
    ENDPOINT=endpoint-5938dcb6
    MODEL=azureml://registries/HuggingFace/models/tongyi-mai-z-image-turbo/labels/latest
    INSTANCE=Standard_NC40ads_H100_v5 x 1
DEPLOYMENT=deployment-9d047244 CREATE / UPDATE
Check: endpoint endpoint-5938dcb6 exists
...............................................................................................................................................................
DEPLOYMENT=deployment-9d047244 SUCCESS
ENDPOINT=endpoint-5938dcb6 INFORMATION
    SCORING URI=https://endpoint-5938dcb6.eastus.inference.ml.azure.com/predict
    HEADER="azureml-model-deployment: deployment-9d047244"
    PRIMARY KEY=***
    SECONDARY KEY=***
```

> [!WARNING]
> `hfoundry` might even take 30+ minutes, depending on the instance you select,
> the region and the availability, so be patient.

Finally, you can send HTTP requests to it as follows (using the values above):

```bash
curl \
  -X POST \
  "https://endpoint-5938dcb6.eastus.inference.ml.azure.com/predict" \
  -H "Authorization: Bearer ***" \
  -H "azureml-model-deployment: deployment-9d047244" \
  -H "Accept: image/png" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": "Young Chinese woman in red Hanfu, intricate embroidery. Impeccable makeup, red floral forehead pattern. Elaborate high bun, golden phoenix headdress, red flowers, beads. Holds round folding fan with lady, trees, bird. Neon lightning-bolt lamp (⚡️), bright yellow glow, above extended left palm. Soft-lit outdoor night background, silhouetted tiered pagoda (西安大雁塔), blurred colorful distant lights.",
    "parameters": {
      "width": 1024,
      "height": 1024
    }
  }' \
  --output output.png
```

> [!NOTE]
> The cURL request above is for `text-to-image` models only, for other models please
> make sure you use the correct request parameters, as indicated in the model card in
> Microsoft Foundry.
