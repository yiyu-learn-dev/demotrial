window.TAORAN_MEMO = {
  tags: [
    { id: 'all', label: '全部', icon: 'fa-layer-group' },
    { id: 'grammar', label: '语法', icon: 'fa-spell-check' },
    { id: 'cloze', label: '完形', icon: 'fa-align-left' },
    { id: 'reading', label: '阅读', icon: 'fa-book-open' }
  ],
  curated: [
    {
      id: 'grammar-overview',
      tag: 'grammar',
      title: '语法填空解题总览',
      summary: '有提示词先分流；无提示词看后面是短语还是句子。',
      sections: [
        {
          heading: '有提示词时',
          bullets: [
            '空后是短语 → 优先想冠词、介词',
            '动词作谓语 → 时态、语态、主谓一致',
            '动词作非谓语 → 主动 doing / to do，被动 done',
            '词性变换 → 动名形副互转；名词注意单复数',
            '形容词 / 副词比较级 → 简单词 +er/+est，复杂词 more/most；绝无 more+er',
            '提示词是动词：主要考谓语、非谓语、词性变换',
            '提示词是名词：主要考复数变化、词性转换'
          ]
        },
        {
          heading: '无提示词时',
          bullets: [
            '空后是名词短语 → 冠词 / 介词',
            '空后是句子 → 从句关系词或连词',
            '主句不完整、从句完整 → how / why / whether 等',
            '主句完整、从句不完整 → 缺人 that/who，缺物 that/which',
            '空前出现 some of / many of 等 “…of” → 可先删掉再判断',
            '极少考代词；若考，多是形式主语/宾语 it，或比较代词 that/those'
          ]
        }
      ]
    },
    {
      id: 'grammar-article',
      tag: 'grammar',
      title: '冠词 · 介词 · 硬规则',
      summary: '独一无二用 the；a/an 看音素；一套题里同细节不重复。',
      sections: [
        {
          heading: '冠词',
          bullets: [
            '后面名词独一无二 → the',
            '不是独一无二 → a / an（看元音音素，不是看字母）',
            'hour 的 h 不发音 → an hour',
            'university / universe / uniform（ju:）→ a',
            '介词重点靠常见搭配积累，不是临场硬猜'
          ]
        },
        {
          heading: '考场硬规则',
          bullets: [
            '语法填空禁止照抄提示词原词',
            '若填一般现在却等于照抄原词，一般现在通常不成立',
            '“情态动词 + 动词原形”在句中一定充当谓语',
            '尽量杜绝由繁入简、两步变形、跨两个考点',
            '一套题里相同考点细节通常不重复出现',
            '空格在句首注意首字母大写',
            '两个逗号之间是插入语，不纳入主句正式结构',
            '破折号内容也不纳入句子主体结构'
          ]
        }
      ]
    },
    {
      id: 'grammar-tense',
      tag: 'grammar',
      title: '谓语：时态 · 语态 · 主谓一致',
      summary: '先定时间轴，再定主动被动，最后核对单复数。',
      sections: [
        {
          heading: '时态信号',
          bullets: [
            '现在完成：句中常有“过去到现在”的时间标志；already 也可作完成时标志',
            '“for + 时间段”不是现在完成专属标志，可用于多种时态',
            '过去完成：同一句话里两个过去，并强调先后；by + 过去时间是典型标志',
            '若出现过去完成，句中通常还有一般过去或过去进行',
            '突发动作：一般过去（突发）+ when + 过去进行（过程）',
            '提到谓语动作次数时，常用现在完成 / 过去完成',
            '主将从现：条件满足后将来发生；主现从现：普遍现象与条件',
            '较少考：过去将来 would do；现在完成进行 have/has been doing'
          ]
        },
        {
          heading: '语态与一致',
          bullets: [
            '动词后该有宾语却没有 → 常看被动',
            '双宾语动词后只有一个名词 → 常需被动（tell / call）',
            '若动词后不需要名词，该动作多为主动',
            '动名词或从句作主语 → 视作单数',
            '被动语态句子本身可以是完整句',
            '情态动词后若填被动，只考虑 be done',
            '助动词 do/does/did + 动词原形 → 强调',
            '谓语在句首，通常只有祈使句：Do sth. / Don’t do sth.'
          ]
        }
      ]
    },
    {
      id: 'grammar-nonfinite-note',
      tag: 'grammar',
      title: '非谓语动词要点',
      summary: '先判主动被动，再判同时发生还是目的结果。',
      sections: [
        {
          heading: '形态选择',
          bullets: [
            '主动：doing（同时发生）、to do（目的 / 预期 / 结果）；偶尔 having done',
            '被动：done；必要时 to be done',
            '作主语或宾语：主动 doing，被动 being done（to do 作主语偏哲理句，少考）',
            '独立介词后：主动 doing，被动 being done，不用 to do',
            '逗号后的非谓语主动形式一般不用 to do（插入语除外）',
            'to 本身是介词时，to do 是整体，与“介词后非谓语”规则无关'
          ]
        },
        {
          heading: '常见固定与陷阱',
          bullets: [
            'when / while / before / after / though / if 后无主语直接接动词 → 用非谓语',
            'first / last / only 修饰名词后的非谓语补充常用 to do',
            'Based on / located in / compared with / Judging from / dating back 等结构要熟',
            '非谓语作形容词：doing 表主动或进行，done 表被动或完成',
            '动作先后：一个结束另一个开始 → 不是同时发生，慎用 doing'
          ]
        }
      ]
    },
    {
      id: 'grammar-clause',
      tag: 'grammar',
      title: '从句与关系词',
      summary: '先切开主从句，再看两边完不完整，最后选关系词。',
      sections: [
        {
          heading: '切分与完整',
          bullets: [
            '从句在句首：找到第二个谓语断开，前从后主',
            '从句插在主句中间：主句一定完整',
            '主句完整、从句不完整：介词后用人 whom、用物 which',
            '主句不完整、从句完整且确定 → that；不确定 → how / why / whether / where / when 等',
            '主句不完整、从句倒装强调状态（形/副）→ how；强调事物（名词）→ what',
            '主句完整且从句主语突兀直接出现名词 → 考虑 whose',
            'I have no idea / am not sure：两边都完整时，关系词都不成立才考虑逻辑连词',
            '两句都完整且四个关系词不成立 → 再看 and / or / but 等连词'
          ]
        },
        {
          heading: '高频提醒',
          bullets: [
            '是否只用 whether；if 只表示“如果”；unless 表“除非”',
            'whether…or… 是固定组合',
            'whose 强调归属；where 强调位置或状况',
            'however / therefore / thus 是副词，不能直接连两个句子',
            'that is why + 结果；that is because + 原因',
            '不定代词、最高级、极端词后关系词优先 that',
            '介词前置时：主句完整、从句不完整',
            'time 后面的从句常省略关系词；say/think/believe/prove + that 可省略',
            'those who/which… 建议直接记熟'
          ]
        }
      ]
    },
    {
      id: 'grammar-word-form',
      tag: 'grammar',
      title: '词性变换 · 比较级 · 并列',
      summary: '词性看态度与单复数；比较级看形态；and/or 看并列对象。',
      sections: [
        {
          heading: '词性与比较',
          bullets: [
            '词性转换时，形容词要注意正负态度',
            '动词或形容词变名词时，要考虑名词单复数',
            '比较级：可 +er/+est，也可 more/most + 原形；绝无 more+er',
            'much + 比较级 → “…得多”',
            'even 表递进，后面常用比较级',
            '形容词变副词特殊变化要单独记：full/whole/true/considerable/responsible/gentle/possible/probable/simple/incredible/horrible/terrible/remarkable 等'
          ]
        },
        {
          heading: '并列与结构小点',
          bullets: [
            'and / or / but 既可连句子，也可连词或短语',
            'and 并列：A and B；列举：A, B, and C',
            '判断并列时重点看 and/or 后面的内容',
            'A of B = B 的 A，语义重心在 A',
            '比较用代词：单数 that，复数 those',
            '形式主语 / 形式宾语 it 可先“视作不存在”再看结构',
            '介词短语不能作主语',
            'It is proved / believed that… 一类结构要熟'
          ]
        }
      ]
    },
    {
      id: 'cloze-overview',
      tag: 'cloze',
      title: '完形填空总览',
      summary: '抓中心、看人物关系，记叙文按起承转合推进。',
      sections: [
        {
          heading: '全局意识',
          bullets: [
            '开头结尾出现概括句，往往就是文章中心',
            '时刻注意人物身份与人物关系',
            '结尾抽象名词题，该名词常是核心概念',
            '重复出现原词的多数是名词题',
            '动词短语不必死记，靠语境积累'
          ]
        },
        {
          heading: '记叙文套路',
          bullets: [
            '常见“起承转合”：负→正，或正→负→正',
            '开头若是负面问题，结尾多会转向正面',
            '选项里直接的“好 / 坏”要特别警惕是否在考态度翻转'
          ]
        }
      ]
    },
    {
      id: 'cloze-parts',
      tag: 'cloze',
      title: '完形五类词性题',
      summary: '名词复现、动词顺序、形容词态度、副词逻辑、连词关系。',
      sections: [
        {
          heading: '名词题',
          bullets: [
            '名词要有具体对应内容',
            '抽象名词 / 概念 → 常起概括作用',
            '具体名词 / 人物事物 → 常靠复现呼应'
          ]
        },
        {
          heading: '动词题',
          bullets: [
            '动词和名词关系密切：分清发出者与对象',
            '已知动词与未知动词要形成连续、合理的动作链',
            '别只看单句词义，要看整段动作是否接得上'
          ]
        },
        {
          heading: '形容词题',
          bullets: [
            '可描述人物 / 事物性质，也可描述情感心理',
            '正态度、负态度、中性态度要与已知信息统一',
            '遇到极端褒贬词，先核对全文基调'
          ]
        },
        {
          heading: '副词与连词',
          bullets: [
            '副词可表动作状态、主观态度、句间逻辑或程度',
            '副词有时就是上下文逻辑标志',
            '连词题盯两句关系：转折、因果、条件、并列、时间先后'
          ]
        }
      ]
    },
    {
      id: 'reading-timing',
      tag: 'reading',
      title: '阅读解题顺序与限时',
      summary: '先题后文或先文后题都可以，关键是限时与结构意识。',
      sections: [
        {
          heading: '顺序与节奏',
          bullets: [
            '两种顺序：先看题目速战速决；先看文章稳扎稳打',
            '开头结尾直接体现主旨，必须重点读',
            '除记叙文外，整段翻译说明思路出了问题',
            'A/B 应用文 3–5 分钟、记叙文 6–8 分钟；C/D 说明/议论 8–10 分钟',
            '四篇目标总时长 25–30 分钟',
            '方法技巧必须配合大量演练；没练过的技巧别硬搬进考场'
          ]
        },
        {
          heading: '结构提醒',
          bullets: [
            '总分结构是英文最重要逻辑，可在段间或段内出现',
            '明显较短的段落可能是总括、总结或过渡',
            '对事物下定义的内容通常在开头',
            '正确选项一定与文章主题关系密切',
            '题目对应文章不同位置，极少同一处反复考',
            '阅读一般不涉及 research report，但可以涉及 news report'
          ]
        }
      ]
    },
    {
      id: 'reading-practical',
      tag: 'reading',
      title: '应用文阅读要点',
      summary: '广告吸引购买，指南传递方法；要符合生活实际。',
      sections: [
        {
          heading: '两类应用文',
          bullets: [
            '广告：吸引顾客，鼓励购买行为',
            '指南：服务用户，教导方法、传递信息',
            '祈使句常用于建议、要求、请求、命令',
            '做题时要符合生活实际情况',
            '限时建议：应用文约 3–5 分钟'
          ]
        }
      ]
    },
    {
      id: 'reading-narrative',
      tag: 'reading',
      title: '记叙文阅读要点',
      summary: '叙事看情节完整，写人看品质；结果通常正面积极。',
      sections: [
        {
          heading: '两类记叙文',
          bullets: [
            '叙事：单一事件，时间地点人物起因经过结果，落点在道理启示',
            '写人：人物生平与关键事件，落点在品质精神',
            '叙事可用第一或第三人称；写人多用第三人称',
            '记叙文要完整理解情节，结果通常正面积极',
            '标题常落在重要人物、事件、线索或品质特点上',
            '限时建议：记叙文约 6–8 分钟'
          ]
        }
      ]
    },
    {
      id: 'reading-detail',
      tag: 'reading',
      title: '细节题：定位与关键词',
      summary: '去哪找 + 找什么；文题顺序一致，盯同义改写。',
      sections: [
        {
          heading: '步骤',
          bullets: [
            '细节题需要定位，主旨题需要理解',
            '解题核心：去哪找（定位）+ 找什么（关键词）→ 对应正确选项',
            '定位路径：文章局部 → 具体段落 → 具体语句；文题顺序通常一致',
            '关键词来自题干和选项',
            '注意原词复现与同义近义改写',
            '提问点往往是重要位置、重要标志或重复信息',
            '选项正负态度差异要特别关注',
            '笼统式提问要先认真读选项，明确阅读目的再回文'
          ]
        }
      ]
    },
    {
      id: 'reading-main',
      tag: 'reading',
      title: '主旨题类型与思路',
      summary: '盯开头结尾与主题，分清目的、内容、态度、标题等问法。',
      sections: [
        {
          heading: '怎么想',
          bullets: [
            '主旨题优先看标题、首段、末段与全文主题',
            '常见问法：写作目的、主要内容、作者态度',
            '也可能问身份、出处类型、标题，或某细节的作用目的',
            '记叙文标题常见落点：重要人物 / 事件 / 线索 / 品质精神',
            '正确选项必须紧扣主题，别被局部细节带跑'
          ]
        }
      ]
    }
  ],
  wrongQuestionTags: {
    'reading-detail': 'reading',
    'cloze-logic': 'cloze',
    'grammar-nonfinite': 'grammar',
    'seven-cloze-structure': 'reading'
  }
};
