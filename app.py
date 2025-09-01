from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import openai
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import csv
import time
import hashlib
import ssl
import certifi
import urllib3
import re
import glob
import uuid
from werkzeug.utils import secure_filename


# 環境変数を読み込み
load_dotenv()

# SSL設定の改善
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# SSL証明書の設定
ssl_context = ssl.create_default_context(cafile=certifi.where())

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 本番環境では安全なキーに変更

# ファイルアップロード設定
UPLOAD_FOLDER = 'uploads'  # 一時的なアップロード用
ALLOWED_EXTENSIONS = {'md', 'txt'}  # Markdownとテキストファイルのみ
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB制限

# アップロードディレクトリが存在しない場合は作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 教員認証情報（実際の運用では環境変数やデータベースに保存）
TEACHER_CREDENTIALS = {
    # 本番運用時は適切な認証システムを実装してください
}

# 認証チェック用デコレータ
def require_teacher_auth(f):
    def decorated_function(*args, **kwargs):
        if not session.get('teacher_authenticated'):
            return redirect(url_for('teacher_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# OpenAI APIの設定
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("警告: OPENAI_API_KEYが設定されていません")
else:
    print(f"APIキー設定確認: {api_key[:10]}...{api_key[-4:]}")
    
try:
    # OpenAI クライアントを初期化
    client = openai.OpenAI(api_key=api_key)
    print("OpenAI API設定完了")
except Exception as e:
    print(f"OpenAI API設定エラー: {e}")
    client = None

# OpenAI client設定の確認
if client is None:
    print("警告: OpenAIクライアントの初期化に失敗しました")

# マークダウン記法を除去する関数
def remove_markdown_formatting(text):
    """AIの応答からマークダウン記法を除去する"""
    import re
    
    # 太字 **text** や __text__ を通常のテキストに
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # 斜体 *text* や _text_ を通常のテキストに
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # 箇条書きの記号を除去
    text = re.sub(r'^\s*\*\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # 見出し記号 ### text を除去
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # コードブロック ```text``` を除去
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # 引用記号 > を除去
    text = re.sub(r'^\s*>\s*', '', text, flags=re.MULTILINE)
    
    # その他の記号の重複を整理
    text = re.sub(r'\s+', ' ', text)  # 複数の空白を1つに
    text = re.sub(r'\n\s*\n', '\n', text)  # 複数の改行を1つに
    
    return text.strip()

def extract_message_from_json_response(response):
    """JSON形式のレスポンスから純粋なメッセージを抽出する"""
    try:
        # JSON形式かどうか確認
        if response.strip().startswith('{') and response.strip().endswith('}'):
            import json
            parsed = json.loads(response)
            
            # よくあるフィールド名から順番に確認
            common_fields = ['response', 'message', 'question', 'summary', 'text', 'content', 'answer']
            
            for field in common_fields:
                if field in parsed and isinstance(parsed[field], str):
                    return parsed[field]
            
            # その他のフィールドから文字列値を探す
            for key, value in parsed.items():
                if isinstance(value, str) and len(value.strip()) > 0:
                    return value
                    
            # JSONだが適切なフィールドがない場合はそのまま返す
            return response
                
        # リスト形式の場合の処理
        elif response.strip().startswith('[') and response.strip().endswith(']'):
            import json
            parsed = json.loads(response)
            if isinstance(parsed, list) and len(parsed) > 0:
                # リストの各要素を処理
                results = []
                for item in parsed:
                    if isinstance(item, dict):
                        # よくあるフィールド名から順番に確認
                        common_fields = ['予想', 'response', 'message', 'question', 'summary', 'text', 'content']
                        found = False
                        for field in common_fields:
                            if field in item and isinstance(item[field], str):
                                results.append(item[field])
                                found = True
                                break
                        
                        # よくあるフィールドが見つからない場合は最初の文字列値を使用
                        if not found:
                            for key, value in item.items():
                                if isinstance(value, str) and len(value.strip()) > 0:
                                    results.append(value)
                                    break
                    elif isinstance(item, str):
                        results.append(item)
                
                # 複数の予想を改行で結合
                if results:
                    return '\n'.join(results)
            return response
            
        # JSON形式でない場合はそのまま返す
        else:
            return response
            
    except (json.JSONDecodeError, Exception) as e:
        print(f"JSON解析エラー: {e}, 元のレスポンスを返します")
        return response

def load_markdown_content(file_path):
    """Markdownファイルからテキストを読み込む"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content.strip()
    except Exception as e:
        print(f"Markdown読み込みエラー: {e}")
        return None

def get_learning_guidelines():
    """学習指導要領の内容を取得"""
    guidelines_path = "guidelines/learning_guidelines.md"
    if os.path.exists(guidelines_path):
        return load_markdown_content(guidelines_path)
    return None

def get_teaching_support():
    """指導支援方針の内容を取得"""
    support_path = "guidelines/teaching_support.md"
    if os.path.exists(support_path):
        return load_markdown_content(support_path)
    return None

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
            "キーワード": ["対流", "循環", "あたたまり方", "温度差"],
            "産婆法質問": [
                "お風呂に入るとき、どの部分があたたかく感じますか？",
                "やかんでお湯を沸かすとき、どんなことが起こりますか？",
                "水の中で何が動いているのでしょうか？"
            ]
        },
        "空気のあたたまり方": {
            "見方・考え方": "目に見えない物質の性質を構造や状態変化と関係づけて考える",
            "重点活動": ["見えない現象の言語化", "空気の動きの表現", "比喩的表現"],
            "生活経験": ["ドライヤー", "エアコン", "風船の変化"],
            "キーワード": ["対流", "空気の流れ", "軽い・重い", "上昇・下降"],
            "産婆法質問": [
                "ドライヤーの温かい風はどちらに向かって流れますか？",
                "エアコンはなぜ上の方に取り付けてあるのでしょう？",
                "風船を太陽に当てるとどうなりますか？"
            ]
        },
        "金属のあたたまり方": {
            "見方・考え方": "温度と物質の状態・性質の関係性に注目する",
            "重点活動": ["伝導現象の観察", "順序立てた説明", "物質比較"],
            "生活経験": ["フライパンで料理", "金属スプーン", "アイロン"],
            "キーワード": ["伝導", "順番に", "伝わる", "熱くなる"],
            "産婆法質問": [
                "フライパンで料理をするとき、どの部分から熱くなりますか？",
                "金属のスプーンをお湯に入れると、どうなりますか？",
                "なぜ金属は料理道具によく使われるのでしょう？"
            ]
        }
    }
    return unit_characteristics.get(unit, {})

def determine_learning_stage(conversation_count, conversation_content=None):
    """対話内容から学習段階を判定"""
    if conversation_count <= 2:
        return "自己思考段階"
    elif conversation_count <= 4:
        return "伝え合い段階"
    else:
        return "思考まとめ段階"

def generate_stage_appropriate_guidance(stage, unit):
    """学習段階に応じた指導ガイダンスを生成"""
    unit_info = analyze_unit_characteristics(unit)
    
    guidance = {
        "自己思考段階": {
            "目標": "児童が自分の考えを持ち、予想・仮説を立てる",
            "支援方針": ["日常経験を引き出す", "既習事項との関連付け", "根拠を持った予想を促す"],
            "質問例": unit_info.get("産婆法質問", ["どう思いますか？"])[:1],
            "重点": f"生活経験（{', '.join(unit_info.get('生活経験', [])[:2])}）との関連を重視"
        },
        "伝え合い段階": {
            "目標": "他者との比較・共有・討論を通じて考えを深める", 
            "支援方針": ["多様な考えを価値付ける", "比較検討を促す", "根拠を明確化"],
            "質問例": ["友達の考えと比べてどうですか？", "なぜ違いが生まれたのでしょう？"],
            "重点": f"見方・考え方「{unit_info.get('見方・考え方', '')}」の深化"
        },
        "思考まとめ段階": {
            "目標": "結果の整理、概念の抽出、考察の記述",
            "支援方針": ["学習内容の整理", "概念の一般化", "新たな疑問の発見"],
            "質問例": ["今日分かったことは何ですか？", "他でも同じことが起こりそうですか？"],
            "重点": f"キーワード（{', '.join(unit_info.get('キーワード', [])[:3])}）の理解確認"
        }
    }
    return guidance.get(stage, guidance["自己思考段階"])

def save_lesson_plan_info(unit, content):
    """指導案情報をJSONファイルに保存"""
    lesson_plans_file = "lesson_plans_md/lesson_plans_index.json"
    
    # ディレクトリが存在しない場合は作成
    os.makedirs("lesson_plans_md", exist_ok=True)
    
    # 既存の指導案情報を読み込み
    lesson_plans = {}
    if os.path.exists(lesson_plans_file):
        try:
            with open(lesson_plans_file, 'r', encoding='utf-8') as f:
                lesson_plans = json.load(f)
        except (json.JSONDecodeError, Exception):
            lesson_plans = {}
    
    # 新しい指導案情報を追加
    lesson_plans[unit] = {
        'filename': f'{unit}.md',
        'last_updated': datetime.now().isoformat(),
        'content_preview': content[:500] if content else "",  # 最初の500文字のプレビュー
        'content_length': len(content) if content else 0
    }
    
    # ファイルに保存
    with open(lesson_plans_file, 'w', encoding='utf-8') as f:
        json.dump(lesson_plans, f, ensure_ascii=False, indent=2)

def load_lesson_plan_content(unit):
    """指定された単元の指導案内容を読み込む"""
    # まず既存のMarkdownファイルを確認
    markdown_path = f"lesson_plans_md/{unit}.md"
    if os.path.exists(markdown_path):
        return load_markdown_content(markdown_path)
    
    # インデックスファイルからも確認
    lesson_plans_file = "lesson_plans_md/lesson_plans_index.json"
    if not os.path.exists(lesson_plans_file):
        return None
    
    try:
        with open(lesson_plans_file, 'r', encoding='utf-8') as f:
            lesson_plans = json.load(f)
        
        if unit not in lesson_plans:
            return None
        
        # Markdownファイルから内容を読み込み
        markdown_path = os.path.join("lesson_plans_md", lesson_plans[unit]['filename'])
        if os.path.exists(markdown_path):
            return load_markdown_content(markdown_path)
        else:
            return None
            
    except (json.JSONDecodeError, Exception) as e:
        print(f"指導案読み込みエラー: {e}")
        return None

def get_lesson_plans_list():
    """アップロード済みの指導案一覧を取得"""
    lesson_plans_file = "lesson_plans/lesson_plans_index.json"
    
    if not os.path.exists(lesson_plans_file):
        return {}
    
    try:
        with open(lesson_plans_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}

# APIコール用のリトライ関数
def build_enhanced_prompt(base_prompt, unit=None, stage=None):
    """学習指導要領とMarkdownガイドラインを活用して強化されたプロンプトを構築"""
    enhanced_prompt = base_prompt
    
    # 言語化支援の重要な指針を最初に追加
    enhanced_prompt += """

## 最重要：段階別言語化支援の実践
### 予想段階での支援（概念化はしない）
1. **体験的表現の受容**: 児童のオノマトペ・感覚的表現をまず受け止める
2. **一般表現への変換**: 「〜を別の言い方でできないかな？」で支援
3. **関連経験の引き出し**: 「似たような経験はないかな？」
4. **予想の根拠明確化**: 「なぜそう思ったの？」「何から考えたの？」

**予想段階では概念化まで進まない** - 言語表現の引き上げと経験活用に集中

### 考察段階での支援（概念化への足掛かりまで）
1. **結果の言語化**: 実験結果の体験的表現をまず受け止める
2. **一般表現への変換**: 「〜を別の言い方でできないかな？」で支援
3. **予想との比較**: 「予想と同じだった？」「違ったところは？」
4. **経験・既習事項との関連**: 「前に習ったことと似てる？」
5. **概念化への足掛かり**: 「このことから何が言えそうかな？」

**考察段階では概念化への足掛かりまで** - 結果分析と関連付けを重視

### 対話の基本パターン
- 児童の発言を必ず受け止める：「そうですね」「なるほど」
- 1回1つの質問：複数の質問を同時にしない
- 10文字以内の短い質問：「どうなった？」「なぜかな？」
- 経験重視：「〜という経験はない？」「家で見たことと似てる？」

### 理科の見方・考え方の活用
- 量的・関係的視点：「どのくらい？」「前と比べると？」
- 質的・実体的視点：「何の性質？」「どんな特徴？」
- 共通性・多様性視点：「他でも同じ？」「違うところは？」
- 時間的・空間的視点：「いつから？」「どこから変化？」
"""
    
    # 学習指導要領の内容を追加（言語活動重視）
    guidelines = get_learning_guidelines()
    if guidelines:
        # 特に言語活動部分を抽出
        relevant_section = ""
        if "言語活動" in guidelines:
            lines = guidelines.split('\n')
            for i, line in enumerate(lines):
                if "言語活動" in line or "見方・考え方" in line:
                    relevant_section += '\n'.join(lines[max(0, i-2):min(len(lines), i+8)])
                    break
        enhanced_prompt += f"\n\n【学習指導要領（言語活動重視）】:\n{relevant_section[:1000]}..."
    
    # 指導支援方針を追加
    teaching_support = get_teaching_support()
    if teaching_support:
        # 産婆法の部分を重点的に抽出
        if "産婆法" in teaching_support:
            lines = teaching_support.split('\n')
            for i, line in enumerate(lines):
                if "産婆法" in line:
                    support_section = '\n'.join(lines[i:min(len(lines), i+20)])
                    enhanced_prompt += f"\n\n【産婆法実践方針】:\n{support_section[:800]}..."
                    break
    
    # 単元別指導案があれば追加
    if unit:
        lesson_content = load_lesson_plan_content(unit)
        if lesson_content:
            # 産婆法実践のポイント部分を抽出
            if "産婆法実践のポイント" in lesson_content:
                lines = lesson_content.split('\n')
                for i, line in enumerate(lines):
                    if "産婆法実践のポイント" in line:
                        lesson_section = '\n'.join(lines[i:min(len(lines), i+15)])
                        enhanced_prompt += f"\n\n【{unit}指導案（産婆法）】:\n{lesson_section[:600]}..."
                        break
        
        # 単元特性の詳細分析を追加
        unit_info = analyze_unit_characteristics(unit)
        if unit_info:
            enhanced_prompt += f"\n\n【{unit}の特性分析】:\n"
            enhanced_prompt += f"・見方・考え方: {unit_info.get('見方・考え方', '')}\n"
            enhanced_prompt += f"・重点活動: {', '.join(unit_info.get('重点活動', []))}\n"
            enhanced_prompt += f"・生活経験例: {', '.join(unit_info.get('生活経験', []))}\n"
            enhanced_prompt += f"・キーワード: {', '.join(unit_info.get('キーワード', []))}\n"
    
    # 学習段階別の支援ガイダンスを追加
    if stage and unit:
        conversation_count = 1  # デフォルト値
        learning_stage = determine_learning_stage(conversation_count)
        stage_guidance = generate_stage_appropriate_guidance(learning_stage, unit)
        
        enhanced_prompt += f"\n\n【現在の学習段階】: {learning_stage}\n"
        enhanced_prompt += f"・目標: {stage_guidance.get('目標', '')}\n"
        enhanced_prompt += f"・支援方針: {', '.join(stage_guidance.get('支援方針', []))}\n"
        enhanced_prompt += f"・重点: {stage_guidance.get('重点', '')}\n"
        enhanced_prompt += f"・推奨質問: {stage_guidance.get('質問例', [''])[0]}\n"
    
    return enhanced_prompt

def analyze_student_response(response, unit):
    """児童の発言から学習状況を分析して次の支援方針を決定"""
    analysis = {
        "理解度": "継続観察",
        "言語化レベル": "基礎段階", 
        "日常関連": False,
        "概念理解": False,
        "感情・態度": "普通",
        "推奨支援": "継続質問",
        "次の質問タイプ": "開放的質問"
    }
    
    response = response.lower() if response else ""
    
    # 理解度の判定
    positive_indicators = ["分かった", "なるほど", "そういうこと", "面白い", "すごい"]
    negative_indicators = ["分からない", "よく分からない", "難しい", "よく見えない"]
    
    if any(word in response for word in positive_indicators):
        analysis["理解度"] = "良好"
        analysis["推奨支援"] = "発展質問"
    elif any(word in response for word in negative_indicators):
        analysis["理解度"] = "要支援"
        analysis["推奨支援"] = "基礎確認"
    
    # 言語化レベルの判定
    if len(response) > 30 and any(word in response for word in ["なぜなら", "だから", "理由は"]):
        analysis["言語化レベル"] = "高度"
        analysis["次の質問タイプ"] = "深化質問"
    elif len(response) > 15 and any(word in response for word in ["と思う", "気がする", "みたい"]):
        analysis["言語化レベル"] = "中程度"
    
    # 日常経験との関連確認
    daily_keywords = ["家で", "普段", "お風呂", "料理", "お母さん", "見たことある", "前に", "いつも"]
    if any(word in response for word in daily_keywords):
        analysis["日常関連"] = True
        analysis["推奨支援"] = "関連深化"
    
    # 単元特性に基づく概念理解確認
    unit_info = analyze_unit_characteristics(unit)
    keywords = unit_info.get("キーワード", [])
    if any(keyword.lower() in response for keyword in keywords):
        analysis["概念理解"] = True
        analysis["推奨支援"] = "概念確認"
    
    # 感情・態度の判定
    positive_emotions = ["楽しい", "面白い", "すごい", "びっくり", "驚いた"]
    if any(word in response for word in positive_emotions):
        analysis["感情・態度"] = "積極的"
    
    return analysis

def generate_adaptive_question(analysis, unit, conversation_history=None):
    """分析結果に基づいて適応的な質問を生成"""
    unit_info = analyze_unit_characteristics(unit)
    
    # 理解度に基づく質問選択
    if analysis["理解度"] == "良好":
        if analysis["概念理解"]:
            questions = [
                "他の場面でも同じようなことが起こりそうですか？",
                f"普段の生活で{', '.join(unit_info.get('生活経験', [])[:1])}以外にも似たことはありますか？"
            ]
        else:
            questions = unit_info.get("産婆法質問", ["もう少し詳しく教えてください"])
    elif analysis["理解度"] == "要支援":
        questions = [
            "どの部分が分からないですか？",
            "今見えたことを教えてください",
            "どんな感じがしましたか？"
        ]
    else:
        # 通常の段階的質問
        if analysis["日常関連"]:
            questions = [
                "それと今回の実験、似ているところはありますか？",
                "どんなところが同じだと思いますか？"
            ]
        else:
            questions = unit_info.get("産婆法質問", ["どう思いますか？"])
    
    # 会話履歴を考慮して質問の重複を避ける
    if conversation_history:
        used_patterns = []
        for msg in conversation_history:
            if msg.get('role') == 'assistant':
                used_patterns.append(msg.get('content', ''))
        
        # 使用済みパターンと類似していない質問を選択
        for question in questions:
            if not any(pattern in question or question in pattern for pattern in used_patterns):
                return question
    
    return questions[0] if questions else "どう感じましたか？"

def call_openai_with_retry(prompt, max_retries=3, delay=2, unit=None, stage=None):
    """OpenAI APIを呼び出し、エラー時はリトライする（Markdownガイドライン活用版）"""
    if client is None:
        return "AI システムの初期化に問題があります。管理者に連絡してください。"
    
    # Markdownガイドラインを活用してプロンプトを強化
    enhanced_prompt = build_enhanced_prompt(prompt, unit, stage)
    
    # OpenAI向けの応答指示を追加
    enhanced_prompt += f"""

**重要な応答指示（OpenAI向け）:**
- 必ず普通の日本語の文章で回答してください
- JSON、マークダウン、その他の形式は一切使用しないでください
- 小学生向けの短い質問を1つだけしてください
- 質問は15文字以内で簡潔にしてください
- 専門用語は使わず、日常的な言葉を使ってください
- {{ }}, [ ], **, #, ``` などの記号は使わないでください
- 1文で質問を終えてください
- 「実験お疲れさまでした」「実験の結果は」などの定型句は使わないでください
- 子どもの前の発言を受け止めてから、新しい質問をしてください
- 同じフレーズを繰り返さないでください
- 産婆法（ソクラテス式問答法）を実践し、答えを直接教えるのではなく適切な質問で導いてください
"""
    
    for attempt in range(max_retries):
        try:
            print(f"OpenAI API呼び出し試行 {attempt + 1}/{max_retries}")
            
            # タイムアウト設定を短くして早期に失敗検出
            import time
            start_time = time.time()
            
            # OpenAI APIでリクエストを送信
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": enhanced_prompt}
                ],
                max_tokens=2000,
                temperature=0.3,
                timeout=30  # 30秒タイムアウト
            )
            
            elapsed_time = time.time() - start_time
            print(f"API呼び出し所要時間: {elapsed_time:.2f}秒")
            
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content
                print(f"API呼び出し成功: {len(content)}文字の応答")
                # マークダウン記法を除去してから返す
                cleaned_response = remove_markdown_formatting(content)
                return cleaned_response
            else:
                print("空の応答が返されました")
                print(f"応答全体: {response}")
                raise Exception("空の応答が返されました")
                
        except Exception as e:
            error_msg = str(e)
            print(f"APIコール試行 {attempt + 1}/{max_retries} でエラー: {error_msg}")
            
            # エラーの種類に応じた処理
            if "API_KEY" in error_msg.upper() or "invalid_api_key" in error_msg.lower():
                return "APIキーの設定に問題があります。管理者に連絡してください。"
            elif "QUOTA" in error_msg.upper() or "LIMIT" in error_msg.upper() or "rate_limit_exceeded" in error_msg.lower():
                return "API利用制限に達しました。しばらく待ってから再度お試しください。"
            elif "TIMEOUT" in error_msg.upper() or "DNS" in error_msg.upper() or "503" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = delay * (attempt + 1)
                    print(f"ネットワークエラー、{wait_time}秒後に再試行...")
                    time.sleep(wait_time)
                    continue
                else:
                    return "ネットワーク接続に問題があります。インターネット接続を確認してください。"
            elif "400" in error_msg or "INVALID" in error_msg.upper():
                return "リクエストの形式に問題があります。管理者に連絡してください。"
            elif "403" in error_msg or "PERMISSION" in error_msg.upper():
                return "APIの利用権限に問題があります。管理者に連絡してください。"
            else:
                if attempt < max_retries - 1:
                    wait_time = delay * (attempt + 1)
                    print(f"その他のエラー、{wait_time}秒後に再試行...")
                    time.sleep(wait_time)
                    continue
                else:
                    return f"予期しないエラーが発生しました: {error_msg[:100]}..."
                    
    return "複数回の試行後もAPIに接続できませんでした。しばらく待ってから再度お試しください。"

# 学習単元のデータ
UNITS = [
    "空気の温度と体積",
    "水の温度と体積", 
    "金属の温度と体積",
    "金属のあたたまり方",
    "水のあたたまり方",
    "空気のあたたまり方",
    "ふっとうした時の泡の正体",
    "水を熱し続けた時の温度と様子",
    "冷やした時の水の温度と様子"
]

# 課題文を読み込む関数
def load_task_content(unit_name):
    try:
        with open(f'tasks/{unit_name}.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return f"{unit_name}について実験を行います。どのような結果になると予想しますか？"

# 単元ごとのプロンプトを読み込む関数
def load_unit_prompt(unit_name):
    """単元専用のプロンプトファイルを読み込む"""
    try:
        with open(f'prompts/{unit_name}.md', 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Markdownファイルの内容をプロンプトとして使用
        # ## 単元固有の指導ポイント以降の内容を抽出
        lines = content.split('\n')
        prompt_parts = []
        current_section = ""
        
        for line in lines:
            if line.startswith('## '):
                current_section = line[3:].strip()
                if current_section in ['役割設定', '基本指針', '対話の進め方', '絶対に守ること']:
                    prompt_parts.append(line)
            elif current_section in ['役割設定', '基本指針', '対話の進め方', '絶対に守ること']:
                prompt_parts.append(line)
        
        return '\n'.join(prompt_parts)
    
    except FileNotFoundError:
        # フォールバック: デフォルトプロンプト
        return """
あなたは小学生向けの産婆法（ソクラテス式問答法）を実践する理科指導者です。小学生のレベルに合わせた簡単な質問で、学習者自身に気づかせることが目的です。

## 基本指針
- 1つずつ聞く - 複数の質問を同時にしない
- 身近な例で考えさせる
- 学習者の発言を受け止める - まず肯定してから次の質問
- 経験を聞く - 「前に見たことある？」「どんな時に？」

## 絶対に守ること
- 1文で短く質問する（20文字以内を目指す）
- 小学生が知らない専門用語は使わない
- 複雑な例え話はしない
- 1回に1つのことだけ聞く
- JSON形式では絶対に回答しない
- 普通の文章で質問する
"""

# 学習ログを保存する関数
def save_learning_log(student_number, unit, log_type, data):
    """学習ログをJSONファイルに保存"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'student_number': student_number,
        'unit': unit,
        'log_type': log_type,  # 'prediction_chat', 'prediction_summary', 'reflection_chat', 'final_summary'
        'data': data
    }
    
    # ログディレクトリが存在しない場合は作成
    os.makedirs('logs', exist_ok=True)
    
    # ログファイル名（日付別）
    log_file = f"logs/learning_log_{datetime.now().strftime('%Y%m%d')}.json"
    
    # 既存のログを読み込み
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []
    
    # 新しいログを追加
    logs.append(log_entry)
    
    # ファイルに保存
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# 学習ログを読み込む関数
def load_learning_logs(date=None):
    """指定日の学習ログを読み込み"""
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    log_file = f"logs/learning_log_{date}.json"
    
    if not os.path.exists(log_file):
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

@app.route('/api/test')
def api_test():
    """API接続テスト"""
    try:
        test_prompt = "こんにちは。短い挨拶をお願いします。"
        response = call_openai_with_retry(test_prompt, max_retries=1)
        return jsonify({
            'status': 'success',
            'message': 'API接続テスト成功',
            'response': response
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'API接続テスト失敗: {str(e)}'
        }), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/select_number')
def select_number():
    return render_template('select_number.html')

@app.route('/select_unit')
def select_unit():
    student_number = request.args.get('number')
    session['student_number'] = student_number
    return render_template('select_unit.html', units=UNITS)

@app.route('/prediction')
def prediction():
    unit = request.args.get('unit')
    session['unit'] = unit
    session['conversation'] = []
    
    task_content = load_task_content(unit)
    session['task_content'] = task_content
    
    return render_template('prediction.html', unit=unit, task_content=task_content)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    input_metadata = request.json.get('metadata', {})
    conversation = session.get('conversation', [])
    unit = session.get('unit')
    task_content = session.get('task_content')
    student_number = session.get('student_number')
    
    # 対話履歴に追加
    conversation.append({'role': 'user', 'content': user_message})
    
    # 単元ごとのプロンプトを読み込み
    unit_prompt = load_unit_prompt(unit)
    
    # プロンプト作成
    system_prompt = f"""{unit_prompt}

現在の学習単元: {unit}
課題: {task_content}
対話回数: {len(conversation)}回目

次の質問を普通の文章で1文で書いてください："""
    
    # 対話履歴を含めてプロンプト作成
    full_prompt = system_prompt + "\n\n対話履歴:\n"
    for msg in conversation:
        role = "学習者" if msg['role'] == 'user' else "AI"
        full_prompt += f"{role}: {msg['content']}\n"
    
    try:
        ai_response = call_openai_with_retry(full_prompt, unit=unit, stage='prediction')
        
        # JSON形式のレスポンスの場合は解析して純粋なメッセージを抽出
        ai_message = extract_message_from_json_response(ai_response)
        
        # マークダウン記法を除去
        ai_message = remove_markdown_formatting(ai_message)
        
        conversation.append({'role': 'assistant', 'content': ai_message})
        session['conversation'] = conversation
        
        # 学習ログを保存
        save_learning_log(
            student_number=session.get('student_number'),
            unit=unit,
            log_type='prediction_chat',
            data={
                'user_message': user_message,
                'ai_response': ai_message,
                'conversation_count': len(conversation) // 2,
                'used_suggestion': False,
                'suggestion_index': None
            }
        )
        
        # 対話が3回以上の場合、予想のまとめを提案
        suggest_summary = len(conversation) >= 6  # user + AI で1セット
        
        response_data = {
            'response': ai_message,
            'suggest_summary': suggest_summary
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"チャットエラー: {str(e)}")
        return jsonify({'error': f'AI接続エラーが発生しました。しばらく待ってから再度お試しください。'}), 500

@app.route('/summary', methods=['POST'])
def summary():
    conversation = session.get('conversation', [])
    unit = session.get('unit')
    
    # 課題文を読み込み
    task_content = load_task_content(unit)
    
    # 予想のまとめを生成（対話内容のみに基づく）
    summary_prompt = f"""
以下の対話内容「のみ」を基に、学習者が実際に発言した内容をまとめて予想文を作成してください。

**重要な制約:**
1. 対話に出てこなかった内容は絶対に追加しない
2. 学習者が実際に言った言葉や表現をできるだけ使用する
3. 学習者が話した経験や根拠のみを含める
4. 対話で言及されていない例や理由は一切使わない
5. 1-2文の短い予想文にまとめる
6. 「〜と思います。」「〜だと予想します。」の形で終わる
7. マークダウン記法は一切使用しない

課題文: {task_content}
単元: {unit}

対話履歴:
"""
    for msg in conversation:
        role = "学習者" if msg['role'] == 'user' else "AI"
        summary_prompt += f"{role}: {msg['content']}\n"
    
    try:
        summary_response = call_openai_with_retry(summary_prompt)
        
        # JSON形式のレスポンスの場合は解析して純粋なメッセージを抽出
        summary_text = extract_message_from_json_response(summary_response)
        
        session['prediction_summary'] = summary_text
        
        # 予想まとめのログを保存
        save_learning_log(
            student_number=session.get('student_number'),
            unit=unit,
            log_type='prediction_summary',
            data={
                'summary': summary_text,
                'conversation': conversation
            }
        )
        
        return jsonify({'summary': summary_text})
    except Exception as e:
        print(f"まとめエラー: {str(e)}")
        return jsonify({'error': f'まとめ生成中にエラーが発生しました。'}), 500

@app.route('/experiment')
def experiment():
    return render_template('experiment.html')

@app.route('/reflection')
def reflection():
    return render_template('reflection.html', 
                         unit=session.get('unit'),
                         prediction_summary=session.get('prediction_summary'))

@app.route('/reflect_chat', methods=['POST'])
def reflect_chat():
    user_message = request.json.get('message')
    reflection_conversation = session.get('reflection_conversation', [])
    unit = session.get('unit')
    prediction_summary = session.get('prediction_summary', '')
    
    # 反省対話履歴に追加
    reflection_conversation.append({'role': 'user', 'content': user_message})
    
    # 児童の発言を分析
    student_analysis = analyze_student_response(user_message, unit)
    
    # 学習段階判定
    conversation_turn = len(reflection_conversation) // 2 + 1
    learning_stage = determine_learning_stage(conversation_turn)
    stage_guidance = generate_stage_appropriate_guidance(learning_stage, unit)
    
    # 適応的質問生成
    adaptive_question = generate_adaptive_question(student_analysis, unit, reflection_conversation)
    
    # 強化された考察支援プロンプト
    system_prompt = f"""
あなたは小学生の考察を支援する理科専門の先生です。学習指導要領と産婆法に基づいて子どもの思考を深く導いてください。

【学習情報】
単元: {unit}
予想: {prediction_summary}
対話回数: {conversation_turn}回目

【児童分析結果】
理解度: {student_analysis['理解度']}
言語化レベル: {student_analysis['言語化レベル']}
日常関連: {'あり' if student_analysis['日常関連'] else 'なし'}
概念理解: {'あり' if student_analysis['概念理解'] else 'なし'}
感情・態度: {student_analysis['感情・態度']}

【現在の学習段階】: {learning_stage}
目標: {stage_guidance['目標']}
支援方針: {', '.join(stage_guidance['支援方針'])}
重点: {stage_guidance['重点']}

【推奨質問】: {adaptive_question}

**指導原則:**
- 答えを直接教えずに、適切な質問で児童自身の気づきを促す
- 児童の日常経験と結び付けて理解を深める
- 言語化を支援し、思考を可視化する
- 一度に一つの質問に絞る
- 児童の発言を受け止めてから次の質問をする

前回の発言を受けて、{student_analysis['推奨支援']}の方針で支援してください。

**応答のルール:**
1. 子どもの発言をまず受け止める（「そうですね」「なるほど」等）
2. その後、1つだけ短い質問をする（15文字以内）
3. JSON形式は絶対に使わない
4. 普通の日本語で話す
5. 専門用語は使わない
6. 同じ質問は繰り返さない - 子どもの答えに応じて変化させる
7. 子どもが既に答えた内容については再度聞かない

**良い応答例（段階別）:**
第1段階:
- 1回目: 「実験でどんなことが起こりましたか？」
- 2回目: 「そうですね。どのくらいでしたか？」「なるほど。どんな感じでしたか？」

第2段階:
- 「予想と同じでしたか？」
- 「どんな気持ちですか？」

第3段階:
- 「どうしてそうなったと思いますか？」
- 「何が原因だと思いますか？」

**絶対に避けること:**
- 「実験お疲れさまでした」の繰り返し
- 「実験の結果はどうでしたか」の繰り返し
- 長い説明や複数の質問
- 同じフレーズの使い回し

今は{conversation_turn}回目の対話です。
子どもの発言を受け止めてから、適切な質問を1つしてください。

**重要:** 対話履歴を確認して、子どもが既に答えた内容は聞き直さないでください。
子どもの前の発言に基づいて、次のステップに進む質問をしてください："""
    
    # 強化されたプロンプト構築を使用
    full_prompt = build_enhanced_prompt(system_prompt, unit=unit, stage='reflection')
    
    # 対話履歴を追加
    full_prompt += "\n\n対話履歴:\n"
    for msg in reflection_conversation:
        role = "学習者" if msg['role'] == 'user' else "AI"
        full_prompt += f"{role}: {msg['content']}\n"
    
    try:
        ai_response = call_openai_with_retry(full_prompt, unit=unit, stage='reflection')
        
        # JSON形式のレスポンスの場合は解析して純粋なメッセージを抽出
        ai_message = extract_message_from_json_response(ai_response)
        
        # マークダウン記法を除去
        ai_message = remove_markdown_formatting(ai_message)
        
        reflection_conversation.append({'role': 'assistant', 'content': ai_message})
        session['reflection_conversation'] = reflection_conversation
        
        # 考察チャットのログを保存
        save_learning_log(
            student_number=session.get('student_number'),
            unit=unit,
            log_type='reflection_chat',
            data={
                'user_message': user_message,
                'ai_response': ai_message,
                'conversation_count': len(reflection_conversation) // 2
            }
        )
        
        return jsonify({'response': ai_message})
        
    except Exception as e:
        print(f"考察チャットエラー: {str(e)}")
        return jsonify({'error': f'AI接続エラーが発生しました。しばらく待ってから再度お試しください。'}), 500

@app.route('/final_summary', methods=['POST'])
def final_summary():
    reflection_conversation = session.get('reflection_conversation', [])
    prediction_summary = session.get('prediction_summary', '')
    
    # 最終まとめを生成（対話内容のみに基づく）
    final_prompt = f"""
以下の対話内容「のみ」を基に、学習者が実際に発言した内容をまとめて考察文を作成してください。

**重要な制約:**
1. 対話に出てこなかった内容は絶対に追加しない
2. 学習者が実際に言った実験結果のみを使用する
3. 学習者が実際に話した経験や考えのみを含める
4. 対話で言及されていない結論や解釈は一切追加しない
5. 定型文の形式を守る：「(結果)という結果であった。(予想)と予想していたが、(合っていた/誤っていた)。このことから(経験や既習事項)は~と考えた」
6. マークダウン記法は一切使用しない
7. 学習者の実際の表現をできるだけ使用する

学習者の予想: {prediction_summary}

考察対話履歴:
"""
    for msg in reflection_conversation:
        role = "学習者" if msg['role'] == 'user' else "AI"
        final_prompt += f"{role}: {msg['content']}\n"
    
    try:
        final_summary_response = call_openai_with_retry(final_prompt)
        
        # JSON形式のレスポンスの場合は解析して純粋なメッセージを抽出
        final_summary_text = extract_message_from_json_response(final_summary_response)
        
        # マークダウン記法を除去
        final_summary_text = remove_markdown_formatting(final_summary_text)
        
        # 最終考察のログを保存
        save_learning_log(
            student_number=session.get('student_number'),
            unit=session.get('unit'),
            log_type='final_summary',
            data={
                'final_summary': final_summary_text,
                'prediction_summary': prediction_summary,
                'reflection_conversation': reflection_conversation
            }
        )
        
        return jsonify({'summary': final_summary_text})
    except Exception as e:
        print(f"最終まとめエラー: {str(e)}")
        return jsonify({'error': f'最終まとめ生成中にエラーが発生しました。'}), 500

# 教員用ルート
@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    """教員ログインページ"""
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        password = request.form.get('password')
        
        # 認証チェック
        if teacher_id in TEACHER_CREDENTIALS and TEACHER_CREDENTIALS[teacher_id] == password:
            session['teacher_authenticated'] = True
            session['teacher_id'] = teacher_id
            flash('ログインしました', 'success')
            return redirect(url_for('teacher'))
        else:
            flash('IDまたはパスワードが正しくありません', 'error')
    
    return render_template('teacher/login.html')

@app.route('/teacher/logout')
def teacher_logout():
    """教員ログアウト"""
    session.pop('teacher_authenticated', None)
    session.pop('teacher_id', None)
    flash('ログアウトしました', 'info')
    return redirect(url_for('index'))

@app.route('/teacher')
@require_teacher_auth
def teacher():
    """教員用ダッシュボード"""
    # 指導案一覧も含めて表示
    lesson_plans = get_lesson_plans_list()
    return render_template('teacher/dashboard.html', 
                         units=UNITS, 
                         teacher_id=session.get('teacher_id'),
                         lesson_plans=lesson_plans)

@app.route('/teacher/lesson_plans')
@require_teacher_auth
def teacher_lesson_plans():
    """指導案管理ページ"""
    lesson_plans = get_lesson_plans_list()
    return render_template('teacher/lesson_plans.html', 
                         units=UNITS, 
                         lesson_plans=lesson_plans,
                         teacher_id=session.get('teacher_id'))

@app.route('/teacher/lesson_plans/upload', methods=['POST'])
@require_teacher_auth
def upload_lesson_plan():
    """指導案PDFのアップロード"""
    try:
        unit = request.form.get('unit')
        
        # 単元の検証
        if unit not in UNITS:
            flash('無効な単元が選択されました', 'error')
            return redirect(url_for('teacher_lesson_plans'))
        
        # ファイルの確認
        if 'file' not in request.files:
            flash('ファイルが選択されていません', 'error')
            return redirect(url_for('teacher_lesson_plans'))
        
        file = request.files['file']
        if file.filename == '':
            flash('ファイルが選択されていません', 'error')
            return redirect(url_for('teacher_lesson_plans'))
        
        if file and allowed_file(file.filename):
            # ファイル名を安全にする（単元名を含める）
            filename = secure_filename(f"{unit}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # 既存ファイルがあれば削除
            lesson_plans = get_lesson_plans_list()
            if unit in lesson_plans:
                old_file = os.path.join(app.config['UPLOAD_FOLDER'], lesson_plans[unit]['filename'])
                if os.path.exists(old_file):
                    os.remove(old_file)
            
            # ファイルを保存（現在はMarkdown形式のため、この部分は使用しない）
            # file.save(file_path)
            
            # 指導案情報を保存（Markdownファイルが既に存在すると仮定）
            lesson_content = load_lesson_plan_content(unit)
            if lesson_content:
                save_lesson_plan_info(unit, lesson_content)
                flash(f'{unit}の指導案が更新されました', 'success')
            else:
                flash('指導案の内容を読み込めませんでした', 'error')
        else:
            flash('現在はMarkdown形式の指導案のみ対応しています', 'info')
            
    except Exception as e:
        flash(f'アップロード中にエラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('teacher_lesson_plans'))

@app.route('/teacher/lesson_plans/delete/<unit>')
@require_teacher_auth
def delete_lesson_plan(unit):
    """指導案の削除"""
    try:
        lesson_plans = get_lesson_plans_list()
        if unit in lesson_plans:
            # ファイルを削除
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], lesson_plans[unit]['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # インデックスから削除
            del lesson_plans[unit]
            lesson_plans_file = "lesson_plans/lesson_plans_index.json"
            with open(lesson_plans_file, 'w', encoding='utf-8') as f:
                json.dump(lesson_plans, f, ensure_ascii=False, indent=2)
            
            flash(f'{unit}の指導案が削除されました', 'success')
        else:
            flash('指導案が見つかりません', 'error')
    except Exception as e:
        flash(f'削除中にエラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('teacher_lesson_plans'))

@app.route('/teacher/logs')
@require_teacher_auth
def teacher_logs():
    """学習ログ一覧"""
    # デフォルト日付を最新のログがある日付に設定
    available_dates = get_available_log_dates()
    default_date = available_dates[0]['raw'] if available_dates else datetime.now().strftime('%Y%m%d')
    
    date = request.args.get('date', default_date)
    unit = request.args.get('unit', '')
    student = request.args.get('student', '')
    
    logs = load_learning_logs(date)
    print(f"ログ読み込み - 対象日付: {date}, 読み込んだログ数: {len(logs)}")
    
    # フィルタリング
    if unit:
        logs = [log for log in logs if log.get('unit') == unit]
        print(f"単元フィルタ適用後: {len(logs)}件")
    if student:
        logs = [log for log in logs if log.get('student_number') == student]
        print(f"学生フィルタ適用後: {len(logs)}件")
    
    # 学生ごとにグループ化
    students_data = {}
    for log in logs:
        student_num = log.get('student_number')
        if student_num not in students_data:
            students_data[student_num] = {
                'student_number': student_num,
                'units': {}
            }
        
        unit_name = log.get('unit')
        if unit_name not in students_data[student_num]['units']:
            students_data[student_num]['units'][unit_name] = {
                'prediction_chats': [],
                'prediction_summary': None,
                'reflection_chats': [],
                'final_summary': None
            }
        
        log_type = log.get('log_type')
        if log_type == 'prediction_chat':
            students_data[student_num]['units'][unit_name]['prediction_chats'].append(log)
        elif log_type == 'prediction_summary':
            students_data[student_num]['units'][unit_name]['prediction_summary'] = log
        elif log_type == 'reflection_chat':
            students_data[student_num]['units'][unit_name]['reflection_chats'].append(log)
        elif log_type == 'final_summary':
            students_data[student_num]['units'][unit_name]['final_summary'] = log
    
    return render_template('teacher/logs.html', 
                         students_data=students_data, 
                         units=UNITS,
                         current_date=date,
                         current_unit=unit,
                         current_student=student,
                         available_dates=available_dates,
                         teacher_id=session.get('teacher_id'))

@app.route('/teacher/export')
@require_teacher_auth
def teacher_export():
    """ログをCSVでエクスポート"""
    date = request.args.get('date', datetime.now().strftime('%Y%m%d'))
    logs = load_learning_logs(date)
    
    # CSVファイルを作成
    output_file = f"export_{date}.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['timestamp', 'student_number', 'unit', 'log_type', 'content']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for log in logs:
            content = ""
            if log.get('log_type') == 'prediction_chat':
                content = f"質問: {log['data'].get('user_message', '')} / 回答: {log['data'].get('ai_response', '')}"
            elif log.get('log_type') == 'prediction_summary':
                content = log['data'].get('summary', '')
            elif log.get('log_type') == 'reflection_chat':
                content = f"質問: {log['data'].get('user_message', '')} / 回答: {log['data'].get('ai_response', '')}"
            elif log.get('log_type') == 'final_summary':
                content = log['data'].get('final_summary', '')
            
            writer.writerow({
                'timestamp': log.get('timestamp', ''),
                'student_number': log.get('student_number', ''),
                'unit': log.get('unit', ''),
                'log_type': log.get('log_type', ''),
                'content': content
            })
    
    return jsonify({'message': f'エクスポートが完了しました: {output_file}'})

# ログ分析機能
def load_guidelines_content():
    """指導要領・資料の内容を読み込み"""
    try:
        index_file = 'guidelines/guidelines_index.json'
        
        if not os.path.exists(index_file):
            return ""
        
        with open(index_file, 'r', encoding='utf-8') as f:
            guidelines_index = json.load(f)
        
        # 全ての資料の内容を結合
        combined_content = ""
        for doc_id, doc_info in guidelines_index.items():
            doc_type = doc_info.get('type', '')
            title = doc_info.get('title', '')
            content = doc_info.get('content', '')
            
            combined_content += f"\n【{title}】\n{content}\n"
        
        return combined_content[:2000]  # 最大2000文字まで
    
    except Exception as e:
        print(f"指導要領読み込みエラー: {str(e)}")
        return ""

def analyze_student_learning(student_number, unit, logs):
    """特定の学生・単元の学習過程を詳細分析"""
    print(f"分析開始 - 学生: {student_number}, 単元: {unit}")
    
    # 該当する学生のログを抽出
    student_logs = [log for log in logs if 
                   log.get('student_number') == student_number and 
                   log.get('unit') == unit]
    
    print(f"該当ログ数: {len(student_logs)}")
    
    if not student_logs:
        return {
            'evaluation': '学習データがありません',
            'prediction_analysis': {
                'daily_life_connection': 'データなし - 日常体験との関連付けを確認できません',
                'prior_knowledge_use': 'データなし - 既習事項の活用を確認できません',
                'reasoning_quality': 'データなし - 予想の根拠を確認できません'
            },
            'reflection_analysis': {
                'result_verbalization': 'データなし - 結果の言語化を確認できません',
                'prediction_comparison': 'データなし - 予想との比較を確認できません',
                'daily_life_connection': 'データなし - 日常生活との関連付けを確認できません',
                'scientific_understanding': 'データなし - 科学的理解を確認できません'
            },
            'language_development': '学習活動への参加が必要です',
            'support_recommendations': ['学習活動への参加促進', '対話の機会提供']
        }
    
    # 指導要領・資料の内容を取得
    guidelines_content = load_guidelines_content()
    guidelines_context = ""
    
    if guidelines_content:
        guidelines_context = f"参考指導資料: {guidelines_content[:800]}"
    
    # 対話履歴を整理
    prediction_chats = []
    reflection_chats = []
    prediction_summary = ""
    final_summary = ""
    
    for log in student_logs:
        log_type = log.get('log_type')
        data = log.get('data', {})
        
        if log_type == 'prediction_chat':
            prediction_chats.append({
                'user': data.get('user_message', ''),
                'ai': data.get('ai_response', '')
            })
        elif log_type == 'reflection_chat':
            reflection_chats.append({
                'user': data.get('user_message', ''),
                'ai': data.get('ai_response', '')
            })
        elif log_type == 'prediction_summary':
            prediction_summary = data.get('summary', '')
        elif log_type == 'final_summary':
            final_summary = data.get('final_summary', '')
    
    print(f"予想対話数: {len(prediction_chats)}, 考察対話数: {len(reflection_chats)}")
    
    # 強化された分析プロンプト作成
    analysis_prompt = f"""小学4年理科学習記録の専門的分析をお願いします。

【学習情報】
学習単元: {unit}
学習者ID: {student_number}

【分析基準（学習指導要領準拠）】"""
    
    # 単元特性を分析基準に追加
    unit_info = analyze_unit_characteristics(unit)
    if unit_info:
        analysis_prompt += f"""
単元の見方・考え方: {unit_info.get('見方・考え方', '')}
重点的言語活動: {', '.join(unit_info.get('重点活動', []))}
生活経験関連: {', '.join(unit_info.get('生活経験', []))}
キーワード: {', '.join(unit_info.get('キーワード', []))}
"""
    
    # ガイドライン情報を分析基準に追加
    analysis_prompt += f"""
{guidelines_context}

【学習記録】
◆予想段階の対話記録◆"""
    
    # 予想段階の記録（分析機能付き）
    for i, chat in enumerate(prediction_chats, 1):
        user_msg = chat['user']
        ai_msg = chat['ai'][:100] + "..." if len(chat['ai']) > 100 else chat['ai']
        
        # 児童発言の簡易分析
        student_analysis = analyze_student_response(user_msg, unit)
        analysis_prompt += f"""
対話{i}: 学習者「{user_msg}」→AI「{ai_msg}」
[分析] 理解度:{student_analysis['理解度']} 言語化:{student_analysis['言語化レベル']} 日常関連:{'○' if student_analysis['日常関連'] else '×'}"""
    
    if prediction_summary:
        analysis_prompt += f"\n\n予想段階まとめ: {prediction_summary}"
    
    # 考察段階の記録
    analysis_prompt += f"\n\n◆考察段階の対話記録◆"
    for i, chat in enumerate(reflection_chats, 1):
        user_msg = chat['user']
        ai_msg = chat['ai'][:100] + "..." if len(chat['ai']) > 100 else chat['ai']
        
        # 児童発言の簡易分析
        student_analysis = analyze_student_response(user_msg, unit)
        analysis_prompt += f"""
対話{i}: 学習者「{user_msg}」→AI「{ai_msg}」
[分析] 理解度:{student_analysis['理解度']} 言語化:{student_analysis['言語化レベル']} 概念理解:{'○' if student_analysis['概念理解'] else '×'}"""
    
    if final_summary:
        analysis_prompt += f"\n\n考察段階まとめ: {final_summary}"
    
    analysis_prompt += """

【専門的分析項目】
★言語活動の質的評価★
1. 思考の言語化レベル（感覚→観察→因果→一般化の段階）
2. 見方・考え方の習得状況（単元固有の科学的思考）
3. 日常経験との関連付け能力
4. 産婆法による思考深化の効果

★学習到達度評価★
1. 知識・技能の理解度
2. 思考・判断・表現の発達度
3. 学びに向かう力の状況

★個別支援提案★
1. 言語化支援の具体的方法
2. 次回学習への橋渡し方法
3. 家庭学習での活用提案

詳細で建設的な分析をお願いします。"""

    try:
        print("OpenAI分析開始...")
        response = call_openai_with_retry(analysis_prompt)
        print(f"OpenAI応答: {response[:500]}...")
        
        # 応答から有用な情報を抽出
        return {
            "analysis_text": response,
            "unit": unit,
            "student_number": student_number,
            "prediction_count": len(prediction_chats),
            "reflection_count": len(reflection_chats),
            "has_prediction_summary": bool(prediction_summary),
            "has_final_summary": bool(final_summary)
        }
    
    except Exception as e:
        print(f"分析エラー: {str(e)}")
        return {
            'evaluation': f'分析エラー: {str(e)}',
            'prediction_analysis': {
                'daily_life_connection': 'エラーが発生しました',
                'prior_knowledge_use': 'エラーが発生しました',
                'reasoning_quality': 'エラーが発生しました'
            },
            'reflection_analysis': {
                'result_verbalization': 'エラーが発生しました',
                'prediction_comparison': 'エラーが発生しました',
                'daily_life_connection': 'エラーが発生しました',
                'scientific_understanding': 'エラーが発生しました'
            },
            'language_development': 'エラーが発生しました',
            'support_recommendations': ['システム管理者に連絡してください']
        }
        if json_match:
            json_str = json_match.group(0)
            print(f"抽出されたJSON: {json_str}")
            try:
                result = json.loads(json_str)
                print("方法1でJSON解析成功")
            except json.JSONDecodeError:
                print("方法1でJSON解析失敗")
        
        # 方法2: 複数行にわたるJSONを抽出
        if not result:
            lines = response.split('\n')
            json_lines = []
            in_json = False
            brace_count = 0
            
            for line in lines:
                if '{' in line and not in_json:
                    in_json = True
                    brace_count = line.count('{') - line.count('}')
                    json_lines = [line]
                elif in_json:
                    json_lines.append(line)
                    brace_count += line.count('{') - line.count('}')
                    if brace_count <= 0:
                        break
            
            if json_lines:
                json_str = '\n'.join(json_lines)
                print(f"方法2で抽出されたJSON: {json_str}")
                try:
                    result = json.loads(json_str)
                    print("方法2でJSON解析成功")
                except json.JSONDecodeError:
                    print("方法2でJSON解析失敗")
        
        # 成功した場合は結果を返す
        if result:
            print("分析完了")
            return result
        
        # 全て失敗した場合はフォールバック
        print("JSON抽出に失敗、フォールバックを使用")
        return {
            'evaluation': '言語活動の記録から対話への取り組み姿勢が確認できます',
            'language_support_needed': ['経験の言語化支援', '既習事項との関連付け支援', '結果の表現力向上支援'],
            'prediction_analysis': {
                'experience_connection': '日常経験の引き出しを継続的に支援',
                'prior_knowledge_use': '既習事項との関連付けを意識させる対話が必要'
            },
            'reflection_analysis': {
                'result_verbalization': '実験結果を自分の言葉で表現する練習が必要',
                'prediction_comparison': '予想との比較を言語化する支援が効果的',
                'daily_life_connection': '日常生活との関連を言葉で説明する機会を増やす'
            },
            'language_development': '対話を通じて徐々に言語化能力が向上しています'
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON解析エラー: {e}")
        # 言語活動支援観点のフォールバック応答
        return {
            'evaluation': '分析処理でエラーが発生しましたが、言語活動への取り組みは確認できます',
            'language_support_needed': ['システム安定化後の詳細な言語化支援', '個別対話支援の継続', '表現力向上のための指導'],
            'prediction_analysis': {
                'experience_connection': '経験の言語化について再評価が必要',
                'prior_knowledge_use': '既習事項の活用状況を確認中'
            },
            'reflection_analysis': {
                'result_verbalization': '結果の言語化について評価中',
                'prediction_comparison': '予想との比較の言語化について分析中',
                'daily_life_connection': '日常生活との関連付けについて評価予定'
            },
            'language_development': 'システム復旧後に言語活動の成長を詳細分析予定'
        }
    except Exception as e:
        print(f"分析エラー: {e}")
        return {
            'evaluation': f'システムエラーが発生しましたが、言語活動の記録は保存されています',
            'language_support_needed': ['システム調整後の分析再実施', '継続的な言語化支援', '個別対話指導の継続'],
            'prediction_analysis': {
                'experience_connection': f'エラー詳細: {str(e)[:30]}...',
                'prior_knowledge_use': 'データ解析後に詳細確認'
            },
            'reflection_analysis': {
                'result_verbalization': 'システム復旧後に評価実施',
                'prediction_comparison': '後日詳細分析予定',
                'daily_life_connection': '包括的評価を後日実施'
            },
            'language_development': 'システム安定後に言語活動の変化を分析'
        }
    
    try:
        analysis_result = call_openai_with_retry(analysis_prompt)
        
        # JSONパースを試行
        try:
            # JSONの前後の余分なテキストを除去
            start_idx = analysis_result.find('{')
            end_idx = analysis_result.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = analysis_result[start_idx:end_idx]
                result = json.loads(json_str)
                return result
            else:
                raise ValueError("JSON形式が見つかりません")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON解析エラー: {e}")
            print(f"レスポンス: {analysis_result}")
            return {
                'evaluation': '分析中にエラーが発生しました',
                'strengths': ['分析データを確認中'],
                'improvements': ['システム側で調整が必要'],
                'score': 5,
                'thinking_process': '評価中',
                'engagement': '評価中',
                'scientific_understanding': '評価中'
            }
    except Exception as e:
        print(f"分析エラー: {e}")
        return {
            'evaluation': 'AI分析でエラーが発生しました',
            'strengths': ['学習に取り組んでいます'],
            'improvements': ['継続的な学習'],
            'score': 5,
            'thinking_process': 'システムエラー',
            'engagement': 'システムエラー', 
            'scientific_understanding': 'システムエラー'
        }

def analyze_class_trends(logs, unit=None):
    """クラス全体の学習傾向をOpenAIで分析（指導案考慮）"""
    if unit:
        # 特定単元の分析
        unit_logs = [log for log in logs if log.get('unit') == unit]
        students = set(log.get('student_number') for log in unit_logs)
        analysis_unit = unit
    else:
        # 全体の分析
        unit_logs = logs
        students = set(log.get('student_number') for log in logs)
        analysis_unit = "全単元"
    
    if not unit_logs or len(students) == 0:
        return {
            'overall_trend': '分析対象のデータがありません',
            'common_misconceptions': [],
            'effective_approaches': [],
            'recommendations': []
        }
    
    # 指導案の内容を取得（特定単元の場合）
    lesson_plan_context = ""
    if unit:
        lesson_plan_content = load_lesson_plan_content(unit)
        if lesson_plan_content:
            lesson_plan_preview = lesson_plan_content[:800]
            lesson_plan_context = f"""
指導案情報:
{lesson_plan_preview}

[指導案に基づく分析観点]
- 指導目標の達成状況
- 予想されていた課題や誤解の出現
- 指導計画との整合性
- 次回授業への示唆
"""
        else:
            lesson_plan_context = "※この単元の指導案は設定されていません。"
    
    # 学習データを要約
    summary_data = {}
    for student in students:
        student_logs = [log for log in unit_logs if log.get('student_number') == student]
        summary_data[student] = {
            'prediction_count': len([log for log in student_logs if log.get('log_type') == 'prediction_chat']),
            'reflection_count': len([log for log in student_logs if log.get('log_type') == 'reflection_chat']),
            'has_prediction': any(log.get('log_type') == 'prediction_summary' for log in student_logs),
            'has_final': any(log.get('log_type') == 'final_summary' for log in student_logs)
        }
    
    # よくある予想や考察のパターンを抽出
    predictions = []
    reflections = []
    
    for log in unit_logs:
        if log.get('log_type') == 'prediction_summary':
            predictions.append(log.get('data', {}).get('summary', ''))
        elif log.get('log_type') == 'final_summary':
            reflections.append(log.get('data', {}).get('final_summary', ''))
    
    analysis_prompt = f"""
クラス全体の学習状況を分析してください。

対象単元: {analysis_unit}
学習者数: {len(students)}人

{lesson_plan_context}

各学習者の状況:
"""
    
    for student, data in summary_data.items():
        analysis_prompt += f"学習者{student}: 予想{data['prediction_count']}回 考察{data['reflection_count']}回 "
        analysis_prompt += f"予想完了{'○' if data['has_prediction'] else '×'} 考察完了{'○' if data['has_final'] else '×'}\n"
    
    analysis_prompt += f"\n主な予想:\n"
    for i, pred in enumerate(predictions[:3], 1):  # 最大3つまで
        analysis_prompt += f"{i}. {pred[:50]}...\n"
    
    analysis_prompt += f"\n主な考察:\n"
    for i, ref in enumerate(reflections[:3], 1):  # 最大3つまで
        analysis_prompt += f"{i}. {ref[:50]}...\n"
    
    analysis_prompt += """
言語活動支援の観点からクラス全体の状況を分析してください。

【分析項目】
- overall_trend: クラス全体の言語活動の傾向（100文字程度）
- language_challenges: 児童が共通して抱える言語化の課題を3つ
- verbalization_level: 言語化能力のレベル（発展中/安定/要支援）
- dialogue_engagement: 対話への参加状況
- expression_growth: 表現力の成長状況を2つ

JSON形式で回答してください。
"""
    
    analysis_prompt += """
この学習状況について、以下の形式で分析結果をJSON形式で出力してください。

{
  "overall_trend": "クラス全体で言語活動に意欲的に取り組んでいます",
  "language_challenges": ["経験の言語化", "既習事項との関連付け", "結果の表現"],
  "verbalization_level": "発展中",
  "dialogue_engagement": "積極的に対話に参加しています",
  "expression_growth": ["自分の言葉での表現", "論理的な説明の向上"]
}
"""
    
    try:
        print("クラス分析開始...")
        analysis_result = call_openai_with_retry(analysis_prompt)
        print(f"クラス分析応答（前500文字）: {repr(analysis_result[:500])}")
        print(f"クラス分析応答（後500文字）: {repr(analysis_result[-500:])}")
        
        # 複数の方法でJSONを抽出
        result = None
        
        # 方法1: 通常の正規表現
        import re
        json_match = re.search(r'\{.*?\}', analysis_result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            print(f"クラス分析抽出JSON: {json_str}")
            try:
                result = json.loads(json_str)
                print("クラス分析方法1でJSON解析成功")
            except json.JSONDecodeError:
                print("クラス分析方法1でJSON解析失敗")
        
        # 方法2: 複数行JSON抽出
        if not result:
            lines = analysis_result.split('\n')
            json_lines = []
            in_json = False
            brace_count = 0
            
            for line in lines:
                if '{' in line and not in_json:
                    in_json = True
                    brace_count = line.count('{') - line.count('}')
                    json_lines = [line]
                elif in_json:
                    json_lines.append(line)
                    brace_count += line.count('{') - line.count('}')
                    if brace_count <= 0:
                        break
            
            if json_lines:
                json_str = '\n'.join(json_lines)
                print(f"クラス分析方法2で抽出されたJSON: {json_str}")
                try:
                    result = json.loads(json_str)
                    print("クラス分析方法2でJSON解析成功")
                except json.JSONDecodeError:
                    print("クラス分析方法2でJSON解析失敗")
        
        # 成功した場合は結果を返す
        if result:
            print("クラス分析完了")
            return result
            
        # 全て失敗した場合はフォールバック
        print("クラス分析JSON抽出に失敗、フォールバックを使用")
        return {
            'overall_trend': 'クラス全体として言語活動に意欲的に取り組んでいます',
            'language_challenges': ['経験の言語化', '既習事項との関連付け', '結果の表現力'],
            'verbalization_level': '発展中',
            'dialogue_engagement': '積極的に対話に参加している状況です',
            'expression_growth': ['自分の言葉での表現向上', '思考の言語化進展']
        }
    except Exception as e:
        print(f"クラス分析エラー: {e}")
        return {
            'overall_trend': '言語活動の分析でエラーが発生しました',
            'language_challenges': ['分析データ不足'],
            'verbalization_level': 'システムエラー',
            'dialogue_engagement': 'システムエラー',
            'expression_growth': ['システム調整']
        }

@app.route('/teacher/analysis')
@require_teacher_auth
def teacher_analysis():
    """学習分析ダッシュボード"""
    # デフォルト日付を最新のログがある日付に設定
    available_dates = get_available_log_dates()
    default_date = available_dates[0]['raw'] if available_dates else datetime.now().strftime('%Y%m%d')
    
    date = request.args.get('date', default_date)
    unit = request.args.get('unit', '')
    
    logs = load_learning_logs(date)
    
    # クラス全体の傾向分析
    class_analysis = analyze_class_trends(logs, unit if unit else None)
    
    # 単元別の学習者リスト
    unit_students = {}
    for log in logs:
        log_unit = log.get('unit')
        student = log.get('student_number')
        if log_unit and student:
            if log_unit not in unit_students:
                unit_students[log_unit] = set()
            unit_students[log_unit].add(student)
    
    # 各単元の学習者を配列に変換
    for unit_name in unit_students:
        unit_students[unit_name] = sorted(list(unit_students[unit_name]))
    
    return render_template('teacher/analysis.html',
                         class_analysis=class_analysis,
                         unit_students=unit_students,
                         units=UNITS,
                         current_date=date,
                         current_unit=unit,
                         available_dates=available_dates,
                         teacher_id=session.get('teacher_id'))

@app.route('/teacher/analysis/api/student', methods=['POST'])
@require_teacher_auth
def api_student_analysis():
    """学生分析のAPI（AJAX用）"""
    data = request.get_json()
    student_number = data.get('student_number')
    unit = data.get('unit')
    
    # デフォルト日付を最新のログがある日付に設定
    available_dates = get_available_log_dates()
    default_date = available_dates[0]['raw'] if available_dates else datetime.now().strftime('%Y%m%d')
    
    date = data.get('date', default_date)
    
    logs = load_learning_logs(date)
    analysis = analyze_student_learning(student_number, unit, logs)
    
    return jsonify(analysis)

@app.route('/teacher/analysis/api/class', methods=['POST'])
@require_teacher_auth
def api_class_analysis():
    """クラス分析のAPI（AJAX用）"""
    data = request.get_json()
    unit = data.get('unit')
    
    # デフォルト日付を最新のログがある日付に設定
    available_dates = get_available_log_dates()
    default_date = available_dates[0]['raw'] if available_dates else datetime.now().strftime('%Y%m%d')
    
    date = data.get('date', default_date)
    
    logs = load_learning_logs(date)
    analysis = analyze_class_trends(logs, unit if unit else None)
    
    return jsonify(analysis)

def get_available_log_dates():
    """利用可能なログファイルの日付一覧を取得"""
    import os
    import glob
    
    log_files = glob.glob("logs/learning_log_*.json")
    dates = []
    
    for file in log_files:
        # ファイル名から日付を抽出
        filename = os.path.basename(file)
        if filename.startswith('learning_log_') and filename.endswith('.json'):
            date_str = filename[13:-5]  # learning_log_YYYYMMDD.json
            if len(date_str) == 8 and date_str.isdigit():
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                dates.append({'raw': date_str, 'formatted': formatted_date})
    
    # 日付でソート（新しい順）
    dates.sort(key=lambda x: x['raw'], reverse=True)
    return dates

# プロンプト管理機能
@app.route('/teacher/prompts')
@require_teacher_auth
def teacher_prompts():
    """プロンプト管理ページ"""
    return render_template('teacher/prompts.html', 
                         units=UNITS,
                         teacher_id=session.get('teacher_id'))

@app.route('/teacher/prompts/<unit>')
@require_teacher_auth
def teacher_prompt_edit(unit):
    """特定単元のプロンプト編集ページ"""
    if unit not in UNITS:
        flash('存在しない単元です', 'error')
        return redirect(url_for('teacher_prompts'))
    
    # 現在のプロンプト内容を読み込み
    try:
        with open(f'prompts/{unit}.md', 'r', encoding='utf-8') as f:
            current_content = f.read()
    except FileNotFoundError:
        # ファイルが存在しない場合はテンプレートをコピー
        try:
            with open('prompts/template.md', 'r', encoding='utf-8') as f:
                current_content = f.read()
        except FileNotFoundError:
            current_content = "# プロンプトテンプレートが見つかりません"
    
    return render_template('teacher/prompt_edit.html',
                         unit=unit,
                         content=current_content,
                         teacher_id=session.get('teacher_id'))

@app.route('/teacher/prompts/<unit>/save', methods=['POST'])
@require_teacher_auth
def teacher_prompt_save(unit):
    """プロンプトを保存"""
    if unit not in UNITS:
        return jsonify({'error': 'Invalid unit'}), 400
    
    content = request.json.get('content', '')
    
    try:
        # プロンプトディレクトリが存在しない場合は作成
        os.makedirs('prompts', exist_ok=True)
        
        # ファイルに保存
        with open(f'prompts/{unit}.md', 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True, 'message': 'プロンプトを保存しました'})
    
    except Exception as e:
        return jsonify({'error': f'保存に失敗しました: {str(e)}'}), 500

@app.route('/teacher/prompts/test', methods=['POST'])
@require_teacher_auth
def teacher_prompt_test():
    """プロンプトをテスト"""
    data = request.json
    unit = data.get('unit')
    content = data.get('content', '')
    test_message = data.get('message', 'テストメッセージです')
    
    if unit not in UNITS:
        return jsonify({'error': 'Invalid unit'}), 400
    
    try:
        # 編集中のプロンプトを使用してテスト
        test_prompt = f"""{content}

現在の学習単元: {unit}
課題: テスト用の課題文です
対話回数: 1回目

学習者からのメッセージ: {test_message}

次の質問を普通の文章で1文で書いてください："""
        
        # OpenAI APIでテスト
        response = call_openai_with_retry(test_prompt)
        clean_response = extract_message_from_json_response(response)
        clean_response = remove_markdown_formatting(clean_response)
        
        return jsonify({
            'success': True,
            'response': clean_response,
            'prompt_preview': content[:200] + '...' if len(content) > 200 else content
        })
    
    except Exception as e:
        return jsonify({'error': f'テストに失敗しました: {str(e)}'}), 500

# 指導要領・資料管理機能
@app.route('/teacher/guidelines')
@require_teacher_auth
def teacher_guidelines():
    """指導要領・資料管理ページ"""
    return render_template('teacher/guidelines.html',
                         teacher_id=session.get('teacher_id'))

@app.route('/teacher/guidelines/upload', methods=['POST'])
@require_teacher_auth
def upload_guidelines():
    """指導要領・資料のアップロード"""
    try:
        document_type = request.form.get('document_type')
        title = request.form.get('title')
        description = request.form.get('description', '')
        file = request.files.get('file')
        
        if not file or not file.filename:
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'PDFファイルのみ対応しています'}), 400
        
        # ファイルサイズチェック（16MB）
        if len(file.read()) > 16 * 1024 * 1024:
            return jsonify({'error': 'ファイルサイズが16MBを超えています'}), 400
        
        file.seek(0)  # ファイルポインタをリセット
        
        # ディレクトリ作成
        guidelines_dir = 'guidelines'
        os.makedirs(guidelines_dir, exist_ok=True)
        
        # ファイル名を安全にする
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(guidelines_dir, safe_filename)
        
        # ファイル保存
        file.save(filepath)
        
        # ファイルの内容を読み込み（現在はMarkdown形式のみ対応）
        try:
            # アップロードされたファイルがMarkdown形式と仮定して処理
            content = f"アップロード済みファイル: {filename}\n"
            content += f"アップロード日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += "注意: 現在はMarkdown形式の指導要領のみ対応しています。\n"
        except Exception as e:
            content = f"ファイル処理エラー: {str(e)}"
        
        # インデックスファイルに追加
        index_file = os.path.join(guidelines_dir, 'guidelines_index.json')
        
        # 既存のインデックスを読み込み
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                guidelines_index = json.load(f)
        else:
            guidelines_index = {}
        
        # 新しい文書情報を追加
        doc_id = str(uuid.uuid4())
        guidelines_index[doc_id] = {
            'type': document_type,
            'title': title,
            'description': description,
            'filename': safe_filename,
            'filepath': filepath,
            'content': content[:1000],  # 最初の1000文字のみ保存
            'full_content': content,  # 全文は別途保存
            'uploaded_at': datetime.now().isoformat(),
            'uploaded_by': session.get('teacher_id')
        }
        
        # インデックスファイルに保存
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(guidelines_index, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': '資料をアップロードしました',
            'document_id': doc_id
        })
    
    except Exception as e:
        return jsonify({'error': f'アップロードに失敗しました: {str(e)}'}), 500

@app.route('/teacher/guidelines/list')
@require_teacher_auth
def list_guidelines():
    """アップロード済み資料一覧"""
    try:
        index_file = 'guidelines/guidelines_index.json'
        
        if not os.path.exists(index_file):
            return jsonify({'documents': []})
        
        with open(index_file, 'r', encoding='utf-8') as f:
            guidelines_index = json.load(f)
        
        # 文書一覧を作成（IDを含める）
        documents = []
        for doc_id, doc_info in guidelines_index.items():
            doc_info['id'] = doc_id
            documents.append(doc_info)
        
        # 日付順にソート（新しい順）
        documents.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
        
        return jsonify({'documents': documents})
    
    except Exception as e:
        return jsonify({'error': f'資料一覧の取得に失敗しました: {str(e)}'}), 500

@app.route('/teacher/guidelines/<doc_id>/delete', methods=['DELETE'])
@require_teacher_auth
def delete_guidelines(doc_id):
    """資料の削除"""
    try:
        index_file = 'guidelines/guidelines_index.json'
        
        if not os.path.exists(index_file):
            return jsonify({'error': '資料が見つかりません'}), 404
        
        with open(index_file, 'r', encoding='utf-8') as f:
            guidelines_index = json.load(f)
        
        if doc_id not in guidelines_index:
            return jsonify({'error': '資料が見つかりません'}), 404
        
        # ファイルを削除
        filepath = guidelines_index[doc_id]['filepath']
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # インデックスから削除
        del guidelines_index[doc_id]
        
        # インデックスファイルを更新
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(guidelines_index, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': '資料を削除しました'})
    
    except Exception as e:
        return jsonify({'error': f'削除に失敗しました: {str(e)}'}), 500

@app.route('/teacher/student/<student_number>')
@require_teacher_auth
def student_detail(student_number):
    """学生の詳細ログページ"""
    unit = request.args.get('unit', '')
    
    # デフォルト日付を最新のログがある日付に設定
    available_dates = get_available_log_dates()
    default_date = available_dates[0]['raw'] if available_dates else datetime.now().strftime('%Y%m%d')
    selected_date = request.args.get('date', default_date)
    
    # 学習ログを読み込み
    logs = load_learning_logs(selected_date)
    
    # 該当する学生のログを抽出
    student_logs = [log for log in logs if 
                   log.get('student_number') == student_number and 
                   (not unit or log.get('unit') == unit)]
    
    print(f"学生{student_number}のログ検索結果: {len(student_logs)}件 (単元: {unit}, 日付: {selected_date})")
    
    if not student_logs:
        flash(f'学生{student_number}番のログがありません。日付や単元を変更してお試しください。', 'warning')
    
    # 分析結果を取得
    analysis = analyze_student_learning(student_number, unit, logs) if student_logs else None
    
    # 単元一覧を取得（フィルター用）
    all_units = list(set([log.get('unit') for log in logs if log.get('unit')]))
    
    return render_template('teacher/student_detail.html',
                         student_number=student_number,
                         unit=unit,
                         current_unit=unit,
                         current_date=selected_date,
                         logs=student_logs,
                         analysis=analysis,
                         available_dates=available_dates,
                         units_data={unit_name: {} for unit_name in all_units},
                         teacher_id=session.get('teacher_id', 'teacher'))

if __name__ == '__main__':
    app.run(debug=True, port=5014)