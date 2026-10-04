# License方針

独自に作成したコード・設定・教材文書はリポジトリのMIT Licenseを適用します。実測の画面・ログには個人情報や第三者のコンテンツが含まれ得るため、license表記だけで公開可能とは判断せず、加工と公開範囲を別途確認します。Oracle・WordPress・Grafana等の商標は各権利者に帰属します。

Terraform OCI Provider、公式コンテナ、OSパッケージは取得元のlicenseが適用され、このリポジトリのMITへ置換しません。Providerは[Oracleの配布元](https://github.com/oracle/terraform-provider-oci)、コンテナは `images.lock.json` のsource labelや各公式プロジェクトからlicenseを確認します。MariaDB／WordPressのGPL、Prometheus系のApache-2.0、GrafanaのAGPL-3.0等に留意し、実際に採用するdigest内の同梱noticeと依存物を配布形態に応じ確認します。イメージをこのリポジトリへ再配布せずregistryから取得する方式です。lock metadata中のlicense labelは完全な依存license一覧ではありません。
