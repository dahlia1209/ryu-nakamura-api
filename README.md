## ローカル環境実行
```sh
# アプリ起動
cd C:\src\ryu-nakamura-api
.venv\Scripts\activate
func start

# webhookをローカルでリッスン
C:\src\ryu-nakamura-api\.venv\stripe.exe listen  --forward-to localhost:7071/webhooks
```

## テスト

```sh
cd C:\src\ryu-nakamura-api\tests
pytest -v
```

## デプロイ
```sh
az functionapp config appsettings delete --name nakamura-fa --resource-group nakamura-rg --setting-names  ENABLE_ORYX_BUILD SCM_DO_BUILD_DURING_DEPLOYMENT
az functionapp config appsettings delete --name nakamura-fa-local --resource-group nakamura-rg --setting-names  ENABLE_ORYX_BUILD SCM_DO_BUILD_DURING_DEPLOYMENT
# 手動デプロイ
```

## アクセストークンを取得
```sh
python C:\src\ryu-nakamura-api\.venv\Scripts\auth_client.py
```

## テーブル書き込み権限付与
```sh
$principalId=az ad sp show --id {uuid}  --query id -o tsv
$resourceGroupName='nakamura-rg'
$accountName='nakamura-cosmosdb-local'
$readOnlyRoleDefinitionId='00000000-0000-0000-0000-000000000002'
az cosmosdb sql role assignment create --account-name $accountName --resource-group $resourceGroupName --scope "/" --principal-id $principalId --role-definition-id $readOnlyRoleDefinitionId

```

### Cluade Code
```sh
wsl -d Ubuntu --user root
cd /mnt/c/src/ryu-nakamura-api
claude
```


### 音声合成
```sh
#docker起動
#docker run --rm  -p '127.0.0.1:50021:50021' --name voicevox-engine voicevox/voicevox_engine:cpu-latest
docker run --rm -d -p '127.0.0.1:50021:50021' --name voicevox-engine voicevox/voicevox_engine:cpu-latest
#音声合成
python C:\src\ryu-nakamura-api\work\make_voice.py local pv
#python C:\src\ryu-nakamura-api\work\make_voice.py production 
#docker停止
docker stop voicevox-engine
```
