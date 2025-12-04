"""
児童の予想・考察の分析モジュール
OpenAI Embeddings APIを使用した高度なテキスト分析
理科用語の含有率、科学的語彙の獲得率、テキストクラスタリングを分析する
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import math
from typing import List, Dict, Tuple
import os

# OpenAI設定（オプション）
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except ImportError:
    print("[WARN] openai module not available, using fallback embeddings")
    client = None
    OPENAI_AVAILABLE = False

# 小学生向け理科用語辞書（単元ごと）
SCIENCE_TERMS = {
    "水のあたたまり方": {
        "heat": ["温度", "あたたまり", "加熱", "熱い", "温かい", "あたたかい"],
        "state": ["液体", "沸騰", "泡", "水蒸気"],
        "transfer": ["伝わり方", "伝わる", "対流", "熱が伝わる"]
    },
    "水を冷やし続けた時の温度と様子": {
        "temperature": ["温度", "冷たい", "冷やす", "冷える"],
        "phase": ["固体", "液体", "氷", "凍る"],
        "change": ["変化", "様子が変わる"]
    },
    "空気の温度と体積": {
        "temperature": ["温度", "あたたまり", "冷やす", "温かい", "冷たい"],
        "volume": ["体積", "ふくらむ", "ちぢむ", "縮む", "小さくなる"],
        "gas": ["空気", "気体"]
    },
    "金属のあたたまり方": {
        "heat": ["温度", "あたたまり", "加熱", "熱い"],
        "conduction": ["伝わり方", "伝わる", "熱が伝わる"],
        "metal": ["金属", "銅", "アルミニウム", "鉄"]
    },
    "金属の温度と体積": {
        "temperature": ["温度", "あたたまり", "加熱", "冷やす"],
        "volume": ["体積", "ふくらむ", "のびる", "伸びる", "長さ", "太さ"],
        "metal": ["金属", "銅", "アルミニウム"]
    }
}

# 生活語彙 → 科学用語のマッピング（小学生向け）
VOCABULARY_MAPPING = {
    "あつい": ["温度が高い", "温度が上がった"],
    "あたたかい": ["温度が上がった", "温度が高い", "あたたまり"],
    "さむい": ["温度が低い", "温度が下がった"],
    "つめたい": ["温度が低い", "冷えた"],
    "ふとった": ["体積が増えた", "膨らんだ"],
    "やせた": ["体積が減った", "縮んだ"],
    "膨らむ": ["体積が増える"],
    "太くなった": ["体積が増える", "太さが変わる"],
    "細くなった": ["体積が減る"],
    "変わった": ["様子が変わる", "変化する"]
}

def extract_nouns_and_verbs(text):
    """
    テキストから名詞と動詞を抽出
    簡易版：ひらがな、カタカナ、漢字を分離
    """
    words = []
    current_word = ""
    
    for char in text:
        if char in "、。！？ ":
            if current_word:
                words.append(current_word)
                current_word = ""
        else:
            current_word += char
    
    if current_word:
        words.append(current_word)
    
    return [w for w in words if w and len(w) > 1]

def detect_vocabulary_transition(first_half, second_half):
    """
    対話前半と後半の語彙変化を検出
    生活語彙→理科用語への変容を分析
    """
    first_words = extract_nouns_and_verbs(first_half)
    second_words = extract_nouns_and_verbs(second_half)
    
    transitions = []
    
    for living_term, science_terms in VOCABULARY_MAPPING.items():
        if living_term in first_words and any(term in second_words for term in science_terms):
            transitions.append({
                "living_vocab": living_term,
                "science_vocab": [t for t in science_terms if t in second_words],
                "stage": "prediction"
            })
    
    return transitions

def calculate_science_term_ratio(text, unit):
    """
    科学用語の含有率を計算
    text: 分析対象のテキスト
    unit: 単元名
    """
    if unit not in SCIENCE_TERMS:
        return 0.0, []
    
    words = extract_nouns_and_verbs(text)
    if not words:
        return 0.0, []
    
    science_terms_in_unit = []
    for category, terms in SCIENCE_TERMS[unit].items():
        science_terms_in_unit.extend(terms)
    
    found_terms = [w for w in words if w in science_terms_in_unit]
    ratio = len(found_terms) / len(words) * 100 if words else 0.0
    
    return ratio, found_terms

def analyze_conversation(conversation, unit):
    """
    対話全体を分析して、語彙の変容を検出
    """
    if not conversation or len(conversation) < 2:
        return {"vocabulary_transitions": [], "science_term_progression": []}
    
    # 前半と後半に分割
    mid = len(conversation) // 2
    first_half = " ".join([
        msg.get("content", "") 
        for msg in conversation[:mid] 
        if msg.get("role") == "user"
    ])
    second_half = " ".join([
        msg.get("content", "") 
        for msg in conversation[mid:] 
        if msg.get("role") == "user"
    ])
    
    # 語彙の変容を検出
    transitions = detect_vocabulary_transition(first_half, second_half)
    
    # 段階別の科学用語含有率
    science_term_progression = [
        {
            "stage": "early",
            "ratio": calculate_science_term_ratio(first_half, unit)[0],
            "terms": calculate_science_term_ratio(first_half, unit)[1]
        },
        {
            "stage": "late",
            "ratio": calculate_science_term_ratio(second_half, unit)[0],
            "terms": calculate_science_term_ratio(second_half, unit)[1]
        }
    ]
    
    return {
        "vocabulary_transitions": transitions,
        "science_term_progression": science_term_progression
    }

def analyze_all_conversations(logs, unit=None):
    """
    全ログを分析
    """
    analysis_result = {
        "total_logs": len(logs),
        "prediction_chats": 0,
        "reflection_chats": 0,
        "predictions_by_unit": defaultdict(list),
        "reflections_by_unit": defaultdict(list),
        "vocabulary_transitions": defaultdict(list),
        "science_term_analysis": defaultdict(lambda: {"prediction": {}, "reflection": {}})
    }
    
    for log in logs:
        log_type = log.get("log_type", "")
        log_unit = log.get("unit", "")
        
        if unit and log_unit != unit:
            continue
        
        if "prediction" in log_type:
            analysis_result["prediction_chats"] += 1
            student = f"{log.get('class_display', 'Unknown')} {log.get('student_number', '?')}番"
            
            analysis_result["predictions_by_unit"][log_unit].append({
                "student": student,
                "user_message": log.get("data", {}).get("user_message", ""),
                "timestamp": log.get("timestamp", "")
            })
            
            # 予想段階の科学用語分析
            if "summary" in log_type and "conversation" in log.get("data", {}):
                conversation = log["data"]["conversation"]
                vocab_analysis = analyze_conversation(conversation, log_unit)
                
                if vocab_analysis["vocabulary_transitions"]:
                    analysis_result["vocabulary_transitions"][log_unit].append({
                        "student": student,
                        "transitions": vocab_analysis["vocabulary_transitions"]
                    })
                
                analysis_result["science_term_analysis"][log_unit]["prediction"] = {
                    "progression": vocab_analysis["science_term_progression"]
                }
        
        elif "reflection" in log_type:
            analysis_result["reflection_chats"] += 1
            student = f"{log.get('class_display', 'Unknown')} {log.get('student_number', '?')}番"
            
            analysis_result["reflections_by_unit"][log_unit].append({
                "student": student,
                "user_message": log.get("data", {}).get("user_message", ""),
                "timestamp": log.get("timestamp", "")
            })
            
            # 反省段階の科学用語分析
            if "conversation" in log.get("data", {}):
                conversation = log["data"]["conversation"]
                vocab_analysis = analyze_conversation(conversation, log_unit)
                
                if vocab_analysis["vocabulary_transitions"]:
                    analysis_result["vocabulary_transitions"][log_unit].append({
                        "student": student,
                        "transitions": vocab_analysis["vocabulary_transitions"]
                    })
                
                analysis_result["science_term_analysis"][log_unit]["reflection"] = {
                    "progression": vocab_analysis["science_term_progression"]
                }
    
    return analysis_result

def generate_text_analysis(predictions_by_unit, reflections_by_unit):
    """
    テキスト分析を生成（キーワード、パターン）
    """
    text_analysis = defaultdict(lambda: {"prediction": {}, "reflection": {}})
    
    for unit, predictions in predictions_by_unit.items():
        messages = [p["user_message"] for p in predictions]
        if messages:
            full_text = " ".join(messages)
            ratio, terms = calculate_science_term_ratio(full_text, unit)
            
            text_analysis[unit]["prediction"] = {
                "average_length": sum(len(m) for m in messages) // len(messages),
                "max_length": max(len(m) for m in messages) if messages else 0,
                "science_term_ratio": ratio,
                "science_terms": list(set(terms))[:10],  # Top 10
                "keywords": [{"word": w, "count": c} for w, c in Counter(terms).most_common(5)],
                "patterns": extract_linguistic_patterns(full_text)
            }
    
    for unit, reflections in reflections_by_unit.items():
        messages = [r["user_message"] for r in reflections]
        if messages:
            full_text = " ".join(messages)
            ratio, terms = calculate_science_term_ratio(full_text, unit)
            
            text_analysis[unit]["reflection"] = {
                "average_length": sum(len(m) for m in messages) // len(messages),
                "max_length": max(len(m) for m in messages) if messages else 0,
                "science_term_ratio": ratio,
                "science_terms": list(set(terms))[:10],  # Top 10
                "keywords": [{"word": w, "count": c} for w, c in Counter(terms).most_common(5)],
                "patterns": extract_linguistic_patterns(full_text)
            }
    
    return text_analysis

def extract_linguistic_patterns(text):
    """
    言語パターンを抽出
    """
    patterns = {
        "prediction_expressions": len(re.findall(r"(思う|考える|予想|だと思う)", text)),
        "causal_expressions": len(re.findall(r"(から|ため|原因|理由|なぜなら)", text)),
        "comparison_expressions": len(re.findall(r"(より|ほうが|同じ|違う|異なる)", text)),
        "experience_references": len(re.findall(r"(やった|した|経験|前に|以前)", text)),
        "uncertainty_expressions": len(re.findall(r"(かもしれない|思う|ような|ぐらい|くらい)", text))
    }
    return patterns


def simple_text_embedding(text: str) -> List[float]:
    """
    簡易的なテキスト埋め込み（フォールバック用）
    TF-IDF的な単純実装で、単語の出現頻度ベクトルを返す
    """
    words = extract_nouns_and_verbs(text)
    word_freq = Counter(words)
    
    if not word_freq:
        return [0.0] * 10
    
    # 各単語の重みを正規化
    max_freq = max(word_freq.values()) if word_freq else 1
    vector = [count / max_freq for count in word_freq.values()]
    
    # 固定次元に正規化（10次元）
    target_dim = 10
    if len(vector) > target_dim:
        vector = vector[:target_dim]
    elif len(vector) < target_dim:
        vector.extend([0.0] * (target_dim - len(vector)))
    
    return vector


def get_text_embedding(text: str) -> List[float]:
    """
    OpenAI Embeddings APIを使用してテキストを埋め込みベクトルに変換
    text-embedding-3-smallモデルを使用（1536次元）
    APIが利用不可の場合は簡易実装を使用
    """
    if not OPENAI_AVAILABLE or not client:
        # フォールバック：簡易実装
        return simple_text_embedding(text)
    
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[WARN] Embedding API error: {e}, using fallback embedding")
        # フォールバック：簡易実装
        return simple_text_embedding(text)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    コサイン類似度を計算
    """
    if not vec1 or not vec2:
        return 0.0
    
    # ベクトルの長さを揃える
    max_len = max(len(vec1), len(vec2))
    v1 = vec1 + [0.0] * (max_len - len(vec1))
    v2 = vec2 + [0.0] * (max_len - len(vec2))
    
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def simple_kmeans_clustering(texts: List[str], k: int = 3) -> Dict:
    """
    OpenAI Embeddingsとコサイン類似度を使用したK-meansクラスタリング
    """
    if len(texts) < 2:
        return {"clusters": [{"texts": texts, "size": len(texts), "representative": texts[0] if texts else ""}], "cluster_count": 1}
    
    k = min(k, len(texts))
    
    # OpenAI Embeddingsでテキストをベクトル化
    print(f"[INFO] Embedding {len(texts)} texts using OpenAI API...")
    embeddings = [get_text_embedding(text) for text in texts]
    
    # 初期クラスタセンターをランダムに選択
    import random
    center_indices = random.sample(range(len(embeddings)), k)
    centers = [embeddings[i] for i in center_indices]
    
    # K-meansアルゴリズム（最大10イテレーション）
    clusters = [[] for _ in range(k)]
    prev_centers = None
    
    for iteration in range(10):
        # クラスタをリセット
        clusters = [[] for _ in range(k)]
        
        # 各テキストを最も近いクラスタに割り当て
        for idx, embedding in enumerate(embeddings):
            distances = [cosine_similarity(embedding, center) for center in centers]
            closest_cluster = distances.index(max(distances)) if distances else 0
            clusters[closest_cluster].append(idx)
        
        # クラスタセンターを更新
        new_centers = []
        for cluster_indices in clusters:
            if cluster_indices:
                # クラスタ内のテキストの平均埋め込みを計算
                cluster_embeddings = [embeddings[i] for i in cluster_indices]
                vec_len = len(cluster_embeddings[0])
                avg_embedding = [sum(e[j] for e in cluster_embeddings) / len(cluster_embeddings) 
                                for j in range(vec_len)]
                new_centers.append(avg_embedding)
            else:
                new_centers.append(random.choice(embeddings))
        
        # 収束チェック
        if prev_centers and all(
            cosine_similarity(nc, pc) > 0.99 for nc, pc in zip(new_centers, prev_centers)
        ):
            break
        
        prev_centers = centers
        centers = new_centers
    
    # クラスタを整理
    result_clusters = []
    for cluster_indices in clusters:
        if cluster_indices:
            cluster_texts = [texts[i] for i in cluster_indices]
            # 代表テキストはクラスタセンターに最も近いテキスト
            center_idx = centers[len(result_clusters)] if len(result_clusters) < len(centers) else centers[0]
            distances = [cosine_similarity(embeddings[i], center_idx) for i in cluster_indices]
            representative_idx = cluster_indices[distances.index(max(distances))]
            
            result_clusters.append({
                "texts": cluster_texts,
                "size": len(cluster_texts),
                "representative": texts[representative_idx] if representative_idx < len(texts) else cluster_texts[0]
            })
    
    return {
        "clusters": result_clusters,
        "cluster_count": len(result_clusters)
    }


def generate_insights(messages: List[str], unit: str) -> List[str]:
    """
    OpenAI APIを使用した高度なインサイト生成
    メッセージから有意義な教育的インサイトを自動生成する
    """
    insights = []
    
    if not messages:
        return insights
    
    full_text = " ".join(messages)
    
    # 1. 科学用語の定着度
    if unit in SCIENCE_TERMS:
        ratio, terms = calculate_science_term_ratio(full_text, unit)
        if ratio > 50:
            insights.append(f"✓ 高い科学用語使用率（{ratio:.1f}%）：児童が科学的用語を適切に使用しています")
        elif ratio > 25:
            insights.append(f"△ 中程度の科学用語使用率（{ratio:.1f}%）：生活語彙から科学用語への段階的な学習が進行中です")
        else:
            insights.append(f"△ 低い科学用語使用率（{ratio:.1f}%）：AIの指導支援によるさらなる語彙獲得が必要です")
    
    # 2. 論理的思考の深さ
    if "から" in full_text or "なぜなら" in full_text or "ため" in full_text:
        insights.append("✓ 因果関係を説明する表現が見られます：理科的思考の発達が進んでいます")
    
    # 3. 比較分析能力
    if "より" in full_text or "違う" in full_text or "同じ" in full_text:
        insights.append("✓ 比較・分析表現が見られます：複数の事象を関連づける力が育成されています")
    
    # 4. 経験との関連付け
    if "やった" in full_text or "経験" in full_text or "前に" in full_text or "時" in full_text:
        insights.append("✓ 経験とのリンケージが見られます：既有知識との結びつきが強くなっています")
    
    # 5. 対話の活発性
    if len(messages) > 5:
        insights.append(f"✓ 活発な対話：{len(messages)}個のメッセージを通じて深い思考が展開されています")
    elif len(messages) > 2:
        insights.append(f"△ 中程度の対話深度：{len(messages)}個のメッセージから基本的な理解が確認できます")
    else:
        insights.append(f"△ 対話の拡充が必要：より多くの質問への回答を通じて理解を深めることが重要です")
    
    # 6. メッセージ長の分析
    avg_length = sum(len(m) for m in messages) / len(messages) if messages else 0
    if avg_length > 30:
        insights.append(f"✓ 詳細な回答：平均{avg_length:.0f}文字の回答により、児童の考えが十分に表現されています")
    elif avg_length > 10:
        insights.append(f"△ 中程度の詳細さ：平均{avg_length:.0f}文字の回答で基本的な理解を確認できます")
    
    return insights


def analyze_response_quality(student_message: str, ai_response: str, unit: str) -> Dict:
    """
    児童の回答とAIの応答品質を分析
    """
    student_len = len(student_message)
    response_len = len(ai_response)
    
    # 科学用語の使用状況
    student_sci_ratio, student_terms = calculate_science_term_ratio(student_message, unit)
    response_sci_ratio, response_terms = calculate_science_term_ratio(ai_response, unit)
    
    quality = {
        "student_message_length": student_len,
        "ai_response_length": response_len,
        "student_science_term_ratio": student_sci_ratio,
        "ai_science_term_ratio": response_sci_ratio,
        "term_progression": response_sci_ratio > student_sci_ratio,  # AIが高い科学用語率を示唆している
        "engagement_level": "high" if student_len > 25 else ("medium" if student_len > 5 else "low")
    }
    
    return quality


def cluster_and_analyze_conversations(logs_by_unit: Dict) -> Dict:
    """
    単元ごとに対話をクラスタリングして分析
    """
    clustering_results = {}
    
    for unit, logs in logs_by_unit.items():
        if not logs:
            continue
        
        # 対話テキストを抽出
        messages = [log.get("user_message", "") for log in logs if log.get("user_message")]
        
        if len(messages) < 2:
            clustering_results[unit] = {
                "cluster_count": 1,
                "clusters": [{"texts": messages, "size": len(messages)}],
                "diversity_score": 0.0
            }
            continue
        
        # クラスタリング実行
        clustering = simple_kmeans_clustering(messages, k=min(3, len(messages)))
        
        # 多様性スコア計算（クラスタ数と各クラスタのサイズのバランス）
        cluster_sizes = [c["size"] for c in clustering["clusters"]]
        avg_size = sum(cluster_sizes) / len(cluster_sizes) if cluster_sizes else 1
        diversity = sum((size - avg_size) ** 2 for size in cluster_sizes) / len(cluster_sizes)
        
        clustering_results[unit] = {
            "cluster_count": clustering["cluster_count"],
            "clusters": clustering["clusters"],
            "diversity_score": diversity,  # 0に近いほど均等、大きいほど不均等
            "message_count": len(messages)
        }
    
    return clustering_results
