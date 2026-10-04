# リポジトリ全体レビュー（2026-10-04）

Terraform／OCI／通信制御、Podman／サービス／監視、教材／運用／証跡を3名の
サブエージェントに分担し、主担当が設計との照合・修正・回帰検証を行った。
AGENTS.mdは見つからなかった。クラウドAPIの実行、作成、公開、削除、Git pushは行っていない。

## 見つかった問題と修正

| 優先度 | 問題・影響 | 修正と検証 |
|---|---|---|
| 高 | 初回SSHの鍵確認が、パスワード未設定のopcによるConsoleログインを前提にしていた | [cloud-init](../terraform/modules/vm/cloud-init.yaml)が公開鍵fingerprintをConsoleへ出力し、[bootstrap](bootstrap.md#構築とssh-host-keyの確認)でOCI認証済みConsole履歴を取得して照合。CLIのflagsは導入済み3.83.0のhelpと公式資料で確認。実VMでは未検証 |
| 高 | firewall reload後にPodman通信規則が失われ、公開停止後のWordPress内部通信が壊れうる | [apply-vm.py](../scripts/apply-vm.py)でguardをreloadし、Podman network reloadを実行。[公開停止](../scripts/stop-public.sh)後にready確認。mockで順序・secret保持・pullなしを確認 |
| 高 | `/wp-login.php/extra`等が保護用locationを外れ、ApacheのPATH_INFO処理次第で制限を迂回しうる | [nginx](../service/nginx/nginx.conf)の正規表現を派生パスまで広げた。静的選択テストと[非管理元の実測手順](verification.md#許可拒否の全経路)を追加。実アプリでの迂回・拒否は未検証 |
| 中 | readyの1回のSSH／HTTP検査が止まると、900秒の期限が機能しない。targets待機の90秒表記も実時間と合わない | [wait-ready](../scripts/wait-ready.sh)と[verify-stage](../scripts/verify-stage.sh)で検査全体・個別HTTP・診断を制限。無応答検査を期限で中断する回帰テスト成功 |
| 中 | OCI token期限切れで、SSHによる緊急公開停止さえ実行されない | [stop-public](../scripts/stop-public.sh)はnginx停止を先に実行。認証失敗時に停止維持しTerraformを呼ばない回帰テスト成功 |
| 中 | 接続失敗で計測が1回目に終わり、正常／異常の指定回数がそろわない | [measure](../scripts/measure.sh)は各試行の終了コードを記録して指定回数まで継続。curl／SSH失敗の回帰テスト成功。失敗があれば全体も非0終了 |
| 中 | 残存確認のBlock Volume Backupコマンドが存在しない | [residuals](../scripts/residuals.py)を `oci bv backup list` に修正。公式CLIと導入済みCLIのhelpで確認。実APIの権限・結果は未検証 |
| 中 | 証跡のHEADだけでは、未commit変更やVMへの配備差を識別できない | [evidence](../scripts/evidence.py)に作業ツリー変更有無、ローカル資材hash、VM配備資材hashを追加。取得コマンドのtimeoutは失敗として記録。実VMでの採取は未検証 |

firewall修正は[Podman公式](https://docs.podman.io/en/latest/markdown/podman-network-reload.1.html)、
Console手順は[OCI公式](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/displayingconsole-capturing.htm)、
残存確認は[OCI CLI公式](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/bv/backup/list.html)
と照合した。guard更新にはExecReloadを用い、依存するコンテナへの再起動伝播を避けた。

## 実施した検証

[local-review.json](evidence/local-review.json)の58項目はすべて終了コード0。
Pythonの22テスト（VM操作を模擬）、Terraform 1.16.5のfmt／validate、OCI APIを呼ばない
mock providerの5つのplan試験、14本のshell構文、Python構文、JSON／YAML、
Prometheus 3.15.0のconfig／rules／アラート評価、blackbox exporter 0.28.0の設定を確認した。
[文書確認](evidence/document-checks.json)ではローカルリンク54件とcode fenceにエラーなし。

最初のサンドボックス内validateはProviderのローカルIPC制限で失敗した。
[初回失敗の記録](evidence/review-terraform-sandbox-failure.json)を保持し、制限外の
同じローカル検証で成功を確認した。クラウドAPIを利用した検証ではない。

## 実環境で残る確認

OCIのIAM実効権限・作成・削除、Consoleからの初回鍵照合、OS package導入、Podman起動、
SELinuxと通信制御の実効性、WordPress初期設定、Grafana描画、バックアップ／復元、
再起動復帰、永続化、別送信元からの拒否、異常／復旧、証跡収集、課金資源の残存確認は未検証。
[受け入れ試験](verification.md)を実環境で行う必要がある。TLSは未実装の拡張として扱う。

レビュー実施時点ではGitに初期commit／段階tagがなく、資材は未追跡だった。
その時点の検証manifestは `uncommitted` のまま保持する。今回の実装コミットは
機能別の変更単位であり、段階tagとは区別する。段階設定と適用手順による再現を前提にする。
