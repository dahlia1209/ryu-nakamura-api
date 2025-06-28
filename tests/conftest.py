import json
import os
import pytest
import subprocess


@pytest.fixture(scope="session", autouse=True)
def load_env_from_json():
    with open('C:\\src\\ryu-nakamura-api\\local.settings.json', 'r') as f:
        config = json.load(f)
    
    # Valuesオブジェクト内の値のみを環境変数として設定
    values = config.get('Values', {})
    for key, value in values.items():
        os.environ[key] = str(value)
    os.environ['RECIPENTS_ADDRESS'] = os.getenv('TEST_RECIPENTS_ADDRESS')
        
@pytest.fixture
def auth_headers(scope="session"):
    result = subprocess.run(['python', 'C:\\src\\ryu-nakamura-api\\.venv\\Scripts\\auth_client.py'], capture_output=True, text=True)
    access_token=json.loads(result.stdout)['access_token']
    return  {"Authorization": f"Bearer {access_token}"}