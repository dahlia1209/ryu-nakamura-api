import json
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def load_env_from_json():
    with open('C:\\src\\ryu-nakamura-api\\local.settings.json', 'r') as f:
        config = json.load(f)
    
    # Valuesオブジェクト内の値のみを環境変数として設定
    values = config.get('Values', {})
    for key, value in values.items():
        os.environ[key] = str(value)