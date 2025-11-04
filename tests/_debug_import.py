def test_debug_import():
    import researcharr

    print("package file:", researcharr.__file__)
    print("has attr researcharr:", hasattr(researcharr, "researcharr"))
    mod = getattr(researcharr, "researcharr", None)
    print("nested module:", mod)
    print("nested init_db:", getattr(mod, "init_db", None))
    assert True
