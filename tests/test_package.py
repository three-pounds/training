import threepounds_training


def test_version_is_semver_string():
    parts = threepounds_training.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
