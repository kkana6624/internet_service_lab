# 手動bootstrap

実行環境はLinux／Bash、Terraform >=1.9,<2、OCI CLI 3系、Python3です。Terraform Providerはlock fileのOracle OCI 7.32.0を使います。`terraform init -lockfile=readonly` を標準にし、Provider更新は検証後に別変更として行います。OCI CLIは[公式インストール手順](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm)を利用し、`oci --version`を証跡に記録します。

## Compartmentと実行主体

管理者が専用Compartment `internet-service-lab`、専用グループ `InternetServiceLabOperators`、専用実行ユーザーを手動作成し、ユーザーをグループへ追加します。TerraformはCompartmentやPolicyを作成しません。管理者profileを利用すると権限は限定されません。

以下はIdentity Domain名 `Default` の例です。実際のDomain／グループ／Compartment名へ置き換え、管理者がPolicyを配置します。

```text
Allow group 'Default'/'InternetServiceLabOperators' to manage instance-family in compartment internet-service-lab
Allow group 'Default'/'InternetServiceLabOperators' to manage volume-family in compartment internet-service-lab
Allow group 'Default'/'InternetServiceLabOperators' to manage virtual-network-family in compartment internet-service-lab
Allow group 'Default'/'InternetServiceLabOperators' to read instance-images in tenancy
Allow group 'Default'/'InternetServiceLabOperators' to read app-catalog-listing in tenancy
Allow group 'Default'/'InternetServiceLabOperators' to inspect compartments in tenancy
```

作成・更新・削除の権限は専用Compartmentに限定します。instance-familyにはVMと関連接続、volume-familyにはBoot Volume等、virtual-network-familyにはVCN／VNIC／NSG等の操作が含まれます。教材用の小さなCompartment全体を管理する集合であり、APIごとの完全最小権限ではありません。[Core Servicesの公式権限表](https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/corepolicyreference.htm)でLaunchInstance／TerminateInstanceの依存権限を確認しています。

補助のtenancy権限は**読取だけ**です。Platform Imageの検索・起動用にinstance-images、起動依存のapp-catalog-listing、AD列挙用にinspect compartmentsを与えます。後者はCompartment名等も見えるため管理者の合意を得てください。[IAM権限表](https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/iampolicyreference.htm)はListAvailabilityDomainsがCOMPARTMENT_INSPECTに対応すると記載しています。AD／imageを管理者が指定し、このユーザーで列挙しない運用なら補助権限を減らせるか実APIで確認します。広い `manage all-resources in tenancy` は不要です。現在この集合の実環境plan／applyは未検証であり、403時は失敗APIとrequest IDを非公開記録し、依存権限を確認して修正します。

## Security Token認証

```bash
oci session authenticate --region ap-tokyo-1 --profile-name internet-service-lab
oci session validate --profile internet-service-lab --auth security_token
```

`~/.oci/config` の指定profileにセッション秘密鍵の `key_file` と `security_token_file` が設定されます。秘密鍵・トークンはローカルに存在し、短命tokenでも秘密鍵が不要になるわけではありません。設定・鍵・tokenはownerだけ読める権限にし、Git、転送tar、証跡へ入れません。token既定期限は1時間、有効期間内の更新は `oci session refresh --profile internet-service-lab --auth security_token`、期限切れは再authenticateします。plan／apply／destroy前にvalidateします。[CLI公式仕様](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/clitoken.htm)、[ProviderのSecurityToken設定](https://docs.oracle.com/en-us/iaas/Content/dev/terraform/configuring.htm)を参照してください。

## SSH鍵と入力

```bash
ssh-keygen -t ed25519 -f ~/.ssh/internet-service-lab -C internet-service-lab
chmod 600 ~/.ssh/internet-service-lab
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

パスフレーズ付き鍵は `ssh-add ~/.ssh/internet-service-lab` でagentへ読み込みます。スクリプトはBatchModeを使うので対話入力できません。秘密鍵パスを変える場合は `export SSH_KEY=/absolute/path/to/key` を設定します。`admin_cidr` は外部公開用の自身の管理回線のIPv4 CIDRを管理者に確認し、通常 `/32` にします。サンプルの192.0.2.1は文書用で使えません。

ADとPlatform Imageは同じリージョンで列挙します。`LAB_TENANCY_OCID`、`LAB_COMPARTMENT_OCID` は実値に置き換えます。

```bash
export LAB_TENANCY_OCID=ocid1.tenancy.REPLACE
export LAB_COMPARTMENT_OCID=ocid1.compartment.REPLACE
oci iam availability-domain list --compartment-id "$LAB_TENANCY_OCID" --region ap-tokyo-1 --profile internet-service-lab --auth security_token
oci compute image list --compartment-id "$LAB_COMPARTMENT_OCID" --operating-system 'Oracle Linux' --operating-system-version 9 --shape VM.Standard.E4.Flex --all --region ap-tokyo-1 --profile internet-service-lab --auth security_token
```

結果からx86_64のOracle Linux 9 Platform Imageを選び、OCID、display-name、作成日を非公開manifestとtfvarsに保存します。ARMイメージをE4に指定しません。採用した実OCIDはリージョン依存のためリポジトリ固定値にしません。無料枠・収容力不足では勝手に別Shapeへ変更せず、予算と互換性を再確認します。[OCIのOS／Shape互換性](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/instances.htm)。

## 構築とSSH host keyの確認

```bash
./scripts/preflight.sh
./scripts/bootstrap.sh
terraform -chdir=terraform output -json vms
```

applyはVM作成までです。cloud-initは公開ホスト鍵のfingerprintを `LAB_HOSTKEY` としてserial consoleへ出力します。OCIの認証済みAPIでConsole履歴を取得し、管理PCの `ssh-keyscan` と照合します。opcに既定OSパスワードはなく、serial接続だけではVM内のshellを実行できません。この手順はOSログインを使いません。`ssh-keyscan`だけでは本人確認になりません。

Console履歴取得にはInstance Console Connectionが先に必要です。専用RSA鍵を用意し、各VMに対して次を実行します。bootstrapの `manage instance-family` 権限の範囲です。[公式Console履歴手順](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/displayingconsole-capturing.htm)、[serial接続の前提](https://docs.oracle.com/en-us/iaas/Content/Compute/References/serialconsole.htm)。

```bash
umask 077
mkdir -p .private
ssh-keygen -t rsa -b 4096 -f .private/console-key -N ''
source scripts/common.sh
LAB_OCI_FLAGS=(--region "$(value region)" --profile "$(value oci_profile)" --auth security_token)
for LAB_ROLE in service monitoring; do
  LAB_INSTANCE_ID=$(ip "$LAB_ROLE" id)
  LAB_CONNECTION_ID=$(oci compute instance-console-connection create \
    --instance-id "$LAB_INSTANCE_ID" --ssh-public-key-file .private/console-key.pub \
    --wait-for-state ACTIVE --max-wait-seconds 300 --query data.id --raw-output "${LAB_OCI_FLAGS[@]}")
  printf '%s\n' "$LAB_CONNECTION_ID" > ".private/$LAB_ROLE.console-connection-id"
  LAB_HISTORY_ID=$(oci compute console-history capture --instance-id "$LAB_INSTANCE_ID" \
    --wait-for-state SUCCEEDED --max-wait-seconds 300 --query data.id --raw-output "${LAB_OCI_FLAGS[@]}")
  printf '%s\n' "$LAB_HISTORY_ID" > ".private/$LAB_ROLE.console-history-id"
  oci compute console-history get-content --instance-console-history-id "$LAB_HISTORY_ID" \
    --file ".private/$LAB_ROLE.console.log" "${LAB_OCI_FLAGS[@]}"
  grep -F 'LAB_HOSTKEY' ".private/$LAB_ROLE.console.log"
done
```

cloud-initがまだ鍵を出力していない場合は待って履歴captureだけを再実行します。既存Console接続は再作成せず、旧履歴IDは別ファイルへ保存するか旧履歴を削除してからIDを更新します。履歴は末尾1 MBなのでmarkerが消えた場合も、照合せずSSHへ進みません。信頼済み管理経路で確認するかVM再作成を検討します。生Consoleログは非公開のまま保存します。CLIで作成したConsole接続・履歴のIDはTerraform管理外として残存台帳へ記録します。

```bash
# LAB_SERVICE_IP / LAB_MONITOR_IPにoutputのPublic IPを入れる
export LAB_SERVICE_IP=REPLACE
export LAB_MONITOR_IP=REPLACE
mkdir -p .private
ssh-keyscan -T 10 -t ed25519 "$LAB_SERVICE_IP" "$LAB_MONITOR_IP" > .private/hostkeys
ssh-keygen -lf .private/hostkeys
# 両VMのConsole履歴のLAB_HOSTKEY fingerprintと一致した場合のみ次を実行
cat .private/hostkeys >> ~/.ssh/known_hosts
./scripts/deploy-stage.sh 1
```

照合後は作成したConsole接続・履歴だけを削除します。途中失敗で残ったものも保存したIDとConsoleを照合して処理します。

```bash
for LAB_ROLE in service monitoring; do
  oci compute console-history delete --instance-console-history-id "$(cat ".private/$LAB_ROLE.console-history-id")" --force "${LAB_OCI_FLAGS[@]}"
  oci compute instance-console-connection delete --instance-console-connection-id "$(cat ".private/$LAB_ROLE.console-connection-id")" --force "${LAB_OCI_FLAGS[@]}"
done
# 接続削除完了後、不要になった専用Console鍵の保管／削除を判断
```

スクリプトはStrictHostKeyChecking=yesです。再作成時は新VMの鍵をConsole履歴で再確認し、古いIPエントリを `ssh-keygen -R IP` で除去して登録し直します。cloud-init待機は900秒、準備完了待機も既定900秒、失敗時にsystemd／コンテナ診断を最大20秒取得します。強制終了猶予は2秒です。タイムアウトを無視して次段階へ進めません。

## 初期apply失敗からの廃止

初期作成途中の失敗でoutputsやSSHが使えない場合も、ローカルStateを残して削除できます。

```bash
export OCI_PROFILE=internet-service-lab
oci session validate --profile "$OCI_PROFILE" --auth security_token
./scripts/cleanup.sh partial-plan
```

次に[operationsの途中失敗手順](operations.md#初期構築が途中で失敗した場合)どおり `.private/cleanup-context.json` を実tfvarsから手動保存します（region、oci_profile、compartment_ocid、availability_domain、vms:{}）。planを確認し `./scripts/cleanup.sh destroy` を実行します。partial-planはSSH／準備完了を前提とせず、outputsなしではOCI_PROFILE指定が必須です。destroy後の読取残存一覧を確認し、初期失敗のAPIログを成功結果として扱いません。
