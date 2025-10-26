## ローカル環境実行
```sh
# アプリ起動
cd C:\src\ryu-nakamura-api
.venv\Scripts\activate
func start

## mac
cd /Users/bizd2/src/ryu-nakamura-api
source .venv/bin/activate
func start

#ウェブフック起動
C:\src\ryu-nakamura-api\.venv\stripe.exe login
C:\src\ryu-nakamura-api\.venv\stripe.exe listen  --forward-to localhost:7071/webhooks

```


## テスト

```sh
# C:\src\ryu-nakamura-api\.venv\stripe.exe login 90日ごとに更新が必要
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

### コンテンツ公開手順
・サムネイル画像変換、アップロード
・検証API(api-local)でコンテンツ登録
・コンテンツファイル＋音声合成生成（local pv、local gaの組み合わせ2パターン）
・検証環境確認
・商用APIでコンテンツ登録
・コンテンツファイル＋音声合成生成（production pv, production gaの組み合わせ2パターン）
・サイト商用デプロイ
・ツイート


### 音声合成
```sh
#docker起動
docker run --rm  -p '127.0.0.1:50021:50021' --name voicevox-engine voicevox/voicevox_engine:cpu-latest
#音声合成(新しいターミナルで)
.venv\Scripts\activate
cd C:\src\ryu-nakamura-api\work
python C:\src\ryu-nakamura-api\work\make_voice.py local pv {title_no}
#python C:\src\ryu-nakamura-api\work\make_voice.py production ga
#docker停止
# docker stop voicevox-engine
```

### サムネイル画像形式変換
```sh
cd C:\src\ryu-nakamura-api
.venv\Scripts\activate
python C:\src\ryu-nakamura-api\work\convert_jpeg_to_webp.py "C:\Users\dahli\Downloads\0007.jpg" 0007.webp
```


### セットアップ(Mac)
・VSCODEダウンロード、起動
・source controlを開き、Gitダウンロード、その後vscodeでgithubログイン
・functionをインストール
```sh
brew tap azure/functions
brew install azure-functions-core-tools@4
# if upgrading on a machine that has 2.x or 3.x installed:
brew link --overwrite azure-functions-core-tools@4
```
・Pythonをインストール
```sh
brew install python
```
・仮想環境をインストール
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
・起動
```sh
func start
```



