# ADR 001: 教材の初期プラットフォーム

決定日・公式仕様／料金確認日：2026-10-04。状態：採用、クラウドとコンテナ実行の適合性は未検証。

Oracle Linux 9のx86_64 Platform Imageと `VM.Standard.E4.Flex` を両VMに使います。各1 OCPU／8 GB RAM／50 GB Boot Volumeを既定とします。OCIの[OS／Shape互換性表](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/instances.htm)と各イメージのamd64 manifestを確認しました。Oracle LinuxはOCIの標準管理ユーザーopc、dnf、SELinux、firewalldを使え、少数の手順に収まります。E4はARMを含む差異を教材の主題から外し、小さなDBと監視のメモリ余裕を持たせる選択です。無料枠のShapeではなく、[公式料金表](https://www.oracle.com/cloud/price-list/)に基づき契約・稼働時間・ストレージ・転送量を作成者が見積もります。リージョンの供給と無料枠は保証しません。

OS Image OCIDはregion依存なので実行者がbootstrapで固定し証跡に記録します。cloud-initがインストールするPodmanはOS repository版を採用し、実VMで `rpm -q podman`、`podman version` を記録します。VM実行がないためOS patch／Podmanの実採用版は未取得です。実行時に対応版が違えば同じイメージOCIDで再現し、イメージ更新は独立した検証変更として扱います。

コンテナはrootful Podmanと明示的systemd template unitを採用します。80のbind、ホストnode exporter、named volume管理を単純化するためです。[Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)は現在の推奨候補ですが、OS付属版の対応差を避けるため初版は通常unitとrunnerで起動します。`Restart=always`、enable、ready待機、終了時のstopを実装し、ホスト再起動後の復帰は実機検証事項です。rootfulの影響範囲が大きい限界を持ち、SELinux／firewalld全停止はしません。[Podmanのvolume／SELinux／ログ仕様](https://docs.podman.io/en/latest/markdown/podman-run.1.html)に沿いZ／z、UID、10 MBログ上限を指定します。

## 固定する配布物

Terraform >=1.9,<2、OCI Provider ~>7.0（lock採用版7.32.0）。全コンテナは `images.lock.json` のmanifest digestで固定し、amd64の存在をレジストリで確認しました。tagは解決元で、実行時に追従しません。metadata・固定イメージ内の版情報から取得できた版はnginx 1.30.5、WordPress 7.1.2／PHP 8.3.35、MariaDB 12.3.3、Prometheus 3.15、node exporter 1.12.1、blackbox exporter 0.28です。Grafanaの実アプリ版は未取得で、採用digestとmetadataを記録し、VM起動後にversion出力を証跡へ追加します。digest／metadata確認と起動動作検証は別です。現在コンテナ起動は未検証です。

- [公式WordPressイメージ](https://hub.docker.com/_/wordpress)：php8.3-apache解決digest、FILE変数を使用。
- [公式MariaDBイメージ](https://mariadb.com/docs/server/server-management/automated-mariadb-deployment-and-administration/docker-and-mariadb/mariadb-server-docker-official-image-environment-variables)：lts解決digest、初回初期化とhealthcheckを利用。
- [Prometheus](https://prometheus.io/docs/prometheus/latest/installation/)／[node exporter](https://github.com/prometheus/node_exporter)／[blackbox exporter](https://github.com/prometheus/blackbox_exporter)：プロジェクト配布イメージを使用。
- [Grafana](https://grafana.com/docs/grafana/latest/setup-grafana/configure-docker/)：プロジェクト配布イメージ、provisioningとFILE secret、loopback bind。

監視はPrometheusを7日かつ2 GBに制限し、Grafana datasource／dashboardをコード化します。CPU／メモリ／ディスク、HTTP成功とプローブ時間、upを別パネルにし、probe時間をHTTP p95と呼びません。[Prometheus保持仕様](https://prometheus.io/docs/prometheus/latest/storage/)、[Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)に基づきます。Alertmanagerの通知は未実装で、発火をPrometheus内で観測します。

単一VCN／Public Subnet、2台に動的Public IP、許可のないSecurity List＋役割NSG＋OS guardを採用します。更新／イメージpullに必要なegressは広めです。HA、Kubernetes、集中ログ、GitHub Actions／OIDCは初版から除外し、単一障害点と監視自身の停止の限界を説明します。公開TLS／DNSは未実装の拡張で、5の保護はログイン制限とrate limitです。HTTP実験は機密データを扱いません。

rootは1つで全段階のresource addressを保ち、VM反復のみ薄いmoduleにします。秘密はVM生成、Terraformはsecretを扱いません。実際の段階tagがない場合も1〜5の適用スクリプトと6の削除手順で再現します。完成commitへ異なる名前のtagを付ける方法は採用しません。

公開前の判定は、[WordPress公式の未導入時redirect処理](https://developer.wordpress.org/reference/functions/wp_not_installed/)と[installation mode](https://developer.wordpress.org/reference/functions/wp_installing/)に基づき、WP_INSTALLINGを定義して導入済みを照会します。PHPの終了コードだけでは未導入時の終了を成功と誤認し得るため、明示的な成功markerも照合し、それ以外は公開を拒否します。

内部blackboxはPrivate IPに接続したままWordPressのcanonical Hostに合わせ、redirectを追わず、公開経路へ遷移した成功を内部成功として扱いません。外部Public IPの計測は管理PCから別に取得します。

公開停止はOCI tokenの検査より先にSSHでnginxを停止します。firewalld reload後は
[Podman network reload](https://docs.podman.io/en/latest/markdown/podman-network-reload.1.html)
で通信規則を復元します。guardはExecReloadで更新し、
[systemd Requiresの再起動伝播](https://github.com/systemd/systemd/blob/v252/man/systemd.unit.xml)
を避けます。初回SSHの信頼確認はcloud-initが公開ホスト鍵fingerprintをConsoleへ出力し、
OCI認証済みConsole履歴APIで取得して行います。OSパスワードは設定しません。
