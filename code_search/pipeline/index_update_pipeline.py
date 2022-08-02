# Example Pipeline to update code search UI configuration
# To compile, use Kubeflow Pipelines V0.1.3 SDK or above.

import uuid
from kubernetes import client as k8s_client
import kfp.dsl as dsl
import kfp.gcp as gcp


# disable max arg lint check
# pylint: disable=R0913

def dataflow_function_embedding_op(
        cluster_name: str,
        function_embeddings_bq_table: str,
        function_embeddings_dir: str,
        namespace: str,
        num_workers: int,
        project: 'GcpProject',
        saved_model_dir: 'GcsUri',
        worker_machine_type: str,
        workflow_id: str,
        working_dir: str,):
  return dsl.ContainerOp(
      name='dataflow_function_embedding',
      image=
      'gcr.io/kubeflow-examples/code-search/ks:v20181210-d7487dd-dirty-eb371e',
      command=['/usr/local/src/submit_code_embeddings_job.sh'],
      arguments=[
          f"--cluster={cluster_name}",
          '--dataDir=gs://code-search-demo/20181104/data',
          f"--functionEmbeddingsDir={function_embeddings_dir}",
          f"--functionEmbeddingsBQTable={function_embeddings_bq_table}",
          f"--modelDir={saved_model_dir}",
          f"--namespace={namespace}",
          f"--numWorkers={num_workers}",
          f"--project={project}",
          f"--workerMachineType={worker_machine_type}",
          f"--workflowId={workflow_id}",
          f"--workingDir={working_dir}",
      ],
  ).apply(gcp.use_gcp_secret('user-gcp-sa'))



def search_index_creator_op(
        cluster_name: str,
        function_embeddings_dir: str,
        index_file: str,
        lookup_file: str,
        namespace: str,
        workflow_id: str):
  return dsl.ContainerOp(
      name='search_index_creator',
      image=
      'gcr.io/kubeflow-examples/code-search/ks:v20181210-d7487dd-dirty-eb371e',
      command=['/usr/local/src/launch_search_index_creator_job.sh'],
      arguments=[
          f'--cluster={cluster_name}',
          f'--functionEmbeddingsDir={function_embeddings_dir}',
          f'--indexFile={index_file}',
          f'--lookupFile={lookup_file}',
          f'--namespace={namespace}',
          f'--workflowId={workflow_id}',
      ],
  )


def update_index_op(
        app_dir: str,
        base_branch: str,
        base_git_repo: str,
        bot_email: str,
        fork_git_repo: str,
        index_file: str,
        lookup_file: str,
        workflow_id: str):
  return (dsl.ContainerOp(
      name='update_index',
      image=
      'gcr.io/kubeflow-examples/code-search/ks:v20181210-d7487dd-dirty-eb371e',
      command=['/usr/local/src/update_index.sh'],
      arguments=[
          f'--appDir={app_dir}',
          f'--baseBranch={base_branch}',
          f'--baseGitRepo={base_git_repo}',
          f'--botEmail={bot_email}',
          f'--forkGitRepo={fork_git_repo}',
          f'--indexFile={index_file}',
          f'--lookupFile={lookup_file}',
          f'--workflowId={workflow_id}',
      ],
  ).add_volume(
      k8s_client.V1Volume(
          name='github-access-token',
          secret=k8s_client.V1SecretVolumeSource(
              secret_name='github-access-token'),
      )).add_env_variable(
          k8s_client.V1EnvVar(
              name='GITHUB_TOKEN',
              value_from=k8s_client.V1EnvVarSource(
                  secret_key_ref=k8s_client.V1SecretKeySelector(
                      name='github-access-token',
                      key='token',
                  )),
          )))


# The pipeline definition
@dsl.pipeline(
  name='github_code_index_update',
  description='Example of pipeline to update github code index'
)
def github_code_index_update(
    project='code-search-demo',
    cluster_name='cs-demo-1103',
    namespace='kubeflow',
    working_dir='gs://code-search-demo/pipeline',
    saved_model_dir='gs://code-search-demo/models/20181107-dist-sync-gpu/export/1541712907/',
    target_dataset='code_search',
    worker_machine_type='n1-highcpu-32',
    num_workers=5,
    base_git_repo='kubeflow/examples',
    base_branch='master',
    app_dir='code_search/ks-web-app',
    fork_git_repo='IronPan/examples',
    bot_email='kf.sample.bot@gmail.com',
    # Can't use workflow name as bq_suffix since BQ table doesn't accept '-' and
    # workflow name is assigned at runtime. Pipeline might need to support
    # replacing characters in workflow name.
    # For recurrent pipeline, pass in '[[Index]]' instead, for unique naming.
    bq_suffix=uuid.uuid4().hex[:6].upper()):
  workflow_name = '{{workflow.name}}'
  working_dir = f'{working_dir}/{workflow_name}'
  lookup_file = f'{working_dir}/code-embeddings-index/embedding-to-info.csv'
  index_file = f'{working_dir}/code-embeddings-index/embeddings.index'
  function_embeddings_dir = f'{working_dir}/code_embeddings'
  function_embeddings_bq_table = (
      f'{project}:{target_dataset}.function_embeddings_{bq_suffix}')

  function_embedding = dataflow_function_embedding_op(
    cluster_name,
    function_embeddings_bq_table,
    function_embeddings_dir,
    namespace,
    num_workers,
    project,
    saved_model_dir,
    worker_machine_type,
    workflow_name,
    working_dir)

  search_index_creator = search_index_creator_op(
    cluster_name,
    function_embeddings_dir,
    index_file,
    lookup_file,
    namespace,
    workflow_name)
  search_index_creator.after(function_embedding)

  update_index_op(
    app_dir,
    base_branch,
    base_git_repo,
    bot_email,
    fork_git_repo,
    index_file,
    lookup_file,
    workflow_name).after(search_index_creator)


if __name__ == '__main__':
  import kfp.compiler as compiler

  compiler.Compiler().compile(github_code_index_update, f'{__file__}.tar.gz')
