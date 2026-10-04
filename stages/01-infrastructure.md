# 01 基盤：Public IPと公開は同じか

再現条件：[config/01.json](config/01.json)。構成はVCN、Subnet、IGW、route、空のingress Security List、役割別NSG、2 VM。CompartmentとIAMは手動bootstrap。HTTPのNSG規則は管理CIDR限定だが、この段階にはWebプロセスがない。

問い：Public IPが付くと、誰でもSSHできるか。Terraform applyが終わればアプリは使えるか。予想を管理元／管理元以外／監視VMごとに書く。

```bash
./scripts/preflight.sh
./scripts/bootstrap.sh
# docs/bootstrap.mdに従い、OCI consoleで両VMのSSHホスト鍵を照合してknown_hosts登録
./scripts/deploy-stage.sh 1
./scripts/verify-stage.sh 1
./scripts/collect-evidence.sh 01
```

`bootstrap.sh` はplanを表示しapplyする。クラウド作成認可・課金承認を得た実行担当者だけが実行する。SSH鍵は `SSH_KEY`、CLI profileは `OCI_PROFILE` を必要に応じ指定。cloud-init完了とfirewallの準備完了を900秒以内で待つ。失敗時は出力診断を確認し、完成と記録しない。

予想結果：管理元SSH成功、別送信元SSH拒否、Web未稼働。NSGの許可だけで到達が決まらない。`docs/verification.md` の別送信元試験を実施し、権限や送信元がなければ未検証とする。

証跡：plan/apply終了コード、VM一覧、構成図、cloud-init status、firewall/ss。plan/applyは別途非公開保存し、機微情報を加工してstep01に置く。公式画面のスクリーンショットは実際に取得した分だけ。
