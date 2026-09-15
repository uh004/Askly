# Askly 검증 운영 계획

## 결론

기존 Dataset은 삭제하지 않고 **Regression Set**으로 보존한다. 새로 만든 합성·비식별
30개 Case는 **Final Holdout Benchmark**로 사용한다. 개발 중에는 Regression만
반복 실행하고, Final Holdout은 Reference와 정책 기대값을 먼저 확정한 다음 최종
버전에만 실행한다.

30개는 포트폴리오용 1차 Benchmark로는 현실적인 규모지만 전체 사용자·직무에 대한
성능 보장은 아니다. 결과를 발표할 때 반드시 Case 수와 구성을 함께 표기한다.

## Dataset 역할

| 구분 | 목적 | 결과를 본 뒤 수정 가능한가 |
|---|---|---|
| Regression | 기존 기능이 깨지지 않았는지 확인하고 Prompt·코드를 개선 | 가능 |
| Final Holdout | 개발에 쓰지 않은 사례에서 최종 일반화 성능 확인 | 불가 |

Final Holdout 결과를 보고 Prompt나 Router를 수정했다면 그 Dataset은 더 이상
Final Holdout이 아니다. Regression으로 이동하고 새로운 Holdout을 만들어야 한다.

## 최종 구성

| 대상 | Regression | Final Holdout | 실행 | 대표 지표 |
|---|---:|---:|---:|---|
| 질문 생성 | 30 | 30 (INITIAL/FOLLOW_UP/NEXT 각 10) | Case당 3회 | Groundedness / JD Relevance / Personalization |
| 답변 평가 | 36 | 30 (GOOD/MEDIUM/POOR 각 10) | Case당 3회 | Overall MAE |
| Router | 18 | 30 (FOLLOW_UP/NEXT/END 각 10) | Case당 1회 | Policy Conformance / Boundary Scenario Pass |

질문 생성에는 일반 사례뿐 아니라 서류-JD 약한 일치, 정보 부족, 직전 답변의 누락,
기술 사용을 사실처럼 전제할 위험을 섞었다. 답변 평가는 길이가 아니라 관련성·
구체성·역할·행동·결과가 각각 약한 사례를 섞었다. Router는 69/70점, 질문 9/10개,
꼬리질문 1/2회와 여러 조건이 동시에 참인 우선순위 사례를 포함한다.

## 실행 전 고정해야 하는 것

1. 질문 생성의 Resume, JD, 이전 답변과 기대 질문 유형
2. 답변 평가의 6개 Reference Score
3. Router의 Expected Route와 정책 문서
4. 생성 모델, Judge 모델, Prompt 버전, 반복 횟수

답변 Reference Score는 Agent 결과를 보기 전에 사람이 검토·승인한다. 프로그램이
만든 초깃값은 Human Score라고 부르지 않고 **Rubric-authored Reference Score**라고
표기한다.

## 실행 순서

1. 전체 테스트와 세 Regression 로컬 검증을 실행한다.
2. 필요하면 Regression을 LangSmith에서 실행해 Prompt를 개선한다.
3. `python -m tools.review_answer_holdout`으로 답변 Reference를 직접 검토한다.
4. Prompt·정책·Reference를 동결한다.
5. 세 Final Holdout을 실행한다.
6. 평균 점수와 함께 반복 간 변동 및 실패 Case 2~3개를 기록한다.
7. 결과를 본 뒤 수정했다면 새 버전의 Holdout 없이는 “최종 성능”을 다시 주장하지 않는다.

## 해석 원칙

- 질문 생성 1~5점은 평균만 보지 말고 최저점과 실패 유형도 확인한다.
- 답변 MAE는 낮을수록 좋다. 예: MAE 0.6은 6개 항목에서 평균 0.6점 차이라는 뜻이다.
- Router는 결정 규칙이므로 고정 정책 Benchmark에서는 두 지표 모두 1.0이어야 한다.
- 실패 출력은 제외하지 않는다. 답변 평가의 잘못된 출력은 최대 오차로 계산하고,
  Router 예외는 ERROR로 기록한다.
