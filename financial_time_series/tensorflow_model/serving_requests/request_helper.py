""" Module that builds the request and processes the response from the tf-server.

Uses HTTP protocol to send a request to the tf-server and processes it.
"""

import requests


def send_request(input_tensor):
  """Send a request to the TF-server to obtain a prediction.

  Args:
    input_tensor (np.ndarray): input tensor for which we want a prediction

  Returns:
    int: prediction
    str: version of the ML model

  """
  host = '127.0.0.1'
  port = 8500
  model_name = "finance-model"
  path = f'http://{host}:{port}/v1/models/{model_name}'
  payoad = {'instances': input_tensor.tolist()}

  result = requests.post(
      url=f'{path}:predict', json=payoad).json()['predictions'][0]

  print(result)
