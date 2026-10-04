# 04 公開：Webを公開すると誰が来るか

再現条件：[config/04.json](config/04.json)。WordPress初期設定が完了していることを確認し、Web80のみ世界へ許可する。SSH・DB・Grafana・Prometheus・exporterは公開しない。初期版の公開HTTPは暗号化されないので短時間の教材実験とし、HTTPS追加までは実サービスの認証や実データを扱わない。

問い：管理元以外の接続で、WebとSSHの結果はどう変わるか。未知のアクセスは観測できるか。設定差分と観測を別々に予想する。

```bash
./scripts/deploy-stage.sh 4
./scripts/measure.sh external 10
./scripts/collect-evidence.sh 04
```

`deploy-stage` はVM適用・準備確認の後にNSGを変更する。管理元と別の外部送信元から `curl --max-time 5 http://<service-public-ip>/` を実行する。管理元のPublic IP疎通は「外部経路測定」、非管理元試験は「公開範囲測定」と分ける。

観測開始・終了をUTCで記録し、例えば30分の観測窓を実際の値で残す。nginxの実アクセスログから自身のUser-Agent `lab-controlled-measure`、監視probe、手動閲覧を区別する。未知URI・スキャンらしいアクセスだけでは侵害成功と判断しない。観測できなければ「この期間、不審アクセスは観測されなかった」と記載する。未知アクセスを自作して実攻撃として見せない。

証跡：段階03→04のWeb規則差分、外部疎通と拒否試験、開始終了時刻、ログ件数／UA分類、加工済み実ログ。教材で示す危険公開設定は [説明用diff](../docs/examples/unsafe-public.diff) だけとする。

実験終了時は必要に応じ `./scripts/stop-public.sh`。nginx停止→NSGを管理元限定→OS guardを限定→nginx再開の順で、イメージpullや全コンテナ再適用は行わない。public_web=falseをtfvarsにも明記し、後日の不用意な再公開を防ぐ。
