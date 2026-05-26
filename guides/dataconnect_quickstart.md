# DataConnect Python Library - Quick Start

Instructions in this document apply only once all the steps of the [Setup document](dataconnect_setup.md) are followed, and you have the [Jupyter notebook](dataconnect_usage.ipynb) opened in your IDE where the Data Connect Python Library package was installed.

*Note:* The `User Authentication Token` used to connect with DataConnect and make function calls can be generated from `iMedidata` > `Data Connect` > `Developer Center`.

## Jupyter
* Make sure the Jupyter notebook being used points to the correct Python Virtual Environment. You can configure that by clicking on `Select Kernel` on the top right, and pick the `venv` that has `Python3.13` configured.
* In the Jupyter notebook, under *Preparation*, enter the user token from `Data Connect Developer Center`.
* Run all the code-cells until **Get all available studies**
  * Feel free to enter a `search_study_name` wildcard value
  * Confirm that the `get_studies()` call works.
* Continue running other code-cells in the notebook as desired.

## Stand-alone code
* You may write your own Python files to access the Data Connect Python Library, but they must be in the same directory.
* Sample code:

  ```python
  from uuid import UUID
  from dataconnect import DataConnectClient

  with DataConnectClient.connect(
      token="user-token-from-dataconnect",
  ) as client:
      result = client.get_studies(search_study_name="clin")
      print(result.total_records) # total number of studies accessible to the user
      print(result.studies)  # list of Study objects
  ```
