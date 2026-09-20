# 猫モデルのAndroid表示確認

2026-09-21。最終GLBをAndroid Emulator / Cesium上で描画し、実際のタッチ操作で視点と姿勢を変更して撮影しました。写真品質の認定ではなく、モデルの表示・品種差・姿勢を確認する記録です。スクリーンショットは無加工です。

| 猫 | 正面 | 横 | 座位 |
| --- | --- | --- | --- |
| スコティッシュ・フォールド | [正面](screenshots/cat-scottish-front.png) | [横](screenshots/cat-scottish-side.png) | [座位](screenshots/cat-scottish-sit.png) |
| 混血猫 | [正面](screenshots/cat-mixed-front.png) | [横](screenshots/cat-mixed-side.png) | [座位](screenshots/cat-mixed-sit.png) |
| マンチカン | [正面](screenshots/cat-munchkin-front.png) | [横](screenshots/cat-munchkin-side.png) | [座位](screenshots/cat-munchkin-sit.png) |
| ラグドール | [正面](screenshots/cat-ragdoll-front.png) | [横](screenshots/cat-ragdoll-side.png) | [座位](screenshots/cat-ragdoll-sit.png) |
| ミヌエット | [正面](screenshots/cat-minuet-front.png) | [横](screenshots/cat-minuet-side.png) | [座位](screenshots/cat-minuet-sit.png) |
| サイベリアン | [正面](screenshots/cat-siberian-front.png) | [横](screenshots/cat-siberian-side.png) | [座位](screenshots/cat-siberian-sit.png) |
| ブリティッシュ・ショートヘアー | [正面](screenshots/cat-british-front.png) | [横](screenshots/cat-british-side.png) | [座位](screenshots/cat-british-sit.png) |
| アメリカン・ショートヘア | [正面](screenshots/cat-american-front.png) | [横](screenshots/cat-american-side.png) | [座位](screenshots/cat-american-sit.png) |
| ノルウェージャン・フォレスト・キャット | [正面](screenshots/cat-norwegian-front.png) | [横](screenshots/cat-norwegian-side.png) | [座位](screenshots/cat-norwegian-sit.png) |
| ラガマフィン | [正面](screenshots/cat-ragamuffin-front.png) | [横](screenshots/cat-ragamuffin-side.png) | [座位](screenshots/cat-ragamuffin-sit.png) |

歩行・走行の連続フレームは `screenshots/motion-walk-*.png` と `screenshots/motion-run-*.png`。足の接地の数値検証は [model-validation.txt](model-validation.txt) と [core-tests.txt](core-tests.txt) を参照。

10種類の表示検査で使ったGLBは最終APKのモデルと同じです。この検査後、撮影中のNPCがその場で足踏みする不具合を修正。最終APKで [撮影中の静止姿勢](android-photo-idle.txt)、[全体操作](android-journey.txt)、[プロセス再起動](android-process-restart.txt) を再検証しました。
