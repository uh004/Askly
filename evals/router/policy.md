# Router 기준 정책

현재 정책 상수:

- 최대 전체 질문 수: `10`
- 역량별 최대 FOLLOW_UP 수: `2`
- 답변 충분성 기준: `70점`

## 판단 우선순위

1. `question_count >= 10`이면 즉시 `END`
2. `missing_points`가 있거나 점수가 70점 미만이면 추가 확인 필요
3. 추가 확인이 필요하고 현재 역량의 FOLLOW_UP이 2회 미만이며 남은 역량용
   질문 슬롯이 보장되면 `FOLLOW_UP`
4. 확인하지 않은 다음 역량이 있으면 `NEXT`
5. 그 외에는 `END`

남은 역량용 슬롯 보장 조건:

```python
remaining_question_slots > len(remaining_competencies)
```

`followup_count`는 전체 누적값이고, 역량별 제한은 `interview_history`에서 현재
역량의 FOLLOW_UP 수를 별도로 계산하여 적용한다.
