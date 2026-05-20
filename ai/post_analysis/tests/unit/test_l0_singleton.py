"""PA-L0-SNG: Singleton."""

from common.singleton import Singleton


def test_pa_l0_sng_001_same_class_same_instance() -> None:
    class A(metaclass=Singleton):
        def __init__(self) -> None:
            self.value = 1

    assert A() is A()


def test_pa_l0_sng_002_different_classes_different_instances() -> None:
    class A(metaclass=Singleton):
        pass

    class B(metaclass=Singleton):
        pass

    assert A() is not B()
