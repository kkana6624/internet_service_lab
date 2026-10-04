# 証跡の取得と加工

現在、OCIの作成・公開・削除、画面採取、アクセス観測は実施していない。step01〜06のmanifestは未取得のチェックリストであり実測結果ではない。ローカル検証結果は `docs/verification.md` と検証担当者の報告に記録する。

証跡は4種類を区別する：`measured`（実際にコマンド／画面を取得）、`simulated`（模擬と明記）、`explanatory`（構成図・比較設定）、`not-acquired`（未取得）。コマンド失敗は `failed` と終了コードを記録する。0終了でも対象・時刻・条件を記録しなければ主張の根拠にはならない。

```bash
./scripts/collect-evidence.sh 03
# 表示された .private/evidence/<UTC>-step03/manifest.json と raw を確認
```

スクリプトはツール版・image lock・Terraform outputs、両VMのruntime／firewall／ログ、内部専用endpoint計測、Public IP経由計測を採る。HTTP内部計測は監視VM→専用実験URL、外部計測は管理PC→WordPressであり、相互の時間を同条件比較しない。正常／異常／復旧の内部計測同士を比較する。stage01ではworkload計測、stage02では監視ログと内部計測を、まだ未配備のため理由付き `not-acquired` として記録する。stage03以降は内部／外部計測を実行する。06はVM上の現在段階を参照し、削除前の稼働状態を採る。実際に実行したコマンドの失敗は `failed` として残し、成功に書き換えない。

収集先はumask 077の非公開ディレクトリ。Terraform outputsはsecretを出力しないがIPやOCIDを含みうる。プロセス・ログ・画面を収集しただけで公開可能とはみなさない。生ログを `docs/evidence/` に直接コピーしない。

1. manifestのUTC、commit、tag、作業ツリー変更の有無、ローカルsource hash、各VMのdeployed-source hash、OS、ツール／image digest、対象、実験開始終了、コマンド、exit codeを確認。git履歴未作成なら `uncommitted` と明記する。変更ありのHEADだけでは配備版を再現できないため、対応する資材も非公開保管する。source hashはsecret値のhashではない。
2. rawの原本をアクセス制限付き非公開保管し、sha256を取得する。secret・cookie・token・Authorization・private key・セッションファイル・メール等があれば教材へ含めない。
3. 送信元IPは `ADMIN_IP`／`MONITOR_PRIVATE_IP`／`UNKNOWN_IP_01` のように一貫した識別子へ置換。OCID、public IP、アカウント名、ホスト名、メールも必要に応じ同様に加工する。IPの分類根拠はrawで確認し、加工で新たな意味を加えない。
4. スクリーンショットは秘密入力、URL内識別子、アカウント欄を切り抜き／マスク。UTCの時間軸・メトリック名・計測条件は残す。before／during／afterで同じpanel・scale・時間幅を使う。
5. 加工したcopyだけを `docs/evidence/stepNN/` に置き、raw hash、加工内容、加工後hash、確認者、元manifest参照を追記する。別担当者が内容と加工漏れを確認する。
6. 取得されていない画面・ログは未取得のままにする。設定から予想する図は `explanatory` とする。実観測で未知アクセス0件なら観測期間と分類条件を添えて0件と記録する。

各entryに保存する推奨項目は [manifest.example.json](manifest.example.json)。`capture` のUTCは取得終了時刻なので、比較実験の開始時刻は別途追加する。slide-outlineから実測ファイルへリンクを差し替える際も未取得entryは残す。テンプレートの `exit_code:null` は未実行を意味する。

アクセスログはnginx stdout／Podmanログから採る。自己計測UAとblackboxのアクセスを分離し、「未知の送信元」「スキャンらしいURI」「侵害成功」を別の主張として扱う。短い保存量を全観測期間と解釈せず、`--tail 500` という取得上限も明記する。
