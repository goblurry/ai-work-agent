"""기존 기능 단위 테스트는 인증 의존성을 분리하고, test_auth는 실제 로그인으로 검증한다."""
import pytest


@pytest.fixture(autouse=True)
def demo_accounts_and_workflow_dependencies(request, monkeypatch):
    monkeypatch.setenv('DEMO_STUDENT_USERNAME', 'student')
    monkeypatch.setenv('DEMO_STUDENT_PASSWORD', 'student-test-password')
    monkeypatch.setenv('DEMO_STAFF_USERNAME', 'staff')
    monkeypatch.setenv('DEMO_STAFF_PASSWORD', 'staff-test-password')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('COOKIE_SAMESITE', 'lax')
    if request.path.name not in {'test_inquiries.py','test_student_flow.py','test_compose_reply.py','test_intake.py','test_agent.py'}:
        return
    original = request.module.create_app
    def workflow_app(*args, **kwargs):
        app = original(*args, **kwargs)
        auth = app.state.auth
        app.dependency_overrides[auth.require_student] = lambda: auth.user_by_username('student')
        app.dependency_overrides[auth.require_staff] = lambda: auth.user_by_username('staff')
        return app
    monkeypatch.setattr(request.module, 'create_app', workflow_app)
