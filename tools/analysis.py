"""
分析モジュール: 会話ログとノート（要約）から各種指標を算出する。
出力スキーマ（例）:
{
  "summary": "短い教員向け要約",
  "metrics": {
    "depth_of_thinking": {"self_corrections": int, "hesitation_count": int, "alternative_perspectives": int},
    "vocabulary": {"pre_terms": [...], "post_terms": [...], "infection_rate": float},
    "engagement": {"turns": int, "avg_length": float, "sustained_turns": int}
  },
  "traces": { ... }
}
"""
from collections import Counter
import re
from typing import List, Dict, Any

# 簡易的な科学語彙リスト（必要に応じて拡張）
SCIENCE_TERMS = [
    '温度', '体積', '膨張', '収縮', '圧力', '変化', '加熱', '冷却', '拡大', '縮小',
    '熱', 'エネルギー', '熱膨張', '体積変化'
]

# フィラー・ためらい表現
HESITATION_PATTERNS = ['うーん', 'えー', 'わからない', 'わかんない', 'たぶん', 'かもしれない', '迷う']

# 自己修正を示す語
SELF_CORRECTION_PATTERNS = ['違う', 'ちがう', 'やっぱり', '訂正', '直す', '直した']

# 他視点を示す語
ALTERNATIVE_PATTERNS = ['もし', 'たとえば', '別の', 'ほか', '～だったら', 'ならば']


def analyze_conversation_and_note(conversation: List[Dict[str, Any]], note_text: str) -> Dict[str, Any]:
    """会話（list of {'role', 'content', ...}）とノート（要約文）から各指標を返す。"""
    # 抽出：児童（user）とAI（assistant）の発話を分離
    user_messages = [m.get('content','') for m in conversation if m.get('role') == 'user']
    ai_messages = [m.get('content','') for m in conversation if m.get('role') == 'assistant']

    # Engagement
    turns = len(user_messages)
    lengths = [len(m) for m in user_messages if m]
    avg_length = sum(lengths) / len(lengths) if lengths else 0.0
    sustained_turns = 1 if turns >= 3 else turns  # 簡易指標: 3往復以上を深掘りとみなす

    # Depth of Thinking: self-corrections, hesitation, alternative perspectives
    self_corrections = sum(1 for m in user_messages if any(p in m for p in SELF_CORRECTION_PATTERNS))
    hesitation_count = sum(1 for m in user_messages if any(p in m for p in HESITATION_PATTERNS))
    alternative_perspectives = sum(1 for m in user_messages if any(p in m for p in ALTERNATIVE_PATTERNS))

    # Scientific vocabulary: pre/post frequency
    def extract_terms(texts: List[str]):
        found = []
        for t in texts:
            for term in SCIENCE_TERMS:
                if term in t:
                    found.append(term)
        return Counter(found)

    pre_terms = extract_terms(user_messages[:max(1, len(user_messages)//2)])
    post_terms = extract_terms(user_messages[max(0, len(user_messages)//2):])

    # Infection rate: AI が使った用語を児童がその後使った割合
    ai_terms = set()
    for m in ai_messages:
        for term in SCIENCE_TERMS:
            if term in m:
                ai_terms.add(term)
    if not ai_terms:
        infection_rate = 0.0
    else:
        used_after = 0
        total_candidates = 0
        # if AI used term at some point, check whether user used it later in conversation
        for term in ai_terms:
            total_candidates += 1
            # did any user message contain the term after first ai mention? simplified: any user message contains term
            if any(term in um for um in user_messages):
                used_after += 1
        infection_rate = used_after / total_candidates if total_candidates else 0.0

    # Conversion / transfer: note vs conversation overlap
    # キーワード抽出（簡易）
    def tokenize_jp(text: str):
        # split on non-japanese/word chars
        tokens = re.findall(r'[一-龥ぁ-んァ-ヴー]{2,}|[A-Za-z0-9]{2,}', text)
        return tokens

    conv_tokens = set()
    for m in user_messages:
        conv_tokens.update(tokenize_jp(m))
    note_tokens = set(tokenize_jp(note_text or ''))

    if conv_tokens:
        overlap = conv_tokens & note_tokens
        conversion_rate = len(overlap) / len(conv_tokens)
    else:
        conversion_rate = 0.0

    # Traces: which user messages likely contributed to the note (simple substring match)
    traces = []
    for i, m in enumerate(user_messages):
        score = 0
        for tok in tokenize_jp(m):
            if tok in note_tokens:
                score += 1
        if score > 0:
            traces.append({'index': i, 'message': m, 'match_score': score})

    summary = generate_brief_summary(user_messages, note_text)

    return {
        'summary': summary,
        'metrics': {
            'depth_of_thinking': {
                'self_corrections': self_corrections,
                'hesitation_count': hesitation_count,
                'alternative_perspectives': alternative_perspectives
            },
            'vocabulary': {
                'pre_terms': dict(pre_terms),
                'post_terms': dict(post_terms),
                'ai_terms': list(ai_terms),
                'infection_rate': round(infection_rate, 3)
            },
            'engagement': {
                'turns': turns,
                'avg_length': round(avg_length, 1),
                'sustained_turns': sustained_turns
            },
            'conversion': {
                'conversation_tokens': len(conv_tokens),
                'note_tokens': len(note_tokens),
                'conversion_rate': round(conversion_rate, 3)
            }
        },
        'traces': traces
    }


def generate_brief_summary(user_messages: List[str], note_text: str) -> str:
    """教員向けの短い要約（1-2文）。非常に簡易実装。
    - 主要なキーワードを抜き出し、対話の特徴を述べる。"""
    if not user_messages:
        return '発話がありません。'

    joined = ' '.join(user_messages)
    # キーワード上位3
    kw = []
    for term in SCIENCE_TERMS:
        if term in joined:
            kw.append(term)
    kw = kw[:3]

    turns = len(user_messages)

    s = f"対話は{turns}回行われ、主要語彙: {', '.join(kw) if kw else '特になし'}。"
    if note_text:
        s += " 最終ノートが存在します。"
    else:
        s += " ノートは未作成です。"
    return s
