import json
import os
import pytest
import subprocess


@pytest.fixture(scope="session", autouse=True)
def load_env_from_json():
    # conftest.py の場所を基準にプロジェクトルートを探す
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    settings_path = os.path.join(base_dir, 'local.settings.json')
    
    with open(settings_path, 'r') as f:
        settings = json.load(f)
    
    for key, value in settings.get('Values', {}).items():
        os.environ.setdefault(key, str(value))
        
@pytest.fixture
def auth_headers(scope="session"):
    # macOS/Linux対応の相対パスに変更
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    auth_script = os.path.join(base_dir, '.venv', 'bin', 'auth_client.py')  # macは bin/
    
    result = subprocess.run(
        ['python', auth_script],
        capture_output=True,
        text=True
    )
    
    # デバッグ用：失敗時にエラー内容を表示
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(
            f"auth_client.py の実行に失敗しました\n"
            f"returncode: {result.returncode}\n"
            f"stdout: {result.stdout!r}\n"
            f"stderr: {result.stderr!r}"
        )
    
    access_token = json.loads(result.stdout)['access_token']
    return {"Authorization": f"Bearer {access_token}"}