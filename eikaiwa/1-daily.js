// 日常会話
window.EK_DATA = window.EK_DATA || [];

EK_DATA.push({
  cat: "日常会話", series: "雑談",
  keys: [
    ["How's it going", "調子どう？"],
    ["Can you believe", "〜って信じられる？"],
    ["I know, right?", "ほんとそれ"],
    ["Not much", "特に何も"],
    ["Sounds like", "〜みたいだね"],
    ["I'd better get", "そろそろ〜しなきゃ"],
    ["Catch you later", "またね"]
  ],
  dialogs: [
    { id: "chat-1", title: "近所の人と天気の話", A: "近所の人（リンダ）", B: "あなた", def: "B", lines: [
      ["A", "Morning! Can you believe this weather?", "おはよう！この天気、信じられる？"],
      ["B", "I know, right? It was freezing last week, and now it's like summer.", "ほんとですよね。先週は凍えるほど寒かったのに、今は夏みたい。"],
      ["A", "I heard it's supposed to rain again this weekend, though.", "でも週末はまた雨らしいよ。"],
      ["B", "Seriously? I was planning to do some gardening.", "本当ですか？庭いじりをするつもりだったんですけど。"],
      ["A", "Oh, well. Maybe Saturday morning will be okay.", "まあ、土曜の朝なら大丈夫かもね。"],
      ["B", "Fingers crossed. How's your dog doing, by the way?", "そうだといいですね。ところで、ワンちゃんは元気ですか？"],
      ["A", "Max? He's great. A little too energetic, if anything.", "マックス？元気よ。むしろ元気すぎるくらい。"],
      ["B", "Ha, sounds like my kids.", "はは、うちの子どもたちみたいですね。"],
      ["A", "Speaking of which, how are they doing?", "そういえば、お子さんたちは元気？"],
      ["B", "They're good. Busy with school and soccer.", "元気です。学校とサッカーで忙しくしてます。"],
      ["A", "Well, I'd better get going. Max is waiting.", "さて、そろそろ行かなきゃ。マックスが待ってるから。"],
      ["B", "Sure. Have a good one!", "ええ。良い一日を！"],
      ["A", "You too. Catch you later!", "あなたもね。またね！"]
    ]},
    { id: "chat-2", title: "同僚と週末の話", A: "同僚（トム）", B: "あなた", def: "B", lines: [
      ["A", "Hey, how's it going? Do anything fun this weekend?", "やあ、調子どう？週末は何か楽しいことした？"],
      ["B", "Not much, honestly. I just stayed home and binge-watched a new show.", "正直、特に何も。家で新しいドラマを一気見してただけ。"],
      ["A", "Oh yeah? Which one?", "へえ、どれ？"],
      ["B", "That new crime drama everyone's talking about. I couldn't stop watching.", "みんなが話題にしてる新しい犯罪ドラマ。止まらなくなっちゃって。"],
      ["A", "I've been meaning to check that out. Is it worth it?", "ずっと見ようと思ってたんだ。見る価値ある？"],
      ["B", "Totally. The first episode is a bit slow, but it really picks up.", "絶対ある。1話目はちょっとゆっくりだけど、どんどん面白くなるよ。"],
      ["A", "Good to know. I'll give it a shot.", "いいこと聞いた。見てみるよ。"],
      ["B", "What about you? What did you get up to?", "そっちは？何してたの？"],
      ["A", "I went hiking with my brother. We got caught in the rain, though.", "弟とハイキングに行ったよ。でも雨に降られちゃって。"],
      ["B", "Can you believe how much the weather's been changing lately?", "最近の天気の変わりようって信じられないよね。"],
      ["A", "I know, right? I should've checked the forecast.", "ほんとそれ。天気予報を見とくべきだった。"],
      ["B", "Sounds like you still had fun, though.", "でも楽しかったみたいだね。"],
      ["A", "Yeah, it was worth it. Anyway, I'd better get back to work.", "うん、行ってよかったよ。さて、仕事に戻らなきゃ。"],
      ["B", "Same here. Catch you later.", "私も。じゃあまた。"]
    ]},
    { id: "chat-3", title: "久しぶりの友人と近況報告", A: "友人（エマ）", B: "あなた", def: "B", lines: [
      ["A", "Oh my gosh, is that you? It's been ages!", "うそ、あなた？すごく久しぶり！"],
      ["B", "Emma! I can't believe it. How's it going?", "エマ！信じられない。元気にしてた？"],
      ["A", "Pretty good! So, what have you been up to?", "まあまあかな！それで、最近どうしてたの？"],
      ["B", "Not much, really. Work's been crazy, but I'm hanging in there.", "特に何も。仕事がめちゃくちゃ忙しいけど、なんとかやってるよ。"],
      ["A", "I hear you. Are you still at the same company?", "わかる。まだ同じ会社にいるの？"],
      ["B", "Yeah, but I got promoted last spring.", "うん、でも去年の春に昇進したんだ。"],
      ["A", "No way! Congratulations! That's huge.", "うそ！おめでとう！すごいじゃない。"],
      ["B", "Thanks. What about you? Last I heard, you were moving to Osaka.", "ありがとう。そっちは？最後に聞いたときは大阪に引っ越すって話だったよね。"],
      ["A", "I did, actually. I just came back to visit my parents.", "実際に引っ越したよ。両親に会いに帰ってきたところ。"],
      ["B", "Sounds like things are going well for you.", "順調そうだね。"],
      ["A", "They are. Hey, we should grab coffee while I'm here.", "うん。ねえ、こっちにいる間にコーヒーでも行こうよ。"],
      ["B", "Definitely. Let me give you my new number.", "ぜひ。新しい番号を教えるね。"],
      ["A", "Perfect. I'd better get going, but I'll text you.", "ばっちり。もう行かなきゃだけど、メッセージ送るね。"],
      ["B", "Great. Catch you later!", "いいね。またね！"]
    ]},
    { id: "chat-4", title: "パーティーで初対面", A: "パーティーの参加者（ジェイク）", B: "あなた（ケン）", def: "B", lines: [
      ["A", "Hi there! I don't think we've met. I'm Jake.", "こんにちは！初めてですよね。ジェイクです。"],
      ["B", "Nice to meet you, Jake. I'm Ken. How's it going?", "はじめまして、ジェイク。ケンです。調子はどう？"],
      ["A", "Pretty good, thanks. So, how do you know Lisa?", "いい感じだよ、ありがとう。それで、リサとはどういう知り合い？"],
      ["B", "We used to work together. What about you?", "前に一緒に働いてたんだ。そっちは？"],
      ["A", "We're neighbors. She's always throwing parties like this.", "近所なんだ。彼女はいつもこういうパーティーを開いてるよ。"],
      ["B", "Sounds like she's a great host. The food is amazing.", "いいホストみたいだね。料理がすごくおいしい。"],
      ["A", "I know, right? She made everything herself.", "だよね。全部自分で作ったんだって。"],
      ["B", "Can you believe that? I can barely make toast.", "信じられる？僕なんてトーストもろくに焼けないよ。"],
      ["A", "Ha, same here. So, what do you do?", "はは、僕も。それで、仕事は何してるの？"],
      ["B", "I'm a lawyer. It's not as exciting as it sounds, though.", "弁護士だよ。思われてるほど華やかじゃないけどね。"],
      ["A", "Are you kidding? That sounds really interesting.", "冗談でしょ？すごく面白そうだよ。"],
      ["B", "It has its moments. Anyway, I'd better get another drink. Can I get you one?", "たまにはね。さて、飲み物をもう一杯取ってくるよ。君の分も持ってこようか？"],
      ["A", "I'm good, thanks. Catch you later!", "大丈夫、ありがとう。またあとで！"]
    ]}
  ]
});

EK_DATA.push({
  cat: "日常会話", series: "誘う・予定",
  keys: [
    ["Are you free", "〜は空いてる？"],
    ["Do you want to", "〜しない？"],
    ["Let me check", "確認してみるね"],
    ["How about", "〜はどう？"],
    ["works for me", "（日時などが）都合がいい"],
    ["I'm afraid", "あいにく〜"],
    ["I'd love to", "ぜひ〜したい"],
    ["Something came up", "急用が入った"],
    ["rain check", "また今度（誘いを延期）"],
    ["I owe you one", "借りができたね"]
  ],
  dialogs: [
    { id: "plan-1", title: "食事に誘う", A: "誘う人（サム）", B: "誘われる人", def: "B", lines: [
      ["A", "Hey, are you free this Friday night?", "ねえ、今週の金曜の夜って空いてる？"],
      ["B", "Let me check... Yeah, I think so. What's up?", "ちょっと確認するね…うん、空いてると思う。どうしたの？"],
      ["A", "There's a new Thai place downtown. Do you want to try it?", "街中に新しいタイ料理の店ができたんだ。行ってみない？"],
      ["B", "I'd love to. I've been craving Thai food lately.", "ぜひ。最近ずっとタイ料理が食べたかったんだ。"],
      ["A", "Great! How about seven o'clock?", "よかった！7時でどう？"],
      ["B", "That works for me. Should I make a reservation?", "大丈夫。予約しようか？"],
      ["A", "No, I'll take care of it. They're pretty popular, so I'll call today.", "いや、こっちでやっておくよ。結構人気だから今日電話しておく。"],
      ["B", "Thanks. Should we meet at the station?", "ありがとう。駅で待ち合わせる？"],
      ["A", "Sure. Let's meet at the north exit around ten to seven.", "いいよ。7時10分前くらいに北口で会おう。"],
      ["B", "Sounds good. Can I bring my roommate?", "いいね。ルームメイトも連れて行っていい？"],
      ["A", "Of course! The more, the merrier.", "もちろん！大勢の方が楽しいよ。"],
      ["B", "Awesome. I'll let her know. See you Friday!", "やった。彼女に伝えておくね。じゃあ金曜に！"]
    ]},
    { id: "plan-2", title: "予定を変更する", A: "あなた（変更をお願いする）", B: "友人", def: "A", lines: [
      ["A", "Hey, sorry to do this, but something came up on Friday.", "ねえ、悪いんだけど、金曜に急用が入っちゃって。"],
      ["B", "Oh no, is everything okay?", "えっ、大丈夫？"],
      ["A", "Yeah, it's just work. My boss wants me to finish a report by Monday.", "うん、仕事なんだ。上司に月曜までに報告書を仕上げてって言われて。"],
      ["B", "Ugh, that's the worst. Do you want to push it back to next week?", "うわ、最悪だね。来週にずらす？"],
      ["A", "That would be great. Are you free next Wednesday?", "そうしてもらえると助かる。来週の水曜は空いてる？"],
      ["B", "Let me check my calendar... I'm afraid I have a dentist appointment that day.", "カレンダーを見てみる…あいにくその日は歯医者の予約があるんだ。"],
      ["A", "How about Thursday, then?", "じゃあ木曜はどう？"],
      ["B", "Thursday works for me. Same time?", "木曜なら大丈夫。同じ時間？"],
      ["A", "Yeah, seven o'clock. I'll change the reservation.", "うん、7時で。予約は変更しておくね。"],
      ["B", "Perfect. And don't worry about it. These things happen.", "完璧。気にしないで。よくあることだよ。"],
      ["A", "Thanks for being so understanding. I owe you one.", "わかってくれてありがとう。借りができたね。"],
      ["B", "Ha, then dinner's on you!", "はは、じゃあ夕飯はおごりね！"]
    ]},
    { id: "plan-3", title: "誘いを断る", A: "同僚（レイチェル）", B: "あなた（断る）", def: "B", lines: [
      ["A", "Hey, a few of us are going to karaoke after work. Do you want to come?", "ねえ、仕事の後に何人かでカラオケに行くんだけど。来ない？"],
      ["B", "Oh, I'd love to, but I'm afraid I can't tonight.", "ああ、行きたいんだけど、あいにく今夜は無理なんだ。"],
      ["A", "Aw, that's too bad. Got other plans?", "えー、残念。他に予定があるの？"],
      ["B", "Yeah, I promised my wife I'd be home early. It's our anniversary.", "うん、早く帰るって妻と約束してて。結婚記念日なんだ。"],
      ["A", "Oh, that's sweet! You definitely can't miss that.", "わあ、素敵！それは絶対外せないね。"],
      ["B", "Can I take a rain check, though? I'd really like to go next time.", "でもまた今度誘ってもらえる？次はぜひ行きたいんだ。"],
      ["A", "Of course. How about next Friday?", "もちろん。来週の金曜はどう？"],
      ["B", "Let me check... Yeah, next Friday works for me.", "確認するね…うん、来週の金曜なら大丈夫。"],
      ["A", "Great, I'll let everyone know.", "よかった、みんなに伝えておくね。"],
      ["B", "Thanks for asking me. Have fun tonight!", "誘ってくれてありがとう。今夜楽しんでね！"],
      ["A", "You too. Happy anniversary!", "あなたもね。記念日おめでとう！"]
    ]}
  ]
});

EK_DATA.push({
  cat: "日常会話", series: "体調",
  keys: [
    ["under the weather", "体調がすぐれない"],
    ["get some rest", "休む"],
    ["Let me know if", "〜だったら言ってね"],
    ["Take care", "お大事に／気をつけて"],
    ["I hope", "〜だといいね"],
    ["feel better", "良くなる"],
    ["That must be", "それは〜だろうね"],
    ["I'm sorry to hear that", "それは大変でしたね"]
  ],
  dialogs: [
    { id: "health-1", title: "風邪気味の同僚と話す", A: "同僚（クリス）", B: "あなた（風邪気味）", def: "B", lines: [
      ["A", "Hey, are you okay? You don't look so good.", "ねえ、大丈夫？具合悪そうだよ。"],
      ["B", "I'm feeling a little under the weather. I think I'm coming down with a cold.", "ちょっと体調が悪くて。風邪をひきかけてるみたい。"],
      ["A", "Oh no. Do you have a fever?", "あら。熱はあるの？"],
      ["B", "Not yet, but my throat's killing me.", "まだないけど、喉がすごく痛くて。"],
      ["A", "You should go home and get some rest.", "帰って休んだほうがいいよ。"],
      ["B", "I wish I could, but I have a meeting at three.", "そうしたいけど、3時に会議があるんだ。"],
      ["A", "I can cover for you. Just send me your notes.", "代わりに出るよ。メモだけ送って。"],
      ["B", "Really? That would be a huge help.", "本当？すごく助かる。"],
      ["A", "No problem. Let me know if you need anything else.", "気にしないで。他に何か必要だったら言ってね。"],
      ["B", "Thanks. I owe you one.", "ありがとう。借りができたね。"],
      ["A", "Don't mention it. Take care, and I hope you feel better soon.", "いいって。お大事に、早く良くなるといいね。"]
    ]},
    { id: "health-2", title: "ケガの話", A: "ケガをした友人", B: "あなた", def: "B", lines: [
      ["B", "Whoa, what happened to your arm? Are you okay?", "うわ、その腕どうしたの？大丈夫？"],
      ["A", "Oh, this? I slipped on the stairs at the station and broke my wrist.", "ああ、これ？駅の階段で滑って手首を骨折しちゃって。"],
      ["B", "Ouch! That sounds painful.", "痛っ！それは痛そう。"],
      ["A", "It was. I had to go to the ER.", "痛かったよ。救急に行かなきゃいけなかった。"],
      ["B", "How long do you have to wear the cast?", "ギプスはどれくらいつけなきゃいけないの？"],
      ["A", "About six weeks, they said. It's such a pain. I can't even tie my shoes.", "6週間くらいだって。本当に面倒で。靴ひもも結べないんだ。"],
      ["B", "That must be really frustrating. Is there anything I can do?", "それはすごくもどかしいね。何かできることある？"],
      ["A", "Actually, could you help me carry these bags to my car?", "実は、この荷物を車まで運ぶのを手伝ってもらえる？"],
      ["B", "Sure, no problem. Let me know if you need help with anything else.", "もちろん、いいよ。他にも手伝いが必要だったら言ってね。"],
      ["A", "Thanks, I really appreciate it.", "ありがとう、本当に助かるよ。"],
      ["B", "Take care of yourself. I hope it heals quickly.", "お大事に。早く治るといいね。"]
    ]},
    { id: "health-3", title: "家族の体調を気遣う", A: "同僚（カレン）", B: "あなた（母が入院中）", def: "B", lines: [
      ["A", "Hey, I heard your mom was in the hospital. Is she okay?", "ねえ、お母さんが入院したって聞いたけど。大丈夫？"],
      ["B", "She's doing better now, thanks. She had surgery on her knee last week.", "今はだいぶ良くなってるよ、ありがとう。先週ひざの手術を受けたんだ。"],
      ["A", "Oh, I'm sorry to hear that. How did it go?", "そうだったの、大変だったね。手術はどうだった？"],
      ["B", "It went well. The doctor said she should be walking normally in a couple of months.", "うまくいったよ。お医者さんによると、2、3か月で普通に歩けるようになるって。"],
      ["A", "That's a relief. You must have been worried.", "ほっとしたね。心配だったでしょう。"],
      ["B", "Yeah, I was. I've been visiting her every evening after work.", "うん、心配だった。毎晩仕事の後に会いに行ってるんだ。"],
      ["A", "That must be exhausting. Make sure you get some rest too.", "それは疲れるね。あなたもちゃんと休んでね。"],
      ["B", "I'll try. I might need to leave early a few days this week, though.", "そうするよ。でも今週は何日か早めに帰るかもしれない。"],
      ["A", "Of course. Let me know if I can help with anything at work.", "もちろん。仕事で手伝えることがあったら言ってね。"],
      ["B", "Thanks. That means a lot.", "ありがとう。本当にうれしいよ。"],
      ["A", "Please tell her I hope she feels better soon.", "お母さんに、早く良くなりますようにって伝えてね。"]
    ]}
  ]
});
