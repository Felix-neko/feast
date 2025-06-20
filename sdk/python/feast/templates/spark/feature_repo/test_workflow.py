import subprocess
from datetime import datetime

import pandas as pd

from feast import FeatureStore
from feast.data_source import PushMode


def run_demo():
    store = FeatureStore(repo_path=".")
    print("\n--- Run feast apply to setup feature store on Snowflake ---")
    subprocess.run(["feast", "apply"])

    print("\n--- Historical features for training ---")
    fetch_historical_features_entity_df(store, for_batch_scoring=False)

    print("\n--- Historical features for batch scoring ---")
    fetch_historical_features_entity_df(store, for_batch_scoring=True)

    print("\n--- Load features into online store ---")
    store.materialize_incremental(end_date=datetime.now())

    print("\n--- Online features ---")
    fetch_online_features(store, use_feature_service=False)

    print("\n--- Online features retrieved (instead) through a feature service---")
    fetch_online_features(store, use_feature_service=True)

    print("\n--- Run feast teardown ---")
    subprocess.run(["feast", "teardown"])


def fetch_historical_features_entity_df(store: FeatureStore, for_batch_scoring: bool):
    # Note: see https://docs.feast.dev/getting-started/concepts/feature-retrieval for more details on how to retrieve
    # for all entities in the offline store instead
    entity_df = pd.DataFrame.from_dict(
        {
            # entity's join key -> entity values
            "driver_id": [1001, 1002, 1003],
            # "event_timestamp" (reserved key) -> timestamps
            "event_timestamp": [
                datetime(2021, 4, 12, 10, 59, 42),
                datetime(2021, 4, 12, 8, 12, 10),
                datetime(2021, 4, 12, 16, 40, 26),
            ],
            # (optional) label name -> label values. Feast does not process these
            "label_driver_reported_satisfaction": [1, 5, 3],
            # values we're using for an on-demand transformation
            "val_to_add": [1, 2, 3],
            "val_to_add_2": [10, 20, 30],
        }
    )
    # For batch scoring, we want the latest timestamps
    if for_batch_scoring:
        entity_df["event_timestamp"] = pd.to_datetime("now", utc=True)

    training_df = store.get_historical_features(
        entity_df=entity_df,
        features=[
            "driver_hourly_stats:conv_rate",
            "driver_hourly_stats:acc_rate",
            "driver_hourly_stats:avg_daily_trips",
        ],
    ).to_df()
    print(training_df.head())


def fetch_online_features(store, use_feature_service: bool):
    entity_rows = [
        # {join_key: entity_value}
        {
            "driver_id": 1001,
            "customer_id": 201,
            "val_to_add": 1000,
            "val_to_add_2": 2000,
        },
        {
            "driver_id": 1002,
            "customer_id": 202,
            "val_to_add": 1001,
            "val_to_add_2": 2002,
        },
    ]
    if use_feature_service:
        features_to_fetch = store.get_feature_service("driver_activity")
    else:
        features_to_fetch = [
            "driver_hourly_stats:acc_rate",
            "driver_hourly_stats:avg_daily_trips",
            "transformed_conv_rate:conv_rate_plus_val1",
        ]
    returned_features = store.get_online_features(
        features=features_to_fetch,
        entity_rows=entity_rows,
    ).to_dict()
    for key, value in sorted(returned_features.items()):
        print(key, " : ", value)


if __name__ == "__main__":
    run_demo()
