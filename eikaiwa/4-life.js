// 生活
window.EK_DATA = window.EK_DATA || [];

EK_DATA.push({
  cat: "生活", series: "病院",
  keys: [
    ["Is this your first time", "〜は初めてですか？"],
    ["I've had", "（症状が）続いています"],
    ["Do I need to", "〜する必要がありますか？"],
    ["Not that I know of", "知る限りではありません"],
    ["make you drowsy", "眠くなる"],
    ["allergies", "アレルギー"],
    ["I hope you feel better", "早く良くなりますように"]
  ],
  dialogs: [
    { id: "clinic-1", title: "受付", A: "受付係", B: "あなた（患者）", def: "B", lines: [
      ["B", "Hi, I'd like to see a doctor. I don't have an appointment, though.", "こんにちは、診察を受けたいのですが。予約はしていないんですけど。"],
      ["A", "That's okay. Is this your first time here?", "大丈夫ですよ。こちらは初めてですか？"],
      ["B", "Yes, it is.", "はい、そうです。"],
      ["A", "Then I'll need you to fill out this form. Do you have health insurance?", "では、この用紙に記入してください。健康保険はお持ちですか？"],
      ["B", "Yes, here's my insurance card.", "はい、これが保険証です。"],
      ["A", "Thank you. What seems to be the problem today?", "ありがとうございます。今日はどうされましたか？"],
      ["B", "I've had a bad cough and a fever for three days.", "3日間ひどい咳と熱が続いています。"],
      ["A", "I see. Please take a seat. The wait is about thirty minutes.", "わかりました。おかけください。待ち時間は30分ほどです。"],
      ["B", "Is it okay if I wait outside? I don't want to give it to anyone.", "外で待っていてもいいですか？誰かにうつしたくないので。"],
      ["A", "That's very considerate. We'll call your cell phone when it's your turn.", "お気遣いありがとうございます。順番が来たら携帯にお電話します。"]
    ]},
    { id: "clinic-2", title: "診察", A: "医師（リー先生）", B: "あなた（患者）", def: "B", lines: [
      ["A", "Hi, I'm Dr. Lee. So, what brings you in today?", "こんにちは、医師のリーです。今日はどうされましたか？"],
      ["B", "I've had a bad cough and a fever for three days.", "3日間ひどい咳と熱が続いています。"],
      ["A", "How high is your fever?", "熱はどれくらいありますか？"],
      ["B", "It was 38.5 last night.", "昨夜は38度5分でした。"],
      ["A", "Any other symptoms? Sore throat, headache?", "他に症状はありますか？喉の痛みや頭痛は？"],
      ["B", "My throat hurts, and I feel tired all the time.", "喉が痛くて、ずっとだるいです。"],
      ["A", "Let me listen to your chest. Take a deep breath... Your lungs sound clear.", "胸の音を聴きますね。深呼吸して…肺はきれいな音ですね。"],
      ["B", "That's a relief. Could it be the flu?", "安心しました。インフルエンザの可能性はありますか？"],
      ["A", "We'll do a quick flu test to be sure, but it's probably just a bad cold.", "念のためインフルエンザの簡易検査をしますが、たぶんひどい風邪でしょう。"],
      ["B", "Do I need to take time off work?", "仕事を休む必要がありますか？"],
      ["A", "I'd recommend resting at home until the fever goes down. I'll give you a prescription.", "熱が下がるまで家で休むことをおすすめします。処方箋を出しますね。"],
      ["B", "Thank you, doctor.", "ありがとうございます、先生。"]
    ]},
    { id: "clinic-3", title: "薬局", A: "薬剤師", B: "あなた（患者）", def: "B", lines: [
      ["B", "Hi, I'd like to fill this prescription.", "こんにちは、この処方箋の薬をお願いしたいです。"],
      ["A", "Sure. It'll take about fifteen minutes. Is this your first time here?", "はい。15分ほどかかります。こちらは初めてですか？"],
      ["B", "Yes, it is.", "はい。"],
      ["A", "Do you have any allergies to medication?", "薬のアレルギーはありますか？"],
      ["B", "Not that I know of.", "知る限りではありません。"],
      ["A", "Here you go. This one is for your cough. Take it three times a day after meals.", "どうぞ。こちらは咳止めです。1日3回、食後に飲んでください。"],
      ["B", "And what's this one for?", "こっちは何の薬ですか？"],
      ["A", "That's for your fever. Only take it when your temperature is over 38.", "熱の薬です。38度を超えたときだけ飲んでください。"],
      ["B", "Do they make you drowsy?", "眠くなりますか？"],
      ["A", "The cough medicine might, so don't drive after taking it.", "咳止めは眠くなるかもしれないので、飲んだ後は運転しないでください。"],
      ["B", "Got it. Thank you.", "わかりました。ありがとう。"],
      ["A", "Take care, and I hope you feel better soon.", "お大事に、早く良くなりますように。"]
    ]}
  ]
});

EK_DATA.push({
  cat: "生活", series: "手続",
  keys: [
    ["I'd like to", "〜したいのですが"],
    ["What do I need to bring", "何を持ってくればいいですか？"],
    ["Is there a monthly fee", "月額料金はかかりますか？"],
    ["What's the difference", "違いは何ですか？"],
    ["How long", "どれくらい（期間・時間）？"],
    ["get back to you", "（後で）お返事する"]
  ],
  dialogs: [
    { id: "proc-1", title: "銀行で口座開設", A: "銀行員", B: "あなた（客）", def: "B", lines: [
      ["A", "Good morning. How can I help you today?", "おはようございます。本日はどのようなご用件でしょうか？"],
      ["B", "Hi, I'd like to open a bank account.", "こんにちは、口座を開設したいのですが。"],
      ["A", "Sure. Are you looking for a checking or a savings account?", "かしこまりました。決済用の口座と貯蓄用の口座、どちらをお考えですか？"],
      ["B", "A checking account, please. What do I need to bring?", "決済用でお願いします。何を持ってくればいいですか？"],
      ["A", "We'll need a photo ID and proof of address, like a utility bill.", "写真付きの身分証明書と、公共料金の請求書などの住所証明が必要です。"],
      ["B", "Here's my passport and my lease. Is that okay?", "パスポートと賃貸契約書です。これで大丈夫ですか？"],
      ["A", "That's perfect.", "完璧です。"],
      ["B", "Is there a monthly fee?", "月額手数料はかかりますか？"],
      ["A", "There's a ten-dollar fee, but it's waived if you keep at least 1,500 dollars in the account.", "10ドルかかりますが、口座に1,500ドル以上あれば無料になります。"],
      ["B", "I see. How long does it take to get a debit card?", "なるほど。デビットカードはどれくらいで届きますか？"],
      ["A", "It'll arrive by mail in about a week.", "1週間ほどで郵送で届きます。"],
      ["B", "Great. Let's go ahead with it.", "よかった。それでお願いします。"]
    ]},
    { id: "proc-2", title: "携帯電話の契約", A: "店員", B: "あなた（客）", def: "B", lines: [
      ["A", "Hi! What can I help you with today?", "こんにちは！今日はどうされましたか？"],
      ["B", "I just moved here, and I need a phone plan.", "引っ越してきたばかりで、携帯のプランが必要なんです。"],
      ["A", "Sure. Do you want a contract, or a prepaid plan?", "かしこまりました。契約プランとプリペイド、どちらがいいですか？"],
      ["B", "What's the difference?", "違いは何ですか？"],
      ["A", "A contract is cheaper per month, but you're locked in for two years.", "契約の方が月額は安いですが、2年間縛りがあります。"],
      ["B", "I'm only here for a year, so prepaid sounds better.", "ここには1年しかいないので、プリペイドの方が良さそうです。"],
      ["A", "Got it. This plan gives you unlimited data for 40 dollars a month.", "わかりました。このプランは月40ドルでデータ無制限です。"],
      ["B", "Are there any hidden fees?", "他に隠れた料金はありますか？"],
      ["A", "No, but there's a one-time activation fee of 15 dollars.", "いいえ、ただ初回の開通手数料が15ドルかかります。"],
      ["B", "Okay. Can I keep using my current phone?", "わかりました。今の携帯をそのまま使えますか？"],
      ["A", "Yes, as long as it's unlocked. We'll just give you a new SIM card.", "はい、SIMロックが解除されていれば。新しいSIMカードをお渡しするだけです。"],
      ["B", "Great. How long does it take to set up?", "よかった。設定にどれくらいかかりますか？"],
      ["A", "About ten minutes. I'll just need to see your ID.", "10分ほどです。身分証を拝見するだけです。"]
    ]},
    { id: "proc-3", title: "不動産の内見", A: "不動産業者", B: "あなた（客）", def: "B", lines: [
      ["A", "So, this is the living room. It gets a lot of sunlight in the afternoon.", "こちらがリビングです。午後はよく日が入りますよ。"],
      ["B", "It's nice and bright. How much is the rent?", "明るくていいですね。家賃はいくらですか？"],
      ["A", "It's 1,800 a month, and that includes water.", "月1,800ドルで、水道代込みです。"],
      ["B", "What about electricity and internet?", "電気とインターネットは？"],
      ["A", "Those are separate. You'd set them up yourself.", "それらは別です。ご自身で手続きしていただきます。"],
      ["B", "I see. How long is the lease?", "なるほど。契約期間はどれくらいですか？"],
      ["A", "It's a one-year lease. We'd need the first month's rent and a security deposit.", "1年契約です。初月の家賃と敷金が必要です。"],
      ["B", "Are pets allowed? I have a small cat.", "ペットは大丈夫ですか？小さい猫がいるんです。"],
      ["A", "Cats are okay, but there's an extra pet deposit of 300 dollars.", "猫は大丈夫ですが、追加でペット敷金が300ドルかかります。"],
      ["B", "Is there laundry in the building?", "建物にランドリーはありますか？"],
      ["A", "Yes, there are washers and dryers in the basement.", "はい、地下に洗濯機と乾燥機があります。"],
      ["B", "I really like it. Could I think it over and get back to you tomorrow?", "とても気に入りました。考えて明日お返事してもいいですか？"],
      ["A", "Of course. Just so you know, a few other people are interested.", "もちろんです。念のためお伝えすると、他にも何人か興味を持っている方がいます。"]
    ]}
  ]
});
