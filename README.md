# TOKYO-CAT

東京を野良猫として歩く Android 向け3D探索ゲーム。**0.1.0-dev / 開発版**。

丸の内・新宿・渋谷・浅草・秋葉原を、PLATEAUの実在する建物・地形データで表示します。観光、猫への挨拶、撮影とアルバムを実装しています。猫は、ユーザー指定の動画を参考に独自制作した10区分のスキン付きGLBです。**猫の写実表現、毛の質感、品種ごとの解剖学的精度・モーションは引き続き改良が必要です。完成したフォトリアル作品という位置づけではありません。**

## 起動と操作

Android 10以降、OpenGL ES 3対応、更新されたAndroid System WebView、インターネット接続が必要です。

- ホームで街と猫を選び、「散歩をはじめる」。
- 左スティックで移動、画面の街部分をドラッグして視点を回転。
- 「走る」で走行へ切替。「猫の目線」で約30cmの一人称視点。
- 名所の半径35～80mに入ると観光記録が自動保存され、日英の解説と出典を読めます。
- 各地区12匹の猫が登場。3m以内で挨拶すると友だち帳に記録。
- 撮影モードでは構図、距離、座位を調整。画像はアプリ内アルバムへ保存。
- 写真詳細の「端末に保存」で `Pictures/TOKYO-CAT` へJPEGを保存。端末のカメラやストレージ読取権限は不要です。
- 設定から日本語・英語、画質、視点リセット、出発点への復帰を選択。

## 収録内容

| 地区 | 観光地点 |
| --- | --- |
| 丸の内 | 東京駅丸の内駅舎、丸の内仲通り、皇居外苑 |
| 新宿 | 東京都庁、思い出横丁、花園神社 |
| 渋谷 | 忠犬ハチ公像、スクランブル交差点、MIYASHITA PARK |
| 浅草 | 雷門、浅草寺、浅草神社 |
| 秋葉原 | 電気街、神田明神、万世橋 |

猫の選択肢：スコティッシュ・フォールド、混血猫、マンチカン、ラグドール、ミヌエット、サイベリアン、ブリティッシュ・ショートヘアー、アメリカン・ショートヘア、ノルウェージャン・フォレスト・キャット、ラガマフィン。基準はアニコム2026年調査の新規加入0歳猫の上位10区分です。

## ビルド

JDK 17、Android SDK 36。SDKパスを `local.properties` に設定してください。

```bash
./gradlew assembleDebug assembleDebugAndroidTest lintDebug
node --test tests/core.test.mjs
python3 tools/check_sources.py
```

APK: `app/build/outputs/apk/debug/app-debug.apk`。開発用署名です。

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n io.github.hatake716.tokyocat/.MainActivity
adb install -r app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
adb shell am instrument -w -e class io.github.hatake716.tokyocat.GameFlowTest \
  io.github.hatake716.tokyocat.test/androidx.test.runner.AndroidJUnitRunner
```

猫モデル再生成には `tools/model-requirements.txt` のPython依存が必要です。

```bash
python3 tools/build_cats.py
python3 tools/verify_models.py
```

このNixOS環境ではPythonのネイティブ依存用に `LD_LIBRARY_PATH=/run/current-system/sw/share/nix-ld/lib` を設定します。

## 実装

- Androidホスト：Java / AndroidX Activity / WebViewAssetLoader。アプリに同梱したHTML・JSだけがネイティブ写真保存機能を利用します。
- 描画：CesiumJS 1.127.0を同梱。外部からJavaScriptを取得せず、公開3D Tiles・地形・航空写真をストリーミング。
- 地理座標：WGS84。地形は楕円体高を配信するPLATEAU-Terrain。平面地図の架空ビルではありません。
- 保存：探索状態・言語・猫種はlocalStorage、写真はIndexedDB。画像エクスポートはMediaStoreのIS_PENDINGで失敗時の途中ファイルを削除。
- 猫：暗黙曲面を連続メッシュ化、ボーンへのウェイト付け、PBR素材、色柄、耳・目・ひげ・尾。移動距離に結びつく歩行周期と二関節IK、挨拶・座位への遷移。

## 現段階の範囲

- 都市データは整備時点の建物形状・テクスチャです。地上の看板、小さな像、路面、植栽、人や自動車の全てを再現していません。観光説明がある場所でも小さなモニュメントの3D形状が欠けることがあります。
- 探索は地区の開始地点から半径800～1400m。建物内・地下・屋上への専用ナビゲーションは未実装です。
- 当たり判定は読み込み済みタイルに対するレイ判定です。キャラクター全体の物理形状、階段、段差、複雑な路地、全経路の安全なスポーンには改良が必要です。
- 猫のモデルとモーションは手続き的な独自制作です。動画からの写真測量やモーションキャプチャではありません。10区分の体格・毛色の差を実装していますが、実写同等の毛並みや品種の正確な個体再現は未達です。
- 地図の初回読み込みには通信が必要です。配信サービスの停止時には再試行表示になります。アルバムと解説の閲覧は地図ロードとは独立しています。
- 公開リリース署名、Play Consoleへの提出、GitHub公開、物理端末での長時間性能・操作検証は今回行っていません。

出典・利用条件は [docs/ASSETS.md](docs/ASSETS.md)、モデル単体の仕様は [docs/CAT_MODELS.md](docs/CAT_MODELS.md)、検証結果は [docs/VALIDATION.md](docs/VALIDATION.md) を参照してください。

ビルド後に `python3 tools/package_dev.py` を実行すると、`artifacts/0.1.0-dev/` にAPK、猫モデルZIP、SHA256SUMS.txtを作成します。
