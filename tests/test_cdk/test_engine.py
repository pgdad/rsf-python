"""Tests for CDK Jinja2 template engine."""

from rsf.cdk.engine import create_cdk_environment, render_cdk_template


class TestCDKEngine:
    """Tests for CDK template rendering engine."""

    def test_render_cdk_template_basic(self):
        """Engine renders app.py.j2 with correct variable substitution."""
        result = render_cdk_template(
            "app.py.j2",
            workflow_name="MyWorkflow",
            stack_class_name="RsfStack",
            stack_id="rsf-my-workflow",
        )
        assert "RsfStack" in result
        assert "rsf-my-workflow" in result
        assert "app.synth()" in result
        assert "import aws_cdk as cdk" in result

    def test_render_cdk_template_uses_standard_delimiters(self):
        """Engine uses standard Jinja2 delimiters (not HCL custom ones)."""
        env = create_cdk_environment()
        # Standard delimiters should be the defaults
        assert env.variable_start_string == "{{"
        assert env.variable_end_string == "}}"
        assert env.block_start_string == "{%"
        assert env.block_end_string == "%}"

    def test_render_cdk_json_template(self):
        """Engine renders cdk_json.j2 correctly."""
        result = render_cdk_template("cdk_json.j2")
        assert '"app": "python3 app.py"' in result
        assert '"watch"' in result

    def test_render_requirements_template(self):
        """Engine renders requirements.txt.j2 correctly."""
        result = render_cdk_template("requirements.txt.j2")
        assert "aws-cdk-lib>=2.0.0" in result
        assert "constructs>=10.0.0" in result
