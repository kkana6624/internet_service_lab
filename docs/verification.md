# 検証範囲と実環境の受け入れ試験

教材資材のローカル確認（2026-10-04）：段階設定6件と証跡manifest7件のJSON parse成功、段階Markdownのcode fence整合確認成功。これはクラウド／コンテナの動作検証ではない。

クラウド検証は未実施。認可された実行担当者が下記を順に実行し、実際の終了コードと観測をmanifestへ記入する。静的に安全そうな設定があることと、未許可送信元から拒否された実測は別の確認。VMが存在しないため、再適用、再起動、データ保持、別送信元拒否、異常復旧、destroyは未検証である。

ローカル検証は [tests/README.md](../tests/README.md) に従い `python3 tests/verify-local.py` を実行する。最新の実測一覧・失敗・未取得は [local-review.json](evidence/local-review.json) を参照（検証実行後に生成）。Terraform fmt／validate、shell構文、Python構文、JSON／YAML、Prometheus config/rules、nginx設定は使えるツールで実行し、依存不足やコンテナ実行不可なら未実施と記録する。コンテナpullだけではOS上の起動・永続化・通信経路を検証したことにはならない。採用imageのdigest・architecture確認とVM上の実行検証は区別する。

## 実環境の試験と合格条件

以下の `remote`／`ip` は `source scripts/common.sh` 後に使える。対象roleのPublic IP、region、Compartment、commit、開始終了UTCを事前記録。SSHホスト鍵をconsoleで確認する。作成・公開・reboot・削除は作業認可のある担当者が行う。

| 試験 | 操作と期待 | 証跡 |
|---|---|---|
| 準備 | bootstrap→deploy-stage 1、cloud-initとfirewall完了 | status、900秒timeout診断 |
| 冪等性 | 同stageを2回適用、secret再生成なし、構成同じ | 2回のexit code、Terraform plan、secretファイルhashを非公開比較 |
| サービス | stage02、管理元HTTP、WordPressセットアップ、DB health | ページ、systemd/Podman |
| 永続化 | 架空の記事→stage再適用→記事を再確認 | 記事ID／再適用前後画面 |
| 再起動 | 各VM reboot→cloud-init/systemd/コンテナready→記事再確認 | boot ID、status、記事 |
| 監視 | stage03、nodeとblackboxのtargets UP、Grafana正常 | targets／dashboard／alerts |
| 異常復旧 | 同内部URLのbefore/during/after、nginx停止復旧 | 時刻、raw計測、probe／alert |
| 公開 | stage04、別送信元Web成功、管理ポート拒否 | curl/nc exit code、送信元分類 |
| 保護 | stage05、非管理元ログイン403、トップ到達 | status、設定diff |
| 廃止 | 公開停止→退避→plan/destroy→残存一覧 | State＋OCI一覧 |

### 冪等性・再起動・データ

```bash
source scripts/common.sh
./scripts/deploy-stage.sh 3
./scripts/deploy-stage.sh 3
terraform -chdir=terraform plan -var=public_web=false -detailed-exitcode
# 0=変更なし、2=差分あり、1=失敗。2は内容を調査し「成功」としない
remote service 'sudo podman volume ls; sudo podman exec lab-db healthcheck.sh --connect --innodb_initialized'
remote service 'sudo systemctl reboot'  # SSH切断を伴うため実際の起動完了は別途待つ
./scripts/wait-ready.sh service 3
remote monitoring 'sudo systemctl reboot'
./scripts/wait-ready.sh monitoring 3
./scripts/verify-stage.sh 3
```

Terraformの公開フラグはその段階の実値に合わせる。stage04以降では `-var=public_web=true`、公開停止後はfalse。再適用はcontainerを再作成するため瞬断しうる。secretの内容は証跡へ出さず、hash／mtimeの比較も非公開に保持する。Grafana password fileの永続化だけで管理者パスワード変更が適用されたとはみなさず、実ログインを確認する。

### 許可／拒否の全経路

```bash
source scripts/common.sh
for role in service monitoring; do
  remote "$role" 'sudo nft list table inet lab_guard; sudo firewall-cmd --list-all; sudo ss -lntp; sudo podman port --all; getenforce'
done
remote monitoring "curl --max-time 5 -fsS http://$(ip service private_ip):9100/metrics"
# Grafana/Prometheus/blackboxはSSHトンネル経由またはVM loopbackで到達
```

OCI console/CLIでSubnetのSecurity Listと両VNICのNSG関連付けを確認する。複数NSG／Security Listの許可は加算されるため、対象NSGだけ読んで拒否と判断しない。nftの専用tableを確認し、OCI／Podman/firewalldの他tableをflushしない。

管理CIDR外にある、実行者が利用を許可された別回線／別PCから、対象VM Public IPだけを低頻度で調べる。

```bash
curl --max-time 5 -sS -o /dev/null -w '%{http_code}\n' http://<service-public-ip>/
curl --max-time 5 -sS -o /dev/null -w '%{http_code}\n' http://<service-public-ip>/wp-login.php
curl --max-time 5 -sS -o /dev/null -w '%{http_code}\n' http://<service-public-ip>/wp-login.php/extra
curl --max-time 5 -sS -o /dev/null -w '%{http_code}\n' http://<service-public-ip>/xmlrpc.php/extra
nc -vz -w 3 <service-public-ip> 22
nc -vz -w 3 <service-public-ip> 3306
nc -vz -w 3 <service-public-ip> 8080
nc -vz -w 3 <service-public-ip> 8081
nc -vz -w 3 <service-public-ip> 9100
nc -vz -w 3 <monitoring-public-ip> 22
nc -vz -w 3 <monitoring-public-ip> 3000
nc -vz -w 3 <monitoring-public-ip> 9090
nc -vz -w 3 <monitoring-public-ip> 9115
nc -vz -w 3 <monitoring-public-ip> 9100
```

非管理元のWebはstage01未稼働／stage02〜03拒否／stage04〜05成功。stage05ログインは403。上のTCP管理／DB／実験／監視ポートは非管理元から拒否。timeoutと拒否応答を区別し、それぞれの終了コードを記録する。ncのオプションはOSの実装によるため `nc -h` で確認する。別回線が用意できない項目は未検証。管理元SSH、監視VMからservice nodeと8081、監視VM自身の9100、トンネルGrafanaは成功を別途確認。

### バックアップ／復元・削除

operationsに従い、VM生成secretと停止したnamed volumeのcold exportを `./scripts/backup.sh all` で採り、`./scripts/restore.sh service .private/backups/<UTC>/service` 等で試験データを復元する。この実装はDB論理dumpではなく、停止中のDBデータvolume全体を保存する。保存だけを復元成功と記録しない。バックアップは機微情報として `.private/` に置き、復元対象role・作成版・停止範囲を確認する。

削除はstage06の順序で実行。Boot Volume、block volume、backup、reserved public IP、DNS、IAM、Compartment、ローカルState、session、rawログを残存表で追跡する。Stateが空、VM一覧が空のどちらか単独では全削除を証明しない。

## 未検証一覧

OCI API権限と実apply、cloud-initの選定OS上での成功、systemd／PodmanとSELinuxの実起動、全imageの実CPU動作、WordPressセットアップ、secret回収、バックアップ／復元、再起動、冪等性の実測、内部／外部到達、別送信元拒否、異常／復旧、公開アクセス観測、画面採取、destroyと課金資源の残存確認。TLSは未実装なのでTLS検証も未実施。
