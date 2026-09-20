#!/usr/bin/env python3
"""Curated coordinates (WGS84); discovery points lie outside landmark buildings.
Descriptions are original summaries; source URLs retained for every entry.
"""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
datasets=json.loads((root/'docs/sources/plateau-datasets.json').read_text())
areas=[
 ('marunouchi','丸の内','Marunouchi','赤レンガと、並木道。','Brick, stone & quiet avenues.',139.76455,35.68090,'13101',900,43,80),
 ('shinjuku','新宿','Shinjuku','摩天楼の足もとを歩く。','A small cat. A towering city.',139.69245,35.68960,'13104',1400,76,270),
 ('shibuya','渋谷','Shibuya','交差する街、寄り道の時間。','Every crossing, a new story.',139.70048,35.65925,'13113',800,53,0),
 ('asakusa','浅草','Asakusa','路地の向こうに、江戸の面影。','Old Tokyo, at your own pace.',139.79635,35.71115,'13106',800,40,0),
 ('akihabara','秋葉原','Akihabara','電気街から、神田の坂へ。','Electric streets & hidden shrines.',139.77160,35.69812,'13101',900,42,0),
]
regions=[]
for i,(id,ja,en,jd,ed,lon,lat,ward,radius,h,heading) in enumerate(areas):
 d=next(x for x in datasets if x['city_code']==ward)
 regions.append(dict(id=id,name=dict(ja=ja,en=en),tagline=dict(ja=jd,en=ed),lon=lon,lat=lat,ward=ward,radius=radius,height=h,heading=heading,tiles=d['url'],year=d['year'],index=i+1))
rows=[
 ('tokyo-station','marunouchi','東京駅 丸の内駅舎','Tokyo Station',139.76580,35.68108,75,'1914年に開業した東京駅。丸の内側の赤レンガ駅舎は、東京の玄関口を象徴する建築です。広場からドームと長いファサードを見上げてみましょう。','Opened in 1914, Tokyo Station is a gateway to the capital. Its red-brick Marunouchi building is framed by domes. Look up from the plaza to appreciate its long facade.','https://www.japan.travel/en/spot/1710/'),
 ('naka-dori','marunouchi','丸の内仲通り','Marunouchi Naka-dori',139.76315,35.6800,55,'丸の内の街を南北につなぐ並木道。ショップやアートが点在し、大きなオフィスビルの足もとに散歩の楽しみがあります。猫の目線なら、植栽や歩道にも注目。','This tree-lined avenue links the Marunouchi neighborhood. Shops and outdoor art bring life to the foot of the office towers. From a cat’s height, notice the paving and greenery.','https://visit-chiyoda.tokyo/app/en/spot/detail/462'),
 ('kokyo-gaien','marunouchi','皇居外苑','Kokyo Gaien',139.76025,35.67980,80,'皇居の前に広がる庭園と広場。丸の内のビル群から歩くと、濠と松のある開けた景色に変わります。ゲームでは外苑側から皇居周辺の風景を眺められます。','The outer gardens form an open landscape in front of the Imperial Palace. Walking from Marunouchi, towers give way to moats and pines. Explore the view from the public gardens.','https://www.env.go.jp/garden/kokyogaien/'),
 ('tocho','shinjuku','東京都庁','Tokyo Metropolitan Government',139.69205,35.68963,65,'新宿の高層ビル街に建つ東京都庁。二つの塔をもつ第一本庁舎が街の目印です。大きな建築を足もとから見上げると、猫の小ささがいっそう感じられます。','The twin towers of the main government building are a landmark of western Shinjuku. From ground level, the scale of the surrounding architecture is especially striking.','https://www.yokoso.metro.tokyo.lg.jp/'),
 ('omoide','shinjuku','思い出横丁','Omoide Yokocho',139.69970,35.69300,45,'新宿駅西口近くの、小さな飲食店が集まる路地。高層ビルの街とは異なる、昔ながらの横丁の雰囲気が残っています。入口の周りを気ままに散策しましょう。','Near the west exit of Shinjuku Station, this narrow lane is known for its small eateries and nostalgic atmosphere. It offers a different face of Shinjuku from the skyscraper district.','https://en.shinjuku-omoide.com/'),
 ('hanazono','shinjuku','花園神社','Hanazono Shrine',139.70465,35.69345,60,'新宿のにぎわいの中にある神社。酉の市でも知られ、街の歴史と日常が交差する場所です。境内の外から、ビルと鳥居が同じ風景に収まる新宿らしさを感じます。','A shrine amid the bustle of Shinjuku, Hanazono is known for its Tori-no-Ichi festival. The surrounding streets bring shrine gates and modern buildings into a single city view.','https://www.kanko-shinjuku.jp/officialmovie_en/'),
 ('hachiko','shibuya','忠犬ハチ公像','Hachiko Statue',139.70060,35.65903,35,'渋谷駅前の待ち合わせ場所として親しまれるハチ公像。飼い主を待ち続けた秋田犬を記念しています。猫として訪ねると、いつもの渋谷にも違った物語が見えそうです。','This statue outside Shibuya Station commemorates Hachiko, the Akita remembered for waiting for his owner. It is also a familiar meeting point—a canine story to discover as a cat.','https://www.gotokyo.org/en/spot/86/index.html'),
 ('scramble','shibuya','渋谷スクランブル交差点','Shibuya Scramble Crossing',139.70058,35.65952,40,'渋谷駅前の、いくつもの方向へ横断歩道が延びる交差点。大型のビルに囲まれた歩行者空間が街の象徴です。歩道の端から街を見渡すのも、猫らしい楽しみ方。','Crosswalks fan out in several directions in front of Shibuya Station. Framed by large buildings, the crossing is an emblem of the district. Pause at the pavement edge and take in the city.','https://www.gotokyo.org/en/destinations/western-tokyo/shibuya/index.html'),
 ('miyashita','shibuya','MIYASHITA PARK','MIYASHITA PARK',139.70100,35.66245,60,'公園と商業施設、ホテルが一体となった渋谷の施設。線路沿いに長く延びる建物と屋上の公園が特徴です。この探索地点は施設の地上側にあります。','This Shibuya complex combines a park, shops and a hotel. Its elongated building follows the railway, with a park above. This discovery point is at street level beside the complex.','https://www.gotokyo.org/jp/spot/1844/index.html'),
 ('kaminarimon','asakusa','雷門','Kaminarimon Gate',139.79665,35.71100,45,'浅草寺の入口を示す雷門。正式には風雷神門といい、風神と雷神が守る門として知られます。大きな提灯の下から続く仲見世の参道に、浅草らしい風景が広がります。','Kaminarimon marks the entrance to Senso-ji. Also called Furaijin-mon, it is associated with the wind and thunder gods. Beyond its great lantern, Nakamise leads toward the temple.','https://www.senso-ji.jp/guide/guide01.html'),
 ('sensoji','asakusa','浅草寺','Senso-ji Temple',139.79660,35.71435,70,'浅草観音としても親しまれる、東京で最も古い寺院。参道を進むと大きな本堂が姿を現します。寺院建築の屋根を、地面に近い目線で見上げてみましょう。','Tokyo’s oldest temple is also known as Asakusa Kannon. Its main hall rises beyond the approach. From a low viewpoint, the broad roofs take on a particularly dramatic silhouette.','https://www.senso-ji.jp/english/'),
 ('asakusa-shrine','asakusa','浅草神社','Asakusa Shrine',139.79772,35.71460,50,'浅草寺のすぐ隣にある神社で、三社様とも呼ばれています。浅草寺の始まりにゆかりのある三人を祀ります。寺院と神社が並ぶ浅草の歴史に触れられる場所です。','Beside Senso-ji stands Asakusa Shrine, also known as Sanja-sama. It honors three people associated with the temple’s origins. The neighboring shrine and temple reveal layers of Asakusa’s history.','https://www.asakusajinja.jp/'),
 ('electric-town','akihabara','秋葉原電気街','Akihabara Electric Town',139.77130,35.69845,65,'電気製品や電子部品の店が集まり、アニメやゲームの文化でも知られる秋葉原。中央通りの周辺では、ビルの並びと小さな路地がつくる街の奥行きを楽しめます。','Known for electronics and components as well as anime and games, Akihabara rewards wandering. Around Chuo-dori, large buildings and smaller side streets create a varied urban landscape.','https://www.gotokyo.org/en/destinations/central-tokyo/akihabara/index.html'),
 ('kanda-myojin','akihabara','神田明神','Kanda Myojin Shrine',139.76790,35.70175,55,'秋葉原から坂を上った先にある神田明神。神田祭で知られ、周辺の広い地域と結びついてきた神社です。電気街のにぎわいから少し離れた場所を散策できます。','Uphill from Akihabara, Kanda Myojin is known for the Kanda Matsuri festival and its connections with many central Tokyo neighborhoods. Discover another atmosphere beyond the electronics district.','https://www.gotokyo.org/en/spot/17/'),
 ('manseibashi','akihabara','万世橋','Manseibashi Bridge',139.77065,35.69675,55,'神田川に架かる万世橋。近くには旧万世橋駅の赤レンガ高架が残り、鉄道と街の歴史を感じられます。川沿いから眺める秋葉原も、寄り道にぴったりです。','Manseibashi crosses the Kanda River beside the red-brick railway structure of the former station. The riverside gives a different view of Akihabara and its railway history.','https://www.ecute.jp/maach/'),
]
places=[dict(id=id,area=area,name=dict(ja=ja,en=en),lon=lon,lat=lat,radius=rad,description=dict(ja=jd,en=ed),source=source) for id,area,ja,en,lon,lat,rad,jd,ed,source in rows]
breed_rows=[
 ('scottish','スコティッシュ・フォールド','Scottish Fold','#aa9a88',1,1,True),('mixed','混血猫','Mixed-breed','#c28c56',1,1,False),('munchkin','マンチカン','Munchkin','#c6a77c',.67,1,False),('ragdoll','ラグドール','Ragdoll','#c8c1b6',1,1.18,False),('minuet','ミヌエット','Minuet','#ddd2be',.72,1.2,False),('siberian','サイベリアン','Siberian','#938476',1,1.3,False),('british','ブリティッシュ・ショートヘアー','British Shorthair','#77818b',.93,1.18,False),('american','アメリカン・ショートヘア','American Shorthair','#b1b5b8',1,1,False),('norwegian','ノルウェージャン・フォレスト・キャット','Norwegian Forest Cat','#a48b72',1.15,1.25,False),('ragamuffin','ラガマフィン','Ragamuffin','#d0b6a0',1.05,1.3,False)]
breeds=[dict(id=id,name=dict(ja=ja,en=en),color=c,legs=legs,body=body,fold=fold,model='models/'+id+'.glb',status='prototype') for id,ja,en,c,legs,body,fold in breed_rows]
catalog=dict(regions=regions,places=places,breeds=breeds,breedSource='https://www.anicom-sompo.co.jp/news-release/2025/20260219/',dataPolicy='https://www.mlit.go.jp/plateau/site-policy/',catSource='https://www.youtube.com/watch?v=Jxv0e1VXSR0')
(root/'app/src/main/assets/game/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
print('5 districts, 15 landmarks, 10 breed selections')
