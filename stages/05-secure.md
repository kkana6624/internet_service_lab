# 05 保護：許可する理由を説明できるか

再現条件：[config/05.json](config/05.json)。Web公開は継続し、nginxの `/wp-login.php` と `/xmlrpc.php` は管理CIDRだけに制限し、5回/分のrate limitを加える。共通のSSH／監視／DB制限は最初から有効。TLSは初期版に未実装で、実装済みと説明しない。

問い：NSGだけでDB非公開を証明できるか。許可規則が別のSecurity Listにあればどうなるか。ログイン入口制限は脆弱性修正の代わりになるか。

```bash
./scripts/deploy-stage.sh 5
./scripts/verify-stage.sh 5
./scripts/collect-evidence.sh 05
```

管理PCからトップページとログイン入口の到達を確認し、別送信元からトップは到達、ログイン入口は403、SSH等は拒否を確認する。`/wp-login.php/extra` と `/xmlrpc.php/extra` のPATH_INFO付きURLも403になることを確認する。nginx許可の確認には低頻度のリクエストを使い、制限試験は別条件として実行する。rate limitに当たった応答とsource拒否を混同しない。

NSG、空のingress Security List、firewalld、専用nft table、`ss`、Podman portを照合する。OS再起動後も同じ条件で許可／拒否試験を繰り返す。SELinux/firewall全停止で解決しない。監視はprivate IP、Grafanaはloopback＋トンネル、MariaDBはコンテナネットワークのみ。

更新・バックアップ・復元はoperationsに従う。HTTPSが必要なら所有ドメイン、DNS、証明書、80→443リダイレクト、NSG／OS rule、期限監視を追加設計・検証し、ADRと料金確認を更新する。現状は公開HTTPの限界を教材に示す。

証跡：生成nginx設定のbefore/after、両送信元の終了コード／HTTP status、通信制御全層、未検証送信元の一覧。危険diffは未適用のまま保管する。
