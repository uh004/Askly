# Legacy evaluation datasets

이 폴더는 기존 검증셋의 원본을 보존한다. 삭제하거나 Final Holdout 결과에 맞춰
수정하지 않는다.

- `question_generation/`: 기존 6건 + v2 추가 24건
- `answer_evaluation/`: 기존 18건 + v2 추가 18건
- `router/`: 기존 Router 18건

현재 실행기는 이 원본을 직접 사용하지 않고 각 기능의
`datasets/regression_v1.jsonl`을 사용한다. `tools/build_eval_suites.py`는
보관 원본으로 Regression과 Final Holdout을 다시 만드는 개발용 도구이며, 답변
Reference 승인을 시작한 뒤에는 실행하지 않는다.
