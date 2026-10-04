# 06 廃止：destroyで本当に全部消えるか

再現条件：[config/06.json](config/06.json)。段階06は `deploy-stage.sh 6` ではなく削除フロー。VM内DB、記事、secret、時系列は削除で失われる。

問い：Stateが空なら課金資源も秘密情報もすべて消えたといえるか。残るものと所有者を先に列挙する。

```bash
./scripts/stop-public.sh
./scripts/collect-evidence.sh 06
# docs/operations.mdに従い必要な証跡・DB/WordPressバックアップ・Stateを非公開退避
oci session validate --profile internet-service-lab --auth security_token
./scripts/cleanup.sh plan
# destroy.tfplanを確認し、必要データ退避・作業認可を再確認
./scripts/cleanup.sh destroy
# 対話で DESTROY を入力する
```

`cleanup.sh plan` 自体も公開停止→証跡採取を行うため、上の順序では再実行する。収集失敗はmanifestへ残し、取得できた分を退避する。`cleanup.sh plan` は収集失敗を表示した上でplanを作成するので、証跡の不足を明示してからdestroy可否を判断する。認証切れならCLIの仕様に従い再認証する。plan保存後の時間経過・別applyで状態が変わった場合はplanを作り直す。料金を伴う作成・公開・削除は認可された担当者が行う。

destroy後、`terraform -chdir=terraform state list` が空であることとOCIの実一覧の両方を確認する。対象Compartment／region／時刻を記録し、instance、boot/block volume、volume backup、reserved public IP、VNIC、VCN／NSGを確認。削除途中の資源は完了まで追跡する。

手動Compartment・IAM Policy・ユーザー、任意DNS・証明書・外部設定、OCIセッションとSSH鍵、local State/plan/tfvars、バックアップ／secret控え／rawログ、教材repoはTerraformの削除対象外。operationsの残存表へ所有者・保存期限・処理結果を記入する。VM内secretはdestroyで失うが控えは別途処理する。

証跡：公開停止の時刻、退避場所（機微値を含めない）、destroy plan/applyと終了コード、State一覧、OCI一覧、残存表。destroy後に収集スクリプトでVMへ接続できないのは正常なので、削除証跡はローカル・OCIから別途採る。
