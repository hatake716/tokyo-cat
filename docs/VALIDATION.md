# TOKYO-CAT 0.3.0-dev 検証記録

検証日：2026-09-21。これは動作する開発版の検証です。フォトリアル品質の完成、実機での性能保証、ストア公開の証明ではありません。

## 実行環境とビルド

- アプリID：`io.github.hatake716.tokyocat`
- versionName：`0.3.0-dev`、versionCode：`3`
- JDK 17、Gradle 8.14.3、Android Gradle Plugin 8.13.0
- compileSdk / targetSdk 36、minSdk 29（Android 10）
- Android Emulator API 35、2400 × 1080、ホストGPUを利用。端末指定は `emulator-5554`。
- 接続されている物理端末にはインストールやデータ変更をしていません。

`assembleDebug assembleDebugAndroidTest lintDebug` は成功。lintは **0 errors / 9 warnings**。警告は新しいSDK・依存バージョン、画面方向指定、Android 12以降のバックアップ設定などです。詳細は [gradle-build.txt](verification/gradle-build.txt) と [lint-debug.txt](verification/lint-debug.txt)。

APKは開発用証明書で署名され、署名検証を通過しています。Play公開用署名、AAB、GitHubリリース、Play Consoleへの提出は行っていません。

## ゲームロジック・モデル

- Node.js の **30テスト成功**。5地区・15地点・10モデル、翻訳キー、メートル単位の地理移動、走行速度、斜め移動、境界、発見範囲、挨拶距離、不正セーブの復旧、保存の往復、歩行・速歩の脚運び、停止時の接地を検査。追加テストでは、定速で接地足が前進量を相殺すること、全脚長でIKが足の目標点へ届くこと、離地・着地の速度連続性、脚長と歩幅、まばたき・呼吸・耳、座位への遷移中の接地を検査。
- **10 GLBすべて検査成功**。ファイル長・SHA-256、アクセサの参照範囲、有限値、スキンのウェイト和、24ジョイントの参照、法線と面の表裏の整合性、埋め込み素材、制作元のメタデータを検査。下毛・差し毛の2層、各層の部位別根元数、毛丈、BLENDマテリアル、毛束の法線と面方向、スキン、法線テクスチャ、5クリップのループも検査。全クリップ・全61フレームについてGLBに記録された関節変換を合成し、足の支点が地面を下回らないことと、静止・座位の接地を確認。
- 配布APKをZIPとして開き、収録した5地区・15地点・10GLB、モデルSHA-256、最終描画設定を確認。動画・音声ファイルの混入なし。

証拠：[core-tests.txt](verification/core-tests.txt)、[model-validation.txt](verification/model-validation.txt)、[artifacts.json](verification/artifacts.json)、[apk-signature.txt](verification/apk-signature.txt)、[apk-badging.txt](verification/apk-badging.txt)。

## Android上の操作検証

最終0.3 APKで5本のinstrumentationテストがすべて成功しました。猫の接近表示・性能計測36.838秒、10種と歩行・走行の表示113.055秒、観光・撮影・保存59.247秒、プロセス再起動10.311秒、撮影中のNPC静止16.208秒。

テストはAndroidのタッチイベントを実際に送ります。JavaScriptはDOMの位置と画面状態の読み取りに使用し、探索座標・発見状態・写真をテスト側から注入しません。

`GameFlowTest#completeTokyoJourney` の1本のテストで、次の9段階を確認しています。

1. 起動時の地区（今回の保存状態では浅草）で地形・建物タイル・猫モデルを読み込み、建物の読み込み数が0より大きいこと。
2. 日本語から英語、英語から日本語へ切り替わり、英語の開始ボタンが表示されること。
3. 猫の選択画面に10件あり、ラグドールを選択できること。
4. 新宿・渋谷・秋葉原・浅草へ順に切り替え、各地区の実際の建物タイルと猫モデルが読み込まれること。
5. 散歩を開始し、雷門が観光記録に入り、近くの猫への挨拶が友だち帳に残ること。
6. スティック操作で緯度・経度が実際に変化すること。
7. カメラの座位切替とドラッグで構図を変え、撮影画像がアルバムに入り、MediaStore経由で `Pictures/TOKYO-CAT` へ保存されること。
8. 雷門の説明本文と地点マップを開けること。
9. Activityを再作成し、猫の選択、観光記録、保存した写真を復元できること。

さらに `adb shell am force-stop io.github.hatake716.tokyocat` の後、別の計測プロセスで `GameFlowTest#restoreAfterProcessRestart` を実行。猫種・雷門の記録・友だち・写真がプロセス終了をまたいで復元されることを確認しています。

`CatVisualTest#inspectCatsAndMovement` は、10種類を順に選択し、カメラの距離と向きをタッチで調整して正面・横・座位を撮影します。歩行・走行・停止の連続スクリーンショットも記録し、描画エラーがないことを検査します。JSからの姿勢や座標の注入は行いません。ログは [android-cat-visual.txt](verification/android-cat-visual.txt)。全10種類の比較画像は [cat-review.md](verification/cat-review.md)。

最終APKでは `CatVisualTest#photoPausesNpcLocomotion` も成功。周囲の猫が実際に歩き出すのを待ち、撮影モードへ移ると全匹の歩行アニメーション速度が0へ戻ることを確認しました。[android-photo-idle.txt](verification/android-photo-idle.txt)

ログ：[android-journey.txt](verification/android-journey.txt)、[android-process-restart.txt](verification/android-process-restart.txt)。スクリーンショット：[screenshots](verification/screenshots)。

## 0.3の毛並みと描画測定

10種に毛を追加した最終APKで `FurReviewTest#fluffyCloseup` が成功。ネイティブのタッチ操作でラグドールを選び、散歩してから撮影モードに入り、距離と向きを調整。正面・横・斜め・座位を記録し、描画エラーがないことを検査しました。実際のスクリーンショットを目視で確認し、毛束の板状の明暗を抑え、毛先の半透明によって胸・頬・尾の輪郭が柔らかく表示されることを確認しています。

- 設定：標準画質、目標30fps、画面2400 × 1080、3D描画1800 × 810。
- 対象：浅草で長毛のラグドールを撮影。周囲12匹も0.3の毛付きモデル。
- 待機：接近したカメラの調整後14秒。直近180描画間隔を取得。
- 観測：**平均29.82fps、描画間隔p95 58.9ms**。テストは計測値の取得を検査し、すべての場面で30fpsを保証する性能合格基準にはしていません。
- ホストGPUを使うエミュレーターの1場面・1回の測定です。Android実機の描画性能、発熱や消費電力は未検証です。

[操作ログ](verification/android-fur-review.txt)、[測定値](verification/fur-performance.json)、[モデル別の毛束数](verification/fur-model-stats.json)、[毛の実装仕様](FUR.md)。

## データ配信と観光出典

0.2で記録した4自治体の建物tileset.jsonと地形layer.jsonについて、実際のHTTP応答、長さ、SHA-256を記録しました。**5 URLともHTTP 200**。[live-sources.json](verification/live-sources.json)

0.2では15地点の解説用URLも実際に取得し、HTTP 200、リダイレクト先、ページタイトルを記録しています。[landmark-sources.json](verification/landmark-sources.json)

これは今後の配信継続、全タイルの可用性、全経路での当たり判定を保証するものではありません。

## 修正した不具合と未検証の範囲

開発中に発見した初回起動時のInsets初期化、Cesiumの環境照明による描画不具合、Activity再作成時の全画面復帰とテストの座標ずれ、体表の面方向、猫の正面軸、停止時の足の浮き、低い描画解像度を修正しました。写真の保存データ自体はActivity再作成の失敗時にも残っており、操作座標の修正後に復元フローが通りました。

現時点で未検証・未達の内容：

- 実写同等の猫の毛、品種ごとの精密な体格、動画からの同一個体の再構成、モーションキャプチャ。
- 物理端末の長時間FPS、発熱、消費電力、低メモリ、幅広いWebView / GPU / Androidバージョン。
- 全15名所への徒歩ルート、階段・狭い路地・建物内部・地下・カメラの完全な衝突回避。
- 初回完全オフライン、ストレージ枯渇、通信途中切断などの障害注入試験。
- ストア提出・審査・公開。

0.2の目視確認では、前脚の曲がる向き、突き出た目、耳の先端、胸の輪郭を修正。自動操作で画面外の猫の選択肢へタップしてしまうテストの不具合も、実際のスクロール操作を追加して修正しました。

## 配布物

`artifacts/0.3.0-dev/` にインストール可能な開発用APK、10モデルをまとめたZIP、SHA256SUMS.txtを配置。最終サイズとハッシュは [artifacts.json](verification/artifacts.json) に記録しています。
