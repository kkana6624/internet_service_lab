# 03 監視：CPUが低ければ正常か

再現条件：[config/03.json](config/03.json)。Prometheus／Grafana／blackboxを監視VMで起動し、private IPを使ってHTTPとexporterを収集。Prometheusの保持は7日かつ2GB。GrafanaはloopbackにbindしSSHトンネルで閲覧する。

問い：CPU、`up`、`probe_success`、`probe_duration_seconds` はそれぞれ何を答えるか。低CPUで遅い応答を予想する。

```bash
./scripts/deploy-stage.sh 3
./scripts/verify-stage.sh 3
# 別ターミナル（public_ipはterraform output vmsから取得）
ssh -i "${SSH_KEY:-$HOME/.ssh/internet-service-lab}" -N -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 opc@<monitoring-public-ip>
```

`http://127.0.0.1:3000` でprovision済みダッシュボードを開く。Grafana secret回収はoperations参照。`http://127.0.0.1:9090/targets` と `/alerts` も保存する。内部probeは外部Public IPの可用性を保証しない。

```bash
mkdir -p .private/experiment
./scripts/measure.sh internal 10 > .private/experiment/before.txt
./scripts/anomaly-start.sh delay
./scripts/measure.sh internal 10 > .private/experiment/during.txt
# 60秒程度観測し同じダッシュボード・時間幅で画面採取
./scripts/anomaly-stop.sh delay
./scripts/measure.sh internal 10 > .private/experiment/after.txt
./scripts/anomaly-start.sh stop
# WordPress用probe失敗、ProbeFailedを観測（30秒for＋scrape/evaluation遅延）
./scripts/anomaly-stop.sh stop
./scripts/verify-stage.sh 3
./scripts/collect-evidence.sh 03
```

遅延対象はWordPressではなく `http://<service-private-ip>:8081/experiment`。2秒遅延、同URL・同User-Agent・10回・2秒間隔・5秒timeoutで比較する。`stop` はnginxを停止しWordPressへの入口を停止する。遅延と停止を混ぜず復旧を確認する。SSH実行は管理CIDR限定、専用HTTPは監視VMだけに許可。異常中でもCPU上昇は保証しない。

`probe_duration_seconds` は1回のプローブ所要時間でp95ではない。histogramは実装していない。正常／異常／復旧のUTC時刻・条件・終了コードと計測rawをmanifestへ追加する。
