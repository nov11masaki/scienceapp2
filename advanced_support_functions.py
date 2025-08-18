def get_learning_support_system():
    """学習段階別支援システムの内容を取得"""
    support_path = "guidelines/learning_support_system.md"
    if os.path.exists(support_path):
        return load_markdown_content(support_path)
    return None

def analyze_unit_characteristics(unit):
    """単元の特性を分析して見方・考え方を抽出"""
    unit_characteristics = {
        "水のあたたまり方": {
            "見方・考え方": "温度と物質の状態・性質の関係性に注目する",
            "重点活動": ["温度変化の比較", "対流現象の言語化", "日常経験との関連"],
            "生活経験": ["お風呂の循環", "やかんのお湯", "暖房の仕組み"],
            "キーワード": ["対流", "循環", "あたたまり方", "温度差"]
        },
        "空気のあたたまり方": {
            "見方・考え方": "目に見えない物質の性質を構造や状態変化と関係づけて考える",
            "重点活動": ["見えない現象の言語化", "空気の動きの表現", "比喩的表現"],
            "生活経験": ["ドライヤー", "エアコン", "風船の変化"],
            "キーワード": ["対流", "空気の流れ", "軽い・重い", "上昇・下降"]
        },
        "金属のあたたまり方": {
            "見方・考え方": "温度と物質の状態・性質の関係性に注目する",
            "重点活動": ["伝導現象の観察", "順序立てた説明", "物質比較"],
            "生活経験": ["フライパンで料理", "金属スプーン", "アイロン"],
            "キーワード": ["伝導", "順番に", "伝わる", "熱くなる"]
        }
    }
    return unit_characteristics.get(unit, {})

def determine_learning_stage(conversation_count, conversation_content):
    """対話内容から学習段階を判定"""
    if conversation_count <= 2:
        return "自己思考段階"
    elif conversation_count <= 4:
        return "伝え合い段階"
    else:
        return "思考まとめ段階"

def generate_stage_appropriate_questions(stage, unit, conversation_history):
    """学習段階に応じた適切な質問を生成"""
    unit_info = analyze_unit_characteristics(unit)
    
    question_templates = {
        "自己思考段階": [
            f"普段の生活で{unit_info.get('生活経験', [''])[0]}のようなことを見たことはありますか？",
            "どうしてそうなると思いますか？",
            "前に勉強したことで関係ありそうなことはありますか？"
        ],
        "伝え合い段階": [
            "友達の考えと比べてどうですか？",
            "なぜ違う結果になったと思いますか？",
            "どちらの考えが正しいか調べる方法はありますか？"
        ],
        "思考まとめ段階": [
            "今日分かったことをまとめてみましょう",
            "他の場面でも同じことが起こりそうですか？",
            "新しく疑問に思ったことはありますか？"
        ]
    }
    
    return question_templates.get(stage, ["どう思いますか？"])

def build_enhanced_prompt_with_guidelines(base_prompt, unit=None, stage=None, conversation_history=None):
    """ガイドラインを最大限活用した強化プロンプトを構築"""
    enhanced_prompt = base_prompt
    
    # 学習指導要領の活用
    guidelines = get_learning_guidelines()
    if guidelines:
        enhanced_prompt += f"\n\n【学習指導要領参考（言語活動重視）】:\n{guidelines[:1500]}..."
    
    # 指導支援方針の活用
    teaching_support = get_teaching_support()
    if teaching_support:
        enhanced_prompt += f"\n\n【産婆法指導方針】:\n{teaching_support[:1000]}..."
    
    # 学習支援システムの活用
    support_system = get_learning_support_system()
    if support_system:
        enhanced_prompt += f"\n\n【段階別支援システム】:\n{support_system[:1200]}..."
    
    # 単元特性の活用
    if unit:
        unit_info = analyze_unit_characteristics(unit)
        if unit_info:
            enhanced_prompt += f"\n\n【{unit}の特性】:\n"
            enhanced_prompt += f"見方・考え方: {unit_info.get('見方・考え方', '')}\n"
            enhanced_prompt += f"重点活動: {', '.join(unit_info.get('重点活動', []))}\n"
            enhanced_prompt += f"生活経験例: {', '.join(unit_info.get('生活経験', []))}\n"
    
    # 学習段階の判定と対応
    if conversation_history:
        conversation_count = len(conversation_history) // 2 + 1
        learning_stage = determine_learning_stage(conversation_count, conversation_history)
        appropriate_questions = generate_stage_appropriate_questions(learning_stage, unit, conversation_history)
        
        enhanced_prompt += f"\n\n【現在の学習段階】: {learning_stage}\n"
        enhanced_prompt += f"【推奨質問例】: {', '.join(appropriate_questions)}\n"
    
    return enhanced_prompt

def extract_learning_insights(student_response, unit):
    """児童の発言から学習状況を分析"""
    insights = {
        "理解度": "不明",
        "言語化レベル": "不明", 
        "日常関連": False,
        "概念理解": False,
        "次の支援": "継続観察"
    }
    
    # 理解度の判定
    if any(word in student_response for word in ["分かった", "なるほど", "そういうこと"]):
        insights["理解度"] = "良好"
    elif any(word in student_response for word in ["分からない", "よく分からない", "難しい"]):
        insights["理解度"] = "要支援"
    
    # 言語化レベルの判定
    if len(student_response) > 20 and ("なぜなら" in student_response or "だから" in student_response):
        insights["言語化レベル"] = "高い"
    elif any(word in student_response for word in ["あたたかい", "つめたい", "動いた"]):
        insights["言語化レベル"] = "基礎的"
    
    # 日常関連の確認
    daily_words = ["家で", "普段", "お風呂", "料理", "お母さん", "見たことある"]
    if any(word in student_response for word in daily_words):
        insights["日常関連"] = True
    
    # 概念理解の確認
    unit_info = analyze_unit_characteristics(unit)
    keywords = unit_info.get("キーワード", [])
    if any(keyword in student_response for keyword in keywords):
        insights["概念理解"] = True
    
    return insights
