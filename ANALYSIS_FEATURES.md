# 予想・考察分析機能ドキュメント

## 概要

予想・考察分析では、児童の言語使用の変化、特に**科学的語彙の獲得率**と**理科用語の含有率**を定量的に分析します。

## 主要分析指標

### 1. 理科用語含有率 (Science Term Ratio)

**定義：** テキストに含まれる理科用語の割合

```
含有率 = (検出された理科用語数) / (総単語数) × 100%
```

**例：**
- テキスト：「温度が高い時、空気が大きくなります」
- 理科用語：「温度」「空気」
- 含有率：2/7 ≈ 28.6%

### 2. 科学的語彙の獲得率 (Vocabulary Acquisition Rate)

**定義：** 対話を通じて生活語彙から科学的用語への変容を分析

#### 語彙変容パターン例：

| 生活語彙 | 理科用語への変容 | 段階 |
|---------|------------------|------|
| 「あつい」 | → 「温度が高い」 | 対話中盤～後盤 |
| 「ふとった」 | → 「体積が増えた」 | 対話後盤 |
| 「つめたい」 | → 「温度が低い」 | 反省段階 |
| 「膨らむ」 | → 「膨張する」「体積が増加する」 | 実験後の気づき |

### 3. 段階別分析

分析結果は以下の段階ごとに表示：

#### 予想段階 (Prediction Stage)
- 初期の理科用語含有率
- AIの指導による語彙変化の起点

#### 考察段階 (Reflection Stage)
- 実験後の理科用語含有率
- 最終的な語彙定着度

## 実装フロー

### Backend (`tools/analysis.py`)

```python
# 1. 理科用語辞書の定義
SCIENCE_TERMS = {
    "空気の温度と体積": {
        "temperature": ["温度", "あたたまり", "冷やす"],
        "volume": ["体積", "膨らむ", "膨張", "縮む"],
        "gas": ["空気", "気体"]
    },
    # ... 他単元
}

# 2. 生活語彙→理科用語マッピング
VOCABULARY_MAPPING = {
    "あつい": ["温度が高い", "温度が上がった"],
    "ふとった": ["体積が増えた", "膨らんだ"],
    # ... 他の語彙
}

# 3. 分析関数
def calculate_science_term_ratio(text, unit):
    """理科用語含有率を計算"""
    # 単語抽出 → 理科用語照合 → 比率計算

def detect_vocabulary_transition(first_half, second_half):
    """対話前半と後半の語彙変化を検出"""
    # 生活語彙→科学用語への変容を追跡

def analyze_conversation(conversation, unit):
    """対話全体を分析して段階別の語彙変容を追跡"""
    # 対話を前半・後半に分割
    # 各段階の理科用語含有率を計算
    # 語彙の変容を検出
```

### Frontend (`templates/teacher/analysis_dashboard.html`)

```html
<!-- 理科用語含有率の統計カード -->
<div class="stat-card">
    <h3>理科用語含有率</h3>
    <p id="scienceTermRatio">-</p>
</div>

<!-- 単元ごとの詳細分析 -->
<div class="metric science-metric">
    <label>理科用語含有率:</label>
    <span>28.6%</span>
</div>

<!-- 検出された理科用語の表示 -->
<div class="science-terms-section">
    <h4>検出された理科用語:</h4>
    <div class="science-terms-list">
        <span class="science-term-tag">温度</span>
        <span class="science-term-tag">体積</span>
        <span class="science-term-tag">膨張</span>
    </div>
</div>
```

## データベース項目

### 予想段階
- `prediction_chats`: 予想段階の対話数
- `science_term_ratio`: 理科用語含有率 (%)
- `science_terms`: 検出された理科用語リスト
- `vocabulary_transitions`: 語彙変容パターン

### 考察段階
- `reflection_chats`: 考察段階の対話数
- `science_term_ratio`: 理科用語含有率 (%)
- `science_terms`: 検出された理科用語リスト
- `vocabulary_transitions`: 語彙変容パターン

## API応答例

```json
{
  "success": true,
  "analysis": {
    "total_logs": 50,
    "prediction_chats": 25,
    "reflection_chats": 25,
    "text_analysis": {
      "空気の温度と体積": {
        "prediction": {
          "science_term_ratio": 22.5,
          "science_terms": ["温度", "体積", "膨らむ"],
          "keywords": [{"word": "空気", "count": 8}],
          "patterns": {
            "prediction_expressions": 12,
            "causal_expressions": 8,
            "comparison_expressions": 3
          }
        },
        "reflection": {
          "science_term_ratio": 35.8,
          "science_terms": ["温度", "体積", "膨張", "収縮"],
          "keywords": [{"word": "空気", "count": 12}]
        }
      }
    },
    "vocabulary_transitions": {
      "空気の温度と体積": [
        {
          "student": "2組25番",
          "transitions": [
            {
              "living_vocab": "あつい",
              "science_vocab": ["温度が高い"],
              "stage": "prediction"
            }
          ]
        }
      ]
    }
  }
}
```

## 用語定義（単元別）

### 空気の温度と体積
**科学用語：** 温度, 体積, 膨張, 収縮, 気体, 対流

**生活語彙マッピング：**
- 「あつい/さむい」→ 「温度が高い/低い」
- 「ふとった/やせた」→ 「体積が増えた/減った」
- 「膨らむ/縮む」→ 「膨張/収縮」

### 金属の温度と体積
**科学用語：** 温度, 体積, 膨張, 金属, 熱伝導

**生活語彙マッピング：**
- 「あたたまる」→ 「温度が上昇する」
- 「伸びる」→ 「体積が増える」

## 成功指標

| 指標 | 目標値 | 意義 |
|-----|-------|------|
| 予想段階 vs 考察段階の含有率差 | +10-15% | 対話・実験による語彙定着度 |
| 語彙変容検出数 | 単元あたり 3-5件 | 生活語彙から科学用語への変容 |
| 平均理科用語含有率 | 25-35% | 適切な科学的言語使用レベル |

## 今後の拡張予定

1. **埋め込みベースのクラスタリング**
   - 語意的に類似した表現の自動グループ化
   - 同義語・類義語の自動認識

2. **文法構造分析**
   - 複文化による表現の複雑化の追跡
   - 論理的つながりの定着度測定

3. **個別児童の語彙成長曲線**
   - 児童ごとの理科用語獲得スピード
   - 学習効果の定量化

4. **推奨プロンプト生成**
   - 特定の語彙定着が不足している児童への個別指導プロンプト
   - 段階的な語彙段階化戦略
