# 15枚のスライド骨子

[設計書](design.md)の15枚案に対応します。画面・ログは取得済みmanifestの実測だけを採用し、未取得は「未取得」、構成図・不安全diffは「説明用」と表示します。各段階の[取得ガイド](evidence/README.md)とmanifestに結び付けます。模擬データを作った場合は実測と明確に区別します。

| 枚 | 要点 | 受講者への問い | 必要な証跡・資材 |
|---|---|---|---|
| 1 | 小さなサービスにも運営の責任がある | 公開して終わりでよいか | design.md構成図（説明用） |
| 2 | 予想→変更→観測→考察の6段階 | どの時点で判断するか | stages/の6段階、manifestの取得状況 |
| 3 | 2台のVM、Private／Public経路 | 監視を別VMにする理由は | design.md通信図、step01 VM一覧 |
| 4 | 認証は本人、Policyはできること | tokenを持つだけで安全か | bootstrap.md認証／Policy、加工済validate |
| 5 | planとapplyとreadyは異なる | apply成功なら使えるか | step01 plan／apply／cloud-init／ready |
| 6 | Web入口、WordPress、DB、volume | コンテナを消すとデータは | step02画面、podman一覧、永続化実測 |
| 7 | Public IPと許可経路 | どこが通信を止めるか | step02 NSG／Security List／OS／bind一覧 |
| 8 | 資源、利用者視点、収集健全性 | 正常を何で説明するか | step03 targets、dashboard、PromQL資材 |
| 9 | 低CPUでもサービスは遅い・止まる | どの指標が先に変わるか | step03 同URLの正常／異常／復旧、条件表 |
| 10 | 公開はWebだけを変更 | なぜSSH等は開けないか | step04 NSG／OS差分、外部Public IP疎通 |
| 11 | 未知アクセスは観測次第 | いつ誰が来ると思うか | step04観測開始終了、アクセス数、観測なしも結果 |
| 12 | URIから言える範囲と限界 | スキャンと侵害は同じか | step04加工済実ログ、加工内容、自己アクセス区別 |
| 13 | 許可理由と多層の検証 | 各ポートは誰が必要か | step05管理経路制限、許可／拒否実測、不安全diffは説明用 |
| 14 | 担当システムへ戻す | secret・backup・監視の責任者は | operations.md、未検証項目、HA等の発展課題 |
| 15 | destroyと残存確認 | 全部消えたと言える条件は | step06 destroyログ、StateとOCI一覧、残存台帳 |

9枚目の遅延は専用 `/experiment` の実験でありWordPressそのもののp95とは説明しません。外部Public IP経路と内部Private IPプローブは別の観測です。11・12枚目で不審アクセスがなかった場合は観測時間と「観測なし」を提示し、教材都合で作ったログを実測として差し込みません。15枚目では手動bootstrapのIAM／Compartment、退避バックアップ、ローカルsession／State／ログを意図して残したものとして説明します。
