# 小さなインターネットサービスのライフサイクル教材

**費用が発生します。** 既定では OCI に有料の E4 Flex VM を2台（各1 OCPU／8 GB）、50 GB Boot Volumeを2つ、VCN、Subnet、Internet Gateway、Route Table、Security List、NSGを作成し、各VMに動的Public IPを付けます。無料枠・リージョン在庫は保証しません。作成前に[公式料金表](https://www.oracle.com/cloud/price-list/)と予算を確認してください（料金確認日：2026-10-04）。

**削除はリポジトリ直下から `./scripts/stop-public.sh` → 証跡・必要なバックアップ退避 → `./scripts/cleanup.sh plan` → `./scripts/cleanup.sh destroy`。** 公開停止、認証、destroy plan確認を含みます。VM内のデータは失われます。終了後は[残存確認](docs/operations.md#削除と残存確認)が必要です。手動作成のIAM／Compartment、保存したバックアップやログは残ります。 初期applyの途中失敗でoutputs／SSHが使えなければ `export OCI_PROFILE=internet-service-lab` → `./scripts/cleanup.sh partial-plan` を使い、[残存取得用contextの手動保存](docs/operations.md#初期構築が途中で失敗した場合)後にdestroyします。

[設計基準](docs/design.md)に沿い、構築・監視・公開・保護・廃止を6段階で追体験する社内勉強会教材です。Terraformは単一root／local State、アプリ設定は冪等な適用スクリプトで管理します。実行環境はLinux／Bash（WindowsはWSL2）。実機ハンズオンを前提とせず、[段階教材](stages/)と[15枚の骨子](docs/slide-outline.md)、[証跡](docs/evidence/)を使います。

## 最初に実行すること

```bash
./scripts/preflight.sh
```

Terraform、OCI CLI、Python3、SSH、curl、tar、GNU timeoutが必要です。未導入なら[bootstrap](docs/bootstrap.md)を先に読みます。このリポジトリのコード検証と、費用を伴うクラウド作成は別の作業です。資格情報・作成認可を用意してから次を実行します。

```bash
oci session authenticate --region ap-tokyo-1 --profile-name internet-service-lab
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# terraform.tfvars の全REPLACE、admin_cidr、SSH鍵のパスを実値に編集
./scripts/bootstrap.sh
# OCI ConsoleでSSH host keyを照合しknown_hostsへ登録（bootstrap.md）
./scripts/deploy-stage.sh 1
./scripts/deploy-stage.sh 2
# 管理元だけから http://SERVICE_PUBLIC_IP/ を開きWordPress初期設定を完了
./scripts/deploy-stage.sh 3
```

| 必須入力 | 選び方 |
|---|---|
| region／oci_profile | セッション認証と同じリージョン／profile |
| compartment_ocid | 手動で作った専用Compartment |
| availability_domain | 対象リージョンの実際のAD名 |
| image_ocid | Oracle Linux 9、x86_64、E4対応のPlatform Image OCID |
| ssh_public_key_path | `~/.ssh/internet-service-lab.pub` |
| admin_cidr | 管理PCの出口IPv4、通常 `/32`、許容 `/24`〜`/32` |

`public_web=false` が初期値です。4への移行はWordPressセットアップ済みをDB経由で検査してWeb 80のみ公開します。`./scripts/deploy-stage.sh 4` は公開の認可を得た作業セッションで実行してください。5はログイン・XML-RPCの管理CIDR制限とrate limitです。HTTP構成なので個人情報・実パスワードを投入せず、必要なら[HTTPSの追加条件](docs/operations.md#公開と保護)を満たしてください。

## 運用と検証

- [初期準備とIAM](docs/bootstrap.md)、[運用・バックアップ・復元・削除](docs/operations.md)、[採用判断](docs/adr/001-platform.md)
- [実環境検証](docs/verification.md)、[ローカル検証記録](docs/evidence/local-review.json)、[証跡の取得方法](docs/evidence/README.md)
- `images.lock.json` はレジストリのmanifest digestを固定します。タグ名は解決時の参考情報であり、起動時はdigestを使用します。

クラウド作成・公開・削除、VM上のコンテナ起動、再起動・永続化・経路検証はこの実装作業では未実施です。静的チェックの実施範囲と終了コードは検証記録で確認してください。実測していない画面・アクセスログは成果として作成しません。

独自コード・文書は[MIT License](LICENSE)。外部コンテナ・Providerは各配布物のlicenseに従います（[license方針](docs/license.md)）。
