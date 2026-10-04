# 運用手順

すべてリポジトリ直下のBashで実行します。`source scripts/common.sh` でTerraform出力・SSHを扱う `remote ROLE COMMAND` 関数を使えます。SSHは管理CIDRからだけ許可します。ログやsecret回収は `.private/` 以下の非公開領域を使用し、証跡公開前に加工します。

## 再起動・ログ・再適用

```bash
source scripts/common.sh
remote service 'sudo systemctl status lab-container@nginx lab-container@wordpress lab-container@db --no-pager'
remote monitoring 'sudo systemctl status lab-container@prometheus lab-container@grafana --no-pager'
remote service 'sudo journalctl -u lab-container@nginx -n 100 --no-pager; sudo podman logs --tail 100 lab-nginx'
remote service 'sudo systemctl restart lab-container@nginx'
```

nginxアクセスログは標準出力へ出し、Podmanのk8s-fileで最大10 MBのログ制限を設定します。foregroundのPodman出力はsystemd journalにも保存し、cloud-initで永続journalと100 MB上限を設定します。コンテナの再作成でk8s-fileログは失われるため、段階をまたぐアクセス履歴は `journalctl -u lab-container@nginx` から取得します。永続データはrootful Podmanのnamed volume `lab-db`、`lab-wordpress`、監視VMの `lab-prometheus`、`lab-grafana`。コンテナはsystemdでenableされ、VM再起動で戻ります。コンテナの起動失敗はsystemdが再試行し、DBとHTTPの準備完了は別途ready待機で確認します。実際の再起動復帰・永続化は[検証手順](verification.md)で確認します。

```bash
source scripts/common.sh
remote service 'sudo reboot' # 切断で非0になる場合あり。ここは次の独立コマンドで確認
./scripts/wait-ready.sh service 3
./scripts/deploy-stage.sh 3
```

段階番号は現在の段階に合わせます。3から4等への前進は可能ですが後退は拒否します。停止・ containmentは `./scripts/stop-public.sh`。再適用は同じsecret／volumeを保持しますがコンテナを再起動し、短い停止が発生します。Terraform user_data変更だけで既存VMが更新されるとは扱いません。Stateを移動・複製して同じ資源を別rootから操作しません。

公開停止はSSHでnginxを止めてからOCIセッションを確認します。token期限切れやTerraform失敗の場合はnginxを停止したまま残すので、認証を復旧して公開停止を再実行します。firewalld reload後は `podman network reload --all` でコンテナ通信規則を復元し、非公開HTTPのreadyを確認します。[Podman公式のreload要件](https://docs.podman.io/en/latest/markdown/podman-network-reload.1.html)。

## Grafanaとsecret

```bash
source scripts/common.sh
"${SSH[@]}" -N -L 3000:127.0.0.1:3000 "opc@$(ip monitoring)"
```

管理PCの `http://127.0.0.1:3000` を開き、ユーザー `admin` で入ります。別ターミナルで `remote monitoring 'sudo cat /var/lib/lab/grafana-password'` によりVM生成secretを確認します。この出力は録画・公開ログへ入れず、必要な場合だけ秘密管理保管庫へ移します。Grafana／Prometheus／blackboxはVM loopback bind、DBはPodman内部ネットワーク、WordPress直結はloopbackです。

DB／GrafanaのsecretはVMで暗号学的乱数を生成し、mode 0400のファイルから `_FILE` 設定で渡します。DBの共有原本とコンテナユーザー用コピーを使い、UID 999／33／472とSELinuxラベルの両方を制御します。Terraform State／user_data／outputはsecretを含みません。secretを手動で消して再生成しても、既存DB／Grafanaのアカウントは自動変更されません。変更時はDBの `ALTER USER` やGrafanaの公式パスワード変更機能で実アカウントを変更し、対応ファイルを同期して再起動します。パスワードをshellの引数・履歴・SQL証跡に残さず保守時間中に行います。[WordPressのFILE変数](https://hub.docker.com/_/wordpress)、[MariaDBの初期化変数](https://mariadb.com/docs/server/server-management/automated-mariadb-deployment-and-administration/docker-and-mariadb/mariadb-server-docker-official-image-environment-variables)、[Grafanaのsecretファイル設定](https://grafana.com/docs/grafana/latest/setup-grafana/configure-docker/)。

## バックアップと復元

以下は稼働停止を伴うコールドバックアップです。公開停止、secret・DB・WordPressを組として退避することでファイル間の不整合を避けます。`.private/backups/<UTC>/` へ保存し、管理者だけ読める暗号化ストレージへ二次保存します。アーカイブはWordPress管理者情報・DB・secretを含み、教材用証跡として公開しません。ローカル空き容量を確認してください。

```bash
./scripts/stop-public.sh
./scripts/backup.sh all
# 出力されたBACKUP_DIRを記録し、非公開保管先へ退避
```

VM再作成後は同一OS／architecture／digest／volume名で現在の段階まで導入し、公開を停止した状態で復元します。復元は現在の保護段階を後退させず、バックアップの段階との大きい方を適用します。復元は現在のデータを上書きするため、まず現在データも別バックアップへ保存し、保存先の内容と所有者を確認します。

```bash
./scripts/restore.sh service .private/backups/REPLACE_UTC/service
./scripts/restore.sh monitoring .private/backups/REPLACE_UTC/monitoring
# スクリプトのRESTORE確認に応答。バックアップの実ディレクトリを指定
source scripts/common.sh
LAB_RESTORE_STAGE=$(remote service 'sudo cat /var/lib/lab/stage')
./scripts/wait-ready.sh service "$LAB_RESTORE_STAGE"
LAB_MONITOR_STAGE=$(remote monitoring 'sudo cat /var/lib/lab/stage')
./scripts/wait-ready.sh monitoring "$LAB_MONITOR_STAGE"
# 両VMが同じ段階のバックアップであることを確認した場合
./scripts/verify-stage.sh "$LAB_RESTORE_STAGE"
```

復元はバックアップの段階を保ち、公開フラグはfalseで復帰します。段階5のバックアップを3へ戻す適用は後退として拒否されます。公開再開は内容・経路を確認して別の認可を得た後、現在段階へのdeploy-stageで実行します。両VMの段階が異なるバックアップを組み合わせず、同じ取得セットを使ってください。

復元後は管理元から投稿・添付ファイル・ユーザー・ログイン、DB health、Grafana dashboardを確認します。IP変更時はWordPressのsiteurl／homeも管理画面またはDBで新しいURLへ変更します。バックアップ取得成功と復元成功は別で、復元実施日時・終了コード・内容確認を非公開manifestへ記録します。Prometheusは7日／2 GB上限の教材データであり、履歴を保存しない選択もできます。Stateは `terraform/terraform.tfstate` とbackupを別の非公開保管先へコピーし、同時実行を避けます。

## 更新・異常対応

イメージ更新では `images.lock.json` のdigestと実アプリ版をまとめて更新し、公式リリースノート・互換性・license・脆弱性を確認します。更新前にバックアップ、同一段階を再適用、ready・投稿・監視・復元を検証します。OS更新は管理元SSHから `sudo dnf upgrade`、必要時再起動、その後ready確認。Providerはlock file更新をreviewし、fmt／validate／planでreplacement有無を確認します。自動で最新tagに追従しません。

```bash
./scripts/measure.sh internal 10
./scripts/anomaly-start.sh delay
./scripts/measure.sh internal 10
./scripts/anomaly-stop.sh delay
./scripts/measure.sh internal 10
```

遅延はPrivate IP:8081の専用 `/experiment` だけを2秒遅くします。WordPressの応答性能の実験ではありません。管理PCのSSH操作のみで制御し、観測元は監視VM。正常・異常・復旧でURL／user agent／回数／間隔／timeoutを同じにします。停止実験は `anomaly-start.sh stop`／`anomaly-stop.sh stop` でnginxを止め戻し、内部blackbox成功・alertの変化を観測します。Public IP側は `measure.sh external 10` を別経路として取得します。

HTTPが止まったら公開停止を優先し、cloud-init、systemd、DB health、nginxログ、ディスク空き、NSG／Security List／nftables／firewalld／bindを順に確認します。CPUが低くてもHTTPやscrapeが正常とは限りません。Prometheus probe_durationは単発プローブ時間で、HTTP p95ではありません。侵害が疑われる場合は公開停止、ログ保全、secret失効／交換、既知の正常イメージから再構築し、スキャン風URIだけで侵害成功と結論しません。

計測は接続失敗・timeoutも各試行の終了コードを記録し、指定回数を最後まで実行します。1回でもcurl／SSHが失敗すれば全体は非0終了です。異常時の非0終了は観測結果として保存し、後続の復旧コマンドを別に実行します。

## 公開と保護

4はHTTP 80だけを外部へ公開します。5は `/wp-login.php` と `/xmlrpc.php` を管理CIDRに限定しrate limitを適用します。管理画面の全経路を認証済みにする仕組みやWAFの代替ではありません。NSG・空の許可を持つSecurity List・OSのguard・bindを合わせて検証します。SELinuxとfirewalldは有効のまま、node exporterのホスト読み取りだけ必要なcontainer label例外を使います。

ドメイン・DNS・公開TLSは初期版では未実装です。HTTPは暗号化されず、ログインcookie等を保護できません。HTTPSへ拡張する場合は所有ドメイン、DNS管理者、証明書の発行・更新・秘密鍵保護・失効を決め、nginxの443 listen、NSGとOSの443許可、WordPress URL／proxy scheme、80から443へのredirectを実装し検証してください。TLS対応なしを安全な本番公開として扱いません。悪い全世界SSH／DB等の設定は説明用diffに限定します。

## 費用管理

2026-10-04に[公式料金表](https://www.oracle.com/cloud/price-list/)を確認。2台のE4 OCPUとmemory、計100 GB Boot Volume、Public IPv4、転送量、バックアップ、任意DNS等が確認対象です。見積りは契約通貨・region・税込条件で作成し、予算通知を設定します。VM停止でもVolume等は残るので費用停止の手段をdestroyと区別します。在庫不足時に高価なShapeへ自動切替しません。

## 削除と残存確認

順序は公開停止→証跡退避→必要なバックアップ→認証確認→destroy plan→destroy→残存確認です。cleanup planはdestroy後にも参照できる `.private/cleanup-context.json` を保存し、公開停止と証跡取得を先に実行します。

```bash
./scripts/stop-public.sh
./scripts/collect-evidence.sh 06
./scripts/backup.sh all # 段階3以降でデータが必要な場合。段階2はbackup.sh service
# 証跡・バックアップを非公開の別保管先へコピー
oci session validate --profile internet-service-lab --auth security_token
./scripts/cleanup.sh plan
terraform -chdir=terraform show destroy.tfplan
./scripts/cleanup.sh destroy
```

destroy後は `scripts/residuals.py` がOCIへ読取APIだけを実行し、`.private/residuals/<UTC>/` に一覧とコマンド・終了コードを保存します。非0のAPIは未確認として残り、削除成功に読み替えません。後から `python3 scripts/residuals.py` で再取得できます。

初期SSH照合用に手動作成したConsole接続・履歴も、bootstrapで保存したIDとConsoleを照合して削除します。これらはTerraformと自動残存一覧の対象外です。

### 初期構築が途中で失敗した場合

初期applyの途中失敗でStateに一部資源だけが残り、outputs・SSH・コンテナが利用できない場合、通常planの代わりにpartial-planを使います。初期bootstrapはWeb非公開です。途中失敗のapplyログを非公開退避し、手動追加した公開経路があればConsoleから停止してから進めます。Stateは削除せず、同じrootでdestroyします。

```bash
export OCI_PROFILE=internet-service-lab
oci session validate --profile "$OCI_PROFILE" --auth security_token
./scripts/cleanup.sh partial-plan
```

outputsがない場合は `OCI_PROFILE` が必須です。SSHやreadyへ依存せずdestroy planを作ります。残存取得用に `.private/cleanup-context.json` をtfvarsの実値から手動で作成します。これは秘密値を含めずインフラ識別子を含むため非公開です。`vms` は不明なら空で構いません。

```json
{
  "region": "ap-tokyo-1",
  "oci_profile": "internet-service-lab",
  "compartment_ocid": "ocid1.compartment.REPLACE",
  "availability_domain": "REPLACE:AP-TOKYO-1-AD-1",
  "vms": {}
}
```

```bash
mkdir -p .private
# 上のJSONを実値に置換して .private/cleanup-context.json に保存
chmod 700 .private
chmod 600 .private/cleanup-context.json
terraform -chdir=terraform show destroy.tfplan
./scripts/cleanup.sh destroy
```

残存取得APIが失敗しても資源削除がロールバックするわけではありません。認証・region・Policyを確認して再取得し、Consoleと照合してください。

保存plan作成後に構成変更した場合はplanを作り直します。destroyで `DESTROY` と入力するとVM内データも消えます。`preserve_boot_volume=false`、動的Public IPなので通常はBoot Volume／IPも削除されますが、空Stateだけで完了としません。

```bash
export LAB_COMPARTMENT_OCID=ocid1.compartment.REPLACE
export LAB_AD=REPLACE_AD_NAME
export OCI_CLI_AUTH=security_token
export OCI_CLI_PROFILE=internet-service-lab
export OCI_CLI_REGION=ap-tokyo-1
oci compute instance list --compartment-id "$LAB_COMPARTMENT_OCID" --all
oci bv boot-volume list --compartment-id "$LAB_COMPARTMENT_OCID" --availability-domain "$LAB_AD" --all
oci bv volume list --compartment-id "$LAB_COMPARTMENT_OCID" --all
oci bv boot-volume-backup list --compartment-id "$LAB_COMPARTMENT_OCID" --all
oci bv backup list --compartment-id "$LAB_COMPARTMENT_OCID" --all
oci network public-ip list --compartment-id "$LAB_COMPARTMENT_OCID" --scope REGION --all
oci network vcn list --compartment-id "$LAB_COMPARTMENT_OCID" --all
```

両VMがTERMINATEDになり、VCN・Volume・予約IP・バックアップ等が意図どおり残らないことをConsoleでも確認します。予約IPを追加した場合はその所有者が別途削除。DNS・証明書・外部サービスは初期版では作らず、追加したら台帳に記録して削除。IAM Policy・ユーザー／グループ・Compartmentは手動bootstrapの管理者が保存／廃止判断します。ローカルState／plan／tfvarsは調査要否を判断して非公開保管または削除し、OCI sessionは期限切れとローカルtoken／key_fileの処分を別々に確認します。共有SSH鍵を誤って消さず教材専用鍵の保存期間を決めます。ログ・証跡・DBバックアップは公開範囲と期限を決め、公開Gitには加工済み教材だけを残します。

内部HTTPプローブはPrivate IPへ接続し、HostヘッダーのみWordPressのPublic IPに合わせます。redirectには追従しません。Public IPへのredirectが必要な応答は内部成功とは扱わず、外部経路と混同しません。WordPressのsiteurl／homeを初期手順のPublic IP以外へ変える場合、このHost設定も見直して再検証します。
