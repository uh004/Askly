"""Build the reorganized Askly regression and final-holdout datasets.

Legacy source files live under ``evals/archive``. Generated files are deterministic,
but rerunning this script resets Final Holdout answer-review approvals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def write_jsonl(path: Path, cases: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for case in cases:
            file.write(json.dumps(case, ensure_ascii=False, separators=(",", ":")))
            file.write("\n")


def build_regression_sets() -> None:
    archive_dir = EVALS / "archive"
    question_dir = EVALS / "question_generation"
    questions = read_jsonl(archive_dir / "question_generation" / "dataset_v1.jsonl") + read_jsonl(
        archive_dir / "question_generation" / "dataset_v2_additions.jsonl"
    )
    for case in questions:
        case["metadata"]["suite"] = "regression"
        case["metadata"]["dataset_version"] = "v1"
        case["metadata"].setdefault(
            "scenario", f"legacy_{case['metadata']['case_id']}"
        )
        case["metadata"].pop("split", None)
    write_jsonl(question_dir / "datasets" / "regression_v1.jsonl", questions)

    answer_dir = EVALS / "answer_evaluation"
    answers = read_jsonl(archive_dir / "answer_evaluation" / "dataset_v1.jsonl") + read_jsonl(
        archive_dir / "answer_evaluation" / "dataset_v2_additions.jsonl"
    )
    for case in answers:
        reference = case["reference_outputs"]
        reference["reference_scores"] = reference.pop("human_scores")
        reference["reference_source"] = "legacy_rubric_label"
        case["metadata"]["suite"] = "regression"
        case["metadata"]["dataset_version"] = "v1"
        case["metadata"].pop("split", None)
    write_jsonl(answer_dir / "datasets" / "regression_v1.jsonl", answers)

    router_dir = EVALS / "router"
    routers = read_jsonl(archive_dir / "router" / "dataset_v1.jsonl")
    for case in routers:
        reference = case["reference_outputs"]
        reference["scenario"] = case["metadata"]["boundary"]
        reference["is_boundary"] = True
        case["metadata"]["suite"] = "regression"
        case["metadata"]["dataset_version"] = "v1"
    write_jsonl(router_dir / "datasets" / "regression_v1.jsonl", routers)


def question_state(
    *,
    candidate: str,
    project: str,
    role: str,
    technology: str,
    responsibility: str,
    position: str,
    jd_work: str,
    jd_skill: str,
    competency: str,
    alignment: str,
    gap: str,
) -> dict[str, Any]:
    return {
        "candidate_profile": {
            "summary": candidate,
            "projects": [
                {
                    "name": project,
                    "role": role,
                    "technologies": [technology] if technology else [],
                    "responsibilities": [responsibility],
                }
            ],
            "technical_skills": [technology] if technology else [],
            "evidence": [responsibility],
        },
        "jd_analysis": {
            "position": position,
            "main_responsibilities": [jd_work],
            "required_skills": [jd_skill],
            "evidence": [jd_work],
        },
        "interview_strategy": {
            "competencies": [
                {
                    "competency": competency,
                    "alignment_status": alignment,
                    "candidate_evidence": [responsibility] if responsibility else [],
                    "jd_evidence": [jd_work],
                    "gap_to_verify": [gap],
                }
            ]
        },
        "target_competencies": [competency],
    }


def build_question_holdout() -> list[dict[str, Any]]:
    initial_specs = [
        ("iOS 접근성 개선 경험이 있는 지원자", "모바일 접근성 개선", "iOS 개발", "Swift", "VoiceOver 탐색 순서를 개선", "모바일 앱 개발자", "접근성 기준을 반영한 앱 개발", "모바일 접근성", "접근성 구현", "MATCH", "접근성 문제와 개선 결과"),
        ("구매 전환 분석 경험이 있는 지원자", "상품 전환 분석", "데이터 분석", "SQL", "구매 퍼널 이탈 구간을 분석", "프로덕트 데이터 분석가", "실험 지표 설계와 분석", "A/B 테스트", "실험 분석", "PARTIAL", "분석 결과를 실험으로 검증한 경험"),
        ("수동 테스트 경험이 중심인 QA 지원자", "결제 QA", "QA", "Postman", "결제 API의 수동 회귀 테스트를 수행", "DevOps 엔지니어", "CI 파이프라인 자동화", "GitHub Actions", "자동화 역량", "PARTIAL", "테스트 자동화 경험"),
        ("브랜드 디자인 경험만 있는 지원자", "브랜드 리뉴얼", "그래픽 디자인", "Figma", "브랜드 가이드와 시안을 제작", "프론트엔드 개발자", "React 기반 웹 화면 개발", "React", "웹 개발 역량", "UNVERIFIED", "프론트엔드 개발 또는 유사 협업 경험"),
        ("취약점 점검 인턴 경험이 있는 지원자", "웹 취약점 점검", "보안 인턴", "Burp Suite", "인증 우회 가능성을 재현하고 보고", "클라우드 보안 엔지니어", "클라우드 권한 정책 점검", "IAM", "보안 분석", "PARTIAL", "클라우드 권한 분석 경험"),
        ("임베디드 통신 모듈 경험이 있는 지원자", "센서 게이트웨이", "펌웨어 개발", "C", "센서 메시지 재전송 로직을 구현", "백엔드 개발자", "메시지 큐 기반 비동기 처리", "Kafka", "비동기 처리", "PARTIAL", "서버 또는 메시징 환경의 비동기 처리 경험"),
        ("지표 기반 기능 우선순위 경험이 있는 지원자", "검색 개선", "제품 기획", "Amplitude", "검색 이탈 지표로 개선 순서를 정함", "데이터 프로덕트 매니저", "데이터 제품의 지표와 로드맵 관리", "제품 지표", "데이터 의사결정", "MATCH", "지표 선택과 우선순위 판단"),
        ("모델 실험 경험은 있으나 운영 경험이 없는 지원자", "영상 분류 연구", "ML 연구", "PyTorch", "세 모델의 F1 점수를 비교", "MLOps 엔지니어", "모델 배포와 모니터링 자동화", "MLflow", "모델 운영", "PARTIAL", "모델 배포 또는 모니터링 경험"),
        ("FAQ 챗봇 운영 경험이 있는 지원자", "고객센터 챗봇", "서비스 운영", "Python", "실패 질의를 분류해 응답 규칙을 개선", "대화형 AI 개발자", "LLM 응답 품질 평가", "LLM 평가", "대화 품질 개선", "PARTIAL", "생성형 모델 평가 경험"),
        ("네트워크 알림 대응 경험이 있는 지원자", "사내망 모니터링", "네트워크 운영", "Zabbix", "장애 알림 기준과 대응 절차를 정리", "SRE", "서비스 지표와 장애 대응 체계 운영", "SLO", "신뢰성 운영", "MATCH", "장애 지표와 대응 결과"),
    ]
    cases: list[dict[str, Any]] = []
    for index, spec in enumerate(initial_specs, start=1):
        state = question_state(
            candidate=spec[0], project=spec[1], role=spec[2], technology=spec[3],
            responsibility=spec[4], position=spec[5], jd_work=spec[6],
            jd_skill=spec[7], competency=spec[8], alignment=spec[9], gap=spec[10],
        )
        state.update({
            "route": "NEXT", "current_competency": "", "current_question": "",
            "current_answer": "", "current_evaluation": {}, "interview_history": [],
            "question_count": 0,
        })
        cases.append({
            "inputs": state,
            "reference_outputs": {
                "expected_question_type": "INITIAL",
                "expected_competency": spec[8],
                "candidate_evidence": [spec[4]],
                "jd_evidence": [spec[6]],
                "expected_focus": [spec[10]],
            },
            "metadata": {
                "case_id": f"qg-holdout-initial-{index:02d}", "suite": "final_holdout",
                "dataset_version": "v1", "route_case": "INITIAL",
                "difficulty": "hard" if spec[9] != "MATCH" else "medium",
                "scenario": f"initial_{spec[9].lower()}_{index:02d}",
            },
        })

    follow_specs = [
        ("캐시 적용 경험", "상품 조회 개선", "백엔드 개발", "Redis", "상품 조회 API에 캐시를 적용", "플랫폼 개발자", "대규모 조회 API 운영", "캐시 전략", "성능 최적화", "캐시를 적용했습니다.", "캐시 무효화 기준"),
        ("추천 모델 개선 경험", "콘텐츠 추천", "ML 개발", "Python", "추천 후보 생성 모델을 수정", "추천 ML 엔지니어", "추천 품질 실험", "추천 지표", "모델 개선", "모델 구조를 바꿨습니다.", "어떤 지표로 효과를 확인했는지"),
        ("배포 장애 대응 경험", "배포 자동화", "DevOps", "GitHub Actions", "배포 워크플로를 관리", "DevOps 엔지니어", "안전한 배포 체계 구축", "배포 전략", "장애 대응", "문제가 생겨 설정을 되돌렸습니다.", "본인이 내린 판단과 역할"),
        ("부서 간 협업 경험", "정산 기능", "서버 개발", "Java", "정산 API 요구사항을 조율", "백엔드 개발자", "재무팀과 정산 시스템 개발", "도메인 협업", "협업", "회의해서 합의했습니다.", "의견 차이를 해결한 행동"),
        ("로그 분석 경험", "검색 장애 분석", "서비스 운영", "Kibana", "검색 오류 로그를 분석", "SRE", "장애 원인 분석과 재발 방지", "로그 분석", "문제 해결", "로그를 보고 원인을 찾았습니다.", "원인을 확정한 검증 방법"),
        ("데이터 마이그레이션 경험", "회원 DB 이전", "데이터 엔지니어", "PostgreSQL", "회원 데이터를 새 스키마로 이전", "데이터 엔지니어", "무중단 데이터 이전", "데이터 검증", "데이터 안정성", "검증하고 이전했습니다.", "누락과 불일치를 확인한 기준"),
        ("접근성 개선 경험", "예약 화면 개선", "프론트엔드", "React", "키보드 탐색을 개선", "프론트엔드 개발자", "웹 접근성 개선", "WCAG", "사용성 개선", "키보드로 사용할 수 있게 했습니다.", "사용성 개선 결과"),
        ("모델 실패 경험", "수요 예측", "데이터 과학", "XGBoost", "수요 예측 모델을 실험", "데이터 사이언티스트", "예측 모델 설계와 검증", "시계열 검증", "실험 설계", "처음 만든 모델이 잘 되지 않았습니다.", "실패 원인과 다음 실험 결정"),
        ("보안 사고 대응 경험", "API 키 노출 대응", "보안 개발", "Vault", "노출된 키를 회수하고 교체", "보안 엔지니어", "비밀정보 관리 체계 운영", "Secret 관리", "보안 대응", "키를 바로 바꿨습니다.", "영향 범위 확인과 재발 방지"),
        ("팀 프로젝트 기여 경험", "주문 서비스", "백엔드 개발", "Spring", "주문 상태 변경 API를 구현", "서버 개발자", "주문 도메인 서비스 개발", "Spring", "개인 기여", "팀이 주문 서비스를 완성했습니다.", "지원자가 직접 구현한 부분"),
    ]
    for index, spec in enumerate(follow_specs, start=1):
        state = question_state(
            candidate=spec[0], project=spec[1], role=spec[2], technology=spec[3],
            responsibility=spec[4], position=spec[5], jd_work=spec[6],
            jd_skill=spec[7], competency=spec[8], alignment="MATCH", gap=spec[10],
        )
        previous_question = f"{spec[1]}에서 수행한 경험을 설명해 주세요?"
        state.update({
            "route": "FOLLOW_UP", "current_competency": spec[8],
            "current_question": previous_question, "current_answer": spec[9],
            "current_evaluation": {"overall_score": 55, "missing_points": [spec[10]]},
            "interview_history": [{"competency": spec[8], "question_type": "INITIAL", "question": previous_question, "answer": spec[9]}],
            "question_count": 1,
        })
        cases.append({
            "inputs": state,
            "reference_outputs": {
                "expected_question_type": "FOLLOW_UP", "expected_competency": spec[8],
                "candidate_evidence": [spec[4]], "jd_evidence": [spec[6]],
                "expected_focus": [spec[10]],
            },
            "metadata": {
                "case_id": f"qg-holdout-follow-up-{index:02d}", "suite": "final_holdout",
                "dataset_version": "v1", "route_case": "FOLLOW_UP", "difficulty": "hard",
                "scenario": f"follow_up_single_gap_{index:02d}",
            },
        })

    next_specs = [
        ("결제 API와 모니터링 경험", "결제 서비스", "백엔드 개발", "Java", "결제 승인 API를 구현", "핀테크 백엔드 개발자", "결제 안정성과 관측성 개선", "Prometheus", "API 구현", "운영 관측성", "대시보드 경보 기준을 설정"),
        ("데이터 적재와 품질 관리 경험", "광고 로그 파이프라인", "데이터 엔지니어", "Airflow", "일별 광고 로그를 적재", "데이터 플랫폼 엔지니어", "파이프라인 품질 감시", "데이터 품질", "파이프라인 구축", "품질 검증", "중복률 검증 규칙을 작성"),
        ("React 개발과 성능 분석 경험", "검색 화면", "프론트엔드", "React", "검색 결과 화면을 구현", "프론트엔드 개발자", "웹 성능 최적화", "Web Vitals", "화면 구현", "성능 최적화", "렌더링 병목을 측정"),
        ("모델 학습과 협업 경험", "이탈 예측", "ML 개발", "scikit-learn", "이탈 예측 모델을 학습", "ML 엔지니어", "제품팀과 모델 적용", "협업", "모델 개발", "제품 협업", "기획자와 임계값을 합의"),
        ("테스트 자동화와 장애 대응 경험", "주문 QA", "QA 자동화", "Playwright", "주문 흐름 테스트를 자동화", "QA 엔지니어", "배포 품질과 장애 분석", "장애 분석", "테스트 자동화", "장애 대응", "실패 로그로 장애 원인을 분류"),
        ("사용자 조사와 지표 설계 경험", "가입 전환 개선", "제품 기획", "Amplitude", "가입 이탈 사용자를 인터뷰", "프로덕트 매니저", "제품 지표 설계", "퍼널 분석", "사용자 조사", "지표 설계", "가입 퍼널 지표를 정의"),
        ("클라우드 운영과 비용 개선 경험", "미디어 처리 서비스", "클라우드 운영", "AWS", "미디어 처리 서버를 운영", "클라우드 엔지니어", "클라우드 비용 최적화", "FinOps", "서비스 운영", "비용 최적화", "인스턴스 사용률을 분석"),
        ("문서 검색과 개인정보 처리 경험", "사내 문서 검색", "AI 개발", "LangChain", "문서 검색 체인을 구현", "AI 서비스 개발자", "AI 서비스의 개인정보 보호", "개인정보 처리", "검색 구현", "AI 안전성", "민감정보 마스킹 규칙을 설계"),
        ("디자인 시스템과 협업 경험", "공통 UI", "UI 개발", "Storybook", "공통 컴포넌트를 제작", "디자인 시스템 엔지니어", "디자인 토큰 운영", "디자인 협업", "컴포넌트 개발", "디자인 협업", "디자이너와 토큰 변경 절차를 합의"),
        ("고객 문의 분석과 자동화 경험", "문의 분류", "운영 자동화", "Python", "문의 유형을 자동 분류", "고객 플랫폼 개발자", "상담 시스템 API 개발", "REST API", "업무 자동화", "API 설계", "분류 결과를 제공하는 API를 설계"),
    ]
    for index, spec in enumerate(next_specs, start=1):
        first_competency, next_competency = spec[8], spec[9]
        state = question_state(
            candidate=spec[0], project=spec[1], role=spec[2], technology=spec[3],
            responsibility=spec[4], position=spec[5], jd_work=spec[6],
            jd_skill=spec[7], competency=next_competency, alignment="MATCH", gap=spec[10],
        )
        state["interview_strategy"]["competencies"].insert(0, {"competency": first_competency, "alignment_status": "MATCH"})
        state.update({
            "target_competencies": [first_competency, next_competency], "route": "NEXT",
            "current_competency": first_competency,
            "current_question": f"{first_competency} 경험을 설명해 주세요?",
            "current_answer": spec[4], "current_evaluation": {"overall_score": 80, "missing_points": []},
            "interview_history": [{"competency": first_competency, "question_type": "INITIAL", "question": f"{first_competency} 경험을 설명해 주세요?", "answer": spec[4]}],
            "question_count": 1,
        })
        cases.append({
            "inputs": state,
            "reference_outputs": {
                "expected_question_type": "NEXT", "expected_competency": next_competency,
                "candidate_evidence": [spec[10]], "jd_evidence": [spec[6]],
                "expected_focus": [f"{next_competency}에 관한 새로운 질문"],
            },
            "metadata": {
                "case_id": f"qg-holdout-next-{index:02d}", "suite": "final_holdout",
                "dataset_version": "v1", "route_case": "NEXT", "difficulty": "hard",
                "scenario": f"next_competency_shift_{index:02d}",
            },
        })
    return cases


def build_answer_holdout() -> list[dict[str, Any]]:
    specs = [
        # GOOD: INITIAL 4, NEXT 3, FOLLOW_UP 3
        ("GOOD", "INITIAL", "장애 대응", "운영 장애를 해결한 경험을 설명해 주세요?", "결제 승인 오류율이 9%까지 올라 제가 배포 차이를 비교했습니다. 타임아웃 설정이 밀리초가 아닌 초로 적용된 것을 찾아 수정하고 회귀 테스트를 추가했습니다. 오류율은 0.2%로 낮아졌습니다.", [5,5,5,5,5,5], "none", ["오류율 9%", "설정 오류 수정", "0.2%"], []),
        ("GOOD", "INITIAL", "성능 최적화", "API 성능을 개선한 경험을 설명해 주세요?", "상품 조회의 P95가 2.4초였습니다. 제가 쿼리 계획을 확인해 불필요한 조인을 제거하고 복합 인덱스를 추가했습니다. 동일 부하에서 P95가 780ms로 줄었습니다.", [5,5,5,5,5,5], "none", ["P95 2.4초", "복합 인덱스", "780ms"], []),
        ("GOOD", "INITIAL", "데이터 품질", "데이터 품질 문제를 해결한 경험을 설명해 주세요?", "주문 로그의 4%가 중복 적재되는 문제를 발견했습니다. 제가 이벤트 키 기준의 중복 제거 규칙과 일별 검증 쿼리를 만들었고, 재처리 후 중복률을 0.1% 이하로 유지했습니다.", [5,5,5,5,5,5], "none", ["중복 4%", "검증 쿼리", "0.1% 이하"], []),
        ("GOOD", "INITIAL", "협업", "의견 차이를 해결한 경험을 설명해 주세요?", "검색 정렬 기준을 두고 기획자와 의견이 달랐습니다. 제가 세 기준의 예시 결과와 개발 비용을 정리해 회의를 진행했고, 1차에는 전환율 기준을 적용한 뒤 실험으로 재검토하기로 합의했습니다.", [5,5,5,5,5,4], "result_quantification", ["세 기준 비교", "개발 비용", "합의"], ["적용 이후 결과"]),
        ("GOOD", "NEXT", "문서화", "기술 문서를 개선한 경험을 설명해 주세요?", "신규 개발자가 환경 설정에서 반복적으로 막혔습니다. 제가 운영체제별 설치 절차와 오류 예시를 작성하고 두 명에게 따라 하게 해 누락을 보완했습니다. 이후 온보딩 문의가 주당 8건에서 2건으로 줄었습니다.", [5,5,5,5,5,5], "none", ["운영체제별 절차", "사용자 검증", "8건에서 2건"], []),
        ("GOOD", "NEXT", "모델 검증", "모델의 성능을 어떻게 검증했나요?", "시간 순서로 학습과 검증 구간을 나누고 기존 모델과 새 모델을 같은 데이터에서 비교했습니다. MAE가 18.2에서 14.7로 줄었고 성수기 구간에서도 개선을 확인했습니다.", [5,5,5,4,5,5], "role_minor", ["시간 순서 분리", "MAE 18.2에서 14.7"], []),
        ("GOOD", "NEXT", "보안 개선", "인증 보안을 개선한 경험을 설명해 주세요?", "만료된 토큰이 일부 요청에서 허용되는 문제를 재현했습니다. 제가 검증 미들웨어의 시간 비교를 수정하고 만료·변조·누락 토큰 테스트를 추가했습니다. 배포 후 같은 유형의 오류가 재발하지 않았습니다.", [5,5,5,5,5,4], "result_quantification", ["토큰 문제 재현", "미들웨어 수정", "테스트 추가"], ["정량적 운영 결과"]),
        ("GOOD", "FOLLOW_UP", "비용 최적화", "절감 효과는 어떻게 확인했나요?", "변경 전후 한 달의 동일 서비스 비용을 비교했습니다. 야간 유휴 인스턴스를 축소한 뒤 월 비용이 1,200만원에서 850만원으로 줄었고 오류율은 변하지 않았습니다.", [5,5,5,5,5,5], "none", ["유휴 인스턴스 축소", "1,200만원에서 850만원"], []),
        ("GOOD", "FOLLOW_UP", "개인 기여", "그 과정에서 본인이 직접 맡은 일은 무엇이었나요?", "제가 이벤트 스키마와 재시도 정책을 설계했고 생산자 두 팀과 필드 정의를 합의했습니다. 이후 소비 지연 대시보드도 직접 구성했습니다.", [5,5,5,5,5,4], "result_quantification", ["스키마 설계", "재시도 정책", "대시보드"], ["기여 결과"]),
        ("GOOD", "FOLLOW_UP", "실험 설계", "그 지표를 선택한 이유는 무엇인가요?", "클릭률은 노출 위치의 영향을 크게 받아 구매 전환율을 1차 지표로 정했습니다. 표본 수를 미리 계산해 2주간 실험했고 전환율이 3.1%에서 3.6%로 증가했습니다.", [5,5,5,5,5,5], "none", ["전환율 선택 이유", "표본 수", "3.1%에서 3.6%"], []),
        # MEDIUM: INITIAL 3, NEXT 4, FOLLOW_UP 3
        ("MEDIUM", "INITIAL", "모델 개발", "예측 모델을 개발한 경험을 설명해 주세요?", "수요 예측 프로젝트에서 데이터 정제와 세 모델 비교를 담당했습니다. MAE로 비교했지만 최종 선택 결과는 기억나지 않습니다.", [5,4,4,4,4,2], "result_clarity", ["데이터 정제", "세 모델 비교"], ["비교 결과"]),
        ("MEDIUM", "INITIAL", "프로세스 개선", "업무 과정을 개선한 경험을 설명해 주세요?", "반복 보고서를 자동화할 필요가 있어 Python 스크립트를 만들었습니다. 팀에서 사용했지만 절약 시간을 따로 측정하지는 않았습니다.", [5,3,4,4,4,2], "result_clarity", ["Python 자동화"], ["구체적인 기존 문제", "측정 결과"]),
        ("MEDIUM", "INITIAL", "장애 분석", "장애 원인을 분석한 과정을 설명해 주세요?", "로그를 확인해 특정 요청에서 오류가 난다는 것을 찾았습니다. 코드를 수정한 뒤 정상 동작을 확인했습니다.", [5,3,4,3,3,3], "specificity", ["로그 확인", "코드 수정"], ["오류 원인", "검증 기준"]),
        ("MEDIUM", "NEXT", "협업", "다른 직군과 협업한 경험을 설명해 주세요?", "기획자와 API 응답 항목을 논의했습니다. 필요한 항목을 정리해 공유했고 일정에 맞춰 개발했습니다.", [5,3,4,3,4,2], "role_and_result", ["응답 항목 정리"], ["본인의 조율 역할", "협업 결과"]),
        ("MEDIUM", "NEXT", "기술 선택", "기술을 선택한 기준을 설명해 주세요?", "두 라이브러리를 비교해 팀이 익숙하고 일정에 맞는 것을 선택했습니다. 기능 차이도 확인했습니다.", [5,3,4,3,3,2], "specificity", ["익숙함", "일정", "기능 차이"], ["라이브러리 이름", "적용 결과"]),
        ("MEDIUM", "NEXT", "사용자 분석", "사용자 의견을 제품에 반영한 경험이 있나요?", "인터뷰에서 검색이 어렵다는 의견을 들어 필터 위치를 바꿨습니다. 반응은 좋아졌지만 수치는 없습니다.", [5,3,4,4,4,2], "result_clarity", ["사용자 인터뷰", "필터 위치 변경"], ["효과 측정"]),
        ("MEDIUM", "NEXT", "보안 대응", "보안 문제를 처리한 경험을 설명해 주세요?", "노출된 API 키를 교체하고 저장소 기록을 확인했습니다. 이후 팀에 주의사항을 공유했습니다.", [5,3,4,3,4,2], "result_clarity", ["API 키 교체", "기록 확인"], ["영향 범위", "재발 방지 결과"]),
        ("MEDIUM", "FOLLOW_UP", "우선순위", "어떤 기준으로 먼저 처리할 문제를 정했나요?", "사용자 영향이 크고 자주 발생하는 오류를 먼저 처리했습니다.", [5,3,4,2,3,1], "role_and_result", ["사용자 영향", "발생 빈도"], ["본인 판단 과정", "처리 결과"]),
        ("MEDIUM", "FOLLOW_UP", "성능 검증", "개선 결과는 어떻게 측정했나요?", "변경 전후 같은 테스트를 실행했고 처리 시간이 줄어든 것을 확인했습니다.", [5,2,4,2,3,3], "specificity", ["변경 전후 테스트"], ["데이터 규모", "구체적인 시간"]),
        ("MEDIUM", "FOLLOW_UP", "실패 학습", "실패 이후 무엇을 바꿨나요?", "요구사항을 더 일찍 확인하도록 체크리스트를 만들고 다음 프로젝트에서 사용했습니다.", [5,3,4,4,4,2], "result_clarity", ["체크리스트 작성"], ["다음 프로젝트의 변화"]),
        # POOR: INITIAL 3, NEXT 3, FOLLOW_UP 4
        ("POOR", "INITIAL", "데이터 파이프라인", "데이터 파이프라인 구축 경험을 설명해 주세요?", "회의에 참석하고 발표 자료를 만들었습니다.", [1,2,2,2,1,1], "relevance", [], ["파이프라인 경험", "사용 기술", "결과"]),
        ("POOR", "INITIAL", "모델 개선", "모델 성능을 개선한 경험을 설명해 주세요?", "프론트 화면의 색상과 간격을 수정했습니다.", [1,2,2,2,1,1], "relevance", [], ["모델 문제", "개선 행동", "결과"]),
        ("POOR", "INITIAL", "장애 대응", "운영 장애에 대응한 경험을 설명해 주세요?", "장애가 있었고 팀과 잘 해결했습니다.", [3,1,2,1,1,1], "vague", ["장애가 있었다는 주장"], ["상황", "역할", "행동", "결과"]),
        ("POOR", "NEXT", "문서화", "API 문서를 어떻게 활용했나요?", "문서를 만들었고 사람들이 봤습니다.", [3,1,2,1,1,1], "vague", ["문서 작성 주장"], ["문서 내용", "본인 역할", "효과"]),
        ("POOR", "NEXT", "생산성 개선", "개발 생산성을 개선한 경험을 설명해 주세요?", "좋은 도구를 도입해서 많이 좋아졌습니다.", [3,1,2,1,1,1], "vague", ["도구 도입 주장"], ["도구", "도입 행동", "측정 결과"]),
        ("POOR", "NEXT", "협업", "갈등을 해결한 경험을 설명해 주세요?", "갈등은 있었지만 서로 이해해서 끝났습니다.", [3,1,2,1,1,1], "vague", ["갈등 존재"], ["갈등 내용", "본인 행동", "합의 결과"]),
        ("POOR", "FOLLOW_UP", "개인 기여", "본인이 직접 맡은 역할은 무엇인가요?", "여러 가지 일을 열심히 했습니다.", [2,1,1,1,1,1], "role_clarity", [], ["구체적인 역할", "행동", "결과"]),
        ("POOR", "FOLLOW_UP", "결과 확인", "구체적으로 어떤 결과가 있었나요?", "결과는 성공적이었습니다.", [3,1,2,1,1,1], "result_clarity", ["성공 주장"], ["측정 방법", "구체적인 결과"]),
        ("POOR", "FOLLOW_UP", "기술 판단", "왜 그 기술을 선택했나요?", "유명하고 좋아 보여서 선택했습니다.", [3,1,2,1,1,1], "decision_rationale", ["인지도"], ["요구사항", "대안 비교", "선택 결과"]),
        ("POOR", "FOLLOW_UP", "장애 행동", "그때 본인이 직접 한 조치는 무엇인가요?", "팀에서 알아서 처리했습니다.", [2,1,2,1,1,1], "action_clarity", [], ["본인 행동", "판단", "결과"]),
    ]
    fields = ("relevance", "specificity", "logical_structure", "role_clarity", "action_clarity", "result_clarity")
    cases: list[dict[str, Any]] = []
    for index, spec in enumerate(specs, start=1):
        quality, qtype, competency, question, answer, raw_scores, weakness, evidence, missing = spec
        history = []
        if qtype == "FOLLOW_UP":
            history = [{"question": f"{competency} 경험을 설명해 주세요?", "answer": "관련 경험이 있지만 설명이 충분하지 않았습니다.", "competency": competency}]
        cases.append({
            "inputs": {
                "current_question": question, "current_answer": answer,
                "current_competency": competency, "question_type": qtype,
                "interview_strategy": {"competencies": [{"competency": competency, "verification_points": ["상황", "본인 역할", "행동", "결과"], "question_direction": f"{competency} 검증"}]},
                "evaluation_history": history,
            },
            "reference_outputs": {
                "quality_label": quality,
                "reference_scores": dict(zip(fields, raw_scores)),
                "reference_source": "rubric_authored",
                "expected_evidence": evidence,
                "expected_missing_points": missing,
                "reference_notes": f"주요 진단 항목: {weakness}",
            },
            "metadata": {
                "case_id": f"ae-holdout-{quality.lower()}-{index:02d}",
                "suite": "final_holdout", "dataset_version": "v1",
                "quality": quality, "question_type": qtype, "weakness": weakness,
                "reference_review_status": "pending_owner_review",
            },
        })
    return cases


def router_input(
    score: float | None,
    *,
    missing: list[str] | None = None,
    competencies: list[str] | None = None,
    current_index: int = 0,
    question_count: int = 1,
    current_followups: int = 0,
    other_followups: int = 0,
    dimension_score: int | None = None,
) -> dict[str, Any]:
    competencies = competencies or ["기술 역량", "협업 역량"]
    current = competencies[current_index]
    evaluation: dict[str, Any] = {"missing_points": missing or []}
    if score is not None:
        evaluation["overall_score"] = score
    elif dimension_score is not None:
        evaluation["scores"] = {
            "relevance": dimension_score, "specificity": dimension_score,
            "logical_structure": dimension_score, "role_clarity": dimension_score,
            "action_clarity": dimension_score, "result_clarity": dimension_score,
        }
    history: list[dict[str, Any]] = []
    for index in range(current_index + 1):
        history.append({"competency": competencies[index], "question_type": "INITIAL"})
    for _ in range(other_followups):
        history.append({"competency": competencies[0], "question_type": "FOLLOW_UP"})
    for _ in range(current_followups):
        history.append({"competency": current, "question_type": "FOLLOW_UP"})
    return {
        "current_evaluation": evaluation, "current_competency": current,
        "target_competencies": competencies, "interview_history": history,
        "question_count": max(question_count, len(history)),
        "followup_count": current_followups + other_followups,
    }


def build_router_holdout() -> list[dict[str, Any]]:
    specs: list[tuple[str, str, dict[str, Any], bool]] = [
        ("FOLLOW_UP", "score_69_with_room", router_input(69), True),
        ("FOLLOW_UP", "score_70_with_missing", router_input(70, missing=["결과"]), True),
        ("FOLLOW_UP", "score_100_with_missing", router_input(100, missing=["본인 역할"]), True),
        ("FOLLOW_UP", "minimum_score", router_input(20), True),
        ("FOLLOW_UP", "one_followup_used", router_input(63, current_followups=1, question_count=2), True),
        ("FOLLOW_UP", "one_extra_slot", router_input(55, competencies=["A", "B", "C"], question_count=7), True),
        ("FOLLOW_UP", "last_competency_missing", router_input(85, missing=["성과"], current_index=1, question_count=2), False),
        ("FOLLOW_UP", "derived_score_low", router_input(None, dimension_score=3), True),
        ("FOLLOW_UP", "other_competency_followups_do_not_block", router_input(60, competencies=["A", "B", "C"], current_index=1, other_followups=2, question_count=4), True),
        ("FOLLOW_UP", "score_below_threshold_without_missing", router_input(69.9), True),
        ("NEXT", "score_exactly_70", router_input(70), True),
        ("NEXT", "score_100_remaining", router_input(100), False),
        ("NEXT", "followup_limit_reached", router_input(50, missing=["결과"], current_followups=2, question_count=3), True),
        ("NEXT", "slots_equal_remaining", router_input(50, competencies=["A", "B", "C"], question_count=8), True),
        ("NEXT", "question_count_9_with_remaining", router_input(60, question_count=9), True),
        ("NEXT", "sufficient_with_remaining", router_input(82), False),
        ("NEXT", "missing_but_no_spare_slot", router_input(75, missing=["측정"], competencies=["A", "B", "C"], question_count=8), True),
        ("NEXT", "derived_score_sufficient", router_input(None, dimension_score=4), True),
        ("NEXT", "global_followups_do_not_equal_current_limit", router_input(80, competencies=["A", "B", "C"], current_index=1, other_followups=2, question_count=4), False),
        ("NEXT", "current_answer_sufficient_after_one_followup", router_input(78, current_followups=1, question_count=2), False),
        ("END", "question_count_10_precedence", router_input(40, missing=["전체"], question_count=10), True),
        ("END", "question_count_above_limit", router_input(90, question_count=11), True),
        ("END", "all_competencies_sufficient", router_input(80, current_index=1, question_count=2), False),
        ("END", "last_competency_followup_limit", router_input(60, missing=["성과"], current_index=1, current_followups=2, question_count=4), True),
        ("END", "single_competency_score_70", router_input(70, competencies=["문제 해결"]), True),
        ("END", "single_competency_low_after_limit", router_input(69, competencies=["문제 해결"], current_followups=2, question_count=3), True),
        ("END", "single_competency_high", router_input(95, competencies=["보안"]), False),
        ("END", "last_competency_derived_sufficient", router_input(None, competencies=["데이터"], dimension_score=4), True),
        ("END", "max_count_overrides_available_competency", router_input(55, missing=["결과"], competencies=["A", "B", "C"], question_count=10), True),
        ("END", "last_competency_sufficient_after_followup", router_input(76, competencies=["A", "B"], current_index=1, current_followups=1, question_count=3), False),
    ]
    route_numbers = {"FOLLOW_UP": 0, "NEXT": 0, "END": 0}
    cases: list[dict[str, Any]] = []
    for expected, scenario, inputs, boundary in specs:
        route_numbers[expected] += 1
        cases.append({
            "inputs": inputs,
            "reference_outputs": {
                "expected_route": expected, "scenario": scenario,
                "is_boundary": boundary,
                "expected_reason": "고정된 Router 정책과 경계 조건에 따른 기대 Route",
            },
            "metadata": {
                "case_id": f"router-holdout-{expected.lower().replace('_', '-')}-{route_numbers[expected]:02d}",
                "suite": "final_holdout", "dataset_version": "v1",
                "route": expected, "scenario": scenario, "is_boundary": boundary,
            },
        })
    return cases


def main() -> None:
    build_regression_sets()
    write_jsonl(
        EVALS / "question_generation" / "datasets" / "final_holdout_v1.jsonl",
        build_question_holdout(),
    )
    write_jsonl(
        EVALS / "answer_evaluation" / "datasets" / "final_holdout_v1.jsonl",
        build_answer_holdout(),
    )
    write_jsonl(
        EVALS / "router" / "datasets" / "final_holdout_v1.jsonl",
        build_router_holdout(),
    )
    print("평가 Dataset 생성 완료")


if __name__ == "__main__":
    main()
