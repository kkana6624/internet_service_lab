# ローカル検証

Terraform を init した後、リポジトリルートから実行する。

```bash
terraform -chdir=terraform init -backend=false -lockfile=readonly
python3 tests/verify-local.py
```

`TF`、`PROMTOOL`、`BLACKBOX` に公式実行ファイルのパスを指定できる。
Promtool は固定した Prometheus イメージと同じ版、blackbox_exporter は固定した
blackbox イメージと同じ版を使う。実行ファイルを取得しただけではコンテナ起動を
検証したことにならない。

検証内容は Python / Bash / JSON の構文、Terraform fmt / validate、監視設定と
正常・HTTP失敗・遅延のアラート評価、VM設定の生成・secret再利用・非公開bind・
保護維持・管理CIDR拒否・pull失敗時の段階維持、Prometheus scrape状態判定。
実際の段階移行shellを一時環境で実行し、WordPress照会の終了コード0でも
空応答／DBエラーページ／余分な出力があれば公開移行とTerraform呼び出しを拒否する。
正確な成功markerと終了コード0がそろう場合だけ次の段階処理へ進むことも確認する。
Terraformのmock providerによる5つのplan試験で、公開初期値、公開後のSSH制限、
全世界／広すぎるCIDR／IPv6の管理CIDR拒否も確認する。fixtureの公開鍵は模擬値で、
実VMの認可には使わない。`terraform test` はOCI資格情報・API・クラウド資源を使わない。
PyYAMLが利用できればcloud-initと監視provisioningのYAMLもparseする。
不足ツールは `not-acquired`、検証失敗は `failed` と記録する。失敗があれば終了コードは1。
ツール不足がある場合、終了コード0でもすべての項目が検証済みとは限らない。

レビューで修正した、無応答ready検査の期限、token期限切れでもSSHによる公開停止を
先に行うこと、接続失敗時にも指定回数を計測すること、firewall変更後のPodman通信
復元とコンテナ再適用なしの公開停止を回帰検証する。nginxのPATH_INFO保護は正規表現
選択の静的確認であり、Apache／WordPressへの実リクエスト確認は実環境試験に残る。

`test_vm_generation.py` は一時ディレクトリ内に生成し、rootによる書き込み、chown、
systemctl / firewall / Podman呼び出しを模擬する。実行中のコンテナ、SELinux、
通信許可・拒否、再起動、永続化、バックアップ復元、OCI削除は対象外。
それらは [実環境検証手順](../docs/verification.md) に従う。

実行ごとに `docs/evidence/local-review.json` が更新される。UTC、commit、作業ツリー
変更有無、ファイルhash、実行コマンド、終了コード、版、未検証範囲を残す。
provider plugin の IPC がサンドボックスに遮断された場合、同じコマンドを許可された
実行環境で再実行する。初回失敗を成功に読み替えない。
