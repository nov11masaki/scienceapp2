"""
会話ログからの詳細分析モジュール

以下の観点から学習効果を多角的に評価する（会話ベースのみ）:
1. 思考の深化プロセス（自己修正、迷い、他視点の獲得）
2. 科学的語彙の獲得（前半後半比較、感染率）
3. AIとの対話エンゲージメント（ターン数、発話量）
4. 論理構造の定着（対話の問答構造）
5. 根拠の統合と引き出し
6. メタ認知の有無
7. 思考の明確性と表現
"""

import re
from collections import Counter
from typing import List, Dict, Any
import json


# ===== 語彙・表現パターン定義 =====

# 科学語彙（単元に応じて拡張可能）
SCIENCE_VOCAB = {
    '温度と体積': ['温度', '体積', '膨張', '収縮', '圧力', '変化', '加熱', '冷却', '拡大', '縮小', '熱膨張'],
    '金属のあたたまり方': ['温度', '熱', '金属', '膨張', '導熱', '広がる', '伝わる'],
    '水のあたたまり方': ['温度', '熱', '水', '上昇', '対流', '伝わる'],
    '空気の温度と体積': ['温度', '体積', '空気', '膨張', '気球', '風船'],
    'default': ['温度', '体積', '膨張', '収縮', 'エネルギー', '変化', '理由', '実験', '予想', '結果']
}

# 自己修正の語
SELF_CORRECTION_PATTERNS = ['違う', 'ちがう', 'あ、違った', 'あ、そっか', 'やっぱり', '訂正', '直す', 'いや、']

# ためらい・不確実表現
HESITATION_PATTERNS = ['わからない', 'わかんない', 'うーん', 'えー', 'たぶん', 'かもしれない', '迷う']

# 他視点を促す表現
ALTERNATIVE_PATTERNS = ['もし', 'たとえば', '別の', 'ほか', '～だったら', 'ならば', '反対に', '逆に']

# 経験参照
EXPERIENCE_PATTERNS = ['前に', 'この前', '経験', 'やったことある', 'やってみた', '見たことある']


# ===== 観点1: 思考の深化プロセス =====

def analyze_depth_of_thinking(user_messages: List[str], ai_messages: List[str]) -> Dict[str, Any]:
    """①自己修正の有無、②迷いの可視化、③他視点の獲得"""
    
    # 自己修正インスタンスを特定
    self_corrections = []
    for i, msg in enumerate(user_messages):
        if any(pat in msg for pat in SELF_CORRECTION_PATTERNS):
            context = {
                'turn': i,
                'message': msg,
                'pattern': [p for p in SELF_CORRECTION_PATTERNS if p in msg][0]
            }
            self_corrections.append(context)
    
    # ためらい表現を特定
    hesitations = []
    for i, msg in enumerate(user_messages):
        if any(pat in msg for pat in HESITATION_PATTERNS):
            # そこに対する AI の対応を確認
            ai_followup = ai_messages[i] if i < len(ai_messages) else None
            hesitations.append({
                'turn': i,
                'message': msg,
                'ai_followup': ai_followup,
                'is_guided': bool(ai_followup and any(c in ai_followup for c in 'どうして？ところで何か？'))
            })
    
    # 他視点の獲得
    alternative_mentions = []
    for i, msg in enumerate(user_messages):
        if any(pat in msg for pat in ALTERNATIVE_PATTERNS):
            alternative_mentions.append({
                'turn': i,
                'message': msg,
                'pattern': [p for p in ALTERNATIVE_PATTERNS if p in msg][0]
            })
    
    # スコア化
    depth_score = (
        len(self_corrections) * 2 +
        len(alternative_mentions) * 2 +
        len(hesitations) * 0.5
    )
    
    return {
        'self_corrections': {
            'count': len(self_corrections),
            'instances': self_corrections[:5]
        },
        'hesitations': {
            'count': len(hesitations),
            'guided_count': sum(1 for h in hesitations if h['is_guided']),
            'instances': hesitations[:5]
        },
        'alternative_perspectives': {
            'count': len(alternative_mentions),
            'instances': alternative_mentions[:5]
        },
        'depth_score': round(depth_score, 2),
        'interpretation': interpret_depth_score(depth_score),
        'important_conversation_features': (
            f"自己修正{len(self_corrections)}回、"
            f"他視点{len(alternative_mentions)}回、"
            f"ためらい{len(hesitations)}回。"
        )
    }


def interpret_depth_score(score: float) -> str:
    """深化スコアを教員向けに解釈"""
    if score >= 10:
        return "非常に深い思考過程。自己修正や他視点の検討が積極的。"
    elif score >= 5:
        return "良好な深化。適度な迷いと修正から段階的に理解を深めている。"
    elif score >= 2:
        return "基本的な思考過程。簡潔だが直線的。"
    else:
        return "浅い思考過程。迷いや修正がほぼない。既知か、または不確実性を認識していない可能性。"


# ===== 観点2: 科学的語彙の獲得 =====

def analyze_scientific_vocabulary(
    user_messages: List[str], 
    ai_messages: List[str], 
    unit: str
) -> Dict[str, Any]:
    """①語彙の出現頻度の変化、②AI模倣（感染率）"""
    
    vocab_list = SCIENCE_VOCAB.get(unit, SCIENCE_VOCAB['default'])
    
    # 対話前半・後半で分割
    mid = max(1, len(user_messages) // 2)
    first_half = user_messages[:mid]
    second_half = user_messages[mid:]
    
    # 科学語彙の出現を前半・後半で集計
    first_half_vocab = Counter()
    second_half_vocab = Counter()
    
    for msg in first_half:
        for term in vocab_list:
            if term in msg:
                first_half_vocab[term] += 1
    
    for msg in second_half:
        for term in vocab_list:
            if term in msg:
                second_half_vocab[term] += 1
    
    # AI が使った語を記録
    ai_vocab = Counter()
    for msg in ai_messages:
        for term in vocab_list:
            if term in msg:
                ai_vocab[term] += 1
    
    # 感染率: AI が言った語を児童がその後使ったか
    infection = {}
    for term in ai_vocab:
        if term in second_half_vocab:
            infection[term] = {
                'ai_usage': ai_vocab[term],
                'student_after': second_half_vocab[term],
                'infected': True
            }
    
    infection_rate = len(infection) / len(ai_vocab) if ai_vocab else 0.0
    
    vocab_transition = {
        'scientific_vocab_before': sum(first_half_vocab.values()),
        'scientific_vocab_after': sum(second_half_vocab.values()),
        'transition_direction': 'scientific ↑' if sum(second_half_vocab.values()) > sum(first_half_vocab.values()) else 'stable/down'
    }
    
    return {
        'scientific_terms_before': dict(first_half_vocab),
        'scientific_terms_after': dict(second_half_vocab),
        'ai_used_terms': dict(ai_vocab),
        'infection_rate': round(infection_rate, 3),
        'infected_terms': infection,
        'vocabulary_transition': vocab_transition,
        'interpretation': interpret_vocab_growth(infection_rate, vocab_transition),
        'important_conversation_features': (
            f"前半に科学語彙{sum(first_half_vocab.values())}回、"
            f"後半{sum(second_half_vocab.values())}回使用。"
            f"AI感染率{infection_rate*100:.0f}%。"
        )
    }


def interpret_vocab_growth(infection_rate: float, transition: Dict) -> str:
    """語彙成長を解釈"""
    sci_before = transition['scientific_vocab_before']
    sci_after = transition['scientific_vocab_after']
    
    if infection_rate > 0.5 and sci_after > sci_before:
        return f"優秀。AIの語彙を吸収し、科学語彙が増加。"
    elif infection_rate > 0.3:
        return f"良好。AIの語彙を部分的に採用。"
    elif sci_after > sci_before:
        return f"向上中。科学語彙の使用が増えている。"
    else:
        return f"停滞。科学語彙の採用が進んでいない。"


# ===== 観点3: AIとの対話エンゲージメント =====

def analyze_engagement(user_messages: List[str], ai_messages: List[str]) -> Dict[str, Any]:
    """①ターン数と持続性、②発話量"""
    
    turns = len(user_messages)
    
    # 発話量（文字数）
    lengths = [len(msg) for msg in user_messages if msg]
    avg_length = sum(lengths) / len(lengths) if lengths else 0.0
    max_length = max(lengths) if lengths else 0
    min_length = min(lengths) if lengths else 0
    
    # 持続性の判定
    sustained = 'deep' if turns >= 5 else 'moderate' if turns >= 3 else 'brief'
    
    # 文で答えているか
    sentence_count = sum(1 for msg in user_messages if len(msg.split()) > 3)
    sentence_ratio = sentence_count / len(user_messages) if user_messages else 0.0
    
    # AI の質問への反応
    ai_questions = sum(1 for msg in ai_messages if '？' in msg)
    
    engagement_score = (
        min(turns, 10) +
        min(avg_length / 10, 5) +
        sentence_ratio * 5
    )
    
    return {
        'turn_count': turns,
        'sustainability': sustained,
        'average_response_length': round(avg_length, 1),
        'max_response_length': max_length,
        'min_response_length': min_length,
        'sentence_ratio': round(sentence_ratio, 3),
        'ai_questions_asked': ai_questions,
        'engagement_score': round(engagement_score, 2),
        'interpretation': interpret_engagement(turns, avg_length, sentence_ratio),
        'important_conversation_features': (
            f"{turns}往復の対話。平均{round(avg_length, 0):.0f}文字の応答。"
            f"{round(sentence_ratio*100, 0):.0f}%が複数語以上。"
        )
    }


def interpret_engagement(turns: int, avg_len: float, sentence_ratio: float) -> str:
    """エンゲージメントを解釈"""
    if turns >= 5 and avg_len > 20 and sentence_ratio > 0.5:
        return "高いエンゲージメント。多ターンで、文で答え、深い対話。"
    elif turns >= 3:
        return "中程度のエンゲージメント。適度な対話が展開。"
    else:
        return "低いエンゲージメント。短い対話。より開かれた問いかけが効果的。"


# ===== 観点5: 論理構造の定着 =====

def analyze_structure_crystallization(conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
    """対話での問答構造の質"""
    
    qa_exchanges = 0
    question_types = {'why': 0, 'what': 0, 'how': 0, 'when': 0, 'other': 0}
    
    for i in range(len(conversation)):
        if conversation[i].get('role') == 'assistant' and i + 1 < len(conversation):
            if conversation[i+1].get('role') == 'user':
                ai_msg = conversation[i].get('content', '')
                if '？' in ai_msg:
                    qa_exchanges += 1
                    if any(q in ai_msg for q in ['なぜ', 'どうして', '理由']):
                        question_types['why'] += 1
                    elif any(q in ai_msg for q in ['何', 'どれ', '何個']):
                        question_types['what'] += 1
                    elif any(q in ai_msg for q in ['どう', 'どのように', 'やり方']):
                        question_types['how'] += 1
                    elif any(q in ai_msg for q in ['いつ', 'どの時', '時']):
                        question_types['when'] += 1
                    else:
                        question_types['other'] += 1
    
    # 児童の応答品質
    user_messages = [m.get('content', '') for m in conversation if m.get('role') == 'user']
    multi_sentence_responses = sum(1 for msg in user_messages if msg.count('。') >= 2)
    
    # 因果表現
    causal_count = sum(msg.count('ため') + msg.count('ので') + msg.count('だから') + msg.count('なぜなら') 
                       for msg in user_messages)
    
    structure_score = (
        qa_exchanges * 1.0 +
        multi_sentence_responses * 0.5 +
        causal_count * 0.3
    )
    
    return {
        'qa_exchanges': qa_exchanges,
        'question_types': question_types,
        'multi_sentence_responses': multi_sentence_responses,
        'causal_expressions': causal_count,
        'structure_score': round(structure_score, 2),
        'important_conversation_features': (
            f"AIが{qa_exchanges}回質問。"
            f"児童は{multi_sentence_responses}回複数文で応答。"
            f"因果表現{causal_count}回。"
        ),
        'interpretation': (
            "対話の問答構造が良好。複文で論理的に答えている。" 
            if structure_score >= 5 
            else "対話の深掘りが不足。短い応答が多い。"
        )
    }


# ===== 観点6: 根拠の統合と引き出し =====

def analyze_evidence_integration(conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
    """対話での根拠の使用と経験引き出しの有効性"""
    
    user_messages = [m.get('content', '') for m in conversation if m.get('role') == 'user']
    ai_messages = [m.get('content', '') for m in conversation if m.get('role') == 'assistant']
    
    # 児童が経験参照を述べた場所
    experience_mentions = []
    for i, msg in enumerate(user_messages):
        if any(pat in msg for pat in EXPERIENCE_PATTERNS):
            experience_mentions.append({
                'turn': i,
                'content': msg,
                'pattern': [p for p in EXPERIENCE_PATTERNS if p in msg][0]
            })
    
    # AI が知識・経験引き出しをしたか
    ai_prompts_for_evidence = []
    for i, msg in enumerate(ai_messages):
        content = msg
        if any(q in content for q in ['前に', 'やったことある', '見たことある', '経験', '思い出す']):
            ai_prompts_for_evidence.append({
                'turn': i,
                'content': content
            })
    
    # 児童が根拠的な語を使った回数
    evidence_keywords = ['ため', 'から', 'ので', 'だから', '経験', '見た', 'やった']
    evidence_usage = sum(1 for msg in user_messages for kw in evidence_keywords if kw in msg)
    
    integration_score = (
        len(experience_mentions) * 2 +
        len(ai_prompts_for_evidence) * 1.5 +
        evidence_usage * 0.5
    )
    
    return {
        'experience_mentions': len(experience_mentions),
        'experience_instances': experience_mentions[:5],
        'ai_prompted_evidence_count': len(ai_prompts_for_evidence),
        'ai_prompts_instances': ai_prompts_for_evidence[:3],
        'evidence_keyword_usage': evidence_usage,
        'integration_score': round(integration_score, 2),
        'important_conversation_features': (
            f"児童が{len(experience_mentions)}回経験を参照。"
            f"AIが{len(ai_prompts_for_evidence)}回経験引き出し試行。"
            f"根拠的語彙{evidence_usage}回。"
        ),
        'interpretation': (
            f"良好。児童が具体的な経験から根拠を立てている。"
            if len(experience_mentions) > 0 
            else "経験参照が少ない。より具体的な事例への質問が効果的。"
        )
    }


# ===== 観点7: メタ認知 =====

def analyze_metacognition(user_messages: List[str]) -> Dict[str, Any]:
    """対話での思考プロセスの自覚"""
    
    # 自分の理解や考えを振り返る表現
    metacognitive_phrases = [
        ('気づいた', 1.5),
        ('わかった', 1.0),
        ('考え直した', 2.0),
        ('間違えた', 1.5),
        ('思ってた', 1.0),
        ('そっか', 1.0),
        ('なるほど', 1.0),
        ('初めて知った', 2.0),
    ]
    
    metacognitive_mentions = []
    for msg in user_messages:
        for phrase, weight in metacognitive_phrases:
            if phrase in msg:
                metacognitive_mentions.append({'phrase': phrase, 'weight': weight})
    
    # メタ認知スコア
    meta_score = sum(m['weight'] for m in metacognitive_mentions)
    
    return {
        'has_metacognition': len(metacognitive_mentions) > 0,
        'metacognitive_phrases': [m['phrase'] for m in metacognitive_mentions],
        'mention_count': len(metacognitive_mentions),
        'meta_score': round(meta_score, 2),
        'important_conversation_features': (
            f"児童が自分の思考を{len(metacognitive_mentions)}回言語化。"
            if metacognitive_mentions
            else "思考プロセスへの言及がない。"
        ),
        'interpretation': (
            "優秀。自身の思考過程を自覚し、言語化している。"
            if meta_score >= 3
            else "中程度のメタ認知。一部の気づきが見られる。"
            if len(metacognitive_mentions) > 0
            else "メタ認知表現がない。思考プロセスへの気づきが課題。"
        )
    }


# ===== 観点8: 思考の明確性と表現 =====

def analyze_thought_clarity(user_messages: List[str]) -> Dict[str, Any]:
    """児童の思考の明確さと論理性"""
    
    if not user_messages:
        return {
            'clarity_score': 0,
            'interpretation': 'データなし',
            'important_conversation_features': 'データなし'
        }
    
    # 明確性指標
    clarity_scores = []
    
    for msg in user_messages:
        if not msg.strip():
            continue
        
        score = 0
        
        # 複数の文で構成されている
        sentence_count = msg.count('。') + msg.count('？')
        if sentence_count >= 2:
            score += 1
        elif sentence_count == 1:
            score += 0.5
        
        # 論理語を使っている
        if any(pat in msg for pat in ['だから', 'ため', 'ので', 'なぜなら']):
            score += 1
        
        # 具体例を出している
        if any(pat in msg for pat in ['例えば', 'たとえば', '例：', 'みたいに']):
            score += 1
        
        # 抽象的な表現
        abstract_terms = ['考え', '意見', 'イメージ', '感じ', '気がする']
        if any(pat in msg for pat in abstract_terms):
            score += 0.5
        
        clarity_scores.append(score)
    
    avg_clarity = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0.0
    
    # 発話の一貫性
    unique_messages = len(set(user_messages))
    consistency_ratio = unique_messages / len(user_messages) if user_messages else 0.0
    
    return {
        'average_clarity_score': round(avg_clarity, 2),
        'consistency_ratio': round(consistency_ratio, 3),
        'clarity_score': round(avg_clarity * consistency_ratio * 5, 2),
        'important_conversation_features': (
            f"平均明確性{round(avg_clarity, 2)}/5。"
            f"一貫性{round(consistency_ratio*100, 0):.0f}%。"
        ),
        'interpretation': (
            "思考が明確で論理的に表現できている。"
            if avg_clarity >= 2.0 and consistency_ratio > 0.7
            else "基本的な表現力あり。より論理的な説明を強調。"
            if avg_clarity >= 1.0
            else "表現が曖昧。具体例や因果関係を意識させることが大切。"
        )
    }


# ===== 教員向けサマリー生成 =====

def generate_teacher_summary_conversation_only(
    depth, vocab, engagement, structure, evidence, metacognition, thought_clarity
) -> str:
    """教員が一目で理解できるサマリー"""
    
    points = []
    
    # 強み
    if depth['depth_score'] >= 5:
        points.append(f"✓ 思考が深い（修正{depth['self_corrections']['count']}回）")
    
    if vocab['infection_rate'] > 0.3:
        points.append(f"✓ 科学語彙習得中（感染率{vocab['infection_rate']*100:.0f}%）")
    
    if engagement['engagement_score'] >= 10:
        points.append(f"✓ 高いエンゲージメント（{engagement['turn_count']}往復）")
    
    if thought_clarity['clarity_score'] >= 3:
        points.append(f"✓ 思考が明確")
    
    if metacognition['has_metacognition']:
        points.append(f"✓ メタ認知あり（{metacognition['mention_count']}回）")
    
    if evidence['integration_score'] >= 3:
        points.append(f"✓ 経験から根拠を立てている")
    
    # 課題
    if depth['depth_score'] < 2:
        points.append(f"→ 思考の深化が不足。開かれた問いかけを。")
    
    if vocab['infection_rate'] < 0.2:
        points.append(f"→ 科学語彙習得が進んでいない。")
    
    if engagement['engagement_score'] < 5:
        points.append(f"→ 対話が短い。疑問引き出しのプロンプト検討。")
    
    if thought_clarity['clarity_score'] < 1:
        points.append(f"→ 表現が曖昧。具体例や因果関係を強調。")
    
    summary = "【会話ベース学習効果分析】\n"
    summary += " / ".join(points[:6]) if points else "分析対象となる会話がありません。"
    
    return summary


# ===== メイン分析関数 =====

def analyze_conversation_only(
    conversation: List[Dict[str, Any]], 
    unit: str = 'default'
) -> Dict[str, Any]:
    """会話履歴のみから多角的な学習効果を分析する。
    
    Args:
        conversation: [{'role': 'user'|'assistant', 'content': str}, ...]
        unit: 単元名（語彙リスト選択用）
    
    Returns:
        詳細な分析結果 JSON
    """
    # 抽出
    user_messages = [m.get('content', '') for m in conversation if m.get('role') == 'user']
    ai_messages = [m.get('content', '') for m in conversation if m.get('role') == 'assistant']
    
    # 各観点の分析実行
    depth_analysis = analyze_depth_of_thinking(user_messages, ai_messages)
    vocab_analysis = analyze_scientific_vocabulary(user_messages, ai_messages, unit)
    engagement = analyze_engagement(user_messages, ai_messages)
    structure = analyze_structure_crystallization(conversation)
    evidence = analyze_evidence_integration(conversation)
    metacognition = analyze_metacognition(user_messages)
    thought_quality = analyze_thought_clarity(user_messages)
    
    summary = generate_teacher_summary_conversation_only(
        depth_analysis, vocab_analysis, engagement, structure, evidence, metacognition, thought_quality
    )
    
    return {
        'summary': summary,
        'depth_of_thinking': depth_analysis,
        'scientific_vocabulary': vocab_analysis,
        'engagement': engagement,
        'structure_crystallization': structure,
        'evidence_integration': evidence,
        'metacognition': metacognition,
        'thought_clarity': thought_quality,
        'raw_data': {
            'total_turns': len(user_messages),
            'total_ai_responses': len(ai_messages)
        }
    }


# 互換性のために残す
def analyze_conversation_and_note(
    conversation: List[Dict[str, Any]], 
    note_text: str = '',
    unit: str = 'default'
) -> Dict[str, Any]:
    """後方互換性のため残す（会話のみで分析）"""
    return analyze_conversation_only(conversation, unit)
