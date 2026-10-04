# 02 サービス：コンテナを消すとデータは消えるか

再現条件：[config/02.json](config/02.json)。Web入口→WordPress→MariaDB。DBはホストpublishなし、WordPressはloopback 8080、nginxは80。DBとWordPressはPodman named volumeで永続化する。secretはVMで生成し、Terraformに渡さない。

問い：コンテナ再作成・VM再起動・VM削除で、記事はそれぞれどうなるか。予想を先に記録する。

```bash
./scripts/deploy-stage.sh 2
./scripts/verify-stage.sh 2
terraform -chdir=terraform output -json vms
# 管理CIDRのPCから http://<service public_ip>/ にアクセス
```

管理CIDR内でWordPressの言語、サイト、管理ユーザーを設定する。HTTPは暗号化されないため教材専用の使い捨てパスワード・架空の記事だけを使う。実アカウント・個人情報を入れない。VM生成DB secretとWordPress管理者パスワードは別物。公開段階は `is_blog_installed()` を実際のDBに問い合わせ、初期設定未完了を拒否する。

「永続化確認」という架空記事を投稿し、記事IDとURLを非公開メモする。`docs/verification.md` の再適用／再起動試験後、同じ記事を確認する。初期DB起動待機やコンテナ失敗はjournaldとPodmanログで調べる。

```bash
./scripts/deploy-stage.sh 2
./scripts/collect-evidence.sh 02
```

予想結果：再適用でsecret再生成なし、記事維持。VM削除ではVM内volumeも失われる。採取時点がstage02なら監視コンテナログと内部計測はまだ対象が存在しないため、収集スクリプトは理由付き `not-acquired` として記録する。実際の収集コマンドの失敗は `failed` と非zeroで残し、成功扱いにしない。

証跡：実ページ、コンテナ一覧とbind、named volume一覧、再起動前後の記事、DB準備確認。secret内容・ログイン画面の入力値は収集しない。
