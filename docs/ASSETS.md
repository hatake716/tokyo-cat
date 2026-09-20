# TOKYO-CAT データと制作記録

確認日：2026-09-20。アプリ内の「データとクレジット」からも出典を開けます。

## 都市の建物

指定された [東京都デジタルツイン3Dビューアー](https://3dview.tokyo-digitaltwin.metro.tokyo.lg.jp/) を調査しました。参照カタログの一部が AccessDenied を返したため、公開されている [PLATEAU 配信サービス](https://docs.plateauview.mlit.go.jp/datasets/3d-tiles/) から、同じ対象地域の実在する建築物モデルを直接読み込みます。ビューアーの認証情報は使用しません。

| ゲーム内の地区 | データ | 年度・形状 |
| --- | --- | --- |
| 丸の内・秋葉原 | 東京都 千代田区 | 2025年度、LOD2、テクスチャあり |
| 新宿 | 東京都 新宿区 | 2025年度、LOD2、テクスチャあり |
| 渋谷 | 東京都 渋谷区 | 2025年度、LOD2、テクスチャあり |
| 浅草 | 台東区 | 2025年度、LOD2、テクスチャあり |

カタログ：<https://api.plateauview.mlit.go.jp/datacatalog/plateau-datasets>

採用URL、年度、原データのIDは [plateau-datasets.json](sources/plateau-datasets.json) に記録。各区の `*-license.json` はG空間情報センターのデータセット別利用条件を確認した記録です。各データセットは [PLATEAU サイトポリシー](https://www.mlit.go.jp/plateau/site-policy/) を指定しており、出典と加工の表示を付けます。サイトポリシーに示される公共データ利用規約と第三者権利の扱いも適用されます。

加工：建物の元の地理座標とテクスチャを利用し、ゲームの照明、カメラ、地形、猫モデルを合成。個々の看板、歩道、人、自動車、像の完全な再現を保証しません。配信されたタイル全体の複製はAPKに含めず、必要範囲をオンラインで取得します。

## 地形・航空写真

- 地形：[PLATEAU-Terrain](https://docs.plateauview.mlit.go.jp/datasets/terrain/)。`https://tile.plateauview.mlit.go.jp/terrain/` のquantized-meshを利用。高さはWGS84楕円体高。画面と撮影画像に `PLATEAU | Mapterhorn | 国土地理院` の帰属を表示します。
- 航空写真：[国土地理院 地理院タイル一覧](https://maps.gsi.go.jp/development/ichiran.html) の全国最新写真（シームレス） `seamlessphoto`。実際の路面より解像度が低く、低い猫目線ではぼやけて見えます。国土地理院の出典を表示し、ゲーム画面として加工します。
- 地形配信は試験的サービスです。公開URLの変更・停止に備えたオフライン配信は、まだ実装していません。

## 猫モデル

ユーザーの追加指定により、CGTraderの猫モデルの代わりに [指定動画「ネコの生態【サクっと解説】」](https://www.youtube.com/watch?v=Jxv0e1VXSR0) を制作時の観察参考にしました。動画内の猫の輪郭、耳・目・口元、長毛の胸元や尾などを観察しています。

この動画には複数の猫が登場し、同一個体を多方向から撮ったスキャン素材ではありません。実際の観察時刻と内容は [cat-video-reference.json](sources/cat-video-reference.json) に保存しています。**動画の猫を精密に立体復元したもの、動画から測定したモーション、またはCGTrader由来のモデルとは扱いません。** 動画・音声・フレーム画像はAPKと配布モデルに含めていません。

`tools/build_cats.py` と `tools/skin_surface.py` で作成した独自の形状・柄です。体表を連続メッシュ化し、22のジョイントへウェイトを割り当て、耳・目・鼻・ひげと長毛の輪郭を加えています。10区分で体格、脚の長さ、耳、色柄が異なります。接地用の半透明デカールは近似表現で、太陽光の物理的な影ではありません。

GLBには Idle / Walk / Trot / Greet のサンプルクリップを格納。ゲーム内は実際の移動距離に合わせて脚の接地・遊脚を計算し、二関節IK、頭や尾、座位への遷移を制御します。品種ごとの解剖学的検証、実測モーション、足の滑り抑制、毛のリアルな表現は今後の課題です。猫モデルのSHA-256は `app/src/main/assets/game/models/manifest.json` に記録しています。

猫種の選択基準は [アニコム損保の2026年ランキング](https://www.anicom-sompo.co.jp/news-release/2025/20260219/) の上位10区分です。新規保険加入の0歳猫を対象とする調査で、全国の飼育猫全体の順位と同義ではありません。「混血猫」は厳密には単一の品種ではないため、アプリでは10の選択肢として扱います。

## 観光説明

15地点について日英の短い説明を独自に執筆しました。各項目に公式観光機関・施設のURLを保持し、アプリ内の名所詳細から参照できます。本文や写真を転載した百科事典ではありません。座標はゲーム用の発見位置で、施設の入口や境界を保証する測量成果ではありません。

## ソフトウェア

- CesiumJS 1.127.0：Apache-2.0。公式npm配布物をローカル同梱。ライセンス本文と第三者一覧は `app/src/main/assets/game/vendor/cesium-LICENSE.md`、`cesium-ThirdParty.json`、`cesium-ThirdParty.extra.json`。
- AndroidX Activity / WebKit：Apache-2.0。Gradle依存として取得。
- モデル生成時のNumPy、Pillow、SciPy、scikit-imageは開発用依存です。Python実行環境はAPKに含めません。

本プロジェクトの独自コード・モデルの外部公開ライセンスはまだ設定していません。上記の第三者データ・ライブラリの利用条件とは別に管理します。
