"""FastAPI 엔드포인트. 담당: 현선

프론트(React)가 이 계약만 보고 개발할 수 있도록 먼저 고정한다.
"""
# POST /api/inquiry        {question, student_id}        -> answer_result.json
# GET  /api/student/{id}                                 -> student_profile.json
# GET  /api/evidence/{chunk_id}                          -> chunk_metadata.json + text
# POST /api/inquiry/{id}/review  {action: approve|edit|escalate, text?}
# GET  /api/inquiries?status=...                         -> 처리 이력 (S3 화면)
