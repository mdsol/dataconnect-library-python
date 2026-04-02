def test_import():
    import python_template

    # assert that this module has a name so autoflake doesn't remove the import
    assert python_template.__name__
