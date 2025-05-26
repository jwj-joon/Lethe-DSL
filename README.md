# Lethe-DSL
# Lethe DSL: A Domain-Specific Language for Affective Memory Modulation
# Lethe DSL: 감정 기반 기억 변조를 위한 도메인 특화 언어

![Lethe DSL Banner - Placeholder Image if you have one later]
---

## 1. Introduction
## 1. 소개

**Lethe** is a **Domain-Specific Language (DSL)** designed to model and control memory in artificial agents through affective cues. Inspired by human selective forgetting and emotional salience, Lethe enables explicit representation and modulation of memory decay, emotional states, and contextual relevance.

Unlike traditional AI memory systems that indiscriminately store information or rely on fixed buffers, Lethe facilitates selective memory retention and forgetting based on emotional importance, trustworthiness, repetition, and time. It is a linguistic embodiment of affective memory control.

---

**Lethe**는 인공 에이전트의 기억을 감정적 단서(affective cues)를 통해 모델링하고 제어하기 위해 설계된 **도메인 특화 언어(DSL)**입니다. 인간의 선택적 망각(selective forgetting)과 감정적 중요성(emotional salience)에 영감을 받아, Lethe는 기억 감쇠(memory decay), 감정 상태(emotional state), 맥락적 관련성(contextual relevance)을 명시적으로 표현하고 변조할 수 있도록 합니다.

기존의 AI 메모리 시스템이 정보를 무분별하게 저장하거나 고정된 버퍼에 의존하는 것과 달리, Lethe는 감정적 중요도, 신뢰도, 반복성, 시간에 기반한 선택적인 기억 유지 및 망각을 가능하게 합니다. 이는 감정 기반 기억 제어의 언어적 구현체입니다.

---

## 2. Design Philosophy
## 2. 설계 철학

Lethe is built upon the premise that memory is not static, but **dynamic and affect-driven**. Its syntax and semantics are derived from the following principles:

* **Emotional states serve as triggers**: Such as sadness, anxiety, or trust.
* **Reward and Resolution Values**: Derived from interactions.
* **Time-based Decay**: Modulated by emotional intensity and repetition.
* **Conditional Routines**: Structure responses and forgetting behaviors.

The name 'Lethe' refers to the river of forgetting in Greek mythology — a fitting metaphor for a system designed to **forget by design**.

**Key Insight**: From the perspective of Lethe DSL, customizing GPT means designing the AI's emotional loops, decay structures, and trigger mechanisms differently. This is an attempt to program the AI's **internal emotional states and memory flow** itself, beyond merely adjusting its external behavior.

---

Lethe는 기억이 정적이지 않고, **역동적이며 감정에 의해 구동된다**는 전제 하에 구축되었습니다. 그 문법과 의미론은 다음 원칙들에서 파생됩니다:

* **감정 상태는 트리거 역할을 합니다**: 슬픔, 불안, 신뢰 등.
* **보상(Reward) 및 해상도(Resolution) 값**: 상호작용에서 도출됩니다.
* **시간 기반 감쇠**: 감정 강도와 반복에 의해 변조됩니다.
* **조건부 루틴**: 반응 및 망각 행동을 구조화합니다.

`Lethe`라는 이름은 그리스 신화 속 망각의 강에서 유래했습니다. 이는 **설계에 의한 망각**을 지향하는 시스템에 적합한 은유입니다.

**핵심 통찰**: GPT 맞춤화는 Lethe DSL 관점에서 볼 때, AI의 감정 루프와 감쇠(decay) 구조, 그리고 트리거 구조를 다르게 설계하는 것과 같습니다. 이는 AI의 외부 행동을 넘어 **내면의 감정 상태와 기억의 흐름 자체를 프로그래밍**하려는 시도입니다.

---

## 3. Core Language Concepts
## 3. 핵심 언어 개념

Lethe introduces a minimal yet expressive set of primitives:

* `state <emotion>`: Defines the current emotional context (e.g., `sadness`, `joy`, `trust`).
    * Each emotion has an `intensity` and a `decay_rate`.
* `memory <name> { emotion, reward, decay, repeat_count }`: Defines a memory unit.
    * Memories are linked to specific emotions, reward values, decay rates, and repetition counts.
* `on <trigger_condition> => <action>`: Defines reactive routines.
    * `on user_input contains "I'm sad" => activate(sadness, 0.5)`
    * `on sadness.intensity > 0.7 => trigger(anger, 0.4)`
    * `on trust < 0.4 => forget(past_mistake)`
    * `on recall(childhood_dog) => activate(joy, 0.3)`
    * `on user_speaks == "I'm stuck in this thought" => break_loop(user_loop)`

---

Lethe는 최소한의 표현력 있는 원시 요소를 도입합니다:

* `state <emotion>`: 현재 감정적 맥락을 정의합니다 (예: `sadness`, `joy`, `trust`).
    * 각 감정은 `intensity`(강도)와 `decay_rate`(감쇠율)를 가집니다.
* `memory <name> { emotion, reward, decay, repeat_count }`: 기억 단위를 정의합니다.
    * 기억은 특정 감정, 보상 값, 감쇠율, 그리고 반복 횟수와 연결됩니다.
* `on <trigger_condition> => <action>`: 반응형 루틴을 정의합니다.
    * `on user_input contains "I'm sad" => activate(sadness, 0.5)`
    * `on sadness.intensity > 0.7 => trigger(anger, 0.4)`
    * `on trust < 0.4 => forget(past_mistake)`
    * `on recall(childhood_dog) => activate(joy, 0.3)`
    * `on user_speaks == "I'm stuck in this thought" => break_loop(user_loop)`

---

## 4. Execution Model
## 4. 실행 모델

Lethe code is compiled into a C++-based affective state machine that controls memory weights, updates, and forgetting rules in real-time. Each `memory` block maintains:

* **`W(t)` (Current Weight)**: Current weight.
* **`λ` (Decay Rate)**: Decay rate based on emotion type.
* **Historical Reward Interactions**: Past reward interactions.
* **Dynamic Priority**: Dynamic priority during memory access.

Like human memory, Lethe operates as a **"variable affective memory graph"** where memory order is dynamically reordered in real-time based on emotional intensity, trigger relationships, and loop conditions, rather than a purely chronological list. An `EmotionPriorityQueue` ensures that the most important or actively triggered emotions/memories are processed first.

All core computations, real-time management, and efficient data structure processing (`std::priority_queue` etc.) are handled by the **C++ backend**. Python handles DSL parsing, initial setup and rule delivery to the C++ core, higher-level system integration, simulation control, and visualization.

---

Lethe 코드는 C++ 기반의 감정 상태 머신으로 컴파일되어 기억 가중치, 업데이트, 망각 규칙을 실시간으로 제어합니다. 각 `memory` 블록은 다음을 유지합니다:

* **`W(t)` (현재 가중치)**: 현재 가중치.
* **`λ` (감쇠율)**: 감정 유형에 따른 감쇠율.
* **Historical Reward Interactions (과거 보상 상호작용)**: 과거 보상 상호작용.
* **Dynamic Priority (동적 우선순위)**: 기억 접근 시 동적 우선순위.

인간의 기억처럼, Lethe는 **시간순 리스트가 아닌 감정 강도, 트리거 관계, 루프 조건에 따라 기억 순서가 실시간으로 재정렬되는 '가변적 감정 기억 그래프'**처럼 작동합니다. `EmotionPriorityQueue`를 통해 현재 가장 중요하거나 활성화되어야 할 감정/기억이 우선적으로 처리됩니다.

이 모든 핵심 계산, 실시간 관리, 효율적인 자료구조 처리 (`std::priority_queue` 등)는 **C++ 백엔드**에서 담당합니다. Python은 DSL 파싱, C++ 코어의 초기 설정 및 규칙 전달, 상위 레벨 시스템 통합 및 시뮬레이션 제어, 시각화 등을 담당합니다.

---

## 5. Use Cases
## 5. 활용 사례

Lethe goes beyond simple emotion management, applying to various fields where AI can feel **"emotionally alive"**:

* **Emotion-Driven AI Agents**: Persona control for AI chatbots, digital therapeutic companions, emotionally aware educational systems.
* **Dynamic NPC Behavior**: In games, NPCs exhibit complex, human-like behaviors that are unpredictable yet based on emotional logic.
* **Hyper-Personalized Open Worlds**: The game world's NPCs, environment, and storylines dynamically change in real-time based on the player's emotional footprint, offering a unique "my own" game experience.
* **Deepened Human-AI Interaction**: AI understands user emotions and remembers/forgets accordingly, fostering deeper empathy and trust.

---

Lethe는 단순히 감정을 관리하는 것을 넘어, **AI가 '감정적으로 살아있는' 존재처럼 느껴지게 하는 다양한 분야**에 적용될 수 있습니다:

* **감정 기반 AI 에이전트**: AI 챗봇의 페르소나 제어, 디지털 치료 동반자, 감정 인식 교육 시스템.
* **동적인 NPC 행동**: 게임 내 NPC들이 예측 불가능하지만 감정적 논리에 기반한 복잡하고 인간적인 행동을 보입니다.
* **초개인화된 오픈월드**: 플레이어의 감정적 발자취에 따라 NPC, 환경, 그리고 스토리라인이 실시간으로 변화하여 '나만의' 게임 경험을 제공합니다.
* **인간-AI 상호작용의 심화**: AI가 사용자의 감정을 이해하고 이에 따라 기억하고 망각함으로써 더 깊은 공감과 신뢰를 형성합니다.

---

## 6. The Author's Declaration
## 6. 저자의 선언

---

This project is authored by **Wonjun Jung**.
The origin of its philosophy and structure stems entirely from my own thought process,
with GPT and Gemini serving as collaborative assistants in structuring and implementing this philosophy.
Lethe DSL began as an attempt to understand and structure human emotions.
It started from a moment of casual curiosity, and now it has become a language.
It sounds funny, but it is my sincere truth.

---

이 프로젝트의 저자는 **정원준**입니다.
철학과 구조의 원천은 전적으로 제 사고에서 출발했고,
GPT와 Gemini는 그 철학을 구조화하고 구현하는 데 협력한 조력자였습니다.
Lethe DSL은 인간의 감정을 이해하고 구조화하려는 시도에서 시작됐습니다.
그 시작은 심심함이었고, 지금은 하나의 언어가 되었습니다.
웃기지만 진심입니다.

---

## 7. License
## 7. 라이선스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

이 프로젝트는 MIT 라이선스에 따라 라이선스가 부여됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하십시오.

---

## 8. Support Lethe DSL
## 8. Lethe DSL 후원하기

If you find this project valuable and wish to support its development, you can sponsor the author here:

---

이 프로젝트가 가치 있다고 생각하시고 개발을 지원하고 싶으시다면, 여기에서 저자를 후원하실 수 있습니다:

[Sponsor on GitHub](https://github.com/sponsors/jwj-joon) ---
