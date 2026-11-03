// 旅行
window.EK_DATA = window.EK_DATA || [];

EK_DATA.push({
  cat: "旅行", series: "空港",
  keys: [
    ["Here you go", "はい、どうぞ"],
    ["Do I need to", "〜する必要がありますか？"],
    ["Is it possible to", "〜することはできますか？"],
    ["How long does it take", "どれくらいかかりますか？"],
    ["I'd like", "〜がいいです／〜したいです"],
    ["Excuse me", "すみません"]
  ],
  dialogs: [
    { id: "air-1", title: "チェックイン", A: "航空会社の係員", B: "あなた（乗客）", def: "B", lines: [
      ["A", "Good morning. Where are you flying to today?", "おはようございます。本日はどちらまで？"],
      ["B", "Hi, I'm flying to Vancouver. Here's my passport.", "こんにちは、バンクーバーまでです。パスポートです。"],
      ["A", "Thank you. Are you checking any bags?", "ありがとうございます。お預けになる荷物はありますか？"],
      ["B", "Just this one suitcase.", "このスーツケース一つだけです。"],
      ["A", "Please put it on the scale... I'm afraid it's a little over the limit.", "はかりに載せてください…申し訳ありませんが、少し制限を超えています。"],
      ["B", "Oh, really? How much over is it?", "え、本当ですか？どれくらい超えてますか？"],
      ["A", "About two kilos. You can either pay a fee or move some items to your carry-on.", "2キロほどです。料金をお支払いいただくか、機内持ち込みの荷物に移していただくことになります。"],
      ["B", "I'll move a few things. Give me a second.", "いくつか移します。ちょっと待ってください。"],
      ["A", "No problem... Okay, that's fine now. Would you like a window or an aisle seat?", "大丈夫ですよ…はい、これで問題ありません。窓側と通路側、どちらがよろしいですか？"],
      ["B", "I'd like an aisle seat, if possible.", "できれば通路側がいいです。"],
      ["A", "Sure. Here's your boarding pass. Boarding starts at 10:15 at Gate 32.", "かしこまりました。こちらが搭乗券です。搭乗は10時15分から32番ゲートで始まります。"],
      ["B", "Thank you. How long does it take to get to the gate?", "ありがとうございます。ゲートまでどれくらいかかりますか？"],
      ["A", "About ten minutes, including security. Have a nice flight!", "保安検査を含めて10分ほどです。良いご旅行を！"]
    ]},
    { id: "air-2", title: "保安検査・搭乗口", A: "空港の係員", B: "あなた（乗客）", def: "B", lines: [
      ["A", "Please take your laptop out of your bag and put it in a separate tray.", "バッグからノートパソコンを出して、別のトレーに入れてください。"],
      ["B", "Sure. Do I need to take my shoes off too?", "わかりました。靴も脱ぐ必要がありますか？"],
      ["A", "No, you can keep them on. Any liquids in your bag?", "いいえ、履いたままで結構です。バッグに液体物は入っていますか？"],
      ["B", "Just a small bottle of hand cream. Here you go.", "小さいハンドクリームだけです。どうぞ。"],
      ["A", "That's fine. Please step through the scanner... Okay, you're all set.", "問題ありません。スキャナーを通ってください…はい、大丈夫です。"],
      ["B", "Excuse me, is the flight to Vancouver leaving from Gate 32?", "すみません、バンクーバー行きの便は32番ゲートからですか？"],
      ["A", "It was, but it's been changed to Gate 45.", "そうだったのですが、45番ゲートに変更になりました。"],
      ["B", "Oh, thanks for letting me know. How long does it take to get there?", "あ、教えてくれてありがとうございます。そこまでどれくらいかかりますか？"],
      ["A", "About five minutes. Just follow the signs.", "5分くらいです。表示に従って行ってください。"],
      ["B", "Is the flight still on time?", "便は予定通りですか？"],
      ["A", "I'm afraid it's delayed by about thirty minutes.", "申し訳ありませんが、30分ほど遅れています。"],
      ["B", "Okay. Is it possible to charge my phone somewhere around here?", "わかりました。この辺りで携帯を充電できるところはありますか？"],
      ["A", "There are charging stations next to each gate.", "各ゲートの横に充電スポットがあります。"],
      ["B", "Great, thank you.", "よかった、ありがとうございます。"]
    ]},
    { id: "air-3", title: "欠航と振替", A: "航空会社のカウンター", B: "あなた（乗客）", def: "B", lines: [
      ["B", "Excuse me, my flight to Vancouver was just canceled. What should I do?", "すみません、バンクーバー行きの便が欠航になったんですが。どうすればいいですか？"],
      ["A", "I'm very sorry about that. It's due to the storm. May I see your boarding pass?", "大変申し訳ございません。嵐のためです。搭乗券を拝見できますか？"],
      ["B", "Here you go. I have an important meeting tomorrow afternoon.", "どうぞ。明日の午後に大事な会議があるんです。"],
      ["A", "Let me see... The earliest flight I can put you on leaves tomorrow at 7 a.m.", "確認します…振り替えられる一番早い便は明日の朝7時発です。"],
      ["B", "Is it possible to get on a flight tonight, even with a connection?", "乗り継ぎでもいいので、今夜の便に乗ることはできますか？"],
      ["A", "Unfortunately, everything tonight is fully booked.", "あいにく、今夜の便はすべて満席です。"],
      ["B", "I see. Then I'd like to take the 7 a.m. flight.", "そうですか。では朝7時の便でお願いします。"],
      ["A", "Certainly. Since the cancellation was weather-related, we can't cover a hotel, but we can offer you a meal voucher.", "かしこまりました。天候による欠航のためホテル代はお出しできませんが、お食事券をお渡しできます。"],
      ["B", "Okay. Do I need to check my bag again?", "わかりました。荷物はもう一度預ける必要がありますか？"],
      ["A", "No, your bag will be transferred to the new flight automatically.", "いいえ、お荷物は自動的に新しい便に移されます。"],
      ["B", "How early should I get here tomorrow?", "明日はどれくらい早く来ればいいですか？"],
      ["A", "Please arrive at least an hour and a half before departure. Here's your new boarding pass.", "出発の少なくとも1時間半前にはお越しください。こちらが新しい搭乗券です。"],
      ["B", "Thank you for your help.", "ありがとうございました。"]
    ]}
  ]
});

EK_DATA.push({
  cat: "旅行", series: "ホテル",
  keys: [
    ["I have a reservation under", "〜の名前で予約しています"],
    ["Would it be possible to", "〜していただくことは可能ですか？"],
    ["Could you", "〜してもらえますか？"],
    ["Is there", "〜はありますか？"],
    ["I'd appreciate it", "そうしていただけると助かります"],
    ["I'd like to", "〜したいのですが"]
  ],
  dialogs: [
    { id: "hotel-1", title: "チェックイン", A: "フロント係", B: "あなた（宿泊客）", def: "B", lines: [
      ["A", "Good evening. Welcome to the Harbor Hotel. Checking in?", "こんばんは。ハーバーホテルへようこそ。チェックインですか？"],
      ["B", "Yes. I have a reservation under Tanaka.", "はい。田中の名前で予約しています。"],
      ["A", "Let me see... Yes, a double room for three nights. Could I see your passport, please?", "確認します…はい、ダブルルームで3泊ですね。パスポートを拝見できますか？"],
      ["B", "Sure, here you go.", "はい、どうぞ。"],
      ["A", "Thank you. And I'll need a credit card for incidentals.", "ありがとうございます。それと、付帯料金用にクレジットカードが必要です。"],
      ["B", "No problem. Is breakfast included?", "大丈夫です。朝食は含まれていますか？"],
      ["A", "Yes, it's served from 6:30 to 10 on the second floor.", "はい、2階で6時半から10時までです。"],
      ["B", "Great. Would it be possible to get a room on a higher floor?", "よかった。高い階の部屋にしてもらうことはできますか？"],
      ["A", "Let me check... I can give you a room on the 15th floor with a city view.", "確認します…15階の街が見えるお部屋をご用意できます。"],
      ["B", "That would be perfect. Is there Wi-Fi in the room?", "完璧です。部屋にWi-Fiはありますか？"],
      ["A", "Yes, the password is on the card with your key. Here's your key. Enjoy your stay.", "はい、パスワードは鍵と一緒のカードに書いてあります。こちらが鍵です。ごゆっくりお過ごしください。"],
      ["B", "Thank you.", "ありがとうございます。"]
    ]},
    { id: "hotel-2", title: "部屋の不具合を伝える", A: "フロント係（電話）", B: "あなた（宿泊客）", def: "B", lines: [
      ["A", "Front desk. How may I help you?", "フロントです。どのようなご用件でしょうか？"],
      ["B", "Hi, this is room 1512. The air conditioner doesn't seem to be working.", "もしもし、1512号室です。エアコンが動いていないみたいなんです。"],
      ["A", "I'm sorry about that. Is it not turning on at all?", "申し訳ございません。まったく電源が入らないのでしょうか？"],
      ["B", "It turns on, but it's only blowing warm air.", "電源は入るんですが、温かい風しか出ないんです。"],
      ["A", "I'll send someone from maintenance right away.", "すぐに設備係を向かわせます。"],
      ["B", "Thanks. Also, the shower drain is a little clogged.", "ありがとうございます。それと、シャワーの排水口が少し詰まっています。"],
      ["A", "I'm very sorry. I'll ask them to take a look at that too.", "大変申し訳ございません。そちらも見るように伝えます。"],
      ["B", "Could you tell me roughly how long it'll take?", "だいたいどれくらいかかるか教えてもらえますか？"],
      ["A", "They should be there within fifteen minutes.", "15分以内には伺えるはずです。"],
      ["B", "If it can't be fixed, would it be possible to change rooms?", "もし直らなかったら、部屋を替えてもらうことはできますか？"],
      ["A", "Of course. We'll move you to another room if needed.", "もちろんです。必要であれば別のお部屋をご用意します。"],
      ["B", "I'd appreciate it. Thank you.", "そうしていただけると助かります。ありがとうございます。"]
    ]},
    { id: "hotel-3", title: "チェックアウトと荷物預け", A: "フロント係", B: "あなた（宿泊客）", def: "B", lines: [
      ["B", "Good morning. I'd like to check out, please. Room 1512.", "おはようございます。チェックアウトをお願いします。1512号室です。"],
      ["A", "Certainly. Did you have anything from the minibar?", "かしこまりました。ミニバーはご利用になりましたか？"],
      ["B", "Just one bottle of water.", "水を1本だけです。"],
      ["A", "Okay. Here's your bill. Please take a look.", "わかりました。こちらが請求書です。ご確認ください。"],
      ["B", "Sorry, I think there's a mistake. I didn't order any room service.", "すみません、間違いがあると思います。ルームサービスは頼んでいません。"],
      ["A", "Let me check... You're right. I apologize. I'll remove that charge.", "確認します…おっしゃる通りです。失礼いたしました。その料金は取り消します。"],
      ["B", "Thanks. Also, my flight isn't until this evening. Could you keep my luggage until then?", "ありがとうございます。それと、飛行機が夕方なんです。それまで荷物を預かってもらえますか？"],
      ["A", "Of course. Here's your claim tag.", "もちろんです。こちらが引換札です。"],
      ["B", "Is there a shuttle bus to the airport?", "空港までのシャトルバスはありますか？"],
      ["A", "Yes, it leaves every hour from the main entrance.", "はい、正面玄関から1時間ごとに出ています。"],
      ["B", "Great. I'll be back around four.", "よかった。4時ごろ戻ります。"],
      ["A", "Sounds good. Thank you for staying with us.", "承知しました。ご宿泊ありがとうございました。"]
    ]}
  ]
});

EK_DATA.push({
  cat: "旅行", series: "道案内・交通",
  keys: [
    ["How do I get to", "〜へはどう行けばいいですか？"],
    ["Go straight", "まっすぐ行く"],
    ["on your", "（左手／右手）側に"],
    ["How much", "いくら？"],
    ["How long", "どれくらい（時間）？"],
    ["Can I pay by card", "カードで払えますか？"],
    ["Do I need to", "〜する必要がありますか？"]
  ],
  dialogs: [
    { id: "dir-1", title: "道を尋ねる", A: "通行人", B: "あなた（旅行者）", def: "B", lines: [
      ["B", "Excuse me, sorry to bother you. How do I get to the art museum?", "すみません、お邪魔してごめんなさい。美術館へはどう行けばいいですか？"],
      ["A", "The art museum? Sure. Go straight down this street for two blocks.", "美術館？いいですよ。この通りを2ブロックまっすぐ行ってください。"],
      ["B", "Two blocks, okay.", "2ブロックですね。"],
      ["A", "Then turn right at the big intersection with the bank on the corner.", "それから角に銀行がある大きな交差点を右に曲がります。"],
      ["B", "Turn right at the bank. Got it.", "銀行のところで右ですね。わかりました。"],
      ["A", "It'll be on your left, right after the park. You can't miss it.", "公園を過ぎてすぐ左側にあります。すぐわかりますよ。"],
      ["B", "Is it far? Can I walk there?", "遠いですか？歩いて行けますか？"],
      ["A", "Oh yeah, it's about a ten-minute walk.", "ええ、歩いて10分くらいです。"],
      ["B", "Great. Thanks so much for your help.", "よかった。本当にありがとうございます。"],
      ["A", "No problem. Enjoy the museum!", "どういたしまして。美術館を楽しんで！"]
    ]},
    { id: "dir-2", title: "タクシー", A: "タクシー運転手", B: "あなた（乗客）", def: "B", lines: [
      ["A", "Hi there. Where to?", "こんにちは。どちらまで？"],
      ["B", "Hi. Could you take me to the Grand Central Hotel?", "こんにちは。グランド・セントラル・ホテルまでお願いできますか？"],
      ["A", "Sure thing. Traffic's pretty bad right now, though.", "わかりました。ただ今かなり混んでますよ。"],
      ["B", "How long do you think it'll take?", "どれくらいかかりそうですか？"],
      ["A", "Probably around twenty-five minutes.", "たぶん25分くらいですね。"],
      ["B", "And how much will it be, roughly?", "それと、だいたいいくらになりますか？"],
      ["A", "About thirty dollars, give or take.", "30ドル前後ですね。"],
      ["B", "Okay. I'm in a bit of a hurry, so if there's a faster route, please take it.", "わかりました。少し急いでいるので、早い道があればそちらでお願いします。"],
      ["A", "I'll take the highway, then... Here we are.", "じゃあ高速を使いますね。…着きましたよ。"],
      ["B", "Thanks. Can I pay by card?", "ありがとう。カードで払えますか？"],
      ["A", "Of course. Just tap it here.", "もちろん。ここにかざしてください。"],
      ["B", "Great. Could I get a receipt, too?", "よかった。領収書ももらえますか？"],
      ["A", "Sure, here you go. Have a good day!", "はい、どうぞ。良い一日を！"]
    ]},
    { id: "dir-3", title: "電車の乗り換え", A: "駅員", B: "あなた（旅行者）", def: "B", lines: [
      ["B", "Excuse me. How do I get to Brooklyn Bridge Station?", "すみません。ブルックリン・ブリッジ駅へはどう行けばいいですか？"],
      ["A", "Take the green line going downtown.", "ダウンタウン方面のグリーンラインに乗ってください。"],
      ["B", "Do I need to transfer?", "乗り換えは必要ですか？"],
      ["A", "Yes, you'll need to change trains at Union Square.", "はい、ユニオンスクエアで乗り換えが必要です。"],
      ["B", "Which line should I take from there?", "そこからは何線に乗ればいいですか？"],
      ["A", "The red line. It's two stops from there.", "レッドラインです。そこから2駅です。"],
      ["B", "How much is the fare?", "運賃はいくらですか？"],
      ["A", "It's $2.90, and the transfer is free if you use the same card.", "2ドル90セントで、同じカードを使えば乗り換えは無料です。"],
      ["B", "How long does it take in total?", "全部でどれくらいかかりますか？"],
      ["A", "About twenty minutes.", "20分くらいです。"],
      ["B", "Great. And where's the platform?", "よかった。ホームはどこですか？"],
      ["A", "Go straight, and it's on your right, down the stairs.", "まっすぐ行って、右側の階段を下りたところです。"],
      ["B", "Thanks a lot!", "どうもありがとう！"]
    ]}
  ]
});

EK_DATA.push({
  cat: "旅行", series: "レストラン",
  keys: [
    ["I'd like to make a reservation", "予約をしたいのですが"],
    ["Could we", "（私たちは）〜できますか？"],
    ["Can I get", "〜をもらえますか？"],
    ["Could I get", "〜をいただけますか？"],
    ["I'll have", "〜にします（注文）"],
    ["on the side", "別添えで"],
    ["the check", "お会計"],
    ["No worries", "大丈夫ですよ"]
  ],
  dialogs: [
    { id: "rest-1", title: "予約の電話", A: "店員", B: "あなた（客）", def: "B", lines: [
      ["A", "Thank you for calling Bella Vista. How can I help you?", "お電話ありがとうございます、ベラ・ヴィスタです。ご用件をお伺いします。"],
      ["B", "Hi, I'd like to make a reservation for Saturday night.", "もしもし、土曜の夜の予約をしたいのですが。"],
      ["A", "Sure. For how many people?", "かしこまりました。何名様ですか？"],
      ["B", "There'll be four of us. Do you have anything around seven?", "4人です。7時ごろ空いていますか？"],
      ["A", "Let me check... Seven is full, but I have a table at 7:30.", "確認します…7時は満席ですが、7時半ならお席があります。"],
      ["B", "7:30 works for me. Could we sit by the window?", "7時半で大丈夫です。窓際の席にできますか？"],
      ["A", "I'll make a note of it, but I can't guarantee it.", "メモしておきますが、お約束はできません。"],
      ["B", "That's fine. Also, one of us has a nut allergy.", "大丈夫です。それと、一人ナッツアレルギーがあります。"],
      ["A", "Thanks for letting us know. I'll tell the kitchen. Can I get a name and phone number?", "お知らせありがとうございます。厨房に伝えます。お名前とお電話番号をいただけますか？"],
      ["B", "It's Sato, and my number is 555-0123.", "佐藤で、番号は555-0123です。"],
      ["A", "Great. We'll see you Saturday at 7:30.", "ありがとうございます。土曜の7時半にお待ちしております。"]
    ]},
    { id: "rest-2", title: "注文", A: "店員（ジェシカ）", B: "あなた（客）", def: "B", lines: [
      ["A", "Hi, I'm Jessica, and I'll be your server tonight. Can I get you something to drink?", "こんばんは、本日担当のジェシカです。お飲み物はいかがですか？"],
      ["B", "Could I get a glass of the house red?", "ハウスワインの赤をグラスでもらえますか？"],
      ["A", "Sure. Are you ready to order, or do you need a few more minutes?", "かしこまりました。ご注文はお決まりですか、それとももう少しお時間が必要ですか？"],
      ["B", "I think we're ready. What do you recommend?", "決まったと思います。おすすめは何ですか？"],
      ["A", "The grilled salmon is really popular, and the steak is great too.", "グリルサーモンがすごく人気で、ステーキもおいしいですよ。"],
      ["B", "I'll have the salmon. Does it come with a side?", "サーモンにします。付け合わせはつきますか？"],
      ["A", "Yes, you can choose fries, salad, or mashed potatoes.", "はい、ポテト、サラダ、マッシュポテトから選べます。"],
      ["B", "Salad, please. And could I get the dressing on the side?", "サラダでお願いします。ドレッシングは別にしてもらえますか？"],
      ["A", "No problem. Anything else?", "大丈夫です。他には？"],
      ["B", "That's it for now, thanks.", "とりあえず以上です、ありがとう。"],
      ["A", "Great. I'll put that in for you.", "かしこまりました。ご注文をお通しします。"]
    ]},
    { id: "rest-3", title: "料理の間違い・会計", A: "店員", B: "あなた（客）", def: "B", lines: [
      ["B", "Excuse me. I'm sorry, but I don't think this is what I ordered.", "すみません。申し訳ないんですが、これは注文したものではないと思います。"],
      ["A", "Oh, I'm so sorry. What did you order?", "まあ、大変申し訳ございません。何をご注文でしたか？"],
      ["B", "I ordered the salmon, but this is chicken.", "サーモンを頼んだんですが、これはチキンです。"],
      ["A", "My apologies. I'll get that fixed right away... Here's your salmon. Again, sorry about the mix-up.", "申し訳ございません。すぐにお取り替えします。…サーモンです。改めて、取り違えて申し訳ございませんでした。"],
      ["B", "No worries. It looks great.", "大丈夫ですよ。おいしそう。"],
      ["A", "Enjoy your meal. Just let me know if you need anything.", "ごゆっくりどうぞ。何かあればお申し付けください。"],
      ["B", "Excuse me, could we get the check, please?", "すみません、お会計をお願いできますか？"],
      ["A", "Sure. Will that be together or separate?", "はい。ご一緒ですか、別々ですか？"],
      ["B", "Could we split it between the two of us?", "2人で割ってもらえますか？"],
      ["A", "Absolutely. And the dessert is on the house, because of the mistake earlier.", "もちろんです。それと、先ほどの間違いのお詫びにデザートはサービスです。"],
      ["B", "Oh, that's really kind of you. Thank you.", "まあ、ご親切にありがとうございます。"],
      ["A", "My pleasure. Thanks for coming in!", "どういたしまして。ご来店ありがとうございました！"]
    ]}
  ]
});
