import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api import app


@pytest.fixture
def client():
    """FastAPIテストクライアント"""
    return TestClient(app)


@pytest.fixture
def sample_transaction():
    """テスト用のサンプルトランザクション"""
    return {
        "txid": "4d67e21d58126a507390ade6ce2e8bd4343796588b3a5bc27bfd850a62d2dca0",
        "version": 1,
        "locktime": 0,
        "fee": 10000,
        "vin": [
            {
                "utxo_txid": "0437cd7f8525ceed2324359c2d0ba26006d92d856a9c20fa0241106ee5a597c9",
                "utxo_vout": 0,
                "sequence": 0xFFFFFFFF,
                "script_sig_hex": "47304402204e45e16932b8af514961a1d3a1a25fdf3f4f7732e9d624c6c61548ab5fb8cd410220181522ec8eca07de4860a4acdd12909d831cc56cbbac4622082221a8768d1d0901"
            }
        ],
        "outputs": [
            {
                "value": 4999990000,
                "script_pubkey_hex": "4104ae1a62fe09c5f51b13905f07f06b99a2f7159b2225f374cd378d71302fa28414e7aab37397f554a7df5f142c21c1b7303b8a0626f1baded5c72a704f7e6cd84cac"
            }
        ]
    }


@pytest.fixture
def mock_utxo_output():
    """UTXO検証用のモックUTXOアウトプット"""
    mock = MagicMock()
    mock.block_hash = "000000002a22cfee1f2c846adbd12b3e183d4f97683f85dad08a79780a84bd55"
    mock.script_type = "P2PK"
    mock.script_pubkey_hex = "4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac"
    mock.script_pubkey_asm = "OP_PUSHBYTES_65 04678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5f OP_CHECKSIG"
    mock.value = 5000000000
    return mock


class TestCreateTransactionInMempool:
    """create_transaction_in_mempool APIのテストクラス"""

    def test_valid_transaction_success(self, client, sample_transaction, mock_utxo_output):
        """正常なトランザクションの投入テスト"""
        with patch('repository.blockchain.get_utxo') as mock_get_utxo, \
             patch('repository.blockchain.is_spent_utxo') as mock_is_spent, \
             patch('repository.blockchain.execute_script') as mock_execute_script, \
             patch('repository.blockchain.create_transaction_vin') as mock_create_vin, \
             patch('repository.blockchain.create_transaction_output') as mock_create_output, \
             patch('repository.blockchain.TableConnectionManager') as mock_table_manager:

            # UTXO検証のモック設定
            mock_get_utxo.return_value = mock_utxo_output
            mock_is_spent.return_value = False
            mock_execute_script.return_value = True

            # データベース書き込みのモック設定
            mock_create_vin.return_value = None
            mock_create_output.return_value = None

            # TableConnectionManagerのモック設定
            mock_manager = MagicMock()
            mock_table = MagicMock()
            mock_table.create_entity = MagicMock(return_value=None)
            mock_manager.blockchain_transaction_table = mock_table
            mock_table_manager.return_value = mock_manager

            response = client.post(
                "/blockchain/transaction/mempool",
                json=sample_transaction
            )

            assert response.status_code == 200
            result = response.json()
            assert result["txid"] == sample_transaction["txid"]
            assert result["block_hash"] == "0" * 64

    def test_coinbase_transaction_rejected(self, client):
        """COINBASEトランザクションの拒否テスト"""
        coinbase_transaction = {
            "txid": "f5198aeece8b3316f69b57dc2be34e4ff608de45d8f8b2a00d600e7cedbbca46",
            "version": 1,
            "locktime": 0,
            "fee": 0,
            "vin": [
                {
                    "utxo_txid": "0000000000000000000000000000000000000000000000000000000000000000",
                    "utxo_vout": 4294967295,
                    "sequence": 0xFFFFFFFF,
                    "script_sig_hex": "04ffff001d0104"
                }
            ],
            "outputs": [
                {
                    "value": 5000000000,
                    "script_pubkey_hex": "4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac"
                }
            ]
        }

        response = client.post(
            "/blockchain/transaction/mempool",
            json=coinbase_transaction
        )

        assert response.status_code == 400
        assert "COINBASE" in response.json()["detail"]

    def test_nonexistent_utxo_rejected(self, client, sample_transaction):
        """存在しないUTXOを参照するトランザクションの拒否テスト"""
        with patch('repository.blockchain.get_utxo') as mock_get_utxo:
            mock_get_utxo.return_value = None

            response = client.post(
                "/blockchain/transaction/mempool",
                json=sample_transaction
            )

            assert response.status_code == 400
            assert "存在しません" in response.json()["detail"]

    def test_spent_utxo_rejected(self, client, sample_transaction, mock_utxo_output):
        """使用済みUTXOを参照するトランザクションの拒否テスト"""
        with patch('repository.blockchain.get_utxo') as mock_get_utxo, \
             patch('repository.blockchain.is_spent_utxo') as mock_is_spent:

            mock_get_utxo.return_value = mock_utxo_output
            mock_is_spent.return_value = True

            response = client.post(
                "/blockchain/transaction/mempool",
                json=sample_transaction
            )

            assert response.status_code == 400
            assert "利用済み" in response.json()["detail"]

    def test_invalid_signature_rejected(self, client, sample_transaction, mock_utxo_output):
        """無効な署名のトランザクションの拒否テスト"""
        with patch('repository.blockchain.get_utxo') as mock_get_utxo, \
             patch('repository.blockchain.is_spent_utxo') as mock_is_spent, \
             patch('utils.blockchain.execute_script') as mock_execute_script:

            mock_get_utxo.return_value = mock_utxo_output
            mock_is_spent.return_value = False
            mock_execute_script.return_value = False

            response = client.post(
                "/blockchain/transaction/mempool",
                json=sample_transaction
            )

            assert response.status_code == 400
            assert "署名検証エラー" in response.json()["detail"]


class TestGetTransaction:
    """get_transaction APIのテストクラス"""

    def test_get_transaction_success(self, client, sample_transaction):
        """正常なトランザクション取得テスト"""
        txid = sample_transaction["txid"]

        with patch('repository.blockchain.get_transaction') as mock_get_transaction:
            mock_get_transaction.return_value = sample_transaction

            response = client.get(
                f"/blockchain/transaction?txid={txid}"
            )

            assert response.status_code == 200
            result = response.json()
            assert result["txid"] == txid
            assert result["version"] == sample_transaction["version"]
            assert len(result["vin"]) == len(sample_transaction["vin"])
            assert len(result["outputs"]) == len(sample_transaction["outputs"])

    def test_get_transaction_not_found(self, client):
        """存在しないトランザクションの取得テスト"""
        txid = "0000000000000000000000000000000000000000000000000000000000000001"

        with patch('repository.blockchain.get_transaction') as mock_get_transaction:
            mock_get_transaction.side_effect = ValueError(f"Transaction not found: {txid}")

            response = client.get(
                f"/blockchain/transaction?txid={txid}"
            )

            assert response.status_code == 400
            assert "Transaction not found" in response.json()["detail"]

    def test_get_transaction_invalid_txid_too_short(self, client):
        """不正なtxid（短すぎる）のテスト"""
        txid = "abc123"

        response = client.get(
            f"/blockchain/transaction?txid={txid}"
        )

        assert response.status_code == 422

    def test_get_transaction_invalid_txid_too_long(self, client):
        """不正なtxid（長すぎる）のテスト"""
        txid = "0" * 65

        response = client.get(
            f"/blockchain/transaction?txid={txid}"
        )

        assert response.status_code == 422

    def test_get_transaction_missing_txid(self, client):
        """txidパラメータ未指定のテスト"""
        response = client.get("/blockchain/transaction")

        assert response.status_code == 422

    def test_get_transaction_server_error(self, client):
        """サーバーエラー発生時のテスト"""
        txid = "4d67e21d58126a507390ade6ce2e8bd4343796588b3a5bc27bfd850a62d2dca0"

        with patch('repository.blockchain.get_transaction') as mock_get_transaction:
            mock_get_transaction.side_effect = Exception("Database connection error")

            response = client.get(
                f"/blockchain/transaction?txid={txid}"
            )

            assert response.status_code == 500
            assert "内部サーバーエラー" in response.json()["detail"]


class TestGetTransactionMempoolList:
    """get_transaction_mempool_list APIのテストクラス"""

    def test_get_mempool_list_success(self, client):
        """正常なメモリプールリスト取得テスト"""
        sample_mempool_transactions = [
            {
                "txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
                "version": 1,
                "locktime": 0,
                "block_hash": "0" * 64,
                "vin": [
                    {
                        "utxo_txid": "0437cd7f8525ceed2324359c2d0ba26006d92d856a9c20fa0241106ee5a597c9",
                        "utxo_vout": 0,
                        "sequence": 4294967295,
                        "script_sig_hex": "47304402204e45e16932b8af514961a1d3a1a25fdf3f4f7732e9d624c6c61548ab5fb8cd410220181522ec8eca07de4860a4acdd12909d831cc56cbbac4622082221a8768d1d0901",
                        "spent_block_hash": "0" * 64
                    }
                ],
                "outputs": [
                    {
                        "value": 1000000000,
                        "script_pubkey_hex": "4104ae1a62fe09c5f51b13905f07f06b99a2f7159b2225f374cd378d71302fa28414e7aab37397f554a7df5f142c21c1b7303b8a0626f1baded5c72a704f7e6cd84cac",
                        "block_hash": "0" * 64
                    },
                    {
                        "value": 4000000000,
                        "script_pubkey_hex": "410411db93e1dcdb8a016b49840f8c53bc1eb68a382e97b1482ecad7b148a6909a5cb2e0eaddfb84ccf9744464f82e160bfa9b8b64f9d4c03f999b8643f656b412a3ac",
                        "block_hash": "0" * 64
                    }
                ]
            },
            {
                "txid": "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
                "version": 1,
                "locktime": 0,
                "block_hash": "0" * 64,
                "vin": [
                    {
                        "utxo_txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
                        "utxo_vout": 1,
                        "sequence": 4294967295,
                        "script_sig_hex": "483045022100c12a7d54972f26d14cb311339b5122f8c187417dde1e8efb6841f55c34220ae0022066632c5cd4161efa3a2837764eee9eb84975dd54c2de2865e9752585c53e7cce01",
                        "spent_block_hash": "0" * 64
                    }
                ],
                "outputs": [
                    {
                        "value": 3999990000,
                        "script_pubkey_hex": "410411db93e1dcdb8a016b49840f8c53bc1eb68a382e97b1482ecad7b148a6909a5cb2e0eaddfb84ccf9744464f82e160bfa9b8b64f9d4c03f999b8643f656b412a3ac",
                        "block_hash": "0" * 64
                    }
                ]
            }
        ]

        with patch('repository.blockchain.query_transaction_entity') as mock_query:
            mock_query.return_value = sample_mempool_transactions

            response = client.get("/blockchain/transaction/mempool/list")

            assert response.status_code == 200
            result = response.json()
            assert len(result) == 2
            assert result[0]["txid"] == "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16"
            assert result[0]["block_hash"] == "0" * 64
            assert result[1]["txid"] == "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d"
            assert result[1]["block_hash"] == "0" * 64

    def test_get_mempool_list_empty(self, client):
        """空のメモリプールリスト取得テスト"""
        with patch('repository.blockchain.query_transaction_entity') as mock_query:
            mock_query.return_value = []

            response = client.get("/blockchain/transaction/mempool/list")

            assert response.status_code == 200
            result = response.json()
            assert len(result) == 0
            assert result == []

    def test_get_mempool_list_value_error(self, client):
        """ValueErrorが発生した場合のテスト（400エラー）"""
        with patch('repository.blockchain.query_transaction_entity') as mock_query:
            mock_query.side_effect = ValueError("無効なクエリフィルタです")

            response = client.get("/blockchain/transaction/mempool/list")

            assert response.status_code == 400
            assert "無効なクエリフィルタです" in response.json()["detail"]

    def test_get_mempool_list_server_error(self, client):
        """予期しない例外が発生した場合のテスト（500エラー）"""
        with patch('repository.blockchain.query_transaction_entity') as mock_query:
            mock_query.side_effect = Exception("Database connection error")

            response = client.get("/blockchain/transaction/mempool/list")

            assert response.status_code == 500
            assert "内部サーバーエラー" in response.json()["detail"]