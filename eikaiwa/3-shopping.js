// 買い物
window.EK_DATA = window.EK_DATA || [];

EK_DATA.push({
  cat: "買い物", series: "服",
  keys: [
    ["I'm looking for", "〜を探しています"],
    ["Do you have", "〜はありますか？"],
    ["try", "試着する（try on）"],
    ["fitting room", "試着室"],
    ["I'll take", "〜にします（購入）"],
    ["receipt", "レシート"],
    ["Is there an extra charge", "追加料金はかかりますか？"]
  ],
  dialogs: [
    { id: "cloth-1", title: "サイズを探す", A: "店員", B: "あなた（客）", def: "B", lines: [
      ["A", "Hi there! Can I help you find anything?", "いらっしゃいませ！何かお探しですか？"],
      ["B", "Yes, I'm looking for a light jacket for spring.", "はい、春用の薄手のジャケットを探しています。"],
      ["A", "Sure. These over here just came in.", "わかりました。こちらが入荷したばかりです。"],
      ["B", "Oh, I like this navy one. Do you have this in a medium?", "あ、この紺色のがいいですね。これのMサイズはありますか？"],
      ["A", "Let me check... We have a medium in gray, but only a large in navy.", "確認します…グレーならMがありますが、紺はLしかありません。"],
      ["B", "Hmm. Could you check if another store has it?", "うーん。他の店舗にあるか調べてもらえますか？"],
      ["A", "Sure... Our downtown store has one. I can have it sent here in two days.", "はい…ダウンタウン店に1着あります。2日でこちらに取り寄せられます。"],
      ["B", "That would be great. Is there an extra charge?", "それは助かります。追加料金はかかりますか？"],
      ["A", "No, it's free. Can I get your name and number?", "いいえ、無料です。お名前と番号をいただけますか？"],
      ["B", "Sure. It's Suzuki, 555-0198.", "はい。鈴木、555-0198です。"],
      ["A", "Perfect. We'll call you when it arrives.", "ありがとうございます。届いたらお電話します。"]
    ]},
    { id: "cloth-2", title: "試着", A: "店員", B: "あなた（客）", def: "B", lines: [
      ["B", "Excuse me, can I try these on?", "すみません、これ試着してもいいですか？"],
      ["A", "Of course. The fitting room is right over there. How many items do you have?", "もちろんです。試着室はすぐそこです。何点お持ちですか？"],
      ["B", "Just these two pairs of pants.", "このパンツ2本だけです。"],
      ["A", "Here's your number. Let me know if you need a different size.", "こちらが番号札です。違うサイズが必要なら言ってください。"],
      ["B", "These are a little too tight. Do you have them in a size up?", "これはちょっときついです。ワンサイズ上はありますか？"],
      ["A", "Sure, here you go.", "はい、どうぞ。"],
      ["B", "These fit much better. How do they look?", "こっちの方がずっといいです。どう見えますか？"],
      ["A", "They look great on you. The color really suits you.", "とてもお似合いですよ。色もすごく合ってます。"],
      ["B", "Thanks. Are they on sale?", "ありがとう。これはセール中ですか？"],
      ["A", "Yes, they're 20% off this week.", "はい、今週は20％オフです。"],
      ["B", "Great. I'll take them.", "よかった。これにします。"]
    ]},
    { id: "cloth-3", title: "返品・交換", A: "店員", B: "あなた（客）", def: "B", lines: [
      ["B", "Hi, I'd like to return this sweater.", "こんにちは、このセーターを返品したいのですが。"],
      ["A", "Sure. Was there a problem with it?", "かしこまりました。何か問題がありましたか？"],
      ["B", "It shrank after I washed it once, even though I followed the instructions.", "表示通りに洗ったのに、一回洗ったら縮んでしまったんです。"],
      ["A", "I'm sorry to hear that. Do you have your receipt?", "それは申し訳ございません。レシートはお持ちですか？"],
      ["B", "Yes, here it is. I bought it last week.", "はい、これです。先週買いました。"],
      ["A", "Thank you. Would you like a refund or an exchange?", "ありがとうございます。返金と交換、どちらになさいますか？"],
      ["B", "Can I exchange it? I'm looking for something that's machine-washable.", "交換できますか？洗濯機で洗えるものを探しています。"],
      ["A", "Of course. This cotton one is machine-washable, and it's the same price.", "もちろんです。こちらの綿のものは洗濯機で洗えて、同じ値段です。"],
      ["B", "Do you have this in a small?", "これのSはありますか？"],
      ["A", "Yes, here you go. Would you like to try it on?", "はい、どうぞ。試着なさいますか？"],
      ["B", "No, I'm sure it'll fit. I'll take it.", "いいえ、大丈夫だと思います。これにします。"],
      ["A", "Great. I'll process the exchange for you.", "かしこまりました。交換の手続きをいたします。"]
    ]}
  ]
});

EK_DATA.push({
  cat: "買い物", series: "店で相談",
  keys: [
    ["I'm looking for", "〜を探しています"],
    ["Do you have", "〜はありますか？"],
    ["How often", "どれくらいの頻度で？"],
    ["Does it", "それは〜しますか？"],
    ["Not that I know of", "知る限りではありません"],
    ["What's the difference", "違いは何ですか？"],
    ["we're out of", "〜が品切れです"]
  ],
  dialogs: [
    { id: "store-1", title: "ドラッグストアで薬を相談", A: "薬剤師", B: "あなた（客）", def: "B", lines: [
      ["B", "Hi, I'm looking for something for a headache.", "こんにちは、頭痛に効くものを探しています。"],
      ["A", "Sure. Do you have any allergies to medication?", "わかりました。薬のアレルギーはありますか？"],
      ["B", "Not that I know of.", "知る限りではありません。"],
      ["A", "Are you taking any other medicine right now?", "今、他に飲んでいる薬はありますか？"],
      ["B", "Just some allergy pills for hay fever.", "花粉症のアレルギーの薬だけです。"],
      ["A", "Okay. Then I'd recommend this one. It's pretty gentle on the stomach.", "わかりました。それならこちらをおすすめします。胃にも比較的やさしいですよ。"],
      ["B", "How often should I take it?", "どれくらいの間隔で飲めばいいですか？"],
      ["A", "One tablet every six hours, but no more than four a day.", "6時間おきに1錠ですが、1日4錠までにしてください。"],
      ["B", "Does it make you drowsy?", "眠くなりますか？"],
      ["A", "No, it shouldn't. But if the headache doesn't go away in a few days, you should see a doctor.", "いいえ、ならないはずです。でも数日たっても頭痛が治らなければ、医者に診てもらってください。"],
      ["B", "Got it. Thanks for your help.", "わかりました。ありがとうございます。"]
    ]},
    { id: "store-2", title: "スーパーで品物を探す", A: "店員", B: "あなた（客）", def: "B", lines: [
      ["B", "Excuse me, where can I find baking soda?", "すみません、重曹はどこにありますか？"],
      ["A", "It's in aisle seven, with the baking supplies.", "7番の通路の製菓材料のところです。"],
      ["B", "Thanks. Also, do you have any gluten-free bread?", "ありがとうございます。それと、グルテンフリーのパンはありますか？"],
      ["A", "We do. It's in the frozen section, at the back of the store.", "ありますよ。店の奥の冷凍コーナーです。"],
      ["B", "Great. And I'm looking for fresh basil, but I couldn't find it.", "よかった。あと、生のバジルを探しているんですが、見つからなくて。"],
      ["A", "Hmm, it looks like we're out of it. We should get more tomorrow morning.", "うーん、品切れのようです。明日の朝に入荷するはずです。"],
      ["B", "Oh, okay. Do you have dried basil instead?", "そうですか。代わりに乾燥バジルはありますか？"],
      ["A", "Yes, that's in aisle four with the spices.", "はい、4番通路のスパイスのところです。"],
      ["B", "Perfect. Thanks so much.", "完璧。本当にありがとう。"],
      ["A", "No problem. Let me know if you need anything else.", "どういたしまして。他にも何かあれば言ってください。"]
    ]},
    { id: "store-3", title: "家電の相談", A: "店員", B: "あなた（客）", def: "B", lines: [
      ["A", "Hi, are you looking for anything in particular?", "こんにちは、何か特にお探しですか？"],
      ["B", "Yes, I'm looking for a vacuum cleaner. Something light and cordless.", "はい、掃除機を探しています。軽くてコードレスのものがいいです。"],
      ["A", "Sure. This model is really popular. It only weighs about 1.5 kilos.", "かしこまりました。このモデルはとても人気です。重さはたった1.5キロほどです。"],
      ["B", "How long does the battery last?", "バッテリーはどれくらいもちますか？"],
      ["A", "About forty minutes on a full charge.", "フル充電で40分ほどです。"],
      ["B", "What's the difference between this one and the cheaper one next to it?", "これと隣の安いのとの違いは何ですか？"],
      ["A", "The cheaper one has less suction power, and the battery only lasts about twenty minutes.", "安い方は吸引力が弱く、バッテリーも20分ほどしかもちません。"],
      ["B", "I see. Does it come with a warranty?", "なるほど。保証はついていますか？"],
      ["A", "Yes, a one-year warranty. You can extend it to three years for an extra 30 dollars.", "はい、1年保証です。30ドル追加で3年に延長できます。"],
      ["B", "Hmm, I'll think about the extended warranty. But I'll take this one.", "うーん、延長保証は考えます。でもこれにします。"],
      ["A", "Great choice. I'll get you a new one from the back.", "いい選択です。奥から新品をお持ちします。"]
    ]}
  ]
});

EK_DATA.push({
  cat: "買い物", series: "値段・支払い",
  keys: [
    ["How much", "いくら？"],
    ["Could you", "〜してもらえますか？"],
    ["How about", "〜はどう？"],
    ["on sale", "セール中"],
    ["Can I pay by card", "カードで払えますか？"],
    ["I'm afraid", "あいにく〜"],
    ["Let me check", "確認します"]
  ],
  dialogs: [
    { id: "price-1", title: "市場で値段交渉", A: "店主", B: "あなた（客）", def: "B", lines: [
      ["B", "How much is this bag?", "このバッグはいくらですか？"],
      ["A", "That one's 80 dollars. It's handmade leather.", "それは80ドルです。手作りの革製ですよ。"],
      ["B", "It's really nice, but that's a bit more than I wanted to spend.", "すごく素敵ですが、思っていたより少し高いです。"],
      ["A", "How much were you thinking?", "いくらくらいをお考えですか？"],
      ["B", "Could you do 50?", "50ドルにしてもらえませんか？"],
      ["A", "Oh, 50 is too low. I can do 70.", "いや、50は安すぎますよ。70なら。"],
      ["B", "How about 60? I'll pay cash.", "60ドルではどうですか？現金で払います。"],
      ["A", "Hmm... 65, and that's my final offer.", "うーん…65ドル、これが最終価格です。"],
      ["B", "If I buy two, could you give me a better deal?", "2つ買ったら、もっと安くしてもらえますか？"],
      ["A", "Two for 120. That's a good deal.", "2つで120ドル。お得ですよ。"],
      ["B", "Okay, it's a deal. I'll take two.", "わかりました、それで決まりです。2つください。"],
      ["A", "Thank you! I'll wrap them for you.", "ありがとう！包みますね。"]
    ]},
    { id: "price-2", title: "セール品の確認", A: "店員", B: "あなた（客）", def: "B", lines: [
      ["B", "Excuse me, is this on sale? The sign says 30% off, but there's no sale sticker.", "すみません、これはセール品ですか？30％オフと書いてありますが、セールのシールが貼ってなくて。"],
      ["A", "Let me check... Yes, everything on this rack is 30% off.", "確認します…はい、このラックの商品はすべて30％オフです。"],
      ["B", "Great. So how much would it be?", "よかった。じゃあいくらになりますか？"],
      ["A", "It's normally 60 dollars, so it'd be 42.", "通常60ドルなので、42ドルになります。"],
      ["B", "Is the discount applied at the register?", "割引はレジで適用されますか？"],
      ["A", "Yes, it'll come off automatically when you pay.", "はい、お支払いのときに自動的に引かれます。"],
      ["B", "Can I return it if it doesn't fit?", "サイズが合わなかったら返品できますか？"],
      ["A", "I'm afraid sale items can be exchanged, but not refunded.", "申し訳ありませんが、セール品は交換はできますが、返金はできません。"],
      ["B", "I see. Then could I try it on first?", "なるほど。では先に試着してもいいですか？"],
      ["A", "Of course. The fitting room is in the back.", "もちろんです。試着室は奥にあります。"]
    ]},
    { id: "price-3", title: "支払いトラブル", A: "レジ係", B: "あなた（客）", def: "B", lines: [
      ["A", "That'll be 86 dollars and 40 cents.", "86ドル40セントになります。"],
      ["B", "Hmm, that seems a bit high. Could you check the price on the shampoo? It's supposed to be on sale.", "うーん、ちょっと高い気がします。シャンプーの値段を確認してもらえますか？セール中のはずなんです。"],
      ["A", "Let me check... You're right. It rang up at full price. Sorry about that.", "確認します…おっしゃる通りです。定価で打たれていました。失礼しました。"],
      ["B", "No problem. So how much is it now?", "大丈夫です。それで今はいくらですか？"],
      ["A", "Now it's 79 dollars and 90 cents.", "79ドル90セントです。"],
      ["B", "Okay. Can I pay by card?", "わかりました。カードで払えますか？"],
      ["A", "Sure... Oh, it says the card was declined.", "はい…あ、カードが承認されなかったと出ています。"],
      ["B", "Really? That's strange. Could you try it one more time?", "本当ですか？おかしいな。もう一度試してもらえますか？"],
      ["A", "Sure... I'm afraid it was declined again.", "はい…申し訳ありませんが、また承認されませんでした。"],
      ["B", "Then I'll pay with a different card. Here you go.", "では別のカードで払います。どうぞ。"],
      ["A", "That went through. Here's your receipt.", "通りました。こちらがレシートです。"],
      ["B", "Thanks. Sorry for the trouble.", "ありがとう。お手数おかけしました。"]
    ]}
  ]
});
