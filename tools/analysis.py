"""
児童の予想・考察の分析モジュール
理科用語の含有率、科学的語彙の獲得率を分析する
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# 理科用語辞書（単元ごと）
SCIENCE_TERMS = {
    "水のあたたまり方": {
        "heat": ["温度", "あたたまり", "加熱", "熱", "温かい", "あたたかい"],
        "state": ["液体", "沸騰", "蒸発", "気体", "泡"],
        "transfer": ["対流", "伝わり", "伝導", "流れ"]
    },
    "水を冷やし続けた時の温度と様子": {
        "temperature": ["温度", "冷たい", "冷やす", "冷却"],
        "phase": ["固体", "液体", "氷", "凍る", "凝固"],
        "change": ["変化", "状態変化", "結晶化"]
    },
    "空気の温度と体積": {
        "temperature": ["温度", "あたたまり", "冷やす"],
        "volume": ["体積", "膨らむ", "膨張", "縮む", "収縮"],
        "gas": ["空気", "気体", "分子"]
    },
    "金属のあたたまり方": {
        "heat": ["温度", "あたたまり", "熱", "伝わり"],
        "conduction": ["伝導", "熱伝導", "伝わる"],
        "metal": ["金属", "銅", "アルミニウム"]
    },
    "金属の温度と体積": {
        "temperature": ["温度", "あたたまり", "加熱", "冷やす"],
        "volume": ["体積", "膨らむ", "膨張", "伸びる", "長さ"],
        "metal": ["金属", "銅棒", "アルミニウム"]
    }
}

# 生活語彙 → 理科用語のマッピング
VOCABULARY_MAPPING = {
    "あつい": ["温度が高い", "温度が上がった"],
    "あたたかい": ["温度が上がった", "温度が高い"],
    "さむい": ["温度が低い", "温度が下がった"],
    "つめたい": ["温度が低い", "冷えた"],
    "ふとった": ["体積が増えた", "膨らんだ", "膨張した"],
    "やせた": ["体積が減った", "縮んだ", "収縮した"],
    "ちぢむ": ["体積が減った", "収縮した"],
    "膨らむ": ["体積が増えた"],
    "太くなった": ["体積が増えた"],
    "細くなった": ["体積が減った"]
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
