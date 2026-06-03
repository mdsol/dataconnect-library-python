
# DataConnect Python Library v1.0.0

## Data Transformation Example Using pandas

The fetched *data* is returned as a pandas `DataFrame`. You can use any pandas operations
for data manipulation.

If you have limited memory allocation, we recommend working on a limited set of
records to reduce development time, and then remove the record limit during
recurring execution.

These functions are not provided by the `dataconnect` library. Below are just
examples of how common Python libraries can be used with `dataconnect`.
For details on how these libraries can be used, please consult the respective
library documentation.


```python
from dataconnect import DataConnectClient
import pandas as pd
from uuid import UUID

user_token = "usertoken_from_dataconnect_developer_center"
data =

with DataConnectClient.connect(token=user_token) as dataconnect_client:
  import_data = dataconnect_client.fetch_data(dataset_uuid=UUID("import_dataset_uuid"))

  data = pd.DataFrame() # should be populated

  # Pivot data
  pivot_df = data.rename(
      columns={
          "HCT": "HCT_result",
          "PLAT": "plat_result",
          "WBC": "wbc_result",
          "HCT_UNIT": "HCT_unit",
          "PLAT_UNIT": "plat_unit",
          "WBC_UNIT": "wbc_unit",
      }
  ).melt(
      id_vars=["patient_id", "site_id", "LBTIM"],
      var_name="lab_test_value",
      value_name="value",
  )

  # Split the lab_test_value column into lab_test and measurement type
  pivot_df[["lab_test", "measure"]] = pivot_df["lab_test_value"].str.rsplit("_", n=1, expand=True)
  pivot_df = pivot_df.pivot_table(
      index=["patient_id", "site_id", "LBTIM", "lab_test"],
      columns="measure",
      values="value",
      aggfunc="first",
  ).reset_index()
  pivot_df = pivot_df.rename(columns={"result": "lab_result", "unit": "lab_unit"})

  # Union the datasets together (pivot_df, import_data)
  pivot_df_renamed = pivot_df.rename(
      columns={
          "patient_id": "subjid",
          "site_id": "siteid",
          "lab_test": "lbtest",
          "lab_result": "lbresn",
          "lab_unit": "lbresu",
      }
  )
  union_df = pd.concat([import_data, pivot_df_renamed], ignore_index=True)

  # Create publish_df by outer-joining import_data to the union_df key set
  # (to include keys only present in derived data)
  publish_df = import_data.merge(union_df[["subjid", "siteid", "visitnum"]].drop_duplicates(), ...)

  print(publish_df.head())
```
