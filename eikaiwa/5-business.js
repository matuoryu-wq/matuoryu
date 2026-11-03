// ビジネス
window.EK_DATA = window.EK_DATA || [];

EK_DATA.push({
  cat: "ビジネス", series: "初対面",
  keys: [
    ["Thank you for", "〜していただきありがとうございます"],
    ["Glad to hear that", "それはよかったです"],
    ["Is this your first time", "〜は初めてですか？"],
    ["I'd love to", "ぜひ〜したいです"],
    ["I know just the place", "ぴったりの店を知っています"],
    ["Shall we", "〜しましょうか？"],
    ["Thanks for", "〜してくれてありがとう"]
  ],
  dialogs: [
    { id: "meet-1", title: "挨拶と名刺交換", A: "取引先（デビッド）", B: "あなた（ユキ）", def: "B", lines: [
      ["A", "Hi, you must be Ms. Yamada. I'm David Brown from Clearwater.", "こんにちは、山田さんですね。クリアウォーター社のデビッド・ブラウンです。"],
      ["B", "Yes, nice to meet you, Mr. Brown. Thank you for coming all this way.", "はい、はじめまして、ブラウンさん。遠いところお越しいただきありがとうございます。"],
      ["A", "Please, call me David. And thanks for having me.", "デビッドと呼んでください。お招きいただきありがとうございます。"],
      ["B", "Then please call me Yuki. Here's my card.", "では、ユキと呼んでください。名刺をどうぞ。"],
      ["A", "Thank you. And here's mine.", "ありがとうございます。私のもどうぞ。"],
      ["B", "How was your flight?", "フライトはいかがでしたか？"],
      ["A", "Long, but not bad. I managed to get some sleep.", "長かったですが、悪くなかったです。少し眠れました。"],
      ["B", "Glad to hear that. Is this your first time in Tokyo?", "それはよかったです。東京は初めてですか？"],
      ["A", "It is, actually. I've been looking forward to it.", "実はそうなんです。楽しみにしていました。"],
      ["B", "Well, if you have any free time, I'd be happy to recommend some places.", "もしお時間があれば、喜んでおすすめの場所をご紹介しますよ。"],
      ["A", "That would be great. I'd love to try some authentic sushi.", "それはうれしいです。本格的なお寿司を食べてみたいです。"],
      ["B", "I know just the place. Shall we head to the meeting room?", "ぴったりの店を知っています。会議室に行きましょうか？"]
    ]},
    { id: "meet-2", title: "会食での雑談", A: "取引先（デビッド）", B: "あなた（ユキ）", def: "B", lines: [
      ["B", "So, David, how are you enjoying Tokyo so far?", "それで、デビッド、東京はここまでいかがですか？"],
      ["A", "I love it. Everything's so clean, and the trains are always on time.", "気に入ってます。どこもきれいで、電車はいつも時間通りですね。"],
      ["B", "Ha, people always say that. Have you had a chance to look around?", "はは、みんなそう言いますね。見て回る機会はありましたか？"],
      ["A", "I walked around Asakusa this morning. It was amazing.", "今朝、浅草を歩きました。素晴らしかったです。"],
      ["B", "Glad to hear that. Is there anything else you'd like to try while you're here?", "それはよかった。滞在中に他に試してみたいものはありますか？"],
      ["A", "I'd love to try some authentic ramen. Any recommendations?", "本格的なラーメンを食べてみたいです。おすすめはありますか？"],
      ["B", "I know just the place. It's a small shop near our office.", "ぴったりの店を知っています。うちのオフィスの近くの小さな店です。"],
      ["A", "Perfect. So, how long have you been with your company?", "完璧です。ところで、今の会社にはどのくらいお勤めですか？"],
      ["B", "About eight years now. I started in sales, and moved to planning three years ago.", "もう8年ほどです。営業から始めて、3年前に企画に移りました。"],
      ["A", "Interesting. Do you enjoy it?", "興味深いですね。楽しいですか？"],
      ["B", "I do. It's challenging, but I like working with overseas partners like you.", "はい。大変ですが、あなたのような海外のパートナーと仕事をするのは好きです。"],
      ["A", "Well, cheers to that.", "では、それに乾杯しましょう。"]
    ]},
    { id: "meet-3", title: "オンライン会議の冒頭", A: "海外の取引先（サラ）", B: "あなた", def: "B", lines: [
      ["B", "Hi Sarah, can you hear me okay?", "こんにちは、サラ。声はちゃんと聞こえますか？"],
      ["A", "Yes, loud and clear. Can you see my screen?", "はい、はっきり聞こえます。私の画面は見えますか？"],
      ["B", "Not yet... Oh, there it is.", "まだです…あ、映りました。"],
      ["A", "Great. Thanks for making time today. I know it's late over there.", "よかった。今日は時間をとってくれてありがとう。そちらは遅い時間ですよね。"],
      ["B", "No problem. It's only 8 p.m. here. How's the weather in London?", "大丈夫ですよ。こちらはまだ夜8時です。ロンドンの天気はどうですか？"],
      ["A", "Gray and rainy, as usual.", "いつも通り、どんよりして雨です。"],
      ["B", "Ha, I'd love to visit sometime anyway.", "はは、それでもいつか行ってみたいです。"],
      ["A", "You should! So, shall we get started?", "ぜひ！では、始めましょうか？"],
      ["B", "Sure. Before we begin, is Mark joining us?", "はい。始める前に、マークは参加しますか？"],
      ["A", "He's running a few minutes late, so let's start without him.", "数分遅れるそうなので、彼抜きで始めましょう。"],
      ["B", "Sounds good. I've shared the agenda in the chat.", "いいですね。チャットに議題を共有しました。"],
      ["A", "Got it. Let's go through it one by one.", "確認しました。一つずつ見ていきましょう。"]
    ]}
  ]
});

EK_DATA.push({
  cat: "ビジネス", series: "日程・連絡",
  keys: [
    ["work for you", "ご都合はいかがですか？"],
    ["works for me", "（日時が）大丈夫です"],
    ["How about", "〜はいかがですか？"],
    ["Would you like to", "〜なさいますか？"],
    ["call me back", "折り返し電話する"],
    ["let you know", "お知らせする"],
    ["keep me posted", "随時知らせてください"],
    ["I'm afraid", "申し訳ないのですが"]
  ],
  dialogs: [
    { id: "sched-1", title: "会議の日程調整", A: "取引先（ジェニファー）", B: "あなた", def: "B", lines: [
      ["B", "Hi Jennifer, I'm calling to set up a meeting about the new project.", "こんにちは、ジェニファー。新しいプロジェクトの打ち合わせを設定したくてお電話しました。"],
      ["A", "Sure. When were you thinking?", "いいですよ。いつ頃をお考えですか？"],
      ["B", "Would sometime next week work for you?", "来週のどこかでご都合はいかがですか？"],
      ["A", "Next week's pretty busy, but I could do Tuesday or Thursday afternoon.", "来週はかなり忙しいですが、火曜か木曜の午後なら大丈夫です。"],
      ["B", "How about Thursday at 2?", "木曜の2時はいかがですか？"],
      ["A", "Thursday at 2 works for me. How long do you think it'll take?", "木曜の2時なら大丈夫です。どれくらいかかりそうですか？"],
      ["B", "About an hour. Would you prefer to meet in person or online?", "1時間ほどです。対面とオンライン、どちらがよろしいですか？"],
      ["A", "Online would be easier for me, if that's okay.", "よろしければ、オンラインの方が助かります。"],
      ["B", "No problem. I'll send you a calendar invite with the link.", "大丈夫です。リンク付きのカレンダー招待をお送りします。"],
      ["A", "Great. Should I invite anyone from my team?", "よかった。私のチームから誰か呼んだ方がいいですか？"],
      ["B", "If possible, it'd be great if your engineer could join.", "可能であれば、エンジニアの方にも参加していただけると助かります。"],
      ["A", "I'll check with him and let you know.", "本人に確認してお知らせします。"],
      ["B", "Thanks. I'll follow up by email.", "ありがとうございます。メールでも改めて連絡します。"]
    ]},
    { id: "sched-2", title: "電話の取次ぎ", A: "あなた（受付）", B: "取引先（スティーブ）", def: "A", lines: [
      ["A", "Good morning, Sakura Trading. This is Kato speaking.", "おはようございます、さくら商事の加藤です。"],
      ["B", "Hi, this is Steve Wilson from Pacific Logistics. Could I speak to Mr. Kimura, please?", "もしもし、パシフィック・ロジスティクスのスティーブ・ウィルソンです。木村さんをお願いできますか？"],
      ["A", "Certainly. May I ask what this is regarding?", "かしこまりました。どのようなご用件でしょうか？"],
      ["B", "It's about the shipment schedule for next month.", "来月の出荷スケジュールの件です。"],
      ["A", "One moment, please... I'm afraid Mr. Kimura is in a meeting right now.", "少々お待ちください…申し訳ありませんが、木村はただいま会議中です。"],
      ["B", "Do you know when he'll be available?", "いつ頃お手すきになるかわかりますか？"],
      ["A", "He should be back around three. Would you like to leave a message?", "3時頃には戻る予定です。伝言を承りましょうか？"],
      ["B", "Yes, could you ask him to call me back? It's a bit urgent.", "はい、折り返し電話をいただけるよう伝えていただけますか？少し急ぎなんです。"],
      ["A", "Of course. Could I get your number, just in case?", "かしこまりました。念のためお電話番号をいただけますか？"],
      ["B", "Sure. It's 555-0147.", "はい。555-0147です。"],
      ["A", "Let me read that back: 555-0147. I'll make sure he gets the message.", "復唱します。555-0147ですね。必ず伝えます。"],
      ["B", "Thanks a lot.", "ありがとうございます。"]
    ]},
    { id: "sched-3", title: "締切の延長をお願いする", A: "あなた", B: "取引先（リンダ）", def: "A", lines: [
      ["A", "Hi Linda, do you have a minute?", "こんにちは、リンダ。少しお時間いいですか？"],
      ["B", "Sure. What's up?", "ええ。どうしましたか？"],
      ["A", "I wanted to talk to you about the report deadline.", "報告書の締切についてお話ししたくて。"],
      ["B", "It's due this Friday, right?", "今週の金曜ですよね？"],
      ["A", "Yes. I'm afraid we need a little more time. One of our data sources was delayed.", "はい。申し訳ないのですが、もう少し時間が必要です。データの一部の入手が遅れていまして。"],
      ["B", "I see. How much more time do you need?", "なるほど。あとどれくらい必要ですか？"],
      ["A", "Would next Wednesday work for you?", "来週の水曜でいかがでしょうか？"],
      ["B", "Hmm, that's cutting it close. We have a board meeting on Thursday.", "うーん、ぎりぎりですね。木曜に取締役会があるんです。"],
      ["A", "I understand. How about we send you a draft by Monday, and the final version on Wednesday?", "わかります。月曜までに草案をお送りして、水曜に最終版というのはいかがでしょうか？"],
      ["B", "That works for me. Just keep me posted if anything changes.", "それなら大丈夫です。何か変わったら随時知らせてください。"],
      ["A", "Absolutely. Thanks for being so flexible.", "もちろんです。柔軟にご対応いただきありがとうございます。"]
    ]}
  ]
});

EK_DATA.push({
  cat: "ビジネス", series: "会議・交渉",
  keys: [
    ["That's a good point", "いい指摘ですね"],
    ["I see where you're coming from", "おっしゃることはわかります"],
    ["What if we", "〜するのはどうでしょう？"],
    ["What about", "〜についてはどうですか？"],
    ["Could you", "〜していただけますか？"],
    ["get back to you", "（後で）お返事する"],
    ["I think we should", "〜すべきだと思います"]
  ],
  dialogs: [
    { id: "mtg-1", title: "会議で意見を述べる", A: "上司（マイク）", B: "あなた", def: "B", lines: [
      ["A", "Okay, next item: the marketing budget for next year. Any thoughts?", "では次の議題、来年度のマーケティング予算です。何か意見はありますか？"],
      ["B", "If I may, I'd like to share an idea.", "よろしければ、一つ提案させてください。"],
      ["A", "Sure, go ahead.", "どうぞ。"],
      ["B", "I think we should shift more of the budget to online ads.", "オンライン広告に予算をもっと振り向けるべきだと思います。"],
      ["A", "What makes you say that?", "どうしてそう思うの？"],
      ["B", "Our data shows that most new customers find us through social media.", "データを見ると、新規顧客のほとんどがSNS経由で来ているんです。"],
      ["A", "That's a good point. But what about our older customers?", "いい指摘だね。でも、年配のお客さんはどうする？"],
      ["B", "That's true. We could keep some print ads for them, but cut back gradually.", "確かに。その層向けに紙の広告を一部残しつつ、徐々に減らせばいいと思います。"],
      ["A", "I like that. Could you put together a proposal with some numbers?", "いいね。数字を入れた提案書をまとめてもらえる？"],
      ["B", "Sure. I'll have it ready by next Monday.", "はい。来週の月曜までに用意します。"],
      ["A", "Great. Let's discuss it at the next meeting.", "よし。次の会議で話し合おう。"]
    ]},
    { id: "mtg-2", title: "反対意見を伝える", A: "同僚（ポール）", B: "あなた", def: "B", lines: [
      ["A", "So I think we should launch the new product in April.", "というわけで、新製品は4月に発売すべきだと思います。"],
      ["B", "I see where you're coming from, but I have some concerns.", "言いたいことはわかりますが、いくつか懸念があります。"],
      ["A", "Okay, what are they?", "わかりました、どんな点ですか？"],
      ["B", "Well, testing won't be finished until the end of March. That doesn't give us much time.", "テストが3月末まで終わらないんです。それだと時間的に余裕がありません。"],
      ["A", "But if we wait, our competitors might beat us to it.", "でも待っていたら、競合に先を越されるかもしれません。"],
      ["B", "That's a good point. But if there's a problem after launch, it could hurt our reputation.", "それはもっともです。でも発売後に問題が出たら、評判に傷がつくかもしれません。"],
      ["A", "Hmm. So what do you suggest?", "うーん。では、どうすればいいと思いますか？"],
      ["B", "What if we do a soft launch in April with a small group of customers?", "4月に一部のお客様に限定して先行発売するのはどうでしょう？"],
      ["A", "And then a full launch in June?", "それで6月に本格発売ですか？"],
      ["B", "Exactly. That way, we can fix any issues before the big release.", "その通りです。そうすれば、本格発売前に問題を直せます。"],
      ["A", "I think that could work. Let's run it by the team.", "それならいけそうですね。チームにも相談してみましょう。"]
    ]},
    { id: "mtg-3", title: "条件の交渉", A: "取引先（ガルシア）", B: "あなた", def: "B", lines: [
      ["A", "So, we've looked at your proposal. Overall, we're interested.", "さて、御社の提案を拝見しました。全体としては興味があります。"],
      ["B", "That's great to hear. Do you have any questions?", "それはうれしいです。何かご質問はありますか？"],
      ["A", "To be honest, the price is a little higher than we expected.", "正直に言うと、価格が想定より少し高いです。"],
      ["B", "I understand. What kind of price did you have in mind?", "わかります。どのくらいの価格をお考えでしたか？"],
      ["A", "We were hoping for about 10% lower.", "10％ほど安くなればと思っていました。"],
      ["B", "I see. 10% would be difficult, but if you can commit to a two-year contract, we could do 5%.", "なるほど。10％は難しいですが、2年契約をお約束いただけるなら5％は可能です。"],
      ["A", "Hmm. What about 7%, with a two-year contract?", "うーん。2年契約で7％ではどうですか？"],
      ["B", "I'd need to check with my manager, but I think we could meet you halfway at 6%.", "上司に確認が必要ですが、間を取って6％ならいけると思います。"],
      ["A", "That sounds reasonable. Could you also include free maintenance for the first year?", "それは妥当ですね。初年度の無料メンテナンスもつけてもらえますか？"],
      ["B", "I think that's doable. I'll confirm both points and get back to you by Friday.", "それは可能だと思います。両方の点を確認して、金曜までにお返事します。"],
      ["A", "Great. I look forward to hearing from you.", "よかった。ご連絡をお待ちしています。"]
    ]},
    { id: "mtg-4", title: "会議のまとめ", A: "上司（マイク）", B: "あなた", def: "B", lines: [
      ["A", "We're almost out of time. Could you sum up what we've decided?", "そろそろ時間だ。決まったことをまとめてもらえる？"],
      ["B", "Sure. First, we'll shift part of the budget to online ads.", "はい。まず、予算の一部をオンライン広告に回します。"],
      ["A", "Right. And what about the product launch?", "そうだね。それと、製品の発売は？"],
      ["B", "We'll do a soft launch in April and a full launch in June.", "4月に先行発売、6月に本格発売を行います。"],
      ["A", "Good. Who's going to handle the customer feedback?", "よし。お客さんの意見への対応は誰がやる？"],
      ["B", "I think we should ask Paul's team. They have the most experience.", "ポールのチームにお願いすべきだと思います。一番経験がありますから。"],
      ["A", "That's a good point. I'll talk to him this afternoon.", "いい指摘だね。今日の午後に彼と話すよ。"],
      ["B", "Thank you. What if we meet again next Friday to check our progress?", "ありがとうございます。来週の金曜にもう一度集まって、進み具合を確認するのはどうでしょう？"],
      ["A", "Sounds good. Could you send out the minutes today?", "いいね。議事録を今日中に送ってもらえる？"],
      ["B", "Of course. If anything's unclear, I'll get back to you.", "もちろんです。不明な点があれば、またご連絡します。"],
      ["A", "Great. Thanks, everyone. Good meeting.", "よし。みんなありがとう。いい会議だった。"]
    ]}
  ]
});
