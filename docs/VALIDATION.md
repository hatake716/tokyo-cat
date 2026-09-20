# TOKYO-CAT 0.4.0-dev 検証記録

検証日：2026-09-21。実際の開発APKと収録モデルを検証した記録です。実写相当の品質認定、実機での性能保証、ストア公開の証明ではありません。

## 環境・配布物

- `io.github.hatake716.tokyocat`、versionName `0.4.0-dev`、versionCode `4`。
- JDK 17、Gradle 8.14.3、AGP 8.13.0、compile/target SDK 36、min SDK 29。
- Android Emulator API 35、2400 × 1080、ホストGPU、`emulator-5554`。
- 最終APKの `assembleDebug assembleDebugAndroidTest lintDebug` 成功。lintは0 errors / 9 warnings。既存のSDK・依存更新、画面方向、バックアップ設定等の警告です。
- APKは開発用署名で署名検査成功。5地区・15地点・10GLB、実行コード、全モデルのSHA-256、第三者の帰属表示・ライセンス本文の同梱を検査。
- 物理端末へのインストール・データ変更、Play公開用署名/AAB、GitHub Release作成、Play Console提出は行っていません。

[ビルド](verification/gradle-build.txt)、[lint](verification/lint-debug.txt)、[APK署名](verification/apk-signature.txt)、[パッケージ情報](verification/apk-badging.txt)、[配布物のサイズとSHA-256](verification/artifacts.json)。

## ロジック・モデル

Node.jsの30テストが成功。地区・名所・10猫種・日英の翻訳、移動と境界、発見と挨拶、保存、歩幅と接地、IK、呼吸・耳・座位の計算を検査しています。[ログ](verification/core-tests.txt)。

10 GLBの検査も成功。ファイル長・ハッシュ、全アクセサの範囲と有限値、26ジョイントのウェイト、体表と毛の面方向・法線、2層の毛・部位別根元数・長さ・透過、顔・目のモーフ、CC BYの制作元、6クリップの連続性を検査。移動・姿勢5クリップの各61フレームで足の位置を合成し、床より下に落ちないこと、静止・座位の接地を確認しました。顔のみのBlinkは独立したモーフウェイトを検査します。

顔の座標変換で表裏が反転する不具合を接写で発見し修正しました。計算した法線同士の整合性だけでは見逃すため、元素材の外向き法線との照合も追加しています。[検査ログ](verification/model-validation.txt)、[モデル規模と毛束数](verification/fur-model-stats.json)。

## Androidの操作・表示

最終APKで6本のinstrumentationテストが成功しました。Androidの実際のタッチを使い、JavaScriptはDOM位置・状態の読み取りに使用します。座標、姿勢、写真、発見状態をテストから注入しません。

| 対象 | 結果 | 証拠 |
| --- | --- | --- |
| 顔のアップ・まばたき・距離の復元 | 成功 / 35.857秒 | [ログ](verification/android-face-review.txt) |
| 10種の正面・横・座位、歩行・走行 | 成功 / 117.692秒 | [ログ](verification/android-cat-visual.txt) |
| 長毛の接近表示・描画測定 | 成功 / 38.475秒 | [ログ](verification/android-fur-review.txt) |
| 観光・挨拶・撮影・保存・日英切替 | 成功 / 70.395秒 | [ログ](verification/android-journey.txt) |
| 強制終了後の記録復元 | 成功 / 11.398秒 | [ログ](verification/android-process-restart.txt) |
| 撮影中のNPCの歩行停止 | 成功 / 17.732秒 | [ログ](verification/android-photo-idle.txt) |

顔のテストではラグドールを選択して移動し、カメラの正面・接写・横・斜めを撮影。通常のまばたき周期を待ってまぶたが閉じた画面を記録し、全身へ戻した距離も検査しました。目視で確認した画面は [cat-review.md](verification/cat-review.md)。画像は無加工です。

まばたきと手続き的な関節制御の競合を修正し、固定したCesium 1.127の更新処理と両立させています。内部APIへの依存箇所は [FACE.md](FACE.md) に明記しました。

観光フローでは地区の実タイル読み込み、日英切替、10選択肢、雷門の発見、猫への挨拶、スティック移動、座位・構図変更、撮影、アルバム、MediaStoreへの端末保存、名所解説、Activity再作成を確認。別プロセスで強制終了後の猫種・観光・友だち・写真の復元も確認しています。全15地点への徒歩ルートを完走した検査ではありません。

## 描画測定

標準画質、目標30fps、画面2400 × 1080、3D描画1800 × 810。浅草、長毛ラグドール、周囲12匹も最終0.4モデルの場面です。直近180描画間隔の平均と95パーセンタイルを記録しました。

| 場面 | 平均 | 描画間隔 p95 | 記録 |
| --- | --- | --- | --- |
| 顔の接写、近接後10秒以上待機 | 20.76 fps | 87.1 ms | [face-performance.json](verification/face-performance.json) |
| 全身の毛、近接後14秒待機 | 21.26 fps | 78.1 ms | [fur-performance.json](verification/fur-performance.json) |

顔の細分化・モーフ・質感を追加したことで描画負荷が増えています。測定はホストGPUのエミュレーター上の2場面であり、すべての場面で30fpsを満たす合格判定や実機性能の保証ではありません。物理端末の発熱・消費電力・長時間性能は未検証です。

## 出典・未達の範囲

顔の両作者、CC BY 4.0、変更内容、生成AIを使用したテクスチャ、素材ハッシュを [FACE.md](FACE.md)、[ASSETS.md](ASSETS.md)、[source.json](sources/cat-face/source.json) に保存しています。顔の元メッシュ・モーフはBlenderでも確認し、最終表示はAndroidで確認しました。

都市配信と観光説明のURLは以前の0.2の確認記録を保持しています。[配信元](verification/live-sources.json)、[説明の出典](verification/landmark-sources.json)。今回は実際のゲーム操作中にタイルの読み込みを確認しました。

残る制約：実写と見分けがつかない顔・毛・照明、品種ごとの精密な個体形状、首との色のつながり、独立した毛の物理・影・多重散乱、モーションキャプチャ、複雑な地面での接地、実機の長時間性能、全徒歩経路、障害注入、ストア提出です。

インストール可能な開発APK、10モデルZIP、SHA256SUMS.txtは `artifacts/0.4.0-dev/` に保存しています。
